from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
import datetime
from app.models.activity_log import ActivityLog

def create_activity_log(
    db: Session,
    user_id: int,
    action_type: str,
    entity_type: str,
    entity_id: Optional[int],
    title: str,
    description: str
) -> ActivityLog:
    """
    Creates a new activity log entry for a user action.
    """
    db_obj = ActivityLog(
        user_id=user_id,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        title=title,
        description=description
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_activity_logs(
    db: Session,
    user_id: int,
    search: Optional[str] = None,
    entity_type: Optional[str] = None,
    time_filter: Optional[str] = None,
    limit: int = 100,
    skip: int = 0
) -> List[ActivityLog]:
    """
    Retrieves activity logs for a user, sorted newest first, with search and filter parameters.
    Supports filtering by entity_type and time_filter ('today', 'week', 'month').
    """
    query = db.query(ActivityLog).filter(ActivityLog.user_id == user_id)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                ActivityLog.title.ilike(search_filter),
                ActivityLog.description.ilike(search_filter)
            )
        )

    if entity_type:
        query = query.filter(ActivityLog.entity_type == entity_type)

    if time_filter:
        now = datetime.datetime.now()
        if time_filter == "today":
            start_date = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
            query = query.filter(ActivityLog.created_at >= start_date)
        elif time_filter == "week":
            start_date = now - datetime.timedelta(days=7)
            query = query.filter(ActivityLog.created_at >= start_date)
        elif time_filter == "month":
            start_date = now - datetime.timedelta(days=30)
            query = query.filter(ActivityLog.created_at >= start_date)

    return query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).offset(skip).limit(limit).all()
