"""HTTP-level safety and error responses; requires Flask + the serialized model."""
import pytest
from app import app
from test_mvp import BASE_CASE

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c

def test_health_and_headers(client):
    res = client.get('/health')
    assert res.status_code == 200
    assert res.get_json()['status'] == 'ok'
    assert res.headers['X-Content-Type-Options'] == 'nosniff'
    assert res.headers['Cache-Control'] == 'no-store'
    assert res.headers['X-Request-ID']

@pytest.mark.parametrize('payload', [[], 'hello', None])
def test_reject_non_object(client, payload):
    res = client.post('/predict', json=payload)
    assert res.status_code == 400
    assert res.get_json()['code'] == 'INVALID_PAYLOAD'
    assert res.get_json()['request_id']

def test_reject_additional_field(client):
    res = client.post('/predict', json={**BASE_CASE, 'patient_name': 'No data allowed'})
    assert res.status_code == 400
    assert res.get_json()['code'] == 'UNEXPECTED_FIELDS'

def test_reject_large_payload(client):
    res = client.post('/predict', data='x'*17000, content_type='application/json')
    assert res.status_code == 413
    assert res.get_json()['code'] == 'PAYLOAD_TOO_LARGE'

def test_reject_non_json(client):
    res = client.post('/predict', data='age=59', content_type='application/x-www-form-urlencoded')
    assert res.status_code == 400
    assert res.get_json()['code'] == 'INVALID_PAYLOAD'
