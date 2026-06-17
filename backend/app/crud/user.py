from sqlalchemy.orm import Session
from typing import Optional
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    Retrieves a user by their unique primary key.
    """
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Retrieves a user by their registered email address.
    """
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, obj_in: UserCreate) -> User:
    """
    Registers a new user inside the database, securely hashing their password.
    """
    db_obj = User(
        email=obj_in.email.lower().strip(),
        hashed_password=get_password_hash(obj_in.password),
        full_name=obj_in.full_name,
        role="user", # Default role is "user". We can manually change to "admin" in DB for test admins.
        is_active=True,
        is_verified=False
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def authenticate(db: Session, email: str, password: str) -> Optional[User]:
    """
    Validates user credentials. Returns the User object if valid, else None.
    """
    user = get_user_by_email(db, email=email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
