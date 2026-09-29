import pytest
from fastapi.testclient import TestClient

from app.formatting import format_month
from app.main import app
from app.models import Credential, Experience, Profile

client = TestClient(app)


@pytest.mark.parametrize('value, expected', [
    ('2026-06', 'Jun 2026'),
    ('2025-12', 'Dec 2025'),
    (None, 'Present'),
    ('', 'Present'),
    ('2025', '2025'),
    ('2025-13', '2025-13'),
])
def test_format_month(value, expected):
    assert format_month(value) == expected


def test_home_shows_name_headline_and_current_focus(seeded):
    text = client.get('/').text
    assert '<h1>Test Person</h1>' in text
    assert 'Test Headline' in text
    assert 'Testville, CA · Open to opportunities' in text
    assert '<h2>Current focus</h2>' in text
    assert 'Senior Analyst' in text
    assert 'href="/experience"' in text and 'View experience' in text


def test_about_shows_summary_and_target_roles(seeded):
    text = client.get('/about').text
    assert '<h1>About</h1>' in text
    assert 'Test summary text.' in text
    assert '<h2>Target roles</h2>' in text
    assert '<span class="tag">Data Analyst</span>' in text


def test_experience_lists_newest_first_with_dates_and_highlights(seeded):
    text = client.get('/experience').text
    assert '<h1>Experience</h1>' in text
    assert text.index('Globex') < text.index('Acme Corp')
    assert 'Feb 2025 – Present' in text
    assert 'Jan 2024 – Jun 2024' in text
    assert '<li>Led the Globex pricing study</li>' in text
    assert 'Initech' not in text


def test_projects_show_sections_and_hide_drafts(seeded):
    text = client.get('/projects').text
    assert '<h3>Widget Analysis</h3>' in text
    for heading in ('Problem', 'Solution', 'Impact'):
        assert f'<h4>{heading}</h4>' in text
    assert '<span class="tag">Python</span>' in text
    assert 'Secret Draft' not in text


def test_skills_are_grouped_under_category_headings(seeded):
    text = client.get('/skills').text
    assert '<h2>Finance</h2>' in text
    assert '<h2>Tools</h2>' in text
    assert text.index('<h2>Tools</h2>') < text.index('<span class="tag">SQL</span>')
    assert 'Hidden Skill' not in text


def test_credentials_show_only_sections_with_entries(seeded):
    text = client.get('/credentials').text
    assert '<h2>Education</h2>' in text
    assert '<h2>Certifications</h2>' in text
    assert '<h2>Awards</h2>' not in text
    assert 'B.S. Testing' in text and 'Test University' in text


def test_empty_pages_say_so(session_factory):
    db = session_factory()
    db.add(Profile(full_name='Test Person', headline='H', summary='S', location='L'))
    db.commit()
    db.close()
    assert 'No experience listed yet.' in client.get('/experience').text
    assert 'No projects listed yet.' in client.get('/projects').text
    assert 'No skills listed yet.' in client.get('/skills').text
    assert 'No credentials listed yet.' in client.get('/credentials').text


# Review Focus 1
def test_experience_card_handles_missing_optional_fields(session_factory):
    db = session_factory()
    profile = Profile(full_name='Test Person', headline='H', summary='S', location='L')
    db.add(profile)
    db.flush()
    db.add(Experience(profile_id=profile.id, company_name='Sparse Co', title='Temp',
                      location=None, start_date=None, end_date=None, current_role=False,
                      summary='Only a summary.', highlights=None, status='published'))
    db.commit()
    db.close()
    text = client.get('/experience').text
    assert 'Sparse Co' in text
    assert 'Only a summary.' in text
    assert 'None' not in text
    assert 'Sparse Co ·' not in text
    assert '– Present' not in text


# Review Focus 2
def test_profile_text_is_escaped_once(session_factory):
    db = session_factory()
    db.add(Profile(full_name='A & B', headline='R&D <Lead>', summary='S', location='L'))
    db.commit()
    db.close()
    text = client.get('/').text
    assert 'R&amp;D &lt;Lead&gt;' in text
    assert '<Lead>' not in text
    assert '&amp;amp;' not in text


# Review Focus 4
def test_unknown_credential_type_is_listed_under_other(seeded, session_factory):
    db = session_factory()
    profile_id = db.query(Profile).first().id
    db.add(Credential(profile_id=profile_id, credential_type='training', name='SQL Bootcamp',
                      issuer='Test Academy', status='published'))
    db.commit()
    db.close()
    text = client.get('/credentials').text
    assert '<h2>Other credentials</h2>' in text
    assert 'SQL Bootcamp' in text


# Review Focus 5
def test_home_without_experiences_has_no_focus_card(session_factory):
    db = session_factory()
    db.add(Profile(full_name='Test Person', headline='H', summary='S', location='L'))
    db.commit()
    db.close()
    response = client.get('/')
    assert response.status_code == 200
    assert '<h1>Test Person</h1>' in response.text
    assert 'Current focus' not in response.text
    assert 'Most recent role' not in response.text


def test_home_features_newest_role_as_most_recent_when_it_has_ended(seeded, session_factory):
    db = session_factory()
    profile_id = db.query(Profile).first().id
    db.add(Experience(profile_id=profile_id, company_name='Hooli', title='Summer Intern', start_date='2026-03',
                      end_date='2026-05', current_role=False, summary='Newer past role.',
                      highlights=[], status='published'))
    db.commit()
    db.close()
    text = client.get('/').text
    assert '<h2>Most recent role</h2>' in text
    assert '<h3>Summer Intern</h3>' in text
