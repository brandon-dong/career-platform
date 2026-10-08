import pytest
from fastapi.testclient import TestClient

from app.config import CONTACT_EMAIL, LINKEDIN_URL
from app.main import app

client = TestClient(app)

PAGES = ['/', '/about', '/experience', '/projects', '/skills', '/credentials', '/contact']
MAILTO = f'href="mailto:{CONTACT_EMAIL}"'
LINKEDIN = f'href="{LINKEDIN_URL}"'


def test_contact_page_lists_email_and_linkedin(seeded):
    text = client.get('/contact').text
    assert 'coming soon' not in text
    assert MAILTO in text and CONTACT_EMAIL in text
    assert LINKEDIN in text


def test_home_hero_leads_with_email(seeded):
    text = client.get('/').text
    hero = text[text.index('class="hero"'):text.index('</section>')]
    assert MAILTO in hero and 'Email me' in hero


@pytest.mark.parametrize('path', PAGES)
def test_footer_has_contact_links_even_in_fallback(path):
    text = client.get(path).text
    footer = text[text.index('<footer'):]
    assert MAILTO in footer and LINKEDIN in footer


@pytest.mark.parametrize('path, title', [
    ('/', '<title>Test Person</title>'),
    ('/experience', '<title>Experience · Test Person</title>'),
    ('/contact', '<title>Contact · Test Person</title>'),
])
def test_each_page_has_its_own_title(seeded, path, title):
    assert title in client.get(path).text


@pytest.mark.parametrize('path', PAGES)
def test_skip_link_targets_main(seeded, path):
    text = client.get(path).text
    assert '<a class="skip-link" href="#main">Skip to content</a>' in text
    assert '<main id="main"' in text


def test_experience_card_titles_follow_h1(seeded):
    text = client.get('/experience').text
    assert '<h2>Senior Analyst</h2>' in text
    assert '<h3' not in text


def test_project_headings_follow_h1(seeded):
    text = client.get('/projects').text
    assert '<h2>Widget Analysis</h2>' in text
    for heading in ('Problem', 'Solution', 'Impact'):
        assert f'<h3>{heading}</h3>' in text
    assert '<h4' not in text
