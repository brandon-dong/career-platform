from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.routes.admin import router as admin_router
from app.services.fallback_service import get_fallback_profile
from app.services.profile_service import get_active_profile, get_experiences
from database import SessionLocal

app = FastAPI(title='Career Platform')
app.mount('/static', StaticFiles(directory='static'), name='static')
app.include_router(admin_router)

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
