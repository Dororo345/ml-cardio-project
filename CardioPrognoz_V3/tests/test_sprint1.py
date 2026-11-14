"""Sprint 1 acceptance checks for CARD-13, CARD-14 and CARD-17."""

import pytest
from flask import g

from accounts import create_user, get_db, init_db
from app import app
from validation import check_anomalies

PASSWORD = "TestPassword123!"


@pytest.fixture
def client(tmp_path):
    app.config.update(TESTING=True, DATABASE=str(tmp_path / "test.sqlite3"))
    with app.app_context():
        init_db()
        create_user("admin", PASSWORD, "admin")
        create_user("doctor", PASSWORD, "user")
    with app.test_client() as client:
        yield client


def login(client, username="doctor", password=PASSWORD):
    client.get("/login")
    with client.session_transaction() as sess:
        token = sess["csrf_token"]
    return client.post("/login", data={
        "username": username, "password": password, "csrf_token": token,
    }, follow_redirects=True)


def csrf(client):
    with client.session_transaction() as sess:
        return sess["csrf_token"]


def test_login_and_logout(client):
    response = login(client)
    assert "doctor" in response.get_data(as_text=True)
    assert client.post("/logout", data={"csrf_token": csrf(client)}).status_code == 302
    assert b"login" in client.get("/login").data.lower() or client.get("/login").status_code == 200


def test_wrong_login_does_not_reveal_account_presence(client):
    first = login(client, "doctor", "wrong-password").get_data(as_text=True)
    second = login(client, "unknown", "wrong-password").get_data(as_text=True)
    assert "Неверный логин или пароль" in first
    assert "Неверный логин или пароль" in second


def test_admin_page_is_restricted(client):
    assert client.get("/admin").status_code == 302
    login(client)
    assert client.get("/admin").status_code == 403


def test_admin_creates_and_disables_user(client):
    login(client, "admin")
    response = client.post("/admin/users", data={
        "username": "trainee", "password": PASSWORD, "csrf_token": csrf(client),
    }, follow_redirects=True)
    assert "trainee" in response.get_data(as_text=True)
    with app.app_context():
        row = get_db().execute("SELECT id, active FROM users WHERE username='trainee'").fetchone()
        trainee_id = row["id"]
        assert row["active"] == 1

    assert client.post(
        f"/admin/users/{trainee_id}/disable", data={"csrf_token": csrf(client)}
    ).status_code == 302
    with app.app_context():
        row = get_db().execute("SELECT active FROM users WHERE id=?", (trainee_id,)).fetchone()
        assert row["active"] == 0

    client.post("/logout", data={"csrf_token": csrf(client)})
    assert "Неверный логин или пароль" in login(client, "trainee").get_data(as_text=True)


def test_csrf_is_required(client):
    login(client, "admin")
    assert client.post("/admin/users", data={"username": "xuser", "password": PASSWORD}).status_code == 400
    assert client.post("/logout", data={}).status_code == 400


def test_usernames_are_unique_case_insensitively(client):
    login(client, "admin")
    response = client.post("/admin/users", data={
        "username": "DOCTOR", "password": PASSWORD, "csrf_token": csrf(client),
    }, follow_redirects=True)
    assert "Такой логин уже существует" in response.get_data(as_text=True)


def test_warning_does_not_modify_valid_input(client):
    login(client)
    sample = {
        "age": 59, "sex": 1, "cp": 4, "trestbps": 225, "chol": 500,
        "fbs": 0, "restecg": 2, "thalach": 182, "exang": 0,
        "oldpeak": 0.0, "slope": 1, "ca": 0, "thal": 3,
    }
    before = sample.copy()
    response = client.post("/predict", json=sample)
    assert response.status_code == 200
    result = response.get_json()
    assert result["warnings"]
    assert result["warnings"][0]["fields"] == ["trestbps", "chol"]
    assert sample == before
    assert 0 <= result["probability"] <= 1


def test_validation_non_diagnostic():
    assert check_anomalies({"trestbps": 120, "chol": 200, "age": 40, "thalach": 160}) == []
    warnings = check_anomalies({"trestbps": 225, "chol": 500, "age": 80, "thalach": 220})
    assert len(warnings) == 2


def test_unauthenticated_users_cannot_open_form_or_predict(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    response = client.post("/predict", json={"age": 60})
    assert response.status_code == 401
    assert "войти" in response.get_json()["error"]


def test_login_then_form_and_logout(client):
    response = login(client)
    assert "Ввод медицинских показателей" in response.get_data(as_text=True)
    assert client.get("/").status_code == 200

    response = client.post("/logout", data={"csrf_token": csrf(client)})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert client.get("/").status_code == 302
    assert client.post("/predict", json={"age": 60}).status_code == 401
