from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import date, datetime, timedelta

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.task import Task
from app.schemas.calendar import CalendarEventOut, CalendarStatsOut, DashboardWidgetsOut

router = APIRouter()

@router.get("/events", response_model=List[CalendarEventOut], status_code=status.HTTP_200_OK)
def read_calendar_events(
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Dynamically aggregates projects and tasks with non-null deadlines.
    Supports queries with filters for category (type), status, priority, and date bounds.
    """
    events = []
    today = date.today()

    # 1. Projects Deadlines
    if event_type is None or event_type == "project":
        project_query = db.query(Project).options(joinedload(Project.client)).filter(
            Project.user_id == current_user.id,
            Project.deadline != None
        )
        if priority:
            project_query = project_query.filter(Project.priority == priority)
        if start_date:
            project_query = project_query.filter(Project.deadline >= start_date)
        if end_date:
            project_query = project_query.filter(Project.deadline <= end_date)

        projects_list = project_query.all()
        for p in projects_list:
            is_completed = p.status == "Completed"
            is_overdue = not is_completed and p.deadline < today
            mapped_status = "Completed" if is_completed else ("Overdue" if is_overdue else "Pending")

            if status and status != mapped_status:
                continue

            events.append({
                "id": f"project-{p.id}",
                "original_id": p.id,
                "event_type": "project",
                "title": p.project_name,
                "description": p.description,
                "project_name": p.project_name,
                "client_name": p.client_name,
                "deadline": p.deadline,
                "status": p.status,
                "priority": p.priority,
                "completed_at": p.updated_at if is_completed else None
            })

    # 2. Tasks Deadlines
    if event_type is None or event_type == "task":
        task_query = db.query(Task).options(
            joinedload(Task.project).joinedload(Project.client)
        ).filter(
            Task.user_id == current_user.id,
            Task.deadline != None
        )
        if priority:
            task_query = task_query.filter(Task.priority == priority)
        if start_date:
            task_query = task_query.filter(Task.deadline >= start_date)
        if end_date:
            task_query = task_query.filter(Task.deadline <= end_date)

        tasks_list = task_query.all()
        for t in tasks_list:
            is_completed = t.status == "Completed"
            is_overdue = not is_completed and t.deadline < today
            mapped_status = "Completed" if is_completed else ("Overdue" if is_overdue else "Pending")

            if status and status != mapped_status:
                continue

            events.append({
                "id": f"task-{t.id}",
                "original_id": t.id,
                "event_type": "task",
                "title": t.task_name,
                "description": t.description,
                "project_name": t.project_name,
                "client_name": t.client_name,
                "deadline": t.deadline,
                "status": t.status,
                "priority": t.priority,
                "completed_at": t.completed_at
            })

    # Sort chronologically by deadline date
    events.sort(key=lambda x: x["deadline"])
    return events

@router.get("/stats", response_model=CalendarStatsOut, status_code=status.HTTP_200_OK)
def read_calendar_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Aggregates overall deadlines metrics (Total, Completed, Pending, Overdue).
    """
    today = date.today()

    projects = db.query(Project).filter(
        Project.user_id == current_user.id,
        Project.deadline != None
    ).all()

    tasks = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.deadline != None
    ).all()

    total_events = len(projects) + len(tasks)
    completed_events = 0
    overdue_events = 0
    upcoming_events = 0

    for p in projects:
        if p.status == "Completed":
            completed_events += 1
        elif p.deadline < today:
            overdue_events += 1
        else:
            upcoming_events += 1

    for t in tasks:
        if t.status == "Completed":
            completed_events += 1
        elif t.deadline < today:
            overdue_events += 1
        else:
            upcoming_events += 1

    return {
        "total_events": total_events,
        "upcoming_events": upcoming_events,
        "overdue_events": overdue_events,
        "completed_events": completed_events
    }

