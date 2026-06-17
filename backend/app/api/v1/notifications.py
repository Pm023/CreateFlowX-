from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.notification import NotificationOut, NotificationStatsOut
from app.crud import notification as crud_notification

router = APIRouter()

@router.get("/", response_model=List[NotificationOut], status_code=status.HTTP_200_OK)
def read_notifications(
    is_read: Optional[bool] = None,
    notification_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves user notifications. Triggers an on-demand deadline scan first to refresh states.
    """
    # Trigger on-demand deadline scanner
    crud_notification.scan_and_generate_user_notifications(db=db, user_id=current_user.id)
    
    # Retrieve notifications
    return crud_notification.get_notifications(
        db=db,
        user_id=current_user.id,
        is_read=is_read,
        notification_type=notification_type,
        search=search,
        limit=limit
    )

@router.get("/stats", response_model=NotificationStatsOut, status_code=status.HTTP_200_OK)
def read_notification_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves notification counts (unread vs total). Triggers on-demand scanner first.
    """
    crud_notification.scan_and_generate_user_notifications(db=db, user_id=current_user.id)
    
    unread_count = db.query(crud_notification.Notification).filter(
        crud_notification.Notification.user_id == current_user.id,
        crud_notification.Notification.is_read == False
    ).count()
    
    total_count = db.query(crud_notification.Notification).filter(
        crud_notification.Notification.user_id == current_user.id
    ).count()
    
    return {
        "unread_count": unread_count,
        "total_count": total_count
    }

@router.put("/{notification_id}/read", response_model=NotificationOut, status_code=status.HTTP_200_OK)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marks a notification as read.
    """
    db_notification = crud_notification.mark_as_read(db=db, notification_id=notification_id, user_id=current_user.id)
    if not db_notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or not owned by user"
        )
    return db_notification

@router.put("/read-all", status_code=status.HTTP_200_OK)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marks all notifications for the user as read.
    """
    crud_notification.mark_all_read(db=db, user_id=current_user.id)
    return {"detail": "All notifications marked as read"}

@router.delete("/{notification_id}", response_model=NotificationOut, status_code=status.HTTP_200_OK)
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a notification.
    """
    db_notification = crud_notification.delete_notification(db=db, notification_id=notification_id, user_id=current_user.id)
    if not db_notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or not owned by user"
        )
    return db_notification
