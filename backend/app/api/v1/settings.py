from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.user_settings import UserSettings
from app.schemas.user import UserSettingsOut, UserSettingsUpdate

router = APIRouter()

@router.get("/", response_model=UserSettingsOut)
def read_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves the authenticated user's workspace preferences.
    Creates them on-the-fly if missing.
    """
    settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    if not settings:
        settings = UserSettings(
            user_id=current_user.id,
            theme="light",
            currency="INR",
            date_format="DD/MM/YYYY"
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

@router.put("/", response_model=UserSettingsOut)
def update_settings(
    settings_in: UserSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates the authenticated user's workspace theme, currency, and date format.
    """
    settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    if not settings:
        settings = UserSettings(
            user_id=current_user.id,
            theme="light",
            currency="INR",
            date_format="DD/MM/YYYY"
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)

    update_data = settings_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)

    db.commit()
    db.refresh(settings)

    # Activity Log
    from app.crud.activity_log import create_activity_log
    create_activity_log(
        db=db,
        user_id=current_user.id,
        action_type="update",
        entity_type="user",
        entity_id=current_user.id,
        title="Settings Updated",
        description="Preferences (theme, currency, or date format) were updated."
    )

    return settings
