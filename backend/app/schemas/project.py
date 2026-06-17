from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date

class ProjectBase(BaseModel):
    project_name: Optional[str] = None
    client_id: Optional[int] = None
    description: Optional[str] = None
    status: Optional[str] = "Not Started"
    priority: Optional[str] = "Medium"
    deadline: Optional[date] = None
    progress: Optional[int] = Field(default=0, ge=0, le=100)

class ProjectCreate(ProjectBase):
    project_name: str
    client_id: int

class ProjectUpdate(ProjectBase):
    pass

class ProjectInDBBase(ProjectBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProjectOut(ProjectInDBBase):
    client_name: Optional[str] = None
    company_name: Optional[str] = None
    total_tasks: int = 0
    completed_tasks: int = 0
    pending_tasks: int = 0
