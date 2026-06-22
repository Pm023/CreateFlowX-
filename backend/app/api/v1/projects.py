from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.client import Client
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectOut
from app.crud import project as crud_project

router = APIRouter()

@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new Project record associated with a user and client.
    Enforces that the client belongs to the active authenticated user.
    """
    client = db.query(Client).filter(Client.id == project_in.client_id, Client.user_id == current_user.id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found or unauthorized."
        )
    return crud_project.create_project(db, obj_in=project_in, user_id=current_user.id)

@router.get("/", response_model=List[ProjectOut])
def read_projects(
    search: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves all Project records belonging to the authenticated User.
    Supports optional search query and filters by status or priority.
    """
    return crud_project.get_projects(
        db,
        user_id=current_user.id,
        search=search,
        status=status,
        priority=priority
    )

@router.get("/stats", status_code=status.HTTP_200_OK)
def read_project_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns aggregated metrics and upcoming deadlines for the active user's projects.
    """
    total_projects = db.query(Project).filter(Project.user_id == current_user.id).count()
    
    active_projects = db.query(Project).filter(
        Project.user_id == current_user.id,
        Project.status == "In Progress"
    ).count()
    
    completed_projects = db.query(Project).filter(
        Project.user_id == current_user.id,
        Project.status == "Completed"
    ).count()

    on_hold_projects = db.query(Project).filter(
        Project.user_id == current_user.id,
        Project.status == "On Hold"
    ).count()

    not_started_projects = db.query(Project).filter(
        Project.user_id == current_user.id,
        Project.status == "Not Started"
    ).count()

    # Query upcoming deadlines: not completed, has deadline, sorted by deadline asc
    upcoming = db.query(Project).options(joinedload(Project.client)).filter(
        Project.user_id == current_user.id,
        Project.deadline != None,
        Project.status != "Completed"
    ).order_by(Project.deadline.asc()).limit(5).all()

    upcoming_list = []
    for p in upcoming:
        upcoming_list.append({
            "id": p.id,
            "project_name": p.project_name,
            "client_name": p.client_name,
            "company_name": p.company_name,
            "deadline": p.deadline.isoformat() if p.deadline else None,
            "status": p.status,
            "progress": p.progress
        })

    return {
        "total_projects": total_projects,
        "active_projects": active_projects,
        "completed_projects": completed_projects,
        "on_hold_projects": on_hold_projects,
        "not_started_projects": not_started_projects,
        "upcoming_deadlines": upcoming_list
    }

@router.get("/{project_id}", response_model=ProjectOut)
def read_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves details of a specific project by ID. Assert ownership.
    """
    project = crud_project.get_project_by_id(db, project_id=project_id, user_id=current_user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found."
        )
    return project

@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates details of a project. Validates client ownership if modified.
    """
    project = crud_project.get_project_by_id(db, project_id=project_id, user_id=current_user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found."
        )
    
    if project_in.client_id is not None:
        client = db.query(Client).filter(Client.id == project_in.client_id, Client.user_id == current_user.id).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found or unauthorized."
            )
            
    return crud_project.update_project(db, db_project=project, obj_in=project_in)

@router.delete("/{project_id}", response_model=ProjectOut)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes a specific project. Assert ownership.
    """
    project = crud_project.get_project_by_id(db, project_id=project_id, user_id=current_user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found."
        )
    return crud_project.delete_project(db, db_project=project)
