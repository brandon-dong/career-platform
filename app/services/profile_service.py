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
