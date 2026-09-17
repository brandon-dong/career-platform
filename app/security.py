from fastapi import HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import ADMIN_PASSWORD, ADMIN_USERNAME

security = HTTPBasic()


def verify_admin(credentials: HTTPBasicCredentials):
    if credentials.username != ADMIN_USERNAME or credentials.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return True
