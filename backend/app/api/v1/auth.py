from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.crud.user import get_user_by_email, create_user, authenticate
from app.schemas.user import UserCreate, UserOut, Token
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

# Schema for JSON-based login
class UserLogin(BaseModel):
    email: str
    password: str

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Registers a new user on the CreateFlowX platform.
    Checks if the email is already registered first.
    """
    # Check registration control
    from app.models.system_settings import SystemSettings
    sys_settings = db.query(SystemSettings).first()
    if sys_settings and not sys_settings.registration_open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration is currently closed by the platform administrator."
        )

    existing_user = get_user_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address is already registered."
        )
    user = create_user(db, obj_in=user_in)

    # Activity Log
    from app.crud.activity_log import create_activity_log
    create_activity_log(
        db=db,
        user_id=user.id,
        action_type="register",
        entity_type="user",
        entity_id=user.id,
        title="Account Registered",
        description=f"Creator account registered for email {user.email}."
    )

    return user

@router.post("/login", response_model=Token)
def login_user(login_in: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticates a user via JSON payload (email and password).
    Returns a JWT access token valid for the configured period.
    """
    user = authenticate(
        db, email=login_in.email, password=login_in.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password."
        )
    elif getattr(user, "status", None) == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is suspended"
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user account is inactive."
        )

    # Check maintenance mode
    from app.models.system_settings import SystemSettings
    sys_settings = db.query(SystemSettings).first()
    if sys_settings and sys_settings.maintenance_mode:
        if user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Platform is under maintenance. Only administrators can log in."
            )
    
    # Generate JWT token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )

    # Activity Log
    from app.crud.activity_log import create_activity_log
    create_activity_log(
        db=db,
        user_id=user.id,
        action_type="login",
        entity_type="user",
        entity_id=user.id,
        title="User Logged In",
        description=f"User {user.email} successfully logged in."
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    """
    Returns the authenticated user's profile details.
    """
    return current_user

class ForgotPasswordRequest(BaseModel):
    email: str
    new_password: str

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(req_in: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Resets the password for a registered email address.
    """
    user = get_user_by_email(db, email=req_in.email.lower().strip())
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="A user with this email address was not found."
        )
    
    from app.core.security import get_password_hash
    user.hashed_password = get_password_hash(req_in.new_password)
    db.commit()
    
    # Activity Log
    from app.crud.activity_log import create_activity_log
    create_activity_log(
        db=db,
        user_id=user.id,
        action_type="update",
        entity_type="user",
        entity_id=user.id,
        title="Password Reset",
        description=f"Password was successfully reset for user {user.email}."
    )
    
    return {"message": "Password successfully reset."}
