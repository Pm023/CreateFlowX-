from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    task_name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="To Do", nullable=False) # To Do, In Progress, Completed, On Hold
    priority = Column(String(50), default="Medium", nullable=False) # Low, Medium, High
    deadline = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships back to User and Project
    owner = relationship("User", backref="tasks")
    project = relationship("Project", backref="tasks")

    @property
    def project_name(self) -> str:
        return self.project.project_name if self.project else ""

    @property
    def client_name(self) -> str:
        return self.project.client.client_name if self.project and self.project.client else ""

    @property
    def company_name(self) -> str:
        return self.project.client.company_name if self.project and self.project.client and self.project.client.company_name else ""
