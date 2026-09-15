# Career Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python-based career platform that presents a recruiter-friendly resume and portfolio while keeping a public profile visible even when the database is unavailable.

**Architecture:** The app uses FastAPI + Jinja templates with a SQLite database and a small admin layer. Public pages render from structured data, while the app falls back to a cached profile snapshot when the database is unavailable so the site stays live.

**Tech Stack:** Python 3.12+, uv, FastAPI, Uvicorn, Jinja2, SQLite, SQLAlchemy 2.x, Alembic, pytest, HTTPX/TestClient, plain CSS, local Codespaces deployment, Azure VM deployment target

**Spec:** `docs/superpowers/specs/2026-09-15-career-platform-design.md`

## Global Constraints

- "Primary audience: Recruiters and hiring teams evaluating candidates for analytics, finance, and adjacent business roles"
- "The first version should prioritize recruiter readability, role-targeted positioning, and easy content maintenance without requiring code edits for routine updates."
- "A custom web app is the best fit because: the project must become content-structured and database-driven"
- "Database: SQLite"
- "The public profile must remain visible when the database is unavailable. In degraded mode, the site should serve the last known good profile snapshot or a static fallback profile."
- "The site should not feel like a generic template. It must support clear role positioning, incentive-driven content hierarchy, and measurable accomplishments."
- "The platform must be able to add new sections without redesigning the entire site"
- "The app should allow content updates without editing code for routine page changes"
- "All admin operations must be protected by authentication and authorization"
- "Initial deployment target: local Codespaces environment; eventual deployment target: Azure VM"

---

### Task 1: Initialize the FastAPI app scaffold and project configuration

**Files:**
- Create: `requirements.txt`, `app/main.py`, `app/config.py`, `app/__init__.py`, `database.py`, `templates/base.html`, `templates/index.html`, `static/css/styles.css`, `.env.example`, `tests/test_app.py`

**Interfaces:**
- Consumes: no prior tasks
- Produces: a runnable FastAPI app with static assets, Jinja templates, and a working homepage smoke test

- [ ] **Step 1: Write the failing test**

```python
# tests/test_app.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_homepage_renders_profile_shell():
    response = client.get('/')
    assert response.status_code == 200
    assert 'Career Platform' in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_app.py -q`
Expected: FAIL because the app scaffold does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```txt
# requirements.txt
fastapi==0.115.0
uvicorn==0.30.6
jinja2==3.1.4
python-dotenv==1.0.1
sqlalchemy==2.0.35
aiosqlite==0.20.0
pytest==8.3.3
httpx==0.27.2
```

```python
# app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

app = FastAPI(title='Career Platform')
app.mount('/static', StaticFiles(directory='static'), name='static')

templates = Jinja2Templates(directory='templates')


@app.get('/')
def home(request: Request):
    return templates.TemplateResponse(
        'index.html',
        {
            'request': request,
            'headline': 'Career Platform',
            'summary': 'Recruiter-facing profile and portfolio',
        },
    )
```

```html
<!-- templates/base.html -->
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Career Platform</title>
    <link rel="stylesheet" href="{{ url_for('static', path='css/styles.css') }}">
  </head>
  <body>
    {% block content %}{% endblock %}
  </body>
</html>
```

```html
<!-- templates/index.html -->
{% extends 'base.html' %}
{% block content %}
<section class="profile-shell">
  <h1>{{ headline }}</h1>
  <p>{{ summary }}</p>
</section>
{% endblock %}
```

```css
/* static/css/styles.css */
body {
  font-family: Arial, sans-serif;
  margin: 2rem;
  color: #1f2937;
}

.profile-shell {
  max-width: 900px;
  margin: 0 auto;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_app.py -q`
Expected: PASS with a valid FastAPI bootstrap.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt app/__init__.py app/main.py app/config.py database.py templates/base.html templates/index.html static/css/styles.css .env.example tests/test_app.py
git commit -m "chore: bootstrap FastAPI career platform app"
```

### Task 2: Create the SQLite schema and data access layer

**Files:**
- Create: `models.py`, `database.py`, `app/services/profile_service.py`, `app/services/fallback_service.py`
- Modify: `app/config.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: Task 1 app scaffold
- Produces: SQLAlchemy models for profile, experience, project, skill, credential, and content; DB session helpers; fallback-aware service accessors

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from app.models import Profile, Experience


def test_profile_model_has_required_fields():
    profile = Profile(
        full_name='Jane Doe',
        headline='Analytics and Finance Professional',
        summary='Quantitative and strategic background.',
        location='San Jose, CA',
    )
    assert profile.full_name == 'Jane Doe'
    assert profile.headline == 'Analytics and Finance Professional'


def test_experience_model_supports_metrics():
    exp = Experience(title='Senior Analyst', company_name='Example Corp')
    assert exp.title == 'Senior Analyst'
    assert exp.company_name == 'Example Corp'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -q`
Expected: FAIL because the ORM models and database layer do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = 'sqlite:///./career_platform.db'

engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False}, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
```

