from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL


def engine_kwargs(url: str) -> dict:
    if url.startswith('sqlite'):
        return {'connect_args': {'check_same_thread': False}, 'future': True}
    # pool_pre_ping replaces connections that Postgres or Railway's network closed while idle.
    return {'connect_args': {}, 'pool_pre_ping': True, 'future': True}


engine = create_engine(DATABASE_URL, **engine_kwargs(DATABASE_URL))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
