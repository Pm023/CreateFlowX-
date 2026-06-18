from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.activity_log import ActivityLogOut
from app.crud import activity_log as crud_activity_log

router = APIRouter()

@router.get("/", response_model=List[ActivityLogOut])
def read_activities(
    search: Optional[str] = None,
    entity_type: Optional[str] = None,
    time_filter: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves activity logs for the current authenticated user.
    Enforces strict tenant isolation by only returning logs belonging to current_user.id.
    Supports filters like search, entity_type (client, project, task, invoice, user), and time_filter (today, week, month).
    """
    return crud_activity_log.get_activity_logs(
        db=db,
        user_id=current_user.id,
        search=search,
        entity_type=entity_type,
        time_filter=time_filter,
        limit=limit,
        skip=skip
    )
