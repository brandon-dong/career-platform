from sqlalchemy.orm import Session

from app.models import Experience, Profile


def get_active_profile(db: Session):
    return db.query(Profile).first()


def get_experiences(db: Session):
    return db.query(Experience).filter(Experience.status == 'published').all()
