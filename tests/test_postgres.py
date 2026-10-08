"""Tests that only mean something on PostgreSQL.

Skipped unless TEST_POSTGRES_URL is set. Every test drops all tables, so the URL
must point at a local throwaway database (see Task 2 of the Railway plan).
"""
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.models import Credential, Experience, Profile, Skill
from app.services.profile_service import get_experiences
from database import Base
from scripts.copy_to_postgres import copy_database

PG_URL = os.getenv('TEST_POSTGRES_URL')
pytestmark = pytest.mark.skipif(not PG_URL, reason='set TEST_POSTGRES_URL to run PostgreSQL tests')


@pytest.fixture
def pg_engine():
    if make_url(PG_URL).host not in ('localhost', '127.0.0.1'):
        pytest.fail('TEST_POSTGRES_URL must be a local throwaway database; these tests drop every table.')
    # lock_timeout turns a leaked transaction into an error instead of a DROP TABLE that waits forever.
    engine = create_engine(PG_URL, connect_args={'options': '-c lock_timeout=5000'}, future=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def pg_db(pg_engine):
    # Closed by the fixture, so a failing assertion can't leave a transaction holding table locks.
    db = sessionmaker(bind=pg_engine)()
    yield db
    db.close()


def test_undated_experience_lists_last(pg_db):
    profile = Profile(full_name='T', headline='H', summary='S', location='L')
    pg_db.add(profile)
    pg_db.flush()
    pg_db.add_all([
        Experience(profile_id=profile.id, company_name='Undated', title='A', start_date=None,
                   summary='x', status='published'),
        Experience(profile_id=profile.id, company_name='Dated', title='B', start_date='2025-01',
                   summary='x', status='published'),
    ])
    pg_db.commit()
    assert [e.company_name for e in get_experiences(pg_db)] == ['Dated', 'Undated']


def test_copy_resets_id_sequences(pg_engine, pg_db, source_db_url):
    copy_database(source_db_url, PG_URL)
    skill = Skill(profile_id=1, category='tools', name='New Skill')
    credential = Credential(profile_id=1, credential_type='award', name='First', issuer='X')
    pg_db.add_all([skill, credential])
    pg_db.commit()
    assert skill.id == 3       # copied table: continues after max(id)
    assert credential.id == 1  # empty table: starts at 1
