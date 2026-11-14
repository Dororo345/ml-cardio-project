"""Version 3: *synthetic only* medical-system adapter and CSV importer.

The upstream URL is fixed to a local mock. No user-controlled network address,
patient identifiers, database import, or live medical integration is supported.
"""
from __future__ import annotations

import csv
import io
import json
import re
import urllib.error
import urllib.request

MOCK_BASE_URL = "http://127.0.0.1:5001/api/v1/records"
MAX_UPLOAD_BYTES = 64 * 1024
MAX_ROWS = 50

# Documented external test contract. No name, birth date, phone, passport etc.
EXTERNAL_TO_MODEL = {
    "age_years": "age",
    "sex_code": "sex",
    "chest_pain_code": "cp",
    "resting_bp": "trestbps",
    "cholesterol": "chol",
    "fasting_sugar_flag": "fbs",
    "rest_ecg_code": "restecg",
    "max_heart_rate": "thalach",
    "exercise_angina_flag": "exang",
    "st_depression": "oldpeak",
    "st_slope_code": "slope",
    "vessels_code": "ca",
    "thal_code": "thal",
}
EXTERNAL_COLUMNS = tuple(EXTERNAL_TO_MODEL)
MOCK_ID_PATTERN = re.compile(r"^SYN-\d{3}$")


class IntegrationError(ValueError):
    pass


def to_model_fields(measurements):
    if not isinstance(measurements, dict):
        raise IntegrationError("Показатели должны быть объектом с именованными полями.")
    keys = set(measurements)
    unknown = sorted(keys - set(EXTERNAL_COLUMNS))
    missing = sorted(set(EXTERNAL_COLUMNS) - keys)
    if unknown:
        raise IntegrationError("Неразрешённые поля: " + ", ".join(unknown))
    if missing:
        raise IntegrationError("Отсутствуют поля: " + ", ".join(missing))
    return {dst: measurements[src] for src, dst in EXTERNAL_TO_MODEL.items()}


def fetch_mock_record(record_id):
    if not MOCK_ID_PATTERN.fullmatch(record_id):
        raise IntegrationError("Доступны только синтетические ID формата SYN-001.")
    req = urllib.request.Request(f"{MOCK_BASE_URL}/{record_id}", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.status != 200:
                raise IntegrationError("Тестовая запись не найдена.")
            payload = json.loads(response.read(8192))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise IntegrationError("Тестовая запись не найдена.") from None
        raise IntegrationError("Тестовый сервис ответил с ошибкой.") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise IntegrationError("Локальный mock-сервис недоступен. Запустите python mock_medical_service.py.") from None
    except (json.JSONDecodeError, UnicodeError):
        raise IntegrationError("Тестовый сервис прислал неверный JSON.") from None

    if not isinstance(payload, dict) or set(payload) != {"record_id", "measurements"}:
        raise IntegrationError("Ответ mock-сервиса не соответствует контракту.")
    if payload["record_id"] != record_id:
        raise IntegrationError("Идентификатор тестовой записи не совпал.")
    return to_model_fields(payload["measurements"])


def read_csv_bytes(raw):
    if not raw:
        raise IntegrationError("Выберите CSV-файл с учебными данными.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise IntegrationError("Файл слишком большой. Лимит — 64 КБ.")
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeError:
        raise IntegrationError("Требуется CSV в кодировке UTF-8.") from None
    try:
        csv_reader = csv.DictReader(io.StringIO(decoded, newline=""), strict=True)
        header = csv_reader.fieldnames or []
        if len(header) != len(set(header)):
            raise IntegrationError("В заголовке CSV повторяются поля.")
        unknown = sorted(set(header) - set(EXTERNAL_COLUMNS))
        missing = sorted(set(EXTERNAL_COLUMNS) - set(header))
        if unknown:
            raise IntegrationError("Файл отклонён: неразрешённые поля: " + ", ".join(str(x) for x in unknown))
        if missing:
            raise IntegrationError("Файл отклонён: отсутствуют поля: " + ", ".join(missing))
        rows = []
        for line_number, row in enumerate(csv_reader, start=2):
            if len(rows) >= MAX_ROWS:
                raise IntegrationError("Максимум 50 строк данных в одном файле.")
            if None in row or any(value is None for value in row.values()):
                rows.append((line_number, None, "Число колонок не соответствует заголовку."))
                continue
            try:
                rows.append((line_number, to_model_fields(row), None))
            except IntegrationError as exc:
                rows.append((line_number, None, str(exc)))
    except (csv.Error, UnicodeError):
        raise IntegrationError("CSV имеет некорректную структуру.") from None
    if not rows:
        raise IntegrationError("В CSV нет строк с данными.")
    return rows
