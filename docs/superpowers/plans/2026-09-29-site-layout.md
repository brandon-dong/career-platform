# Site Layout and Data-Driven Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every public page a header with the owner's name and navigation, a real stylesheet, and database-driven content under proper headings, while keeping every page up when the database fails.

**Architecture:** New published-only query functions live in `app/services/profile_service.py`. A single `render_page()` helper in `app/main.py` loads the profile plus each page's named loaders and falls back to `FallbackProfile` with empty collections on any error. Templates extend a new `base.html` that renders the header, nav, degraded banner, and footer.

**Tech Stack:** Python 3.12, FastAPI 0.115.0, Jinja2 3.1.4, SQLAlchemy 2.0.35, SQLite, pytest 8.3.3, httpx 0.27.2 (TestClient), uv.

**Spec:** `docs/superpowers/specs/2026-09-29-site-layout-design.md` (parent: `docs/superpowers/specs/2026-09-15-career-platform-design.md`)

## Global Constraints

- No new dependencies; `pyproject.toml` and `uv.lock` do not change.
- No JavaScript, CSS frameworks, or web fonts. System font stack only.
- `<title>Career Platform</title>` stays in `base.html` (existing test `test_homepage_renders_profile_shell` asserts `'Career Platform'`).
- Public pages show only rows with `status == 'published'`.
- Every public route returns HTTP 200 when the database fails, showing exactly: `Profile view is in fallback mode while the database is unavailable.`
- Nav order and hrefs: Home `/`, About `/about`, Experience `/experience`, Projects `/projects`, Skills `/skills`, Credentials `/credentials`, Contact `/contact`.
- Tests must never read or write `career_platform.db` or `data/career_platform.db`.
- Run tests with `uv run pytest` from the repo root. On this laptop, Git Bash may not find `uv` until a new terminal is opened; PowerShell with a refreshed PATH works.
- Work on branch `feature/site-layout`. Commit messages end with the `Co-Authored-By` line in use for this repo.

## Review Focus

1. **Optional fields are empty** (experience `location`, `start_date`, or `highlights` is `None`; project `tools` is `None`) — the card still renders, with no literal `None` and no dangling separator. Test: Task 3 `test_experience_card_handles_missing_optional_fields`.
2. **Data contains HTML special characters** (e.g. the real headline has `&`) — it is escaped exactly once, never raw and never double-escaped. Test: Task 3 `test_profile_text_is_escaped_once`.
3. **Tables exist but no profile row** (fresh database) — every page returns 200 with the fallback banner, not a 500. Test: Task 2 `test_every_page_shows_fallback_when_no_profile`.
4. **A credential has a type other than education/certification/award** (e.g. `training`) — it still appears, under "Other credentials", instead of silently disappearing. Test: Task 3 `test_unknown_credential_type_is_listed_under_other`.
5. **Profile exists but has no experiences** — Home renders without the Current focus card. Test: Task 3 `test_home_without_experiences_has_no_focus_card`.

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `tests/conftest.py` (create) | Isolated temp database per test, fictional seed data, broken-database fixture | 1 |
| `app/services/profile_service.py` (modify) | Published-only, ordered queries for each collection | 1 |
| `tests/test_profile_service.py` (create) | Query filtering and ordering | 1 |
| `app/services/fallback_service.py` (modify) | Fallback profile has every field templates read | 2 |
| `app/main.py` (modify) | `render_page()` helper; all routes including `/credentials` | 2, 3 |
| `templates/base.html` (modify) | Header, nav with active marker, banner, footer | 2 |
| `templates/credentials.html` (create) | Credentials page | 2 (stub), 3 (content) |
| `static/css/styles.css` (modify) | Full site styles | 2 |
| `tests/test_layout.py` (create) | Header/nav on every page, degraded mode on every page | 2 |
| `app/formatting.py` (create) | `format_month()` Jinja filter | 3 |
| `templates/home.html`, `about.html`, `experience.html`, `projects.html`, `skills.html` (modify) | Page content | 3 |
| `tests/test_pages.py` (create) | Per-page content, filter, Review Focus cases | 3 |

---

### Task 1: Test harness and published-only queries

**Files:**
- Create: `tests/conftest.py`
- Modify: `app/services/profile_service.py`
- Test: `tests/test_profile_service.py`

