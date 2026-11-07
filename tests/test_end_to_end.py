"""HTTP transport tests against a live local Flask/Werkzeug server."""
import json
import threading
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import pytest
from werkzeug.serving import make_server
from app import app
from test_mvp import BASE_CASE

@pytest.fixture
def live_url():
    server = make_server('127.0.0.1', 0, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown()
    thread.join(timeout=5)
    server.server_close()

@pytest.mark.parametrize('body,status,code', [
    (json.dumps(BASE_CASE), 200, None),
    (json.dumps({**BASE_CASE, 'age': -1}), 400, 'OUT_OF_RANGE'),
    ('x' * 17000, 413, 'PAYLOAD_TOO_LARGE'),
])
def test_real_http_prediction(live_url, body, status, code):
    request = Request(live_url+'/predict', data=body.encode(), headers={'Content-Type':'application/json'})
    try:
        response = urlopen(request, timeout=10)
    except HTTPError as error:
        response = error
    with response:
        assert response.status == status
        result = json.load(response)
        assert result['request_id'] == response.headers['X-Request-ID']
        assert response.headers['Cache-Control'] == 'no-store'
    if status == 200:
        assert abs(result['probability_percent']-20.93) < .05
        assert len(result['factors']) == 3
        assert result['warning']
    else:
        assert result['code'] == code
        assert not {'probability','predicted_class','factors'} & result.keys()
