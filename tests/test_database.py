from sqlalchemy import create_engine

from database import engine_kwargs

PG_URL = 'postgresql://user:secret@db.example:5432/app'


def test_sqlite_url_allows_cross_thread_use():
    assert engine_kwargs('sqlite:///./career_platform.db')['connect_args'] == {'check_same_thread': False}


def test_postgres_url_gets_a_connect_timeout_and_no_sqlite_only_options():
    kwargs = engine_kwargs(PG_URL)
    assert kwargs['connect_args'] == {'connect_timeout': 10}
    assert kwargs['pool_pre_ping'] is True


def test_postgres_url_builds_an_engine_with_psycopg2():
    engine = create_engine(PG_URL, **engine_kwargs(PG_URL))  # does not connect
    assert engine.dialect.driver == 'psycopg2'