**Interfaces:**
- Consumes: `database.Base`, `app.models.{Profile, Experience, Project, Skill, Credential}`, module global `app.main.SessionLocal`.
- Produces:
  - Fixture `session_factory` (autouse) → a `sessionmaker` bound to a temp SQLite file with all tables created; also patched into `app.main.SessionLocal`.
  - Fixture `seeded` → inserts the fictional data below; returns `None`.
  - Fixture `broken_db` → patches `app.main.SessionLocal` with a class whose `query()` raises `RuntimeError('database unavailable')` and whose `close()` does nothing.
  - `get_experiences(db) -> list[Experience]`: published only, `current_role` desc then `start_date` desc.
  - `get_projects(db) -> list[Project]`: published only, by `id`.
  - `get_skills(db) -> list[Skill]`: published only, by `category` then `id`.
  - `get_credentials(db) -> list[Credential]`: published only, by `credential_type` then `id`.

Seed data (`seeded`): profile "Test Person" (headline "Test Headline", summary "Test summary text.", location "Testville, CA", target_roles `['Data Analyst', 'Financial Analyst']`, availability "Open to opportunities"); experiences Acme Corp (Analyst, Austin, TX, 2024-01–2024-06, past, highlight "Built the Acme forecast model"), Globex (Senior Analyst, Remote, from 2025-02, current, highlight "Led the Globex pricing study"), Initech (**draft**); projects Widget Analysis (published, tools Python/SQL) and Secret Draft (**draft**); skills tools/Python, tools/SQL, finance/Valuation, tools/Hidden Skill (**draft**); credentials education "B.S. Testing" (Test University, May 2027) and certification "Excel Expert" (Microsoft).

- [ ] **Step 1: Write the fixtures**

Create `tests/conftest.py`:

```python
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


@pytest.fixture
def broken_db(monkeypatch):
    class BrokenSession:
        def query(self, *args, **kwargs):
            raise RuntimeError('database unavailable')

        def close(self):
            pass

    monkeypatch.setattr(app_main, 'SessionLocal', BrokenSession)
```

- [ ] **Step 2: Write the failing query tests**

Create `tests/test_profile_service.py`:

```python
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
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/test_profile_service.py -v`
Expected: collection ERROR — `ImportError: cannot import name 'get_credentials' from 'app.services.profile_service'`.

- [ ] **Step 4: Implement the queries**

Replace `app/services/profile_service.py` with:

```python
from sqlalchemy.orm import Session

from app.models import Credential, Experience, Profile, Project, Skill

PUBLISHED = 'published'


def get_active_profile(db: Session):
    return db.query(Profile).first()


def get_experiences(db: Session):
    return (
        db.query(Experience)
        .filter(Experience.status == PUBLISHED)
        .order_by(Experience.current_role.desc(), Experience.start_date.desc())
        .all()
    )


def get_projects(db: Session):
    return db.query(Project).filter(Project.status == PUBLISHED).order_by(Project.id).all()


def get_skills(db: Session):
    return (
        db.query(Skill)
        .filter(Skill.status == PUBLISHED)
        .order_by(Skill.category, Skill.id)
        .all()
    )


def get_credentials(db: Session):
    return (
        db.query(Credential)
        .filter(Credential.status == PUBLISHED)
        .order_by(Credential.credential_type, Credential.id)
        .all()
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_profile_service.py -v`
Expected: 4 passed.

- [ ] **Step 6: Run the full suite and confirm no stray database file**

Run: `rm -f career_platform.db && uv run pytest && ls career_platform.db`
Expected: 9 passed; then `ls: cannot access 'career_platform.db': No such file or directory` (the autouse fixture keeps every test off the real database).

- [ ] **Step 7: Commit**

```bash
git add tests/conftest.py tests/test_profile_service.py app/services/profile_service.py
git commit -m "feat: add published-only queries and isolated test database"
```

---

### Task 2: Shared layout, render_page, and degraded mode on every page

**Files:**
- Modify: `app/main.py`, `app/services/fallback_service.py`, `templates/base.html`, `templates/home.html`, `static/css/styles.css`
- Create: `templates/credentials.html`
- Test: `tests/test_layout.py`

