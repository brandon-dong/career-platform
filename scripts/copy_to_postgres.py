"""One-time copy of the local SQLite data into another database (Railway Postgres).

Run from the repo root (Git Bash):
    .venv/Scripts/python.exe scripts/copy_to_postgres.py
It reads the target URL from TARGET_DATABASE_URL, or asks for it without echoing,
so the database password stays out of shell history. Source: data/career_platform.db.
Refuses to run if the target already has a profile.
"""
import getpass
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app.models  # noqa: E402,F401  registers tables on Base.metadata
from database import Base, engine_kwargs  # noqa: E402

SOURCE_PATH = ROOT / 'data' / 'career_platform.db'
LOCAL_HOSTS = ('localhost', '127.0.0.1')


def target_engine_kwargs(target_url: str) -> dict:
    kwargs = engine_kwargs(target_url)
    url = make_url(target_url)
    if url.get_backend_name() == 'postgresql' and url.host not in LOCAL_HOSTS:
        # Over the public TCP proxy, refuse a plaintext fallback that would expose the password.
        kwargs['connect_args'] = {**kwargs['connect_args'], 'sslmode': 'require'}
    return kwargs


def copy_database(source_url: str, target_url: str) -> dict[str, int]:
    source = create_engine(source_url, future=True)
    target = create_engine(target_url, **target_engine_kwargs(target_url))
    try:
        Base.metadata.create_all(bind=target)
        profiles = Base.metadata.tables['profiles']
        with target.connect() as conn:
            if conn.scalar(select(func.count()).select_from(profiles)):
                raise RuntimeError('Target already has a profile; refusing to overwrite.')

        counts = {}
        with source.connect() as src, target.begin() as dst:
            for table in Base.metadata.sorted_tables:
                rows = [dict(row._mapping) for row in src.execute(select(table))]
                if rows:
                    dst.execute(table.insert(), rows)
                counts[table.name] = len(rows)
                if target.dialect.name == 'postgresql':
                    # Rows arrived with explicit ids, so the SERIAL sequence never moved.
                    # Point it at max(id), or leave it at 1 (not yet used) for an empty table.
                    dst.execute(text(
                        f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                        f"COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM {table.name}"
                    ))
        return counts
    finally:
        source.dispose()
        target.dispose()


def main():
    if not SOURCE_PATH.exists():
        sys.exit(f'{SOURCE_PATH} not found.')
    target_url = os.getenv('TARGET_DATABASE_URL') or getpass.getpass('Target database URL: ')
    counts = copy_database(f'sqlite:///{SOURCE_PATH.as_posix()}', target_url.strip())
    for name, count in counts.items():
        print(f'{name}: {count}')


if __name__ == '__main__':
    main()
