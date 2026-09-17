from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_about_page_renders():
    response = client.get('/about')
    assert response.status_code == 200
