from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_homepage_renders_profile_shell():
    response = client.get('/')
    assert response.status_code == 200
    assert 'Career Platform' in response.text