**Interfaces:**
- Consumes: fixtures `session_factory`, `seeded`, `broken_db`; `get_active_profile`, `get_experiences`, `get_projects`, `get_skills`, `get_credentials` from Task 1.
- Produces:
  - `render_page(request, template, **loaders)` in `app/main.py`; templates always receive `request`, `profile`, `degraded`, plus one variable per loader name (a list; `[]` when degraded).
  - Template variable names: `experiences` (on `/` and `/experience`), `projects`, `skills`, `credentials`.
  - `FallbackProfile` fields: `full_name='Career Platform'`, `headline`, `summary`, `location`, `availability_status=''`, `target_roles=[]`.
  - `base.html` markup that Task 3 tests rely on: `<a class="site-name" href="/">{{ profile.full_name }}</a>`; nav links rendered as `<a href="HREF">LABEL</a>` with ` aria-current="page"` inserted before `>` on the current page; banner `<p class="status-banner">…</p>` inside `<main class="container">`.
  - CSS classes available to Task 3: `card`, `card-head`, `meta`, `dates`, `headline`, `lead`, `tags`, `tag`, `plain`, `actions`, `button`, `button-secondary`, `empty`, `hero`.

- [ ] **Step 1: Write the failing layout tests**

Create `tests/test_layout.py`:

```python
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PAGES = ['/', '/about', '/experience', '/projects', '/skills', '/credentials', '/contact']
BANNER = 'Profile view is in fallback mode while the database is unavailable.'


@pytest.mark.parametrize('path', PAGES)
def test_every_page_has_header_with_name_and_nav(seeded, path):
    response = client.get(path)
    assert response.status_code == 200
    assert '<a class="site-name" href="/">Test Person</a>' in response.text
    for href in PAGES:
        assert f'href="{href}"' in response.text
    assert BANNER not in response.text


def test_current_page_is_marked_in_nav(seeded):
    response = client.get('/skills')
    assert '<a href="/skills" aria-current="page">Skills</a>' in response.text
    assert response.text.count('aria-current="page"') == 1


@pytest.mark.parametrize('path', PAGES)
def test_every_page_survives_database_failure(broken_db, path):
    response = client.get(path)
    assert response.status_code == 200
    assert BANNER in response.text
    assert 'database unavailable' not in response.text


@pytest.mark.parametrize('path', PAGES)
def test_every_page_shows_fallback_when_no_profile(path):
    response = client.get(path)
    assert response.status_code == 200
    assert BANNER in response.text
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_layout.py -v`
Expected: FAIL — header assertions fail on every page (no `site-name` link), `/credentials` returns 404, and the degraded tests fail on every page except `/`.

- [ ] **Step 3: Give the fallback profile every field templates read**

Replace `app/services/fallback_service.py` with:

```python
from dataclasses import dataclass, field


@dataclass
class FallbackProfile:
    full_name: str = 'Career Platform'
    headline: str = 'Analytics and Finance Professional'
    summary: str = 'Recruiter-facing profile currently served from fallback content.'
    location: str = 'San Jose, CA'
    availability_status: str = ''
    target_roles: list = field(default_factory=list)


def get_fallback_profile():
    return FallbackProfile()
```

- [ ] **Step 4: Add render_page and route every page through it**

Replace `app/main.py` with:

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.routes.admin import router as admin_router
from app.services.fallback_service import get_fallback_profile
from app.services.profile_service import (
    get_active_profile,
    get_credentials,
    get_experiences,
    get_projects,
    get_skills,
)
from database import SessionLocal

app = FastAPI(title='Career Platform')
app.mount('/static', StaticFiles(directory='static'), name='static')
app.include_router(admin_router)

templates = Jinja2Templates(directory='templates')


def render_page(request: Request, template: str, **loaders):
    db = SessionLocal()
    try:
        profile = get_active_profile(db)
        if profile is None:
            raise RuntimeError('No profile found')
        data = {name: load(db) for name, load in loaders.items()}
        degraded = False
    except Exception:
        profile = get_fallback_profile()
        data = {name: [] for name in loaders}
        degraded = True
    finally:
        db.close()
    return templates.TemplateResponse(
        template,
        {'request': request, 'profile': profile, 'degraded': degraded, **data},
    )


