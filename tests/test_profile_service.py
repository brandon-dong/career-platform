import pytest

from app.services.profile_service import get_credentials, get_experiences, get_projects, get_skills


@pytest.fixture
def db(session_factory, seeded):
    session = session_factory()
    yield session
    session.close()


def test_get_experiences_puts_current_role_first_and_hides_drafts(db):
    assert [e.company_name for e in get_experiences(db)] == ['Globex', 'Acme Corp']


def test_get_projects_hides_drafts(db):
    assert [p.title for p in get_projects(db)] == ['Widget Analysis']


def test_get_skills_orders_by_category_and_hides_drafts(db):
    assert [(s.category, s.name) for s in get_skills(db)] == [
        ('finance', 'Valuation'),
        ('tools', 'Python'),
        ('tools', 'SQL'),
    ]


def test_get_credentials_orders_by_type(db):
    assert [c.credential_type for c in get_credentials(db)] == ['certification', 'education']
