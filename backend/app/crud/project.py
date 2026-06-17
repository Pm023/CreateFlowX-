from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import List, Optional
from app.models.project import Project
from app.models.client import Client
from app.schemas.project import ProjectCreate, ProjectUpdate

def get_project_by_id(db: Session, project_id: int, user_id: int) -> Optional[Project]:
    """
    Fetches a project by ID, restricted by user_id to enforce multi-tenant isolation.
    """
    return db.query(Project).options(joinedload(Project.client)).filter(
        Project.id == project_id,
        Project.user_id == user_id
    ).first()

def get_projects(
    db: Session,
    user_id: int,
    search: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None
) -> List[Project]:
    """
    Retrieves all projects belonging to a user, with optional search filtering and status/priority tags.
    """
    query = db.query(Project).options(joinedload(Project.client)).filter(Project.user_id == user_id)

    if search:
        search_filter = f"%{search}%"
        # We perform an outer join on Client to search across client names and company names
        query = query.outerjoin(Client, Project.client_id == Client.id).filter(
            or_(
                Project.project_name.ilike(search_filter),
                Project.description.ilike(search_filter),
                Client.client_name.ilike(search_filter),
                Client.company_name.ilike(search_filter)
            )
        )

    if status:
        query = query.filter(Project.status == status)

    if priority:
        query = query.filter(Project.priority == priority)

    return query.order_by(Project.created_at.desc()).all()

def recalculate_project_progress(db: Session, project_id: int) -> int:
    """
    Updates the project's progress percentage based on associated tasks completion.
    """
    from app.models.task import Task
    total = db.query(Task).filter(Task.project_id == project_id).count()
    
    if total == 0:
        progress = 0
    else:
        completed = db.query(Task).filter(Task.project_id == project_id, Task.status == "Completed").count()
        progress = int((completed / total) * 100)
    
    db.query(Project).filter(Project.id == project_id).update({"progress": progress})
    db.commit()
    return progress

def create_project(db: Session, obj_in: ProjectCreate, user_id: int) -> Project:
    """
    Creates a new project record mapped to the user and their client.
    Initializes progress to 0 since progress is task-driven.
    """
    db_obj = Project(
        user_id=user_id,
        client_id=obj_in.client_id,
        project_name=obj_in.project_name.strip(),
        description=obj_in.description.strip() if obj_in.description else None,
        status=obj_in.status.strip() if obj_in.status else "Not Started",
        priority=obj_in.priority.strip() if obj_in.priority else "Medium",
        deadline=obj_in.deadline,
        progress=0 # Task-driven, defaults to 0
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    # Dispatch project_created notification/activity
    from app.services.dispatcher import dispatcher
    dispatcher.dispatch(
        db=db,
        user_id=user_id,
        notification_type="project_created",
        title="Project Created",
        message=f"Project \"{db_obj.project_name}\" was created.",
        project_id=db_obj.id
    )

    return db_obj

def update_project(db: Session, db_project: Project, obj_in: ProjectUpdate) -> Project:
    """
    Updates details of a project. Disallows manual progress modifications.
    """
    old_status = db_project.status
    update_data = obj_in.model_dump(exclude_unset=True)
    update_data.pop("progress", None) # Exclude manual progress edits

    for field, value in update_data.items():
        if isinstance(value, str):
            setattr(db_project, field, value.strip())
        else:
            setattr(db_project, field, value)

    db.commit()
    db.refresh(db_project)

    if db_project.status == "Completed" and old_status != "Completed":
        from app.services.dispatcher import dispatcher
        dispatcher.dispatch(
            db=db,
            user_id=db_project.user_id,
            notification_type="project_completed",
            title="Project Completed",
            message=f"Project \"{db_project.project_name}\" has been marked as Completed.",
            project_id=db_project.id
        )

    return db_project

def delete_project(db: Session, db_project: Project) -> Project:
    """
    Deletes the project from the database.
    """
    db.delete(db_project)
    db.commit()
    return db_project
