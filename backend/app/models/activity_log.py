from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    action_type = Column(String(50), nullable=False) # create, update, delete, complete, paid, login, register
    entity_type = Column(String(50), nullable=False) # client, project, task, invoice, user
    entity_id = Column(Integer, nullable=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)
