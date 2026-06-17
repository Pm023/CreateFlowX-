from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date

class TaskBase(BaseModel):
    task_name: Optional[str] = None
    project_id: Optional[int] = None
    description: Optional[str] = None
    status: Optional[str] = "To Do"
    priority: Optional[str] = "Medium"
    deadline: Optional[date] = None

class TaskCreate(TaskBase):
    task_name: str
    project_id: int

class TaskUpdate(TaskBase):
    pass

class TaskInDBBase(TaskBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TaskOut(TaskInDBBase):
    project_name: Optional[str] = None
    client_name: Optional[str] = None
    company_name: Optional[str] = None
