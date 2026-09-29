# Site Layout and Data-Driven Pages Design

**Date:** 2026-09-29
**Parent spec:** `docs/superpowers/specs/2026-09-15-career-platform-design.md`
**Status:** Approved in conversation; awaiting written-spec review

## Summary

The public site has no site header or navigation, a two-rule stylesheet, and placeholder text on every page except Home. This change adds a shared header with the owner's name and navigation, a real stylesheet, and makes the About, Experience, Projects, Skills, and a new Credentials page render published database content under proper headings. Every page keeps rendering, with the fallback banner, when the database is unavailable.

## Goals

- Every public page shows a header with the profile's full name and links to all seven primary pages, with the current page marked.
- About, Experience, Projects, Skills, and Credentials show the owner's database content under clear headings.
- Only rows with `status == 'published'` appear on public pages (parent spec §7).
- Every page returns HTTP 200 with the fallback banner when the database fails (parent spec §9).
- Tests never read or write the real database file.

## Non-goals

- Contact form or showing contact details (Contact stays a styled placeholder).
- Project detail pages, role-targeted views, articles.
- Showing experience `metrics` or `tags`.
- Dark mode, JavaScript, CSS frameworks, web fonts, or any new dependency.
- Admin UI changes.

## Decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Scope | Layout **and** real data on pages |
| Credentials placement | Own `/credentials` page and nav link (matches parent spec's page list) |
| Data loading | Approach A: one shared `render_page()` helper; each route names its own loaders |

## Architecture

### Queries — `app/services/profile_service.py`

Keep `get_active_profile(db)`. Change and add:

| Function | Returns |
|---|---|
| `get_experiences(db)` | Published `Experience` rows ordered by `start_date` descending (strings in `YYYY-MM` sort correctly), then `id`. Changed after final review: current-roles-first featured a club role over the owner's newer internship |
| `get_projects(db)` | Published `Project` rows ordered by `id` |
| `get_skills(db)` | Published `Skill` rows ordered by `category`, then `id` |
| `get_credentials(db)` | Published `Credential` rows ordered by `credential_type`, then `id` |

### Page helper — `app/main.py`

```python
def render_page(request, template, **loaders):
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
```

`render_page` must look up `SessionLocal` at call time from `app.main`'s module namespace so tests can replace it.

### Routes

| Route | Template | Loaders |
|---|---|---|
| `/` | `home.html` | `experiences=get_experiences` |
| `/about` | `about.html` | none |
| `/experience` | `experience.html` | `experiences=get_experiences` |
| `/projects` | `projects.html` | `projects=get_projects` |
| `/skills` | `skills.html` | `skills=get_skills` |
| `/credentials` (new) | `credentials.html` (new) | `credentials=get_credentials` |
| `/contact` | `contact.html` | none |

Templates receive `request.url.path` through `request` for active-nav marking.

### Fallback profile — `app/services/fallback_service.py`

Add `full_name: str = 'Career Platform'` and `target_roles: list = field(default_factory=list)` and `availability_status: str = ''` to `FallbackProfile` so every template can render in degraded mode without attribute errors.

### Month filter

A Jinja filter `month` registered on `templates.env.filters`:

| Input | Output |
|---|---|
| `'2026-06'` | `'Jun 2026'` |
| `None` or `''` | `'Present'` |
| anything not matching `YYYY-MM` (e.g. `'2025'`) | returned unchanged |

## Layout

### `base.html` (every page)

- `<title>Career Platform</title>` stays (an existing test asserts it).
- `<header class="site-header">`: the profile's `full_name` linking to `/`, then `<nav>` with links in this order: Home, About, Experience, Projects, Skills, Credentials, Contact. The link whose path equals `request.url.path` gets `aria-current="page"`.
- `<main class="container">` holds the page block. The degraded banner renders here, in `base.html`, for every page (moved out of `home.html`).
- `<footer>`: `© 2026 {{ profile.full_name }}`.

### Styles — `static/css/styles.css`

- System font stack; body text `#1f2937` on white; accent navy `#1e3a5f`.
- Header: navy background, white name and links, active link underlined; nav wraps below the name under 640px wide.
- Content max width 900px, centered, 16px side padding on small screens.
- `h1` page title with a bottom border; `h2` section headings; `h3` card titles.
- `.card`: light border, rounded corners, padding, spacing between cards.
- `.tag`: small rounded pill used for target roles, project tools, and skills.
- `.status-banner`: amber background for degraded mode.
- `.button`: navy link-button for the Home calls to action.

### Page content

| Page | Content |
|---|---|
| Home | `h1` full name; headline; "location · availability_status"; summary; a **Current focus** card for the first experience (hidden if none); buttons to `/experience` and `/projects` |
| About | `h1` About; summary; **Target roles** as tags (section hidden if empty); **Location & availability** |
| Experience | `h1` Experience; one card per experience: title, "company · location", "start – end" via `month`, highlights as a bulleted list. Empty: "No experience listed yet." |
| Projects | `h1` Projects; one card per project: title, short description, **Problem**, **Solution**, **Impact** subheadings, tools as tags. Empty: "No projects listed yet." |
| Skills | `h1` Skills; one `h2` per category (title-cased) with skills as tags. Empty: "No skills listed yet." |
| Credentials | `h1` Credentials; `h2` sections **Education** (`education`), **Certifications** (`certification`), **Awards** (`award`), each entry "name — issuer · date"; a section with no entries is not rendered. Empty overall: "No credentials listed yet." |
| Contact | `h1` Contact; "Recruiter inquiry form coming soon." |

## Testing

### Fixture — `tests/conftest.py`

- An autouse fixture creates a temporary SQLite file, runs `Base.metadata.create_all`, and monkeypatches `app.main.SessionLocal` to a sessionmaker bound to it — so no test touches `career_platform.db` in the repo or `data/`.
- A `seeded` fixture inserts fictional data: profile "Test Person"; experiences "Acme Corp" (past, `2024-01`–`2024-06`) and "Globex" (current, from `2025-02`) with highlights; one published project "Widget Analysis" and one **draft** project "Secret Draft"; skills in categories `tools` and `finance`; one `education`, one `certification`, zero `award` credentials.
- A `broken_db` fixture monkeypatches `app.main.SessionLocal` to one whose session raises on query.

### Tests

| Test | Asserts |
|---|---|
| Header on every page | Each of the 7 routes: 200, contains "Test Person" in the header and all 7 nav hrefs |
| Active nav | `/skills` response has `aria-current="page"` on the Skills link only |
| Experience | "Globex" appears before "Acme Corp"; a highlight bullet appears; "Feb 2025 – Present" appears |
| Projects | "Widget Analysis", "Problem", "Solution", "Impact" appear; "Secret Draft" does not |
| Skills | "Tools" and "Finance" headings appear with their skills |
| Credentials | "Education" and "Certifications" headings appear; "Awards" does not |
| Degraded | With `broken_db`, each of the 7 routes returns 200 and contains the fallback banner text |
| Month filter | `'2026-06'`→`'Jun 2026'`, `None`→`'Present'`, `''`→`'Present'`, `'2025'`→`'2025'` |

The existing 5 tests must keep passing. Full suite: `uv run pytest`.

## Deployment

1. Implement on `feature/site-layout`; merge to `main` and push after approval.
2. On the VM: `git pull --ff-only`, stop uvicorn (`kill $(cat ~/uvicorn.pid)`), start it again with migration-plan step Pr1. No dependency changes.
3. Verify on the VM with `curl`: all 7 routes return 200, no fallback banner, and each page contains its headings and the owner's data; then the owner checks through the SSH tunnel.
