from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    username = Column(String(100), unique=True, index=True, nullable=True)
    profession = Column(String(100), default="Freelancer", nullable=True)
    role = Column(String(50), default="user", nullable=False) # "user" or "admin"
    status = Column(String(50), default="active", nullable=False) # "active" or "suspended"
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    last_password_change = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # One-to-one relationship to settings
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")

