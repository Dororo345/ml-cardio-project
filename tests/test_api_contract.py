import pytest
import app as service
from test_mvp import BASE_CASE

@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_model_output(monkeypatch, value):
    monkeypatch.setattr(service.model, "predict_proba", lambda frame: [[0, value]])
    response = service.app.test_client().post("/predict", json=BASE_CASE)
    assert response.status_code == 500
    assert response.json["code"] == "PREDICTION_ERROR"
    assert "probability" not in response.json

def test_exception_does_not_leak_input(monkeypatch, caplog):
    marker = "SENSITIVE_SYNTHETIC_MARKER"
    def fail(frame):
        raise ValueError(marker)
    monkeypatch.setattr(service.model, "predict_proba", fail)
    response = service.app.test_client().post("/predict", json=BASE_CASE)
    assert response.status_code == 500
    assert marker not in response.get_data(as_text=True)
    assert marker not in caplog.text
    assert response.json["request_id"] == response.headers["X-Request-ID"]

@pytest.mark.parametrize("data", ['{broken', 'null', '[]'])
def test_bad_json(data):
    response = service.app.test_client().post("/predict", data=data, content_type="application/json")
    assert response.status_code == 400
    assert response.json["code"] == "INVALID_PAYLOAD"
    assert "probability" not in response.json
