# Railway + PostgreSQL Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve the career platform from the existing Railway project's web service, reading the same data the laptop has, now stored in the project's PostgreSQL service instead of a SQLite file.

**Architecture:** Railway builds the app from GitHub `main` with Railpack. Railpack uses `uv.lock` and Python 3.12, and uvicorn starts on Railway's `$PORT`. The web service reaches Postgres over Railway's private network through a reference variable. The laptop's SQLite rows are copied into Postgres once by a script, through a temporary public TCP proxy that is removed afterwards. A `/healthz` endpoint makes Railway refuse a deploy that would only show the fallback page.

```
Browser ──HTTPS──► Railway edge (TLS ends here) ──HTTP──► web service: uvicorn app.main:app :$PORT
                                                              │  DATABASE_URL = ${{Postgres.DATABASE_URL}}
                                                              ▼  (postgres.railway.internal, private)
Laptop ──scripts/copy_to_postgres.py──► DATABASE_PUBLIC_URL ──► Postgres service
          (one time, R5)                (TCP proxy, removed in R6)
```

**Tech Stack:** Railway (Railpack builder, managed PostgreSQL), FastAPI 0.115, uvicorn 0.30.6, SQLAlchemy 2.0.35, psycopg2-binary 2.9.10, uv, Python 3.12, Docker (local throwaway Postgres for tests only).

**Spec:** Brandon's request (chat, 2026-10-08): "Inspect my app and plan its move to Railway and PostgreSQL. The Railway project already exists with Postgres and a web service."

## What the inspection found (read first)

| # | Finding | Where | Consequence on Railway | Fixed in |
|---|---|---|---|---|
| 1 | `connect_args={'check_same_thread': False}` is always passed | `database.py:6` | psycopg2 rejects the unknown option on the first query, so every page shows the fallback | Task 1 |
| 2 | No PostgreSQL driver is installed | `pyproject.toml` | `create_engine('postgresql://…')` raises `ModuleNotFoundError: psycopg2` at import, so the app won't start | Task 1 |
| 3 | `requirements.txt` and `uv.lock` both exist and disagree (the first includes pytest/httpx and would lack the driver) | repo root | Railpack may pick the wrong package manager | Task 1 (delete `requirements.txt`) |
| 4 | No Python version is pinned | repo root | Railpack defaults to Python 3.13.2, but the laptop and the lock file were tested on 3.12 | Task 1 (`.python-version`) |
| 5 | `ORDER BY start_date DESC` with a NULL `start_date` | `app/services/profile_service.py:12-17` | SQLite sorts NULLs last on DESC and Postgres sorts them first, so an undated role jumps to the top | Task 2 |
| 6 | The stylesheet uses `url_for('static', …)`, which builds an **absolute** URL from the request's scheme | `templates/base.html:10` | Railway ends TLS at its edge, so the app sees `http`. The page loads over https but asks for `http://…/styles.css`, which browsers block as mixed content, so the site renders unstyled | Task 3 |
| 7 | When the DB is empty or unreachable, every page still returns **200** with the fallback banner | `app/main.py:28-44` | A broken deploy looks healthy to Railway | Task 4 (`/healthz`) |
| 8 | Nothing creates tables, and the data exists only in the gitignored `data/career_platform.db` (1 profile, 3 experiences, 1 project, 9 skills, 6 credentials) | `database.py`, `data/` | Postgres starts empty | Task 5 + R5 |
| 9 | Copying rows with their `id`s leaves Postgres `SERIAL` sequences at 1 | n/a | The first future insert into any table fails with `duplicate key value violates unique constraint` | Task 5 |
| 10 | Railpack's FastAPI default start command is `uvicorn main:app` | Railpack docs | Our app is `app.main:app`, so the deploy crashes at start | R3 |
| 11 | `railway.json` (Config as Code) is deprecated and only works for legacy services until 2026-12-01 | Railway docs | Don't add one. Build/deploy settings go in the service's Settings tab | R3 |

## Global Constraints

