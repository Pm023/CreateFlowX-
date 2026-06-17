from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate, TaskOut
from app.crud import task as crud_task

router = APIRouter()

@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new Task record associated with a user and project.
    Enforces that the project belongs to the active authenticated user.
    """
    project = db.query(Project).filter(Project.id == task_in.project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or unauthorized."
        )
    return crud_task.create_task(db, obj_in=task_in, user_id=current_user.id)

@router.get("/", response_model=List[TaskOut])
def read_tasks(
    search: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves all Task records belonging to the authenticated User.
    Supports optional search query and filters by status, priority, or project.
    """
    return crud_task.get_tasks(
        db,
        user_id=current_user.id,
        search=search,
        status=status,
        priority=priority,
        project_id=project_id
    )

@router.get("/stats", status_code=status.HTTP_200_OK)
def read_task_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns aggregated task metrics (total, pending, completed, overdue)
    and upcoming task deadlines for the active user.
    """
    today = date.today()

    total_tasks = db.query(Task).filter(Task.user_id == current_user.id).count()
    
    completed_tasks = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.status == "Completed"
    ).count()
    
    pending_tasks = total_tasks - completed_tasks

    # Overdue tasks: deadline < today, status != Completed
    overdue_tasks = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.deadline != None,
        Task.deadline < today,
        Task.status != "Completed"
    ).count()

    # Upcoming task deadlines: deadline >= today, status != Completed, ordered by deadline asc
    upcoming = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.deadline != None,
        Task.deadline >= today,
        Task.status != "Completed"
    ).order_by(Task.deadline.asc()).limit(5).all()

    upcoming_list = []
    for t in upcoming:
        upcoming_list.append({
            "id": t.id,
            "task_name": t.task_name,
            "project_name": t.project_name,
            "client_name": t.client_name,
            "deadline": t.deadline.isoformat() if t.deadline else None,
            "status": t.status,
            "priority": t.priority
        })

    return {
        "total_tasks": total_tasks,
        "pending_tasks": pending_tasks,
        "completed_tasks": completed_tasks,
        "overdue_tasks": overdue_tasks,
        "upcoming_deadlines": upcoming_list
    }

@router.get("/{task_id}", response_model=TaskOut)
def read_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves details of a specific task by ID. Enforces ownership.
    """
    task = crud_task.get_task_by_id(db, task_id=task_id, user_id=current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found."
        )
    return task

@router.put("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    task_in: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates details of a task. Enforces project ownership checks if modified.
    """
    task = crud_task.get_task_by_id(db, task_id=task_id, user_id=current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found."
        )
    
    if task_in.project_id is not None:
        project = db.query(Project).filter(Project.id == task_in.project_id, Project.user_id == current_user.id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or unauthorized."
            )
            
    return crud_task.update_task(db, db_task=task, obj_in=task_in)

@router.delete("/{task_id}", response_model=TaskOut)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a specific task. Enforces ownership.
    """
    task = crud_task.get_task_by_id(db, task_id=task_id, user_id=current_user.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found."
        )
    return crud_task.delete_task(db, db_task=task)
