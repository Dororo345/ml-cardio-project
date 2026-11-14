"""Acceptance checks for CARD-19 (mock adapter) and CARD-20 (CSV import)."""
import csv
import io
from unittest.mock import patch

import pytest

from accounts import create_user, init_db
from app import app
from integration import EXTERNAL_COLUMNS, IntegrationError, read_csv_bytes, to_model_fields
from mock_medical_service import RECORDS

PASSWORD = "TestPassword123!"


@pytest.fixture
def client(tmp_path):
    app.config.update(TESTING=True, DATABASE=str(tmp_path / "v3.sqlite3"))
    with app.app_context():
        init_db()
        create_user("doctor", PASSWORD)
    with app.test_client() as tc:
        tc.get("/login")
        with tc.session_transaction() as sess:
            token = sess["csrf_token"]
        assert tc.post("/login", data={"username": "doctor", "password": PASSWORD, "csrf_token": token}).status_code == 302
        tc.get("/integration")  # Render the form to obtain the new post-login CSRF token.
        yield tc


def csrf(client):
    with client.session_transaction() as sess:
        return sess["csrf_token"]


def sample_csv(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=EXTERNAL_COLUMNS)
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def test_external_mapping_matches_existing_model_features():
    from app import FEATURES
    mapped = to_model_fields(RECORDS["SYN-001"])
    assert set(mapped) == set(FEATURES)
    assert mapped["age"] == 59
    assert mapped["trestbps"] == 138


def test_unknown_external_fields_are_rejected():
    with pytest.raises(IntegrationError, match="Неразрешённые поля"):
        to_model_fields({**RECORDS["SYN-001"], "passport": "DUMMY"})
    data = sample_csv([RECORDS["SYN-001"]])
    changed = data.replace(b"age_years,", b"passport,", 1)
    with pytest.raises(IntegrationError, match="неразрешённые поля"):
        read_csv_bytes(changed)


def test_csv_handles_good_bad_and_trailing_rows():
    r = read_csv_bytes(sample_csv([
        RECORDS["SYN-001"],
        {**RECORDS["SYN-001"], "age_years": "not-an-age"},
    ]))
    assert len(r) == 2
    assert r[0][0] == 2 and r[1][0] == 3
    assert r[0][1]["age"] == "59" and r[1][1]["age"] == "not-an-age"


def test_csv_rejects_more_than_50_rows():
    with pytest.raises(IntegrationError, match="Максимум 50"):
        read_csv_bytes(sample_csv([RECORDS["SYN-001"]] * 51))


def test_mock_fetch_and_scoring(client):
    with patch("integration.fetch_mock_record", return_value=to_model_fields(RECORDS["SYN-001"])):
        res = client.post("/integration/mock", data={"record_id": "SYN-001", "csrf_token": csrf(client)})
    assert res.status_code == 200
    content = res.get_data(as_text=True)
    assert "SYN-001" in content
    assert "Все 13 полей успешно сопоставлены" in content


def test_mock_offline_message(client):
    with patch("integration.fetch_mock_record", side_effect=IntegrationError("Локальный mock-сервис недоступен")):
        res = client.post("/integration/mock", data={"record_id": "SYN-001", "csrf_token": csrf(client)})
    assert res.status_code == 400
    assert "mock-сервис недоступен" in res.get_data(as_text=True)


def test_upload_per_row_results(client):
    data = sample_csv([RECORDS["SYN-001"], {**RECORDS["SYN-002"], "age_years": "-1"}])
    res = client.post("/integration/import", data={
        "csrf_token": csrf(client), "file": (io.BytesIO(data), "synthetic.csv")
    }, content_type="multipart/form-data")
    assert res.status_code == 200
    text = res.get_data(as_text=True)
    assert "Пройдено" in text
    assert "Выход за пределы: age" in text


def test_upload_unknown_columns_rejected(client):
    data = sample_csv([RECORDS["SYN-001"]]).replace(b"age_years,", b"patient_name,", 1)
    res = client.post("/integration/import", data={
        "csrf_token": csrf(client), "file": (io.BytesIO(data), "not_allowed.csv")
    }, content_type="multipart/form-data")
    assert res.status_code == 400
    assert "неразрешённые поля" in res.get_data(as_text=True)


def test_csrf_and_login_required(client):
    assert client.post("/integration/import").status_code == 400
    assert client.get("/integration/sample.csv").status_code == 200
    client.post("/logout", data={"csrf_token": csrf(client)})
    assert client.get("/integration").status_code == 302
    assert client.post("/integration/mock").status_code == 302
    assert client.get("/integration/sample.csv").status_code == 302
