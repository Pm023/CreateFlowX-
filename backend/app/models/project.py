from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False)
    project_name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="Not Started", nullable=False) # Not Started, In Progress, Completed, On Hold
    priority = Column(String(50), default="Medium", nullable=False) # Low, Medium, High
    deadline = Column(Date, nullable=True)
    progress = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships back to User and Client
    owner = relationship("User", backref="projects")
    client = relationship("Client", backref="projects")

    @property
    def client_name(self) -> str:
        return self.client.client_name if self.client else ""

    @property
    def company_name(self) -> str:
        return self.client.company_name if self.client and self.client.company_name else ""

    @property
    def total_tasks(self) -> int:
        return len(self.tasks)

    @property
    def completed_tasks(self) -> int:
        return sum(1 for t in self.tasks if t.status == "Completed")

    @property
    def pending_tasks(self) -> int:
        return sum(1 for t in self.tasks if t.status != "Completed")
