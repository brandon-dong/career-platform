import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  registers tables on Base.metadata
from app import main as app_main
from app.models import Credential, Experience, Profile, Project, Skill
from database import Base


@pytest.fixture(autouse=True)
def session_factory(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        connect_args={'check_same_thread': False},
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(app_main, 'SessionLocal', factory)
    # Each test starts as a fresh process would: no remembered profile.
    monkeypatch.setattr(app_main, '_last_good_profile', None, raising=False)
    yield factory
    engine.dispose()


@pytest.fixture
def seeded(session_factory):
    db = session_factory()
    profile = Profile(
        full_name='Test Person',
        headline='Test Headline',
        summary='Test summary text.',
        location='Testville, CA',
        target_roles=['Data Analyst', 'Financial Analyst'],
        availability_status='Open to opportunities',
    )
    db.add(profile)
    db.flush()
    pid = profile.id
    db.add_all([
        Experience(profile_id=pid, company_name='Acme Corp', title='Analyst', location='Austin, TX',
                   start_date='2024-01', end_date='2024-06', current_role=False, summary='Past role.',
                   highlights=['Built the Acme forecast model'], status='published'),
        Experience(profile_id=pid, company_name='Globex', title='Senior Analyst', location='Remote',
                   start_date='2025-02', end_date=None, current_role=True, summary='Current role.',
                   highlights=['Led the Globex pricing study'], status='published'),
        Experience(profile_id=pid, company_name='Initech', title='Draft Role', start_date='2025-06',
                   current_role=True, summary='Draft.', highlights=[], status='draft'),
        Project(profile_id=pid, title='Widget Analysis', short_description='Widget demand study.',
                problem_statement='Widget demand was unclear.', solution_summary='Modeled widget demand.',
                tools=['Python', 'SQL'], impact_summary='Cut widget waste.', status='published'),
        Project(profile_id=pid, title='Secret Draft', short_description='Hidden.',
                problem_statement='Hidden.', solution_summary='Hidden.', tools=[],
                impact_summary='Hidden.', status='draft'),
        Skill(profile_id=pid, category='tools', name='Python', status='published'),
        Skill(profile_id=pid, category='tools', name='SQL', status='published'),
        Skill(profile_id=pid, category='finance', name='Valuation', status='published'),
        Skill(profile_id=pid, category='tools', name='Hidden Skill', status='draft'),
        Credential(profile_id=pid, credential_type='education', name='B.S. Testing',
                   issuer='Test University', date_earned='May 2027', status='published'),
        Credential(profile_id=pid, credential_type='certification', name='Excel Expert',
                   issuer='Microsoft', date_earned=None, status='published'),
    ])
    db.commit()
    db.close()


class BrokenSession:
    def query(self, *args, **kwargs):
        raise RuntimeError('database unavailable')

    def close(self):
        pass


@pytest.fixture
def broken_db(monkeypatch):
    monkeypatch.setattr(app_main, 'SessionLocal', BrokenSession)


@pytest.fixture
def break_db(monkeypatch):
    """Call it mid-test to make every later request fail to reach the database."""
    return lambda: monkeypatch.setattr(app_main, 'SessionLocal', BrokenSession)


@pytest.fixture
def source_db_url(tmp_path):
    """A standalone SQLite file to copy from: 1 profile, 2 skills, 1 experience."""
    url = f"sqlite:///{(tmp_path / 'source.db').as_posix()}"
    engine = create_engine(url, future=True)
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    profile = Profile(full_name='Source Person', headline='H', summary='S', location='L',
                      target_roles=['Data Analyst'])
    db.add(profile)
    db.flush()
    db.add_all([
        Skill(profile_id=profile.id, category='tools', name='Python'),
        Skill(profile_id=profile.id, category='tools', name='SQL'),
        Experience(profile_id=profile.id, company_name='Acme', title='Analyst', start_date='2024-01',
                   summary='Did things.', highlights=['Built a model'], current_role=False),
    ])
    db.commit()
    db.close()
    engine.dispose()
    return url
