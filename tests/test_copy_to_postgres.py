import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Experience, Profile
from scripts.copy_to_postgres import copy_database


def target_url(tmp_path):
    return f"sqlite:///{(tmp_path / 'target.db').as_posix()}"


def open_session(url):
    engine = create_engine(url, future=True)
    return engine, sessionmaker(bind=engine)()


def test_copies_every_row(tmp_path, source_db_url):
    counts = copy_database(source_db_url, target_url(tmp_path))
    assert counts == {'profiles': 1, 'experiences': 1, 'projects': 0, 'skills': 2,
                      'credentials': 0, 'content_pieces': 0, 'contact_submissions': 0}


def test_json_and_boolean_columns_survive(tmp_path, source_db_url):
    url = target_url(tmp_path)
    copy_database(source_db_url, url)
    engine, db = open_session(url)
    assert db.query(Profile).one().target_roles == ['Data Analyst']
    experience = db.query(Experience).one()
    assert experience.highlights == ['Built a model']
    assert experience.current_role is False
    db.close()
    engine.dispose()


def test_refuses_to_copy_into_a_database_that_has_a_profile(tmp_path, source_db_url):
    url = target_url(tmp_path)
    copy_database(source_db_url, url)
    with pytest.raises(RuntimeError, match='already has a profile'):
        copy_database(source_db_url, url)
    engine, db = open_session(url)
    assert db.query(Profile).count() == 1
    assert db.query(Experience).count() == 1
    db.close()
    engine.dispose()
