from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ActivityLogBase(BaseModel):
    action_type: str  # create, update, delete, complete, paid, login, register
    entity_type: str  # client, project, task, invoice, user
    entity_id: Optional[int] = None
    title: str
    description: str

class ActivityLogCreate(ActivityLogBase):
    user_id: int

class ActivityLogOut(ActivityLogBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
