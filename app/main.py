from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.config import CONTACT_EMAIL, LINKEDIN_URL
from app.formatting import format_month
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
# Railway ends HTTPS at its edge and forwards plain HTTP. Trusting its
# X-Forwarded-Proto header makes url_for() build https:// links.
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts='*')
app.mount('/static', StaticFiles(directory='static'), name='static')
app.include_router(admin_router)

templates = Jinja2Templates(directory='templates')
templates.env.filters['month'] = format_month
templates.env.globals['contact'] = {'email': CONTACT_EMAIL, 'linkedin': LINKEDIN_URL}


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