@app.get('/')
def home(request: Request):
    return render_page(request, 'home.html', experiences=get_experiences)


@app.get('/about')
def about(request: Request):
    return render_page(request, 'about.html')


@app.get('/experience')
def experience(request: Request):
    return render_page(request, 'experience.html', experiences=get_experiences)


@app.get('/projects')
def projects(request: Request):
    return render_page(request, 'projects.html', projects=get_projects)


@app.get('/skills')
def skills(request: Request):
    return render_page(request, 'skills.html', skills=get_skills)


@app.get('/credentials')
def credentials(request: Request):
    return render_page(request, 'credentials.html', credentials=get_credentials)


@app.get('/contact')
def contact(request: Request):
    return render_page(request, 'contact.html')
```

- [ ] **Step 5: Write the shared layout**

Replace `templates/base.html` with:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Career Platform</title>
    <link rel="stylesheet" href="{{ url_for('static', path='css/styles.css') }}">
  </head>
  <body>
    {% set nav_links = [('/', 'Home'), ('/about', 'About'), ('/experience', 'Experience'), ('/projects', 'Projects'), ('/skills', 'Skills'), ('/credentials', 'Credentials'), ('/contact', 'Contact')] %}
    <header class="site-header">
      <div class="container header-inner">
        <a class="site-name" href="/">{{ profile.full_name }}</a>
        <nav aria-label="Main">
          {% for href, label in nav_links %}
          <a href="{{ href }}"{% if request.url.path == href %} aria-current="page"{% endif %}>{{ label }}</a>
          {% endfor %}
        </nav>
      </div>
    </header>
    <main class="container">
      {% if degraded %}
      <p class="status-banner">Profile view is in fallback mode while the database is unavailable.</p>
      {% endif %}
      {% block content %}{% endblock %}
    </main>
    <footer class="site-footer">
      <div class="container">&copy; 2026 {{ profile.full_name }}</div>
    </footer>
  </body>
</html>
```

Replace `templates/home.html` with (banner moved to `base.html`; full content comes in Task 3):

```html
{% extends 'base.html' %}
{% block content %}
<section class="hero">
  <h1>{{ profile.headline }}</h1>
  <p>{{ profile.summary }}</p>
  <p>{{ profile.location }}</p>
</section>
{% endblock %}
```

Create `templates/credentials.html` (content comes in Task 3):

```html
{% extends 'base.html' %}
{% block content %}
<h1>Credentials</h1>
{% endblock %}
```

- [ ] **Step 6: Write the stylesheet**

Replace `static/css/styles.css` with:

```css
:root {
  --text: #1f2937;
  --muted: #6b7280;
  --accent: #1e3a5f;
  --border: #e5e7eb;
  --soft: #f8fafc;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, "Helvetica Neue", Arial, sans-serif;
  color: var(--text);
  background: #fff;
  line-height: 1.6;
}

a { color: var(--accent); }

.container { max-width: 900px; margin: 0 auto; padding: 0 16px; }

.site-header { background: var(--accent); color: #fff; }
.header-inner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px 24px;
  padding-top: 16px;
  padding-bottom: 16px;
}
.site-name {
  color: #fff;
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  text-decoration: none;
}
.site-header nav { display: flex; flex-wrap: wrap; gap: 4px 16px; }
.site-header nav a {
  color: #dbe4ee;
  text-decoration: none;
  padding: 2px 0;
  border-bottom: 2px solid transparent;
}
.site-header nav a:hover { color: #fff; }
.site-header nav a[aria-current="page"] { color: #fff; border-bottom-color: #fff; }

main.container { padding-top: 32px; padding-bottom: 48px; }

h1 {
  font-size: 2rem;
  line-height: 1.2;
  margin: 0 0 24px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--border);
}
h2 { font-size: 1.35rem; color: var(--accent); margin: 32px 0 12px; }
h3 { font-size: 1.1rem; margin: 0; }
h4 {
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
  margin: 16px 0 4px;
}

.hero h1 { border-bottom: none; margin-bottom: 8px; padding-bottom: 0; }
.headline { font-size: 1.2rem; margin: 0 0 4px; }
.meta, .dates { color: var(--muted); margin: 4px 0 0; }
.dates { font-size: 0.9rem; white-space: nowrap; }
.lead { margin: 8px 0 0; }

.card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 16px;
  background: #fff;
}
.card-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: baseline;
  gap: 4px 16px;
}
.card ul { margin: 12px 0 0; padding-left: 20px; }

.tags { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 0; }
.tag {
  background: var(--soft);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 2px 12px;
  font-size: 0.9rem;
}

.plain { list-style: none; padding: 0; margin: 0; }
.plain li { padding: 8px 0; border-bottom: 1px solid var(--border); }

.actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 20px; }
.button {
  display: inline-block;
  background: var(--accent);
  color: #fff;
  text-decoration: none;
  padding: 8px 18px;
  border-radius: 6px;
  border: 1px solid var(--accent);
}
.button-secondary { background: #fff; color: var(--accent); }

.status-banner {
  background: #fef3c7;
  border: 1px solid #f59e0b;
  color: #78350f;
  border-radius: 6px;
  padding: 10px 14px;
}
.empty { color: var(--muted); }

.site-footer {
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 0.9rem;
  padding: 20px 0;
}
```

