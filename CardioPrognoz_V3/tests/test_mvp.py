
import math
import pytest
from app import app
from accounts import get_db, init_db

BASE_CASE = {
    "age": 59,
    "sex": 1,
    "cp": 4,
    "trestbps": 138,
    "chol": 271,
    "fbs": 0,
    "restecg": 2,
    "thalach": 182,
    "exang": 0,
    "oldpeak": 0.0,
    "slope": 1,
    "ca": 0,
    "thal": 3
}


@pytest.fixture
def client(tmp_path):
    app.config.update(TESTING=True, DATABASE=str(tmp_path / "mvp.sqlite3"))
    with app.app_context():
        init_db()
        db = get_db()
        db.execute(
            "INSERT INTO users (username, password_hash, role, active) VALUES (?, ?, ?, 1)",
            ("mvp_test_user", "test-only-no-password", "user"),
        )
        db.commit()
        user_id = db.execute("SELECT id FROM users WHERE username=?", ("mvp_test_user",)).fetchone()["id"]
    with app.test_client() as test_client:
        with test_client.session_transaction() as session:
            session["user_id"] = user_id
        yield test_client


def make_synthetic_case(i):
    return {
        "age": 40 + i % 40,
        "sex": i % 2,
        "cp": 1 + i % 4,
        "trestbps": 110 + (i * 3) % 60,
        "chol": 170 + (i * 7) % 140,
        "fbs": i % 2,
        "restecg": i % 3,
        "thalach": 100 + (i * 5) % 90,
        "exang": (i // 2) % 2,
        "oldpeak": round((i % 21) * 0.2, 1),
        "slope": 1 + i % 3,
        "ca": i % 4,
        "thal": [3, 6, 7][i % 3]
    }


@pytest.mark.parametrize("i", range(50))
def test_50_synthetic_cases(client, i):
    data = make_synthetic_case(i)

    response = client.post("/predict", json=data)

    assert response.status_code == 200

    result = response.get_json()

    probability = result["probability"]

    assert math.isfinite(probability)
    assert 0 <= probability <= 1
    assert result["predicted_class"] in [0, 1]
    assert len(result["factors"]) == 3

    assert all(
        factor["direction"] in [
            "увеличивает",
            "уменьшает",
            "не изменяет"
        ]
        for factor in result["factors"]
    )


def test_known_colab_prediction(client):
    response = client.post("/predict", json=BASE_CASE)

    assert response.status_code == 200

    result = response.get_json()

    assert abs(
        result["probability_percent"] - 20.93
    ) < 0.05

    assert result["predicted_class"] == 0


@pytest.mark.parametrize("field", BASE_CASE.keys())
def test_missing_required_field(client, field):
    data = BASE_CASE.copy()
    del data[field]

    response = client.post("/predict", json=data)

    assert response.status_code == 400


@pytest.mark.parametrize("field,value", [
    ("age", -5),
    ("age", 150),
    ("chol", -20),
    ("cp", 9),
    ("thal", 99),
    ("trestbps", "abc"),
    ("age", None)
])
def test_invalid_values(client, field, value):
    data = BASE_CASE.copy()
    data[field] = value

    response = client.post("/predict", json=data)

    assert response.status_code == 400