- Python **3.12** (`.python-version` = `3.12`, `requires-python >=3.12`). Laptop: 3.12.10.
- Dependencies come only from `pyproject.toml` + `uv.lock`. Add packages with `uv add`, pinned with `==`. New runtime dependency: `psycopg2-binary==2.9.10`.
- Local development and the existing 71 tests keep using SQLite. The local `.env` keeps `DATABASE_URL=sqlite:///./career_platform.db`. Postgres-only tests are skipped unless `TEST_POSTGRES_URL` is set.
- `TEST_POSTGRES_URL` must point at a **local throwaway** database (`localhost`/`127.0.0.1`). The Postgres tests drop every table. Never point it at Railway.
- The repo is public on GitHub. Never commit database URLs, passwords or `.env`. The admin password on Railway must not be `career-platform` (it's in `.env.example`).
- Don't add `railway.json`/`railway.toml` (finding 11).
- Railway web service start command: `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`. Healthcheck path: `/healthz`.
- Railway Postgres service name is assumed to be **`Postgres`** (R1 confirms it). If it differs, replace `Postgres` in `${{Postgres.DATABASE_URL}}`.
- Test command (Git Bash, repo root): `.venv/Scripts/python.exe -m pytest -q`
- Commit style: conventional commits (`feat:`, `fix:`, `docs:`, `chore:`), ending with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`

## Review Focus

These failure modes are the most likely to hurt a visitor. Each one looks like success unless something checks for it:

1. **Unstyled site over HTTPS** (finding 6). Expected: the stylesheet link uses `https://` when Railway forwards `X-Forwarded-Proto: https`. Pinned by `test_stylesheet_url_uses_forwarded_https_scheme` (Task 3) and checked live in R8.
2. **Empty or unreachable database still deploys** (finding 7). Expected: `/healthz` returns 503 so Railway marks the deploy failed and keeps the previous one. Pinned by `test_healthz_*` (Task 4).
3. **Future inserts fail after the copy** (finding 9). Expected: the next row inserted into any copied table gets `max(id)+1`, and the first row into an empty table gets `1`. Pinned by `test_copy_resets_id_sequences` (Task 5, Postgres).
4. **Undated experience jumps to the top on Postgres** (finding 5). Expected: undated roles list after dated ones on both databases. Pinned by `test_undated_experience_lists_last` (Task 2, Postgres) plus a SQLite twin.
5. **Copy script run twice, or against a database that already has data.** Expected: it refuses and changes nothing. Pinned by `test_refuses_to_copy_into_a_database_that_has_a_profile` (Task 5).

---

### Task 1: Make the engine work with PostgreSQL

**Files:**
- Modify: `database.py`
- Modify: `pyproject.toml`, `uv.lock` (via `uv add`)
- Create: `.python-version`
- Delete: `requirements.txt`
- Test: `tests/test_database.py` (create)

**Interfaces:**
- Produces: `database.engine_kwargs(url: str) -> dict`, the keyword arguments for `create_engine` that suit the URL's database. `database.engine`, `database.SessionLocal` and `database.Base` keep their names.

- [ ] **Step 1: Write the failing tests**

`tests/test_database.py`:

```python
from sqlalchemy import create_engine

from database import engine_kwargs

PG_URL = 'postgresql://user:secret@db.example:5432/app'


def test_sqlite_url_allows_cross_thread_use():
    assert engine_kwargs('sqlite:///./career_platform.db')['connect_args'] == {'check_same_thread': False}


def test_postgres_url_gets_no_sqlite_only_options():
    kwargs = engine_kwargs(PG_URL)
    assert kwargs['connect_args'] == {}
    assert kwargs['pool_pre_ping'] is True


def test_postgres_url_builds_an_engine_with_psycopg2():
    engine = create_engine(PG_URL, **engine_kwargs(PG_URL))  # does not connect
    assert engine.dialect.driver == 'psycopg2'
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_database.py -v`
Expected: collection error, `ImportError: cannot import name 'engine_kwargs' from 'database'`.

- [ ] **Step 3: Implement `engine_kwargs`**

`database.py` (whole file):

```python
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
```

- [ ] **Step 4: Run the tests**

Run: `.venv/Scripts/python.exe -m pytest tests/test_database.py -v`
Expected: the first two PASS. `test_postgres_url_builds_an_engine_with_psycopg2` FAILS with `ModuleNotFoundError: No module named 'psycopg2'`.

- [ ] **Step 5: Add the driver, pin Python, drop `requirements.txt`**

```bash
echo 3.12 > .python-version
uv add psycopg2-binary==2.9.10
git rm requirements.txt
```

Why `-binary`: it ships its own `libpq`, so neither the laptop nor Railpack needs PostgreSQL headers to build it. Why delete `requirements.txt`: Railpack supports both pip (`requirements.txt`) and uv (`uv.lock`). With one source of truth there is nothing to drift, and the build log in R7 must show uv.

- [ ] **Step 6: Run the whole suite**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: `74 passed` (71 existing + 3 new).

- [ ] **Step 7: Commit**

```bash
git add database.py tests/test_database.py pyproject.toml uv.lock .python-version
git commit -m "feat: support PostgreSQL in the database engine

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Local Postgres tests, and stable ordering for undated experience

**Files:**
- Modify: `app/services/profile_service.py:12-17`
- Test: `tests/test_postgres.py` (create), `tests/test_profile_service.py` (append)

**Interfaces:**
- Consumes: `database.Base`, `app.services.profile_service.get_experiences(db) -> list[Experience]`
- Produces: the `pg_engine` fixture and the `PG_URL` constant in `tests/test_postgres.py` (Task 5 appends to this file).

- [ ] **Step 1: Start a throwaway Postgres (Docker Desktop must be running)**

```bash
docker run -d --name career-pg -e POSTGRES_PASSWORD=test -e POSTGRES_DB=career_test -p 54329:5432 postgres:17
export TEST_POSTGRES_URL=postgresql://postgres:test@localhost:54329/career_test
```

Check: `docker ps --filter name=career-pg` shows `Up`. Undo: `docker rm -f career-pg`. Port 54329 avoids clashing with any local Postgres on 5432. Use the same major version that R1 records for Railway, if it differs from 17.

- [ ] **Step 2: Write the failing tests**

`tests/test_postgres.py`:

```python
"""Tests that only mean something on PostgreSQL.

Skipped unless TEST_POSTGRES_URL is set. Every test drops all tables, so the URL
must point at a local throwaway database (see Task 2 of the Railway plan).
"""
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.models import Experience, Profile
from app.services.profile_service import get_experiences
from database import Base

PG_URL = os.getenv('TEST_POSTGRES_URL')
pytestmark = pytest.mark.skipif(not PG_URL, reason='set TEST_POSTGRES_URL to run PostgreSQL tests')


@pytest.fixture
def pg_engine():
    if make_url(PG_URL).host not in ('localhost', '127.0.0.1'):
        pytest.fail('TEST_POSTGRES_URL must be a local throwaway database; these tests drop every table.')
    engine = create_engine(PG_URL, future=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_undated_experience_lists_last(pg_engine):
    db = sessionmaker(bind=pg_engine)()
    profile = Profile(full_name='T', headline='H', summary='S', location='L')
    db.add(profile)
    db.flush()
    db.add_all([
        Experience(profile_id=profile.id, company_name='Undated', title='A', start_date=None,
                   summary='x', status='published'),
        Experience(profile_id=profile.id, company_name='Dated', title='B', start_date='2025-01',
                   summary='x', status='published'),
    ])
    db.commit()
    assert [e.company_name for e in get_experiences(db)] == ['Dated', 'Undated']
    db.close()
```

Append to `tests/test_profile_service.py` (the SQLite twin; it already passes, and it keeps SQLite behavior pinned after the change):

```python
def test_undated_experience_lists_last_on_sqlite(session_factory):
    db = session_factory()
    profile = Profile(full_name='T', headline='H', summary='S', location='L')
    db.add(profile)
    db.flush()
    db.add_all([
        Experience(profile_id=profile.id, company_name='Undated', title='A', start_date=None,
                   summary='x', status='published'),
        Experience(profile_id=profile.id, company_name='Dated', title='B', start_date='2025-01',
                   summary='x', status='published'),
    ])
    db.commit()
    assert [e.company_name for e in get_experiences(db)] == ['Dated', 'Undated']
    db.close()
```

Also change line 3 of `tests/test_profile_service.py` from `from app.models import Experience` to `from app.models import Experience, Profile`. (`get_experiences` is already imported. The test uses `session_factory`, not the file's `db` fixture, because `db` is pre-seeded.)

- [ ] **Step 3: Run the Postgres test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_postgres.py -v`
Expected: FAIL, `['Undated', 'Dated'] != ['Dated', 'Undated']`. If it says `SKIPPED`, `TEST_POSTGRES_URL` isn't exported in this shell.

- [ ] **Step 4: Make the ordering explicit**

In `app/services/profile_service.py`, change `get_experiences`:

```python
def get_experiences(db: Session):
    return (
        db.query(Experience)
        .filter(Experience.status == PUBLISHED)
        .order_by(Experience.start_date.desc().nulls_last(), Experience.id)
        .all()
    )
```

(SQLite has supported `NULLS LAST` since 3.30. The laptop's Python reports SQLite 3.49.1.)

- [ ] **Step 5: Run both suites**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: `76 passed` (Postgres test included, because `TEST_POSTGRES_URL` is set).
Then run `env -u TEST_POSTGRES_URL .venv/Scripts/python.exe -m pytest -q`. Expected: `75 passed, 1 skipped`.

- [ ] **Step 6: Commit**

```bash
git add app/services/profile_service.py tests/test_postgres.py tests/test_profile_service.py
git commit -m "fix: list undated experience last on every database

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Trust Railway's proxy so static URLs use HTTPS

**Files:**
- Modify: `app/main.py` (imports + right after `app = FastAPI(...)`)
- Test: `tests/test_proxy_headers.py` (create)

**Interfaces:**
- Consumes: the `seeded` fixture from `tests/conftest.py`.

- [ ] **Step 1: Write the failing test**

`tests/test_proxy_headers.py`:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_stylesheet_url_uses_forwarded_https_scheme(seeded):
    html = client.get('/', headers={'X-Forwarded-Proto': 'https'}).text
    assert 'href="https://testserver/static/css/styles.css"' in html


def test_stylesheet_url_stays_http_without_proxy_header(seeded):
    html = client.get('/').text
    assert 'href="http://testserver/static/css/styles.css"' in html
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_proxy_headers.py -v`
Expected: the first test FAILS (the page contains `http://testserver/static/...`). The second PASSES.

- [ ] **Step 3: Add the middleware**

In `app/main.py`, add the import next to the other imports:

```python
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
```

and directly after `app = FastAPI(title='Career Platform')`:

```python
# Railway ends HTTPS at its edge and forwards plain HTTP. Trusting its
# X-Forwarded-Proto header makes url_for() build https:// links.
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts='*')
```

Why in the app and not the start command: uvicorn's own `--forwarded-allow-ips` would also work, but it isn't visible to tests and is easy to lose when someone edits the dashboard. `'*'` is safe here because the only way into a Railway service is through Railway's edge.

- [ ] **Step 4: Run the whole suite**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: all pass (78 with `TEST_POSTGRES_URL` set).

- [ ] **Step 5: Commit**

```bash
git add app/main.py tests/test_proxy_headers.py
git commit -m "fix: build https static URLs behind Railway's proxy

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: `/healthz` endpoint for Railway's deploy healthcheck

**Files:**
- Modify: `app/main.py` (import + new route after `contact`)
- Test: `tests/test_health.py` (create)

**Interfaces:**
- Consumes: `app.main.SessionLocal` (tests swap it via the `session_factory` and `broken_db` fixtures), `get_active_profile(db)`.
- Produces: `GET /healthz` returns `200 {"status": "ok"}` when a profile can be read, `503 {"status": "no profile"}` when the DB is reachable but empty, and `503 {"status": "database unavailable"}` on any database error. R3 points Railway's healthcheck here.

- [ ] **Step 1: Write the failing tests**

`tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz_ok_when_profile_exists(seeded):
    response = client.get('/healthz')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_healthz_fails_when_database_is_empty():
    response = client.get('/healthz')
    assert response.status_code == 503
    assert response.json() == {'status': 'no profile'}


def test_healthz_fails_when_database_is_unreachable(broken_db):
    response = client.get('/healthz')
    assert response.status_code == 503
    assert response.json() == {'status': 'database unavailable'}
```

(The autouse `session_factory` fixture gives every test an empty SQLite DB, which is why the second test needs no fixture.)

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_health.py -v`
Expected: all 3 FAIL with `404`.

- [ ] **Step 3: Implement**

In `app/main.py`, add `from fastapi.responses import JSONResponse` with the other imports, and at the end of the file:

```python
@app.get('/healthz')
def healthz():
    db = SessionLocal()
    try:
        has_profile = get_active_profile(db) is not None
    except Exception:
        return JSONResponse({'status': 'database unavailable'}, status_code=503)
    finally:
        db.close()
    if not has_profile:
        return JSONResponse({'status': 'no profile'}, status_code=503)
    return {'status': 'ok'}
```

Why check for a profile and not just `SELECT 1`: an empty database still serves 200 with the fallback banner (finding 7). Railway's healthcheck runs only while a deploy is going live. If it fails, Railway keeps the previous deploy serving.

- [ ] **Step 4: Run the whole suite**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add app/main.py tests/test_health.py
git commit -m "feat: add /healthz that fails without a readable profile

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Script that copies the SQLite data into Postgres

**Files:**
- Create: `scripts/copy_to_postgres.py` (committed: it holds no personal data, unlike the excluded `scripts/seed_resume.py`)
- Modify: `tests/conftest.py` (add `source_db_url` fixture)
- Test: `tests/test_copy_to_postgres.py` (create), `tests/test_postgres.py` (append)

**Interfaces:**
- Consumes: `database.Base`, `app.models` (all tables), `pg_engine` and `PG_URL` from `tests/test_postgres.py`.
- Produces: `scripts.copy_to_postgres.copy_database(source_url: str, target_url: str) -> dict[str, int]`. It creates missing tables on the target, refuses (raises `RuntimeError` containing `already has a profile`) if the target has any profile, copies every table in foreign-key order inside one transaction, resets Postgres id sequences, and returns `{table_name: rows_copied}`.

- [ ] **Step 1: Add the shared source fixture**

Append to `tests/conftest.py`:

```python
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
```

- [ ] **Step 2: Write the failing SQLite tests**

`tests/test_copy_to_postgres.py`:

```python
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
```

- [ ] **Step 3: Write the failing Postgres test**

Append to `tests/test_postgres.py` (and add `Credential, Skill` to its `from app.models import ...` line, and `from scripts.copy_to_postgres import copy_database` to its imports):

```python
def test_copy_resets_id_sequences(pg_engine, source_db_url):
    copy_database(source_db_url, PG_URL)
    db = sessionmaker(bind=pg_engine)()
    skill = Skill(profile_id=1, category='tools', name='New Skill')
    credential = Credential(profile_id=1, credential_type='award', name='First', issuer='X')
    db.add_all([skill, credential])
    db.commit()
    assert skill.id == 3       # copied table: continues after max(id)
    assert credential.id == 1  # empty table: starts at 1
    db.close()
```

- [ ] **Step 4: Run to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest tests/test_copy_to_postgres.py tests/test_postgres.py -v`
Expected: collection errors, `ModuleNotFoundError: No module named 'scripts.copy_to_postgres'`.

- [ ] **Step 5: Implement the script**

`scripts/copy_to_postgres.py`:

```python
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

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app.models  # noqa: E402,F401  registers tables on Base.metadata
from database import Base  # noqa: E402

SOURCE_PATH = ROOT / 'data' / 'career_platform.db'


def copy_database(source_url: str, target_url: str) -> dict[str, int]:
    source = create_engine(source_url, future=True)
    target = create_engine(target_url, future=True)
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
```

- [ ] **Step 6: Run the whole suite**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: all pass, with `test_copy_resets_id_sequences` PASSED, not skipped. To see the sequence reset matter, temporarily comment out the `setval` block and rerun. `test_copy_resets_id_sequences` should fail with `duplicate key value violates unique constraint "skills_pkey"`. Then restore it.

- [ ] **Step 7: Rehearse against the local Postgres with the real data**

```bash
TARGET_DATABASE_URL=$TEST_POSTGRES_URL .venv/Scripts/python.exe scripts/copy_to_postgres.py
```

Expected output:
```
profiles: 1
experiences: 3
projects: 1
skills: 9
credentials: 6
content_pieces: 0
contact_submissions: 0
```

Then serve the site from the local Postgres and look at it:

```bash
DATABASE_URL=$TEST_POSTGRES_URL .venv/Scripts/python.exe -m uvicorn app.main:app --port 8001
```

Check: `curl -s localhost:8001/healthz` returns `{"status":"ok"}`. `curl -s localhost:8001/ | grep -c "fallback mode"` returns `0`. `/experience` lists Western Express first. Stop uvicorn, then run `docker rm -f career-pg` (the next test run starts a new container).

- [ ] **Step 8: Commit and push**

```bash
git add scripts/copy_to_postgres.py tests/conftest.py tests/test_copy_to_postgres.py tests/test_postgres.py
git commit -m "feat: add one-time SQLite to Postgres copy script

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin main
```

Railway deploys from GitHub, so Section R needs Tasks 1–5 on `origin/main`.

---

## Section R: Railway setup and cutover (dashboard, done by hand)

Each step has **Where / Do / Why / Check / Undo**, like the Azure plans. Real values (passwords, URLs) are never written into this file.

- [ ] **R1. Read the project as it is**
  - **Where:** railway.com → the project.
  - **Do:** Note (1) the Postgres service's exact name on the canvas, (2) its version (Postgres service → Database tab, or its image tag in Settings), and (3) the web service's Settings → Source: is it connected to `brandon-dong/career-platform`, and which branch?
  - **Why:** The reference variable in R2 uses the service name. The Docker image in Task 2 should match the major version.
  - **Check:** Record all three in the Results table below.

- [ ] **R2. Web service variables**
  - **Where:** web service → Variables → Raw Editor.
  - **Do:**
    ```
    DATABASE_URL=${{Postgres.DATABASE_URL}}
    ADMIN_USERNAME=admin
    ADMIN_PASSWORD=<new random value>
    ```
    Generate the password on the laptop: `.venv/Scripts/python.exe -c "import secrets; print(secrets.token_urlsafe(24))"`. Store it in a password manager. `CONTACT_EMAIL` and `LINKEDIN_URL` can stay unset, because `app/config.py` defaults to the right values.
  - **Why:** `${{Postgres.DATABASE_URL}}` is a reference variable. It points at `postgres.railway.internal` (private network, no egress cost) and follows password rotations automatically. Railway injects variables as real environment variables, and `load_dotenv` never overrides them. No `.env` is deployed.
  - **Check:** Hover the variable. The resolved value starts with `postgresql://` and contains `railway.internal`.
  - **Undo:** Delete the variables.

- [ ] **R3. Web service build and deploy settings**
  - **Where:** web service → Settings.
  - **Do:**
    - Source: repo `brandon-dong/career-platform`, branch `main` (connect it if R1 found none).
    - Deploy → Custom Start Command: `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`
    - Deploy → Healthcheck Path: `/healthz`
    - Deploy → Restart Policy: On Failure.
  - **Why:** Railpack's FastAPI default is `uvicorn main:app`, but our module is `app.main` (finding 10). `0.0.0.0` lets Railway's edge reach the container. `$PORT` is the port Railway routes to. These settings live in the dashboard because `railway.json` is deprecated (finding 11).
  - **Check:** Settings shows all four values.
  - **Note:** Connecting the repo starts a deploy right away. Before R5 it will fail its healthcheck with `no profile`, which is expected and harmless.

- [ ] **R4. Open Postgres to the laptop, temporarily**
  - **Where:** Postgres service → Settings → Networking → Public Networking → add TCP Proxy.
  - **Why:** Postgres is private by default, and the copy runs on the laptop. Adding the proxy populates `DATABASE_PUBLIC_URL`.
  - **Check:** Postgres → Variables shows `DATABASE_PUBLIC_URL` (host like `*.proxy.rlwy.net`).
  - **Undo:** R6.

- [ ] **R5. Copy the data**
  - **Where:** Laptop, Git Bash, repo root, on the commit pushed in Task 5.
  - **Do:** `.venv/Scripts/python.exe scripts/copy_to_postgres.py`, then paste `DATABASE_PUBLIC_URL` at the hidden prompt.
  - **Check:** The output matches Task 5 Step 7 (1 / 3 / 1 / 9 / 6 / 0 / 0). Running it again prints `Target already has a profile; refusing to overwrite.` and changes nothing. In Postgres → Database → Data, `profiles` has 1 row.
  - **Undo (start over):** Postgres → Database → Data → drop the seven tables, then run R5 again.

- [ ] **R6. Close Postgres again**
  - **Where:** Postgres service → Settings → Networking → remove the TCP Proxy.
  - **Why:** While the proxy exists, anyone on the internet can try the database password. The app only needs the private network.
  - **Check:** `DATABASE_PUBLIC_URL` is gone from Postgres → Variables, and R2's `DATABASE_URL` still resolves.

- [ ] **R7. Deploy and read the logs**
  - **Where:** web service → Deployments → Redeploy the latest (or push any commit).
  - **Check, build log:** It mentions `uv` and Python `3.12` (not pip, not 3.13).
  - **Check, deploy log:** `Uvicorn running on http://0.0.0.0:<port>`, then `Healthcheck succeeded`. If it shows `ModuleNotFoundError: No module named 'main'`, R3's start command wasn't saved. If it shows `503` for the healthcheck, read the body: `no profile` means redo R5, and `database unavailable` means check R2.
  - **Undo:** Deployments → previous deploy → Rollback.

- [ ] **R8. Public domain and end-to-end check**
  - **Where:** web service → Settings → Networking → Generate Domain (accept the detected port).
  - **Check (Git Bash, replace `<domain>`):**
    ```bash
    curl -s https://<domain>/healthz                                  # {"status":"ok"}
    curl -s https://<domain>/ | grep -c "fallback mode"                # 0
    curl -s https://<domain>/ | grep -o 'href="[^"]*styles.css"'       # href="https://<domain>/static/css/styles.css"
    curl -s https://<domain>/experience | grep -c "Western Express"    # 1 or more
    curl -s -o /dev/null -w "%{http_code}\n" -u admin:career-platform https://<domain>/admin/   # 401
    curl -s -o /dev/null -w "%{http_code}\n" -u "admin:<R2 password>" https://<domain>/admin/  # 200
    ```
    Then open the domain in a browser. The page is styled, and DevTools → Console shows no mixed-content warnings.

- [ ] **R9. Record results and commit**
  - Fill in the table below (no passwords or database URLs). Then:
    ```bash
    git add docs/superpowers/plans/2026-10-08-railway-migration.md
    git commit -m "docs: record Railway migration results

    Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
    git push origin main
    ```

### Results

| Item | Value |
|---|---|
| Postgres service name / version (R1) | |
| Web service source repo / branch (R1) | |
| Build used uv + Python 3.12 (R7) | |
| Public domain (R8) | |
| R8 checks all passed (date) | |

## Out of scope (decide separately)

- **The Azure VM** (`vm-career-platform`) keeps running and still serves `http://20.80.7.163` with its own SQLite copy. Keep it as a fallback until R8 passes. Then deallocate or delete it, which is a separate, destructive step.
- **Schema migrations.** `create_all` only creates missing tables and never alters existing ones. The first model change after this migration needs Alembic (or a hand-written `ALTER TABLE`).
- Custom domain, Postgres backups/retention settings, and moving `seed_resume.py` data into the repo.