- [ ] **Step 7: Run the layout tests to verify they pass**

Run: `uv run pytest tests/test_layout.py -v`
Expected: 22 passed (7 header + 1 active nav + 7 database failure + 7 no profile).

- [ ] **Step 8: Run the full suite**

Run: `uv run pytest`
Expected: 31 passed (5 original + 4 from Task 1 + 22 from this task).

- [ ] **Step 9: Commit**

```bash
git add app/main.py app/services/fallback_service.py templates/base.html templates/home.html templates/credentials.html static/css/styles.css tests/test_layout.py
git commit -m "feat: add site header, nav, stylesheet, and degraded mode on every page"
```

---

### Task 3: Page content and month filter

**Files:**
- Create: `app/formatting.py`
- Modify: `app/main.py` (register filter), `templates/home.html`, `templates/about.html`, `templates/experience.html`, `templates/projects.html`, `templates/skills.html`, `templates/credentials.html`, `templates/contact.html`
- Test: `tests/test_pages.py`

**Interfaces:**
- Consumes: fixtures `session_factory`, `seeded`; template variables `profile`, `experiences`, `projects`, `skills`, `credentials` and CSS classes from Task 2.
- Produces: `format_month(value: str | None) -> str` in `app/formatting.py`, registered as Jinja filter `month`.

- [ ] **Step 1: Write the failing page tests**

Create `tests/test_pages.py`:

```python
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


def test_experience_lists_current_role_first_with_dates_and_highlights(seeded):
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
    assert 'Current focus' not in response.text
    assert 'Most recent role' not in response.text
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_pages.py -v`
Expected: collection ERROR — `ModuleNotFoundError: No module named 'app.formatting'`.

- [ ] **Step 3: Implement the month filter and register it**

Create `app/formatting.py`:

```python
import re

MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
YEAR_MONTH = re.compile(r'^(\d{4})-(0[1-9]|1[0-2])$')


def format_month(value):
    if not value:
        return 'Present'
    match = YEAR_MONTH.match(value)
    if match is None:
        return value
    return f'{MONTHS[int(match.group(2)) - 1]} {match.group(1)}'
```

In `app/main.py`, add the import after the other `app.` imports:

```python
from app.formatting import format_month
```

and register the filter directly under `templates = Jinja2Templates(directory='templates')`:

```python
templates.env.filters['month'] = format_month
```

- [ ] **Step 4: Run the filter tests to verify they pass**

Run: `uv run pytest tests/test_pages.py -k format_month -v`
Expected: 6 passed.

- [ ] **Step 5: Write the page templates**

Replace `templates/home.html`:

```html
{% extends 'base.html' %}
{% block content %}
<section class="hero">
  <h1>{{ profile.full_name }}</h1>
  <p class="headline">{{ profile.headline }}</p>
  <p class="meta">{{ profile.location }}{% if profile.availability_status %} · {{ profile.availability_status }}{% endif %}</p>
  <p>{{ profile.summary }}</p>
  <p class="actions">
    <a class="button" href="/experience">View experience</a>
    <a class="button button-secondary" href="/projects">View projects</a>
  </p>
</section>
{% if experiences %}
{% set focus = experiences[0] %}
<section>
  <h2>{{ 'Current focus' if focus.current_role else 'Most recent role' }}</h2>
  <article class="card">
    <h3>{{ focus.title }}</h3>
    <p class="meta">{{ focus.company_name }}{% if focus.location %} · {{ focus.location }}{% endif %}</p>
    <p>{{ focus.summary }}</p>
  </article>
</section>
{% endif %}
{% endblock %}
```

