from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz_ok_when_profile_exists(seeded):
    response = client.get('/healthz')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_healthz_fails_when_database_is_empty():
    response = client.get('/healthz')
    assert response.status_code == 503
    assert response.json() == {'status': 'no profile'}


def test_healthz_fails_when_database_is_unreachable(broken_db):
    response = client.get('/healthz')
    assert response.status_code == 503
    assert response.json() == {'status': 'database unavailable'}
