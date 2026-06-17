from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date

class CalendarEventOut(BaseModel):
    id: str  # Unique string ID, e.g. "project-12" or "task-4"
    original_id: int
    event_type: str  # "project" or "task"
    title: str
    description: Optional[str] = None
    project_name: str
    client_name: str
    deadline: date
    status: str
    priority: str
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CalendarStatsOut(BaseModel):
    total_events: int
    upcoming_events: int
    overdue_events: int
    completed_events: int

class DashboardWidgetsOut(BaseModel):
    upcoming_deadlines: List[CalendarEventOut]
    today_tasks: List[CalendarEventOut]
    overdue_tasks: List[CalendarEventOut]
    this_weeks_projects: List[CalendarEventOut]
