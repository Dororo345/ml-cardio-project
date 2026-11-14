"""Synthetic acceptance evidence for LZ9; isolated SQLite and real local mock HTTP."""
import csv, io, threading
import pytest
from flask import template_rendered
from http.server import ThreadingHTTPServer
from accounts import create_user, init_db, get_db
from app import app
from integration import EXTERNAL_COLUMNS, IntegrationError, fetch_mock_record, to_model_fields
from mock_medical_service import MockHandler, RECORDS

@pytest.fixture
def client(tmp_path):
    app.config.update(TESTING=True, DATABASE=str(tmp_path/'audit.sqlite3'))
    with app.app_context():
        init_db();create_user('doctor','TestPassword123!')
    with app.test_client() as c:
        c.get('/login')
        with c.session_transaction() as s: token=s['csrf_token']
        assert c.post('/login',data={'username':'doctor','password':'TestPassword123!','csrf_token':token}).status_code==302
        c.get('/integration');yield c

def token(c):
    with c.session_transaction() as s:return s['csrf_token']

@pytest.fixture
def live_mock():
    server=ThreadingHTTPServer(('127.0.0.1',5001),MockHandler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield
    server.shutdown();thread.join();server.server_close()

@pytest.mark.parametrize('i',range(20))
def test_nft18_twenty_real_http_requests(live_mock,i):
    key=list(RECORDS)[i]
    assert len(RECORDS) == 20
    assert len({tuple(row.values()) for row in RECORDS.values()}) == 20
    assert fetch_mock_record(key)==to_model_fields(RECORDS[key])

def test_real_http_route_and_prediction(client,live_mock):
    r=client.post('/integration/mock',data={'csrf_token':token(client),'record_id':'SYN-001'})
    assert r.status_code==200
    assert '20.93%' in r.get_data(as_text=True)

def test_real_offline_adapter():
    with pytest.raises(IntegrationError,match='недоступен'):fetch_mock_record('SYN-001')

def test_nft19_45_valid_and_5_invalid_rows(client):
    rows=[dict(RECORDS['SYN-001']) for _ in range(50)]
    bad=[9,19,29,39,49]
    for i in bad:rows[i]['age_years']='-1'
    buf=io.StringIO();w=csv.DictWriter(buf,fieldnames=EXTERNAL_COLUMNS);w.writeheader();w.writerows(rows)
    captured=[]
    def receive(sender,template,context,**kw):captured.append(context)
    template_rendered.connect(receive,app)
    try:r=client.post('/integration/import',data={'csrf_token':token(client),'file':(io.BytesIO(buf.getvalue().encode()),'synthetic.csv')})
    finally:template_rendered.disconnect(receive,app)
    assert r.status_code==200
    results=captured[-1]['results']
    assert len(results)==50 and sum(x['ok'] for x in results)==45
    assert [x['line'] for x in results if not x['ok']]==[i+2 for i in bad]
    assert all(0<=x['score']['percent']<=100 for x in results if x['ok'])

def test_disabled_existing_session_is_revoked(client):
    with app.app_context():
        db=get_db();db.execute("UPDATE users SET active=0 WHERE username='doctor'");db.commit()
    assert client.get('/').status_code==302
    assert client.post('/predict',json={}).status_code==401

def test_password_hash_scheme_observed(client):
    with app.app_context():
        value=get_db().execute("SELECT password_hash FROM users WHERE username='doctor'").fetchone()[0]
        assert value.startswith('$argon2id$') and 'TestPassword123!' not in value


def test_ten_accounts_use_unique_argon2id_hashes(client):
    from accounts import verify_password
    with app.app_context():
        for i in range(10):create_user(f"hash_user_{i}", "SyntheticPassword123!")
        hashes=[r[0] for r in get_db().execute("SELECT password_hash FROM users WHERE username LIKE 'hash_user_%'")]
        assert len(hashes) == len(set(hashes)) == 10
        assert all(x.startswith("$argon2id$") and verify_password(x,"SyntheticPassword123!") for x in hashes)


def test_legacy_scrypt_account_upgrades_on_correct_login(client):
    from werkzeug.security import generate_password_hash
    with app.app_context():
        db=get_db();db.execute("UPDATE users SET password_hash=? WHERE username='doctor'",(generate_password_hash("TestPassword123!"),));db.commit()
    client.post('/logout', data={'csrf_token':token(client)})
    client.get('/login')
    result=client.post('/login',data={'username':'doctor','password':'wrong','csrf_token':token(client)})
    assert result.status_code==200
    with app.app_context():assert get_db().execute("SELECT password_hash FROM users WHERE username='doctor'").fetchone()[0].startswith('scrypt:')
    result=client.post('/login',data={'username':'doctor','password':'TestPassword123!','csrf_token':token(client)})
    assert result.status_code==302
    with app.app_context():assert get_db().execute("SELECT password_hash FROM users WHERE username='doctor'").fetchone()[0].startswith('$argon2id$')
