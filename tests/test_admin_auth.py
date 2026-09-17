from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_admin_requires_login():
    response = client.get('/admin')
    assert response.status_code in (302, 401)
