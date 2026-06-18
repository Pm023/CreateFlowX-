from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from datetime import datetime
from typing import List, Optional
from app.models.task import Task
from app.models.project import Project
from app.schemas.task import TaskCreate, TaskUpdate
from app.crud.project import recalculate_project_progress

def get_task_by_id(db: Session, task_id: int, user_id: int) -> Optional[Task]:
    """
    Fetches a task by ID, restricted by user_id to enforce multi-tenant isolation.
    """
    return db.query(Task).options(
        joinedload(Task.project).joinedload(Project.client)
    ).filter(Task.id == task_id, Task.user_id == user_id).first()

def get_tasks(
    db: Session,
    user_id: int,
    search: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    project_id: Optional[int] = None
) -> List[Task]:
    """
    Retrieves all tasks belonging to a user, supporting search and filtering.
    """
    query = db.query(Task).options(
        joinedload(Task.project).joinedload(Project.client)
    ).filter(Task.user_id == user_id)

    if search:
        search_filter = f"%{search}%"
        query = query.join(Task.project).filter(
            or_(
                Task.task_name.ilike(search_filter),
                Task.description.ilike(search_filter),
                Project.project_name.ilike(search_filter)
            )
        )

    if status:
        query = query.filter(Task.status == status)

    if priority:
        query = query.filter(Task.priority == priority)

    if project_id is not None:
        query = query.filter(Task.project_id == project_id)

    return query.order_by(Task.created_at.desc()).all()

def create_task(db: Session, obj_in: TaskCreate, user_id: int) -> Task:
    """
    Creates a new task and recalculates the progress of the associated project.
    """
    completed_at = None
    if obj_in.status == "Completed":
        completed_at = datetime.now()

    db_obj = Task(
        user_id=user_id,
        project_id=obj_in.project_id,
        task_name=obj_in.task_name.strip(),
        description=obj_in.description.strip() if obj_in.description else None,
        status=obj_in.status.strip() if obj_in.status else "To Do",
        priority=obj_in.priority.strip() if obj_in.priority else "Medium",
        deadline=obj_in.deadline,
        completed_at=completed_at
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    # Recalculate progress for the associated project
    recalculate_project_progress(db, db_obj.project_id)

    # Dispatch task_created notification/activity
    from app.services.dispatcher import dispatcher
    dispatcher.dispatch(
        db=db,
        user_id=user_id,
        notification_type="task_created",
        title="Task Created",
        message=f"Task \"{db_obj.task_name}\" was created for project \"{db_obj.project_name}\".",
        project_id=db_obj.project_id,
        task_id=db_obj.id
    )

    from app.crud.activity_log import create_activity_log
    create_activity_log(
        db=db,
        user_id=user_id,
        action_type="create",
        entity_type="task",
        entity_id=db_obj.id,
        title="Task Created",
        description=f"Task '{db_obj.task_name}' was created."
    )

    return db_obj

def update_task(db: Session, db_task: Task, obj_in: TaskUpdate) -> Task:
    """
    Updates a task, manages completed_at transitions, and recalculates project progress.
    """
    old_project_id = db_task.project_id
    old_status = db_task.status
    update_data = obj_in.model_dump(exclude_unset=True)

    # Handle completion timestamp transition
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == "Completed" and db_task.status != "Completed":
            db_task.completed_at = datetime.now()
        elif new_status != "Completed" and db_task.status == "Completed":
            db_task.completed_at = None

    for field, value in update_data.items():
        if isinstance(value, str):
            setattr(db_task, field, value.strip())
        else:
            setattr(db_task, field, value)

    db.commit()
    db.refresh(db_task)

    # Recalculate progress for old project
    recalculate_project_progress(db, old_project_id)

    # Recalculate progress for new project if the project changed
    if db_task.project_id != old_project_id:
        recalculate_project_progress(db, db_task.project_id)

    from app.crud.activity_log import create_activity_log
    # Dispatch task_completed notification/activity
    if db_task.status == "Completed" and old_status != "Completed":
        from app.services.dispatcher import dispatcher
        dispatcher.dispatch(
            db=db,
            user_id=db_task.user_id,
            notification_type="task_completed",
            title="Task Completed",
            message=f"Task \"{db_task.task_name}\" has been marked as Completed.",
            project_id=db_task.project_id,
            task_id=db_task.id
        )

        create_activity_log(
            db=db,
            user_id=db_task.user_id,
            action_type="complete",
            entity_type="task",
            entity_id=db_task.id,
            title="Task Completed",
            description=f"Task '{db_task.task_name}' was marked as completed."
        )
    else:
        create_activity_log(
            db=db,
            user_id=db_task.user_id,
            action_type="update",
            entity_type="task",
            entity_id=db_task.id,
            title="Task Updated",
            description=f"Task '{db_task.task_name}' was updated."
        )

    return db_task

def delete_task(db: Session, db_task: Task) -> Task:
    """
    Deletes a task and recalculates the progress of the associated project.
    """
    user_id = db_task.user_id
    task_id = db_task.id
    task_name = db_task.task_name
    project_id = db_task.project_id

    db.delete(db_task)
    db.commit()

    # Recalculate progress for project
    recalculate_project_progress(db, project_id)

    from app.crud.activity_log import create_activity_log
    create_activity_log(
        db=db,
        user_id=user_id,
        action_type="delete",
        entity_type="task",
        entity_id=task_id,
        title="Task Deleted",
        description=f"Task '{task_name}' was deleted."
    )

    return db_task
