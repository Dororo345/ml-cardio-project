import hashlib
import re
import app as service
from test_mvp import BASE_CASE

def test_version_matches_model_bytes_and_metadata():
    digest=hashlib.sha256((service.BASE_DIR/'models'/'heart_model.joblib').read_bytes()).hexdigest()
    assert service.model_info['artifact_sha256']==digest
    assert service.MODEL_VERSION=='cleveland-logreg-1-'+digest[:12]
    assert re.fullmatch(r'[a-z0-9-]+',service.MODEL_VERSION)

def test_version_is_stable_and_additive():
    client=service.app.test_client()
    first=client.post('/predict',json=BASE_CASE).json
    second=client.post('/predict',json={**BASE_CASE,'age':60}).json
    assert first['model_version']==second['model_version']==service.MODEL_VERSION
    assert client.get('/health').json['model_version']==service.MODEL_VERSION
    assert {'probability','probability_percent','predicted_class','factors','warning','request_id'} <= first.keys()
