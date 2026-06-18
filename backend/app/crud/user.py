from sqlalchemy.orm import Session, joinedload
from typing import Optional
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    Retrieves a user by their unique primary key, eager loading their settings.
    """
    return db.query(User).options(joinedload(User.settings)).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Retrieves a user by their registered email address, eager loading their settings.
    """
    return db.query(User).options(joinedload(User.settings)).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    Retrieves a user by their unique username.
    """
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, obj_in: UserCreate) -> User:
    """
    Registers a new user inside the database, securely hashing their password,
    and automatically seeding a settings record.
    """
    db_obj = User(
        email=obj_in.email.lower().strip(),
        hashed_password=get_password_hash(obj_in.password),
        full_name=obj_in.full_name,
        role="user",
        is_active=True,
        is_verified=False,
        is_deleted=False
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    # Automatically create user settings record
    from app.models.user_settings import UserSettings
    db_settings = UserSettings(
        user_id=db_obj.id,
        theme="light",
        currency="INR",
        date_format="DD/MM/YYYY"
    )
    db.add(db_settings)
    db.commit()
    
    db.refresh(db_obj)
    return db_obj

def authenticate(db: Session, email: str, password: str) -> Optional[User]:
    """
    Validates user credentials. Returns the User object if valid and not deleted, else None.
    """
    user = get_user_by_email(db, email=email)
    if not user:
        return None
    if user.is_deleted:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
