"""Dependency-light checks for the server's strict feature validation."""
import pytest
from validation import validate_payload, ValidationError

FEATURES = [
    'age','sex','cp','trestbps','chol','fbs','restecg','thalach',
    'exang','oldpeak','slope','ca','thal',
]
VALID = {
    'age':59,'sex':1,'cp':4,'trestbps':138,'chol':271,'fbs':0,'restecg':2,
    'thalach':182,'exang':0,'oldpeak':0.,'slope':1,'ca':0,'thal':3,
}


def test_valid_case():
    assert validate_payload(VALID.copy(), FEATURES)['age'] == 59.0

@pytest.mark.parametrize('value', [None, 'a', '59', True, float('nan'), float('inf'), -1, 150, [], {}])
def test_invalid_age(value):
    with pytest.raises(ValidationError):
        validate_payload({**VALID, 'age': value}, FEATURES)

@pytest.mark.parametrize('field,value', [('cp',9),('chol',0),('oldpeak',8),('fbs',0.5),('age',59.5),('thal',99)])
def test_invalid_feature(field, value):
    with pytest.raises(ValidationError):
        validate_payload({**VALID, field:value}, FEATURES)

def test_missing_field():
    with pytest.raises(ValidationError) as err:
        validate_payload({'age':59}, FEATURES)
    assert err.value.code == 'MISSING_FIELDS'
    assert 'sex' in err.value.fields

def test_unexpected_field():
    with pytest.raises(ValidationError) as err:
        validate_payload({**VALID, 'secret': 'no'}, FEATURES)
    assert err.value.code == 'UNEXPECTED_FIELDS'

@pytest.mark.parametrize('payload',[None, [], 'hello', 3])
def test_invalid_body(payload):
    with pytest.raises(ValidationError):
        validate_payload(payload, FEATURES)