Replace `templates/about.html`:

```html
{% extends 'base.html' %}
{% block content %}
<h1>About</h1>
<p>{{ profile.summary }}</p>
{% if profile.target_roles %}
<h2>Target roles</h2>
<p class="tags">{% for role in profile.target_roles %}<span class="tag">{{ role }}</span>{% endfor %}</p>
{% endif %}
<h2>Location &amp; availability</h2>
<p>{{ profile.location }}{% if profile.availability_status %} · {{ profile.availability_status }}{% endif %}</p>
{% endblock %}
```

Replace `templates/experience.html`:

```html
{% extends 'base.html' %}
{% block content %}
<h1>Experience</h1>
{% for e in experiences %}
<article class="card">
  <div class="card-head">
    <h3>{{ e.title }}</h3>
    {% if e.start_date %}<p class="dates">{{ e.start_date|month }} – {% if e.end_date %}{{ e.end_date|month }}{% else %}Present{% endif %}</p>{% endif %}
  </div>
  <p class="meta">{{ e.company_name }}{% if e.location %} · {{ e.location }}{% endif %}</p>
  {% if e.highlights %}
  <ul>{% for h in e.highlights %}<li>{{ h }}</li>{% endfor %}</ul>
  {% else %}
  <p>{{ e.summary }}</p>
  {% endif %}
</article>
{% else %}
<p class="empty">No experience listed yet.</p>
{% endfor %}
{% endblock %}
```

Replace `templates/projects.html`:

```html
{% extends 'base.html' %}
{% block content %}
<h1>Projects</h1>
{% for p in projects %}
<article class="card">
  <h3>{{ p.title }}</h3>
  <p class="lead">{{ p.short_description }}</p>
  <h4>Problem</h4>
  <p>{{ p.problem_statement }}</p>
  <h4>Solution</h4>
  <p>{{ p.solution_summary }}</p>
  <h4>Impact</h4>
  <p>{{ p.impact_summary }}</p>
  {% if p.tools %}
  <p class="tags">{% for tool in p.tools %}<span class="tag">{{ tool }}</span>{% endfor %}</p>
  {% endif %}
</article>
{% else %}
<p class="empty">No projects listed yet.</p>
{% endfor %}
{% endblock %}
```

Replace `templates/skills.html`:

```html
{% extends 'base.html' %}
{% block content %}
<h1>Skills</h1>
{% for group in skills|groupby('category') %}
<section>
  <h2>{{ group.grouper|title }}</h2>
  <p class="tags">{% for skill in group.list %}<span class="tag">{{ skill.name }}</span>{% endfor %}</p>
</section>
{% else %}
<p class="empty">No skills listed yet.</p>
{% endfor %}
{% endblock %}
```

Replace `templates/credentials.html`:

```html
{% extends 'base.html' %}
{% block content %}
{% macro entry(c) %}<li><strong>{{ c.name }}</strong> — {{ c.issuer }}{% if c.date_earned %} · {{ c.date_earned }}{% endif %}</li>{% endmacro %}
{% set sections = [('education', 'Education'), ('certification', 'Certifications'), ('award', 'Awards')] %}
{% set known = sections|map('first')|list %}
<h1>Credentials</h1>
{% for type, heading in sections %}
{% set items = credentials|selectattr('credential_type', 'equalto', type)|list %}
{% if items %}
<section>
  <h2>{{ heading }}</h2>
  <ul class="plain">{% for c in items %}{{ entry(c) }}{% endfor %}</ul>
</section>
{% endif %}
{% endfor %}
{% set other = credentials|rejectattr('credential_type', 'in', known)|list %}
{% if other %}
<section>
  <h2>Other credentials</h2>
  <ul class="plain">{% for c in other %}{{ entry(c) }}{% endfor %}</ul>
</section>
{% endif %}
{% if not credentials %}
<p class="empty">No credentials listed yet.</p>
{% endif %}
{% endblock %}
```

