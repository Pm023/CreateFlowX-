from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
import datetime
from app.models.notification import Notification

def get_notifications(
    db: Session,
    user_id: int,
    is_read: Optional[bool] = None,
    notification_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100
) -> List[Notification]:
    """
    Fetches user notifications sorted by created_at descending.
    """
    query = db.query(Notification).filter(Notification.user_id == user_id)
    
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
        
    if notification_type:
        # Support grouping notifications vs actions
        if notification_type == "activity_logs":
            # Activity logs are those created from client_added, project_created, task_created, etc.
            query = query.filter(Notification.notification_type.in_([
                "client_added", "project_created", "project_completed", "task_created", "task_completed"
            ]))
        elif notification_type == "alerts":
            # Deadline alerts
            query = query.filter(Notification.notification_type.in_([
                "upcoming_task", "upcoming_project", "overdue_task", "overdue_project"
            ]))
        else:
            query = query.filter(Notification.notification_type == notification_type)
            
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Notification.title.ilike(search_filter),
                Notification.message.ilike(search_filter)
            )
        )
        
    return query.order_by(Notification.created_at.desc()).limit(limit).all()

def create_notification(
    db: Session,
    user_id: int,
    notification_type: str,
    title: str,
    message: str,
    project_id: Optional[int] = None,
    task_id: Optional[int] = None,
    reminder_rule: Optional[str] = None
) -> Notification:
    """
    Directly creates a notification record in the database.
    """
    db_obj = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        project_id=project_id,
        task_id=task_id,
        reminder_rule=reminder_rule,
        is_read=False
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def mark_as_read(db: Session, notification_id: int, user_id: int) -> Optional[Notification]:
    """
    Marks a single notification as read.
    """
    db_obj = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id
    ).first()
    if db_obj:
        db_obj.is_read = True
        db.commit()
        db.refresh(db_obj)
    return db_obj

def mark_all_read(db: Session, user_id: int):
    """
    Marks all unread notifications of a user as read.
    """
    db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).update({"is_read": True}, synchronize_session=False)
    db.commit()

def delete_notification(db: Session, notification_id: int, user_id: int) -> Optional[Notification]:
    """
    Deletes a notification.
    """
    db_obj = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id
    ).first()
    if db_obj:
        db.delete(db_obj)
        db.commit()
    return db_obj

def scan_and_generate_user_notifications(db: Session, user_id: int):
    """
    On-demand deadline scanner. Checks user's projects and tasks for upcoming or overdue deadlines.
    Uses unique reminder_rule tag to prevent duplicate notifications.
    """
    from app.models.task import Task
    from app.models.project import Project
    
    today = datetime.date.today()
    
    # 1. Scan Tasks
    tasks = db.query(Task).filter(
        Task.user_id == user_id,
        Task.deadline.isnot(None),
        Task.status != "Completed"
    ).all()
    
    for task in tasks:
        days_diff = (task.deadline - today).days
        rule = None
        title = ""
        message = ""
        notification_type = ""
        
        if days_diff == 3:
            rule = "task-3days"
            title = "Upcoming Task Deadline"
            message = f"Task \"{task.task_name}\" for project \"{task.project_name}\" is due in 3 days (Deadline: {task.deadline})."
            notification_type = "upcoming_task"
        elif days_diff == 1:
            rule = "task-1day"
            title = "Upcoming Task Deadline"
            message = f"Task \"{task.task_name}\" for project \"{task.project_name}\" is due tomorrow (Deadline: {task.deadline})."
            notification_type = "upcoming_task"
        elif days_diff == 0:
            rule = "task-0days"
            title = "Task Deadline Today"
            message = f"Task \"{task.task_name}\" for project \"{task.project_name}\" is due today!"
            notification_type = "upcoming_task"
        elif days_diff < 0:
            rule = "task-overdue"
            title = "Overdue Task Alert"
            message = f"Task \"{task.task_name}\" for project \"{task.project_name}\" is overdue! (Deadline was: {task.deadline})."
            notification_type = "overdue_task"
            
        if rule:
            # Check for existing record
            exists = db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.task_id == task.id,
                Notification.reminder_rule == rule
            ).first()
            
            if not exists:
                from app.services.dispatcher import dispatcher
                dispatcher.dispatch(
                    db=db,
                    user_id=user_id,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    project_id=task.project_id,
                    task_id=task.id,
                    reminder_rule=rule
                )
                
    # 2. Scan Projects
    projects = db.query(Project).filter(
        Project.user_id == user_id,
        Project.deadline.isnot(None),
        Project.status != "Completed"
    ).all()
    
    for project in projects:
        days_diff = (project.deadline - today).days
        rule = None
        title = ""
        message = ""
        notification_type = ""
        
        if days_diff == 7:
            rule = "project-7days"
            title = "Upcoming Project Deadline"
            message = f"Project \"{project.project_name}\" is due in 7 days (Deadline: {project.deadline})."
            notification_type = "upcoming_project"
        elif days_diff == 3:
            rule = "project-3days"
            title = "Upcoming Project Deadline"
            message = f"Project \"{project.project_name}\" is due in 3 days (Deadline: {project.deadline})."
            notification_type = "upcoming_project"
        elif days_diff == 1:
            rule = "project-1day"
            title = "Upcoming Project Deadline"
            message = f"Project \"{project.project_name}\" is due tomorrow (Deadline: {project.deadline})."
            notification_type = "upcoming_project"
        elif days_diff == 0:
            rule = "project-0days"
            title = "Project Deadline Today"
            message = f"Project \"{project.project_name}\" is due today!"
            notification_type = "upcoming_project"
        elif days_diff < 0:
            rule = "project-overdue"
            title = "Overdue Project Alert"
            message = f"Project \"{project.project_name}\" is overdue! (Deadline was: {project.deadline})."
            notification_type = "overdue_project"
            
        if rule:
            # Check for existing record
            exists = db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.project_id == project.id,
                Notification.reminder_rule == rule
            ).first()
            
            if not exists:
                from app.services.dispatcher import dispatcher
                dispatcher.dispatch(
                    db=db,
                    user_id=user_id,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    project_id=project.id,
                    task_id=None,
                    reminder_rule=rule
                )
