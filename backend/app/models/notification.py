from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=True)
    notification_type = Column(String(100), nullable=False)  # e.g. upcoming_task, task_completed
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    reminder_rule = Column(String(100), nullable=True)  # Unique rule tag to avoid duplicates during scanner runs
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships back to User, Project, and Task
    owner = relationship("User", backref="notifications")
    project = relationship("Project", backref="notifications")
    task = relationship("Task", backref="notifications")
