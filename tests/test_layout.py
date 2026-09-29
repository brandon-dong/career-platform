import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PAGES = ['/', '/about', '/experience', '/projects', '/skills', '/credentials', '/contact']
BANNER = 'Profile view is in fallback mode while the database is unavailable.'


@pytest.mark.parametrize('path', PAGES)
def test_every_page_has_header_with_name_and_nav(seeded, path):
    response = client.get(path)
    assert response.status_code == 200
    assert '<a class="site-name" href="/">Test Person</a>' in response.text
    for href in PAGES:
        assert f'href="{href}"' in response.text
    assert BANNER not in response.text


def test_current_page_is_marked_in_nav(seeded):
    response = client.get('/skills')
    assert '<a href="/skills" aria-current="page">Skills</a>' in response.text
    assert response.text.count('aria-current="page"') == 1


@pytest.mark.parametrize('path', PAGES)
def test_every_page_survives_database_failure(broken_db, path):
    response = client.get(path)
    assert response.status_code == 200
    assert BANNER in response.text
    assert 'database unavailable' not in response.text


@pytest.mark.parametrize('path', PAGES)
def test_every_page_shows_fallback_when_no_profile(path):
    response = client.get(path)
    assert response.status_code == 200
    assert BANNER in response.text
