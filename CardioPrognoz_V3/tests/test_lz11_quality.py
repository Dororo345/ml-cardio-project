"""LZ11: deterministic data and regression of critical acceptance journeys."""

from unittest.mock import patch

import pytest

from accounts import create_user, init_db
from app import app
from feature_contract import InputError, normalize_values
from integration import EXTERNAL_COLUMNS, read_csv_bytes, to_model_fields
from mock_medical_service import RECORDS
from qa_data import generate_csv


@pytest.fixture
def browser_client(tmp_path):
    app.config.update(TESTING=True, DATABASE=str(tmp_path / "lz11.sqlite3"))
    with app.app_context():
        init_db()
        create_user("uat_doctor", "SyntheticPassword123!")
    with app.test_client() as client:
        yield client


def csrf_token(client):
    with client.session_transaction() as session:
        return session["csrf_token"]


def login(client):
    client.get("/login")
    return client.post("/login", data={
        "username": "uat_doctor", "password": "SyntheticPassword123!",
        "csrf_token": csrf_token(client),
    })


def test_generator_reproducible_with_a_fixed_seed():
    first = generate_csv(seed=11011)
    assert first == generate_csv(seed=11011)
    assert first != generate_csv(seed=11012)
    assert len(first) <= 64 * 1024


def test_45_valid_and_5_invalid_synthetic_rows():
    data = generate_csv(seed=11011)
    header = data.decode("utf-8").splitlines()[0].split(",")
    assert tuple(header) == EXTERNAL_COLUMNS
    assert not set(header) & {"patient_name", "passport", "email", "phone"}
    parsed = read_csv_bytes(data)
    assert len(parsed) == 50
    valid, invalid = [], []
    for line_number, values, structural_error in parsed:
        try:
            if structural_error:
                raise ValueError(structural_error)
            normalize_values(values, tuple(to_model_fields(RECORDS["SYN-001"]).keys()))
            valid.append(line_number)
        except (InputError, ValueError):
            invalid.append(line_number)
    assert len(valid) == 45
    assert invalid == [11, 21, 31, 41, 51]


def test_invalid_generator_configuration_is_rejected():
    with pytest.raises(ValueError, match="between"):
        generate_csv(rows=51)
    with pytest.raises(ValueError, match="existing"):
        generate_csv(rows=3, invalid_rows=(4,))


def test_unauthenticated_routes_remain_protected(browser_client):
    for path in ("/", "/integration", "/integration/sample.csv", "/admin"):
        response = browser_client.get(path)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")
    assert browser_client.post("/predict", json={"age": 59}).status_code == 401


def test_csrf_session_rotation_and_authenticated_mock(browser_client):
    assert login(browser_client).status_code == 302
    # Successful login clears the anonymous session. Opening the next form
    # generates its new CSRF token; replay of the old token must be rejected.
    browser_client.get("/integration")
    fresh = csrf_token(browser_client)
    with patch("integration.fetch_mock_record", return_value=to_model_fields(RECORDS["SYN-001"])):
        assert browser_client.post("/integration/mock", data={
            "record_id": "SYN-001", "csrf_token": "outdated-token",
        }).status_code == 400
        assert browser_client.post("/integration/mock", data={
            "record_id": "SYN-001", "csrf_token": fresh,
        }).status_code == 200


def test_logout_revokes_access_to_prediction(browser_client):
    assert login(browser_client).status_code == 302
    browser_client.get("/")
    assert browser_client.post("/logout", data={"csrf_token": csrf_token(browser_client)}).status_code == 302
    assert browser_client.post("/predict", json={"age": 59}).status_code == 401
