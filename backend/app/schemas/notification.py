from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class NotificationBase(BaseModel):
    title: str
    message: str
    notification_type: str
    project_id: Optional[int] = None
    task_id: Optional[int] = None

class NotificationCreate(NotificationBase):
    user_id: int
    reminder_rule: Optional[str] = None

class NotificationOut(BaseModel):
    id: int
    notification_type: str
    title: str
    message: str
    is_read: bool
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class NotificationStatsOut(BaseModel):
    unread_count: int
    total_count: int