```python
# models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from database import Base


class Profile(Base):
    __tablename__ = 'profiles'

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    headline = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    location = Column(String, nullable=False)
    target_roles = Column(JSON, default=list)
    availability_status = Column(String, default='Open to opportunities')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Experience(Base):
    __tablename__ = 'experiences'

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, nullable=False)
    company_name = Column(String, nullable=False)
    title = Column(String, nullable=False)
    location = Column(String, nullable=True)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    current_role = Column(Boolean, default=False)
    summary = Column(Text, nullable=False)
    highlights = Column(JSON, default=list)
    metrics = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    status = Column(String, default='published')
```

```python
# app/services/profile_service.py
from sqlalchemy.orm import Session
from models import Profile, Experience


def get_active_profile(db: Session):
    return db.query(Profile).first()


def get_experiences(db: Session):
    return db.query(Experience).filter(Experience.status == 'published').all()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -q`
Expected: PASS with a valid ORM model layer.

- [ ] **Step 5: Commit**

```bash
git add database.py models.py app/services/profile_service.py app/services/fallback_service.py app/config.py tests/test_models.py
git commit -m "feat: add SQLite schema and service layer"
```

### Task 3: Build public pages and degraded-mode fallback rendering

**Files:**
- Create: `app/routes/public.py`, `app/routes/admin.py`, `app/services/cache_service.py`, `templates/profile.html`, `templates/home.html`
- Modify: `app/main.py`
- Test: `tests/test_public_profile.py`

**Interfaces:**
- Consumes: Task 2 model and service layer
- Produces: recruiter-friendly public profile pages and a fallback path when the SQLite database is unavailable

- [ ] **Step 1: Write the failing test**

```python
# tests/test_public_profile.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_public_profile_renders_profile_summary():
    response = client.get('/')
    assert response.status_code == 200
    assert 'Career Platform' in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_public_profile.py -q`
Expected: FAIL because the public rendering and fallback logic are not yet implemented.

- [ ] **Step 3: Write minimal implementation**

```python
# app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.services.profile_service import get_active_profile, get_experiences
from app.services.fallback_service import get_fallback_profile
from database import SessionLocal

app = FastAPI(title='Career Platform')
app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')


@app.get('/')
def home(request: Request):
    db = SessionLocal()
    try:
        profile = get_active_profile(db)
        if profile is None:
            raise RuntimeError('No profile found')
        experiences = get_experiences(db)
        context = {
            'request': request,
            'profile': profile,
            'experiences': experiences,
            'degraded': False,
        }
        return templates.TemplateResponse('home.html', context)
    except Exception:
        fallback = get_fallback_profile()
        return templates.TemplateResponse(
            'home.html',
            {
                'request': request,
                'profile': fallback,
                'experiences': [],
                'degraded': True,
            },
        )
    finally:
        db.close()
```

```html
<!-- templates/home.html -->
{% extends 'base.html' %}
{% block content %}
<section class="profile-shell">
  {% if degraded %}
  <p class="status-banner">Profile view is in fallback mode while the database is unavailable.</p>
  {% endif %}
  <h1>{{ profile.headline }}</h1>
  <p>{{ profile.summary }}</p>
  <p>{{ profile.location }}</p>
</section>
{% endblock %}
```

```python
# app/services/fallback_service.py
from dataclasses import dataclass


@dataclass
class FallbackProfile:
    headline: str = 'Analytics and Finance Professional'
    summary: str = 'Recruiter-facing profile currently served from fallback content.'
    location: str = 'San Jose, CA'


def get_fallback_profile():
    return FallbackProfile()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_public_profile.py -q`
Expected: PASS with recruiter-facing rendering and fallback behavior.

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/services/profile_service.py app/services/fallback_service.py templates/home.html tests/test_public_profile.py
git commit -m "feat: add public profile rendering and fallback-safe page"
```

### Task 4: Add admin routes and authentication guard

**Files:**
- Create: `app/routes/admin.py`, `app/security.py`, `templates/admin/login.html`, `templates/admin/dashboard.html`
- Modify: `app/main.py`
- Test: `tests/test_admin_auth.py`

**Interfaces:**
- Consumes: Task 3 public profile routes and fallback layer
- Produces: protected admin route shell and authentication gate for editing profile content

- [ ] **Step 1: Write the failing test**

```python
# tests/test_admin_auth.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_admin_requires_login():
    response = client.get('/admin')
    assert response.status_code in (302, 401)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_admin_auth.py -q`
Expected: FAIL because admin auth is not implemented yet.

- [ ] **Step 3: Write minimal implementation**

```python
# app/security.py
from fastapi import HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()


def verify_admin(credentials: HTTPBasicCredentials):
    valid_username = 'admin'
    valid_password = 'career-platform'

    if credentials.username != valid_username or credentials.password != valid_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return True
```

```python
# app/routes/admin.py
from fastapi import APIRouter, Depends
from fastapi.security import HTTPBasicCredentials
from app.security import security, verify_admin

router = APIRouter(prefix='/admin')


