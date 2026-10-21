import re

import pytest
from fastapi.testclient import TestClient

from app import main as app_main
from app.main import app

client = TestClient(app)

PAGES = ['/', '/about', '/experience', '/projects', '/skills', '/credentials', '/contact', '/privacy']
TEST_ID = 'G-TEST12345'


@pytest.fixture
def analytics_on(monkeypatch):
    monkeypatch.setitem(app_main.templates.env.globals, 'analytics_id', TEST_ID)


@pytest.fixture
def analytics_off(monkeypatch):
    monkeypatch.setitem(app_main.templates.env.globals, 'analytics_id', '')


def head_of(html):
    return html.split('<head>', 1)[1].split('</head>', 1)[0]


# --- Privacy page -----------------------------------------------------------

def test_privacy_page_explains_analytics_choices(seeded):
    response = client.get('/privacy')
    assert response.status_code == 200
    assert '<h1>Privacy</h1>' in response.text
    for phrase in ['Google Analytics', 'outbound', 'Railway', 'Decline', 'withdraw']:
        assert phrase in response.text


def test_privacy_page_has_its_own_title(seeded):
    assert '<title>Privacy · Test Person</title>' in client.get('/privacy').text


def test_privacy_page_stays_readable_during_database_failure(broken_db):
    response = client.get('/privacy')
    assert response.status_code == 503
    assert 'Google Analytics' in response.text


@pytest.mark.parametrize('path', PAGES)
def test_footer_links_to_privacy_page(seeded, path):
    footer = client.get(path).text.split('<footer', 1)[1]
    assert '<a href="/privacy">Privacy</a>' in footer


# --- Google tag -------------------------------------------------------------

@pytest.mark.parametrize('path', PAGES)
def test_tag_loads_once_per_page_with_the_measurement_id(seeded, analytics_on, path):
    html = client.get(path).text
    assert html.count('googletagmanager.com/gtag/js') == 1
    assert f'googletagmanager.com/gtag/js?id={TEST_ID}' in html
    assert html.count(f"gtag('config', '{TEST_ID}')") == 1


def test_tag_is_the_first_thing_in_head(seeded, analytics_on):
    head = head_of(client.get('/').text)
    assert head.lstrip().startswith('<!-- Google tag (gtag.js) -->')


def test_tag_waits_for_consent(seeded, analytics_on):
    head = head_of(client.get('/').text)
    loader = re.search(r'<script[^>]*googletagmanager[^>]*>', head).group(0)
    # The browser does not run or fetch a script whose type is text/plain,
    # so Google's script stays unloaded until consent.js swaps it in.
    assert 'type="text/plain"' in loader
    assert 'data-consent="analytics"' in loader
    denied = head.index("'analytics_storage': 'denied'")
    assert denied < head.index("gtag('config'")


def test_page_view_waits_for_the_consent_update(seeded, analytics_on):
    # config (which sends page_view) is queued before consent.js adds the
    # 'granted' update. Without wait_for_update, gtag.js sends that page_view
    # as a denied, cookieless ping that GA4 Realtime never shows.
    head = head_of(client.get('/').text)
    default = re.search(r"gtag\('consent', 'default', \{[^}]*\}\)", head).group(0)
    assert "'wait_for_update': 500" in default


def test_consent_banner_and_settings_start_hidden(seeded, analytics_on):
    html = client.get('/').text
    banner = re.search(r'<div[^>]*data-consent-banner[^>]*>', html).group(0)
    assert 'hidden' in banner
    assert '<button type="button" data-consent-choice="granted">Accept</button>' in html
    assert '<button type="button" data-consent-choice="denied">Decline</button>' in html
    settings = re.search(r'<button[^>]*data-consent-open[^>]*>', html).group(0)
    assert 'hidden' in settings
    assert 'src="http://testserver/static/js/consent.js"' in html


def test_consent_script_is_served(seeded):
    response = client.get('/static/js/consent.js')
    assert response.status_code == 200
    assert "gtag('consent', 'update'" in response.text


@pytest.mark.parametrize('path', PAGES)
def test_no_tag_or_banner_without_a_measurement_id(seeded, analytics_off, path):
    response = client.get(path)
    assert response.status_code == 200
    assert 'googletagmanager' not in response.text
    assert 'data-consent-banner' not in response.text
    assert 'consent.js' not in response.text


def test_measurement_id_defaults_to_the_live_property():
    from app.config import GA_MEASUREMENT_ID
    assert GA_MEASUREMENT_ID == 'G-RBCK2JQ78P'
