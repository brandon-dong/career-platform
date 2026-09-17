from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    short_description = Column(Text, nullable=False)
    problem_statement = Column(Text, nullable=False)
    solution_summary = Column(Text, nullable=False)
    tools = Column(JSON, default=list)
    impact_summary = Column(Text, nullable=False)
    links = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    status = Column(String, default='published')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Skill(Base):
    __tablename__ = 'skills'

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, nullable=False)
    category = Column(String, nullable=False)
    name = Column(String, nullable=False)
    proficiency = Column(String, nullable=True)
    years_experience = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String, default='published')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Credential(Base):
    __tablename__ = 'credentials'

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, nullable=False)
    credential_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    issuer = Column(String, nullable=False)
    date_earned = Column(String, nullable=True)
    expiration_date = Column(String, nullable=True)
    status = Column(String, default='published')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ContentPiece(Base):
    __tablename__ = 'content_pieces'

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, nullable=False)
    piece_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True)
    excerpt = Column(Text, nullable=True)
    body_markdown = Column(Text, nullable=False)
    status = Column(String, default='draft')
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ContactSubmission(Base):
    __tablename__ = 'contact_submissions'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    company = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    processed = Column(Boolean, default=False)
