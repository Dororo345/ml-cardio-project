import app as service
from test_mvp import BASE_CASE

def test_xai_failure_preserves_prediction(monkeypatch, caplog):
    client = service.app.test_client()
    expected = client.post('/predict',json=BASE_CASE).json
    def fail(frame):
        raise RuntimeError('PRIVATE_SYNTHETIC_VALUE')
    monkeypatch.setattr(service.xai_explainer,'explain',fail)
    response=client.post('/predict',json=BASE_CASE)
    assert response.status_code==200
    assert response.json['probability']==expected['probability']
    assert response.json['factors']==[]
    assert response.json['xai_status']=='unavailable'
    assert response.json['xai_message']
    assert 'PRIVATE_SYNTHETIC_VALUE' not in caplog.text

def test_uninitialized_xai_is_safe(monkeypatch):
    monkeypatch.setattr(service,'xai_explainer',None)
    response=service.app.test_client().post('/predict',json=BASE_CASE)
    assert response.status_code==200
    assert response.json['factors']==[]
    assert response.json['xai_status']=='unavailable'
