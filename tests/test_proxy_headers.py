from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_stylesheet_url_uses_forwarded_https_scheme(seeded):
    html = client.get('/', headers={'X-Forwarded-Proto': 'https'}).text
    assert 'href="https://testserver/static/css/styles.css"' in html


def test_stylesheet_url_stays_http_without_proxy_header(seeded):
    html = client.get('/').text
    assert 'href="http://testserver/static/css/styles.css"' in html
