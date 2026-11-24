"""Run all 13 LZ11 UAT journeys against a disposable local HTTP test stand.

This is a developer-operated technical self-check, NOT independent human UAT.
It exercises real HTTP routes, forms, cookies and a live local mock service;
HTML5 validation is checked via markup because no graphical browser is used.
Only synthetic data and a temporary SQLite database are used.

Run from CardioPrognoz_V3:
    python scripts/lz11_uat_selfcheck.py --output ../docs/qa/evidence/lz11-uat-selfcheck-20261124.json
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer

import httpx
from lxml import html
from werkzeug.serving import make_server

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from accounts import create_user, init_db
from app import app
from mock_medical_service import MockHandler
from qa_data import generate_csv


USER = "uat_self_user"
ADMIN = "uat_self_admin"
NEW_USER = "uat_self_created"
USER_PASSWORD = "LocalUatUser123!"
ADMIN_PASSWORD = "LocalUatAdmin123!"
NEW_PASSWORD = "LocalUatCreated123!"


def parse(response: httpx.Response):
    return html.fromstring(response.content)


def csrf(response: httpx.Response) -> str:
    tokens = parse(response).xpath("//input[@name='csrf_token']/@value")
    assert tokens, "Форма не содержит CSRF-токен"
    return tokens[0]


def login(client: httpx.Client, username: str, password: str) -> httpx.Response:
    form = client.get("/login")
    assert form.status_code == 200
    return client.post("/login", data={
        "username": username, "password": password, "csrf_token": csrf(form),
    })


def logout(client: httpx.Client) -> httpx.Response:
    form = client.get("/")
    assert form.status_code == 200
    return client.post("/logout", data={"csrf_token": csrf(form)})


def check(condition: bool, details: str) -> str:
    if not condition:
        raise AssertionError(details)
    return details


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    start = datetime.now(timezone.utc)
    results = []

    def scenario(number: int, label: str, execute, *, limitation: str | None = None) -> None:
        try:
            evidence = execute()
            state = "Пройдено технически"
            print(f"UAT-{number:02d}: PASS — {evidence}")
        except Exception as exc:
            evidence = f"{type(exc).__name__}: {exc}"
            state = "Не пройдено"
            print(f"UAT-{number:02d}: FAIL — {evidence}")
        results.append({
            "id": f"UAT-{number:02d}", "name": label, "result": state,
            "evidence": evidence, "limitation": limitation,
        })

    with tempfile.TemporaryDirectory(prefix="cardio-lz11-uat-") as temp_dir:
        app.config.update(TESTING=False, DATABASE=str(Path(temp_dir) / "accounts.sqlite3"))
        with app.app_context():
            init_db()
            create_user(USER, USER_PASSWORD, "user")
            create_user(ADMIN, ADMIN_PASSWORD, "admin")

        mock_server = ThreadingHTTPServer(("127.0.0.1", 5001), MockHandler)
        mock_thread = threading.Thread(target=mock_server.serve_forever, daemon=True)
        mock_thread.start()
        server = make_server("127.0.0.1", 0, app, threaded=True)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        url = f"http://127.0.0.1:{server.server_port}"
        try:
            def session():
                return httpx.Client(base_url=url, follow_redirects=False,
                                    trust_env=False, timeout=10)

            with session() as doctor, session() as administrator, session() as created:
                def uat01():
                    before = doctor.get("/")
                    signed = login(doctor, USER, USER_PASSWORD)
                    page = doctor.get("/")
                    return check(before.status_code == 302
                                 and signed.status_code == 302
                                 and page.status_code == 200
                                 and 'id="predictionForm"' in page.text,
                                 "Вход HTTP 302; форма прогнозирования HTTP 200")

                scenario(1, "Успешный вход", uat01)

                def uat02():
                    out = logout(doctor)
                    bad = login(doctor, USER, "WrongPassword999!")
                    protected = doctor.get("/")
                    return check(out.status_code == 302 and bad.status_code == 200
                                 and "Неверный логин или пароль" in bad.text
                                 and protected.status_code == 302,
                                 "Неверный пароль: сообщение есть, доступа нет")

                scenario(2, "Неверный пароль", uat02)

                def ensure_user():
                    signed = login(doctor, USER, USER_PASSWORD)
                    assert signed.status_code == 302

                ensure_user()
                valid = {
                    "age": 59, "sex": 1, "cp": 4, "trestbps": 138,
                    "chol": 271, "fbs": 0, "restecg": 2, "thalach": 182,
                    "exang": 0, "oldpeak": 0, "slope": 1, "ca": 0, "thal": 3,
                }

                def uat03():
                    page = doctor.get("/")
                    response = doctor.post("/predict", json=valid)
                    payload = response.json()
                    p = payload.get("probability_percent")
                    return check(response.status_code == 200
                                 and isinstance(p, (int, float)) and 0 <= p <= 100
                                 and "Учебный прогноз" in payload.get("warning", "")
                                 and "не является" in page.text,
                                 f"Модель HTTP 200, вероятность {p}%, учебное предупреждение")

                scenario(3, "Расчёт 13 показателей", uat03)

                def uat04():
                    page = parse(doctor.get("/"))
                    age = page.xpath("//input[@id='age']")[0]
                    missing = dict(valid)
                    missing.pop("age")
                    response = doctor.post("/predict", json=missing)
                    return check(age.get("required") is not None
                                 and response.status_code == 400
                                 and "age" in json.dumps(response.json(), ensure_ascii=False),
                                 "HTML5 required; backend HTTP 400 без возраста")

                scenario(4, "Пустое обязательное поле", uat04,
                         limitation="Поведение встроенного сообщения браузера визуально не проверялось")

                def uat05():
                    page = parse(doctor.get("/"))
                    age = page.xpath("//input[@id='age']")[0]
                    invalid = dict(valid, age=-5)
                    response = doctor.post("/predict", json=invalid)
                    return check(age.get("min") == "18" and age.get("max") == "120"
                                 and response.status_code == 400
                                 and "error" in response.json(),
                                 "HTML5 диапазон 18–120; backend HTTP 400 для -5")

                scenario(5, "Неверный возраст", uat05,
                         limitation="Всплывающая подсказка браузера визуально не проверялась")

                def uat06():
                    denied = doctor.get("/admin")
                    return check(denied.status_code == 403
                                 and "uat_self_admin" not in denied.text,
                                 "Обычный пользователь: /admin отвечает HTTP 403")

                scenario(6, "Запрет доступа к администрированию", uat06)

                def uat07():
                    assert login(administrator, ADMIN, ADMIN_PASSWORD).status_code == 302
                    before = administrator.get("/admin")
                    created_response = administrator.post("/admin/users", data={
                        "username": NEW_USER, "password": NEW_PASSWORD,
                        "csrf_token": csrf(before),
                    })
                    after = administrator.get("/admin")
                    signed = login(created, NEW_USER, NEW_PASSWORD)
                    home = created.get("/")
                    return check(created_response.status_code == 302
                                 and NEW_USER in after.text
                                 and signed.status_code == 302
                                 and home.status_code == 200,
                                 "Администратор создал пользователя; новый логин работает")

                scenario(7, "Создание аккаунта администратором", uat07)

                def upload(client: httpx.Client, content: bytes, name: str) -> httpx.Response:
                    token = csrf(client.get("/integration"))
                    return client.post("/integration/import", data={"csrf_token": token},
                                       files={"file": (name, content, "text/csv")})

                def uat08():
                    sample = doctor.get("/integration/sample.csv")
                    assert sample.status_code == 200
                    res = upload(doctor, sample.content, "sample.csv")
                    return check(res.status_code == 200
                                 and "Результаты импорта" in res.text
                                 and "Строк:" in res.text,
                                 "Пример CSV скачан и обработан без общей ошибки")

                scenario(8, "Скачать и импортировать пример CSV", uat08)

                def uat09():
                    res = upload(doctor, generate_csv(seed=11011), "lz11_synthetic_50.csv")
                    rows = parse(res).xpath("//table[contains(@class,'account-table')]/tbody/tr")
                    bad_rows = [row.xpath("./td[1]/text()")[0].strip() for row in rows
                                if "Ошибка" in "".join(row.itertext())]
                    return check(res.status_code == 200
                                 and "Строк: 50; успешно: 45; с ошибками: 5" in res.text
                                 and bad_rows == ["11", "21", "31", "41", "51"],
                                 "50 строк: 45 приняты, 5 ошибок на строках 11/21/31/41/51")

                scenario(9, "45 правильных и 5 ошибочных строк", uat09)

                def uat10():
                    raw = generate_csv(seed=11011)
                    lines = raw.decode("utf-8").splitlines()
                    altered = (lines[0] + ",patient_name\n" + "\n".join(
                        line + ",SYNTHETIC" for line in lines[1:]) + "\n").encode("utf-8")
                    res = upload(doctor, altered, "forbidden_column.csv")
                    return check(res.status_code == 400 and "patient_name" in res.text
                                 and "неразрешённые поля" in res.text
                                 and "Результаты импорта" not in res.text,
                                 "Добавлен patient_name: файл целиком отвергнут (HTTP 400)")

                scenario(10, "Запрет персонального поля в CSV", uat10)

                def uat11():
                    token = csrf(doctor.get("/integration"))
                    res = doctor.post("/integration/mock", data={
                        "record_id": "SYN-001", "csrf_token": token,
                    })
                    rows = parse(res).xpath("//table[@id='synthetic-parameters']/tbody/tr")
                    return check(res.status_code == 200
                                 and "SYN-001" in res.text
                                 and "Все 13 полей" in res.text
                                 and len(rows) == 13 and "Модельная вероятность" in res.text,
                                 f"Mock HTTP 200; показаны {len(rows)} параметров и прогноз")

                scenario(11, "Получение SYN-001 и 13 значений", uat11)

                mock_server.shutdown()
                mock_server.server_close()
                mock_thread.join(timeout=5)

                def uat12():
                    token = csrf(doctor.get("/integration"))
                    res = doctor.post("/integration/mock", data={
                        "record_id": "SYN-001", "csrf_token": token,
                    })
                    return check(res.status_code == 400
                                 and "mock-сервис недоступен" in res.text
                                 and "Тестовая запись SYN-001" not in res.text,
                                 "Остановленный mock: HTTP 400, понятная ошибка без прогноза")

                scenario(12, "Mock-сервис недоступен", uat12)

                def uat13():
                    out = logout(doctor)
                    blocked = doctor.get("/integration")
                    return check(out.status_code == 302
                                 and blocked.status_code == 302
                                 and blocked.headers["Location"].endswith("/login"),
                                 "После выхода /integration перенаправляет на /login")

                scenario(13, "Выход завершает сеанс", uat13)
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=5)
            if mock_thread.is_alive():
                mock_server.shutdown()
                mock_server.server_close()
                mock_thread.join(timeout=5)

    report = {
        "title": "ЛЗ 11: самостоятельный технический прогон 13 UAT-маршрутов",
        "started_at_utc": start.isoformat(timespec="seconds"),
        "finished_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tester": "ChatGPT / developer-operated technical self-check",
        "method": "Live local HTTP (Werkzeug + httpx + 127.0.0.1:5001 mock), isolated temporary SQLite, synthetic CSV; no GUI browser",
        "independent_user_acceptance": False,
        "results": results,
        "passed_technical": sum(item["result"] == "Пройдено технически" for item in results),
        "failed": sum(item["result"] == "Не пройдено" for item in results),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"RESULT {report['passed_technical']}/{len(results)} technical PASS; {report['failed']} failures; {args.output}")
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