@router.get("/dashboard", response_model=DashboardWidgetsOut, status_code=status.HTTP_200_OK)
def read_calendar_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Aggregates dashboard-specific query subsets to reduce client request loops.
    """
    today = date.today()
    upcoming_events = []

    # 1. Upcoming Deadlines (Limit 5: not completed, deadline >= today)
    up_projects = db.query(Project).options(joinedload(Project.client)).filter(
        Project.user_id == current_user.id,
        Project.deadline != None,
        Project.deadline >= today,
        Project.status != "Completed"
    ).order_by(Project.deadline.asc()).limit(5).all()

    for p in up_projects:
        upcoming_events.append({
            "id": f"project-{p.id}",
            "original_id": p.id,
            "event_type": "project",
            "title": p.project_name,
            "description": p.description,
            "project_name": p.project_name,
            "client_name": p.client_name,
            "deadline": p.deadline,
            "status": p.status,
            "priority": p.priority,
            "completed_at": None
        })

    up_tasks = db.query(Task).options(
        joinedload(Task.project).joinedload(Project.client)
    ).filter(
        Task.user_id == current_user.id,
        Task.deadline != None,
        Task.deadline >= today,
        Task.status != "Completed"
    ).order_by(Task.deadline.asc()).limit(5).all()

    for t in up_tasks:
        upcoming_events.append({
            "id": f"task-{t.id}",
            "original_id": t.id,
            "event_type": "task",
            "title": t.task_name,
            "description": t.description,
            "project_name": t.project_name,
            "client_name": t.client_name,
            "deadline": t.deadline,
            "status": t.status,
            "priority": t.priority,
            "completed_at": None
        })

    upcoming_events.sort(key=lambda x: x["deadline"])
    upcoming_events = upcoming_events[:5]

    # 2. Today's Tasks (deadline == today, not completed)
    today_tasks_list = []
    t_tasks = db.query(Task).options(
        joinedload(Task.project).joinedload(Project.client)
    ).filter(
        Task.user_id == current_user.id,
        Task.deadline == today,
        Task.status != "Completed"
    ).all()

    for t in t_tasks:
        today_tasks_list.append({
            "id": f"task-{t.id}",
            "original_id": t.id,
            "event_type": "task",
            "title": t.task_name,
            "description": t.description,
            "project_name": t.project_name,
            "client_name": t.client_name,
            "deadline": t.deadline,
            "status": t.status,
            "priority": t.priority,
            "completed_at": None
        })

    # 3. Overdue Tasks (deadline < today, not completed)
    overdue_tasks_list = []
    o_tasks = db.query(Task).options(
        joinedload(Task.project).joinedload(Project.client)
    ).filter(
        Task.user_id == current_user.id,
        Task.deadline < today,
        Task.status != "Completed"
    ).order_by(Task.deadline.asc()).all()

    for t in o_tasks:
        overdue_tasks_list.append({
            "id": f"task-{t.id}",
            "original_id": t.id,
            "event_type": "task",
            "title": t.task_name,
            "description": t.description,
            "project_name": t.project_name,
            "client_name": t.client_name,
            "deadline": t.deadline,
            "status": t.status,
            "priority": t.priority,
            "completed_at": None
        })

    # 4. This Week's Projects (deadline in Mon-Sun of current week)
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    week_projects_list = []
    w_projects = db.query(Project).options(joinedload(Project.client)).filter(
        Project.user_id == current_user.id,
        Project.deadline >= start_of_week,
        Project.deadline <= end_of_week
    ).order_by(Project.deadline.asc()).all()

    for p in w_projects:
        week_projects_list.append({
            "id": f"project-{p.id}",
            "original_id": p.id,
            "event_type": "project",
            "title": p.project_name,
            "description": p.description,
            "project_name": p.project_name,
            "client_name": p.client_name,
            "deadline": p.deadline,
            "status": p.status,
            "priority": p.priority,
            "completed_at": p.updated_at if p.status == "Completed" else None
        })

    return {
        "upcoming_deadlines": upcoming_events,
        "today_tasks": today_tasks_list,
        "overdue_tasks": overdue_tasks_list,
        "this_weeks_projects": week_projects_list
    }