Replace `templates/contact.html`:

```html
{% extends 'base.html' %}
{% block content %}
<h1>Contact</h1>
<p>Recruiter inquiry form coming soon.</p>
{% endblock %}
```

- [ ] **Step 6: Run the page tests to verify they pass**

Run: `uv run pytest tests/test_pages.py -v`
Expected: 17 passed.

- [ ] **Step 7: Run the full suite**

Run: `uv run pytest`
Expected: 48 passed (31 before + 17).

- [ ] **Step 8: Commit**

```bash
git add app/formatting.py app/main.py templates/home.html templates/about.html templates/experience.html templates/projects.html templates/skills.html templates/credentials.html templates/contact.html tests/test_pages.py
git commit -m "feat: render profile, experience, projects, skills, and credentials pages from the database"
```

---

### Task 4: Merge, push, and deploy to the VM

**Files:** none changed. Runs on the laptop (Git Bash) and the VM (`ssh career-vm`, alias from the migration plan).

**Interfaces:**
- Consumes: branch `feature/site-layout` with Tasks 1–3 committed; VM app at `~/career-platform`, uvicorn PID in `~/uvicorn.pid`.
- Produces: `main` on GitHub and on the VM at the merged commit; uvicorn serving it on `127.0.0.1:8000`.

- [ ] **Step 1: Confirm the branch is green and clean**

Run: `git status --short && uv run pytest -q`
Expected: no output from `git status`; `48 passed`.

- [ ] **Step 2: Fast-forward main**

Run: `git switch main && git merge --ff-only feature/site-layout && git log --oneline -1`
Expected: `main` now points at Task 3's commit.

- [ ] **Step 3: Push (STOP — needs the owner's approval; the repo is public)**

Run: `git push origin main`
Check: `git ls-remote origin refs/heads/main` equals `git rev-parse HEAD`.

- [ ] **Step 4: Make sure the VM is running**

Run (PowerShell): `az vm start -g rg-career-platform -n vm-career-platform`
Check: `ssh career-vm hostname` prints `vm-career-platform`.

- [ ] **Step 5: Pull and restart uvicorn on the VM**

```bash
ssh career-vm 'cd ~/career-platform && git pull --ff-only && git log --oneline -1
if test -f ~/uvicorn.pid && kill -0 $(cat ~/uvicorn.pid) 2>/dev/null; then kill $(cat ~/uvicorn.pid); sleep 2; fi
nohup .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 > ~/uvicorn.log 2>&1 < /dev/null &
echo $! > ~/uvicorn.pid
sleep 3; grep "Application startup complete" ~/uvicorn.log'
```

Expected: the merged commit's one-line log, then `INFO:     Application startup complete.`

- [ ] **Step 6: Verify every page on the VM**

```bash
ssh career-vm 'for p in / /about /experience /projects /skills /credentials /contact; do
  printf "%-14s %s\n" "$p" "$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000$p)"; done
curl -s http://127.0.0.1:8000/ | grep -c "fallback mode"
curl -s http://127.0.0.1:8000/ | grep -o "<a class=\"site-name\" href=\"/\">[^<]*</a>"
curl -s http://127.0.0.1:8000/experience | grep -c "Western Express"
curl -s http://127.0.0.1:8000/projects | grep -c "Fintech Consumer Analytics Pipeline"
curl -s http://127.0.0.1:8000/skills | grep -c "<h2>Tools</h2>"
curl -s http://127.0.0.1:8000/credentials | grep -c "<h2>Education</h2>"'
```

Expected: all seven paths `200`; fallback count `0`; `<a class="site-name" href="/">Brandon Dong</a>`; the four counts each `1` or more.

- [ ] **Step 7: Owner checks in the browser**

Start the tunnel on the laptop: `ssh -N -L 8000:127.0.0.1:8000 career-vm`, then open http://localhost:8000 and click through every nav link.
Check: the header, headings, cards, and tags look right on each page; also narrow the window to phone width and confirm the nav wraps under the name.

- [ ] **Step 8: Delete the merged branch**

Run: `git branch -d feature/site-layout`
Expected: `Deleted branch feature/site-layout`.
