from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import datetime

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserOut, UserProfileUpdate, UserPasswordUpdate
from app.core.security import verify_password, get_password_hash
from app.crud.user import get_user_by_username

router = APIRouter()

@router.put("/me", response_model=UserOut)
def update_profile(
    profile_in: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates the current user's profile details (Full Name and Username).
    Enforces username uniqueness constraints.
    """
    # Required validation
    full_name_val = profile_in.full_name.strip()
    username_val = profile_in.username.strip().lower()

    if not full_name_val:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full Name is a required field."
        )
    if not username_val:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is a required field."
        )

    # Username uniqueness check (excluding current user)
    existing_user = db.query(User).filter(
        User.username == username_val,
        User.id != current_user.id,
        User.is_deleted == False
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already taken."
        )

    current_user.full_name = full_name_val
    current_user.username = username_val
    
    db.commit()
    db.refresh(current_user)

    # Activity Log
    from app.crud.activity_log import create_activity_log
    create_activity_log(
        db=db,
        user_id=current_user.id,
        action_type="update",
        entity_type="user",
        entity_id=current_user.id,
        title="Profile Updated",
        description=f"Profile name changed to '{full_name_val}' and username to '@{username_val}'."
    )

    return current_user

@router.put("/me/password", status_code=status.HTTP_200_OK)
def update_password(
    password_in: UserPasswordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates the authenticated user's account password with verification.
    """
    # 1. Verify current password
    if not verify_password(password_in.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password verification failed."
        )

    # 2. Minimum length check
    new_pwd = password_in.new_password
    if len(new_pwd) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long."
        )

    # 3. Confirmation match check
    if new_pwd != password_in.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords confirmation does not match."
        )

    # 4. Hash and save
    current_user.hashed_password = get_password_hash(new_pwd)
    current_user.last_password_change = datetime.datetime.now()
    
    db.commit()

    # Activity Log
    from app.crud.activity_log import create_activity_log
    create_activity_log(
        db=db,
        user_id=current_user.id,
        action_type="update",
        entity_type="user",
        entity_id=current_user.id,
        title="Password Changed",
        description="Security password was successfully updated."
    )

    return {"message": "Password updated successfully."}

@router.delete("/me", status_code=status.HTTP_200_OK)
def soft_delete_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft-deletes the authenticated user account and deactivates login access.
    """
    # Deactivate
    current_user.is_active = False
    current_user.is_deleted = True
    
    # Activity Log
    from app.crud.activity_log import create_activity_log
    create_activity_log(
        db=db,
        user_id=current_user.id,
        action_type="delete",
        entity_type="user",
        entity_id=current_user.id,
        title="Account Deleted",
        description=f"Creator profile for {current_user.email} soft deleted from system."
    )
    
    db.commit()
    return {"message": "Account has been deleted successfully."}
