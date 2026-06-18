from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.schemas.user import TokenPayload
from app.crud.user import get_user_by_id
from app.models.user import User

# OAuth2 scheme that pulls the token from the request header: Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    """
    Dependency that decodes the access token from the Authorization header
    and retrieves the corresponding User from the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode the JWT token using the application's configuration
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenPayload(sub=user_id)
    except JWTError:
        raise credentials_exception
    
    # Retrieve the user by the ID embedded in the JWT payload sub
    user = get_user_by_id(db, user_id=int(token_data.sub))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user account"
        )
    
    # 1. Enforce Suspension checks
    if getattr(user, "status", None) == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="User account is suspended"
        )

    # 2. Enforce Maintenance Mode checks for regular users
    from app.models.system_settings import SystemSettings
    sys_settings = db.query(SystemSettings).first()
    if sys_settings and sys_settings.maintenance_mode:
        if user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
                detail="Platform is currently undergoing maintenance. Please try again later."
            )

    return user

def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency that enforces the current user has the 'admin' role.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have enough privileges"
        )
    return current_user
