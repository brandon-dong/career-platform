from fastapi import APIRouter, Depends
from fastapi.security import HTTPBasicCredentials

from app.security import security, verify_admin

router = APIRouter(prefix='/admin')


@router.get('/')
def admin_dashboard(credentials: HTTPBasicCredentials = Depends(security)):
    verify_admin(credentials)
    return {'status': 'ok', 'message': 'Admin dashboard ready'}
