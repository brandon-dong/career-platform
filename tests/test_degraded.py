import pytest
from fastapi.testclient import TestClient

from app import main as app_main
from app.config import CONTACT_EMAIL
from app.main import app
from app.models import Profile

client = TestClient(app)

PAGES = ['/', '/about', '/experience', '/projects', '/skills', '/credentials', '/contact', '/privacy']
INVENTED = ['Career Platform', 'Analytics and Finance Professional', 'San Jose, CA', 'fallback']


@pytest.fixture
def profile_only(session_factory):
    db = session_factory()
    db.add(Profile(full_name='Test Person', headline='Test Headline', summary='Test summary text.',
                   location='Testville, CA', target_roles=[]))
    db.commit()
    db.close()


@pytest.mark.parametrize('path', PAGES)
def test_database_failure_returns_503(broken_db, path):
    assert client.get(path).status_code == 503


def test_healthy_projects_page_returns_200(seeded):
    assert client.get('/projects').status_code == 200


def test_database_failure_says_projects_temporarily_unavailable(broken_db):
    text = client.get('/projects').text
    assert 'Projects temporarily unavailable' in text
    assert 'No projects listed yet' not in text


def test_empty_projects_table_is_not_reported_as_an_outage(profile_only):
    response = client.get('/projects')
    assert response.status_code == 200
    assert 'No projects listed yet' in response.text
    assert 'temporarily unavailable' not in response.text


@pytest.mark.parametrize('path, empty_text', [
    ('/experience', 'No experience listed yet'),
    ('/skills', 'No skills listed yet'),
    ('/credentials', 'No credentials listed yet'),
])
def test_database_failure_never_claims_a_section_is_empty(broken_db, path, empty_text):
    text = client.get(path).text
    assert 'temporarily unavailable' in text
    assert empty_text not in text


def test_database_failure_keeps_last_good_profile_visible(seeded, break_db):
    assert client.get('/').status_code == 200
    break_db()
    response = client.get('/')
    assert response.status_code == 503
    assert '<h1>Test Person</h1>' in response.text
    assert 'Test Headline' in response.text


def test_database_failure_at_cold_start_shows_no_invented_profile(broken_db):
    text = client.get('/').text
    assert 'Profile temporarily unavailable' in text
    assert CONTACT_EMAIL in text
    for phrase in INVENTED:
        assert phrase not in text


def test_last_good_profile_does_not_hide_failed_projects(seeded, break_db):
    client.get('/projects')
    break_db()
    text = client.get('/projects').text
    assert 'Projects temporarily unavailable' in text
    assert 'Widget Analysis' not in text


def test_projects_return_after_database_recovers_without_restart(seeded, session_factory, break_db, monkeypatch):
    break_db()
    assert client.get('/projects').status_code == 503
    monkeypatch.setattr(app_main, 'SessionLocal', session_factory)
    response = client.get('/projects')
    assert response.status_code == 200
    assert '<h2>Widget Analysis</h2>' in response.text
    assert 'temporarily unavailable' not in response.text
