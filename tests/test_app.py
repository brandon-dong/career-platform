from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_homepage_renders_when_no_profile_is_published():
    response = client.get('/')
    assert response.status_code == 200
    assert 'Profile not published yet.' in response.text