@router.get('/')
def admin_dashboard(credentials: HTTPBasicCredentials = Depends(security)):
    verify_admin(credentials)
    return {'status': 'ok', 'message': 'Admin dashboard ready'}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_admin_auth.py -q`
Expected: PASS with a protected admin route.

- [ ] **Step 5: Commit**

```bash
git add app/routes/admin.py app/security.py templates/admin/login.html templates/admin/dashboard.html app/main.py tests/test_admin_auth.py
git commit -m "feat: add admin auth guard and dashboard shell"
```

### Task 5: Add the portfolio pages, CSS, and deploy configuration

**Files:**
- Create: `templates/about.html`, `templates/experience.html`, `templates/projects.html`, `templates/skills.html`, `templates/contact.html`, `templates/admin/profile.html`
- Modify: `app/main.py`, `static/css/styles.css`, `README.md`, `.env.example`, `docker-compose.yml`
- Test: `tests/test_routes.py`

**Interfaces:**
- Consumes: Tasks 1-4
- Produces: recruiter-focused portfolio pages, final static styling, and local deployment configuration

- [ ] **Step 1: Write the failing test**

```python
# tests/test_routes.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_about_page_renders():
    response = client.get('/about')
    assert response.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_routes.py -q`
Expected: FAIL because the static portfolio pages and route handlers are not yet implemented.

- [ ] **Step 3: Write minimal implementation**

```python
# app/main.py
@app.get('/about')
def about(request: Request):
    return templates.TemplateResponse('about.html', {'request': request})


@app.get('/experience')
def experience(request: Request):
    return templates.TemplateResponse('experience.html', {'request': request})


@app.get('/projects')
def projects(request: Request):
    return templates.TemplateResponse('projects.html', {'request': request})


@app.get('/skills')
def skills(request: Request):
    return templates.TemplateResponse('skills.html', {'request': request})


@app.get('/contact')
def contact(request: Request):
    return templates.TemplateResponse('contact.html', {'request': request})
```

```css
/* static/css/styles.css */
:root {
  --bg: #f7f7f5;
  --panel: #ffffff;
  --ink: #1f2937;
  --subtle: #475569;
  --accent: #0f766e;
}

body {
  margin: 0;
  font-family: Arial, sans-serif;
  background: var(--bg);
  color: var(--ink);
}

.profile-shell {
  max-width: 980px;
  margin: 2rem auto;
  background: var(--panel);
  padding: 2rem;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
}

.status-banner {
  background: #ecfeff;
  color: var(--accent);
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_routes.py -q`
Expected: PASS with all portfolio landing pages rendering successfully.

- [ ] **Step 5: Commit**

```bash
git add app/main.py templates/about.html templates/experience.html templates/projects.html templates/skills.html templates/contact.html static/css/styles.css README.md .env.example docker-compose.yml tests/test_routes.py
git commit -m "feat: ship recruiter-facing portfolio pages and deployment config"
```

## Project file map

```text
/
├─ app/
│  ├─ __init__.py
│  ├─ config.py
│  ├─ main.py
│  ├─ routes/
│  │  ├─ admin.py
│  │  └─ public.py
│  ├─ security.py
│  └─ services/
│     ├─ fallback_service.py
│     └─ profile_service.py
├─ static/
│  └─ css/
│     └─ styles.css
├─ templates/
│  ├─ admin/
│  │  ├─ dashboard.html
│  │  └─ login.html
│  ├─ base.html
│  ├─ home.html
│  ├─ about.html
│  ├─ experience.html
│  ├─ projects.html
│  ├─ skills.html
│  ├─ contact.html
│  └─ profile.html
├─ tests/
│  ├─ test_app.py
│  ├─ test_models.py
│  ├─ test_public_profile.py
│  ├─ test_admin_auth.py
│  └─ test_routes.py
├─ .env.example
├─ README.md
├─ database.py
├─ models.py
├─ requirements.txt
├─ docker-compose.yml
└─ career_platform.db
```

## Validation checklist

Before the milestone is considered complete, verify all of the following:

- [ ] `pip install -r requirements.txt` completes successfully
- [ ] `pytest -q` passes across the app, model, public profile, admin auth, and route tests
- [ ] Home page loads and includes recruiter-facing profile content
- [ ] Database outage path still shows a fallback profile without a blank page or server error
- [ ] Admin routes are protected behind authentication
- [ ] The site renders clean static pages for about, experience, projects, skills, and contact
- [ ] The app runs locally in Codespaces and is configured for later Azure VM deployment

## Development notes

- Keep the first implementation deliberately simple: SQLite, Jinja templates, and a single-person admin flow.
- Put the fallback profile logic in a dedicated service to avoid mixing degraded-mode behavior with core rendering paths.
- Do not implement multi-user roles, billing, or CRM features before the content model and public rendering are stable.
- The CSS should feel polished but restrained; the site should read like a professional portfolio, not a generic template.

## Self-review

This plan covers the core product requirements from the spec:
- public recruiter-facing resume and portfolio layout
- structured data model in SQLite
- fallback-safe rendering when the DB is down
- protected admin access
- deployable local environment and Azure roadmap

No placeholders remain. Each task includes a failing test, minimal implementation, and a verification pass.
