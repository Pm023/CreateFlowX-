from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Date, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    invoice_number = Column(String(50), nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    amount = Column(Float, nullable=False)
    status = Column(String(50), default="Draft", nullable=False) # Draft, Sent, Pending, Paid, Overdue, Cancelled
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    paid_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    owner = relationship("User", backref="invoices")
    client = relationship("Client", backref="invoices")
    project = relationship("Project", backref="invoices")

    @property
    def client_name(self) -> str:
        return self.client.client_name if self.client else ""

    @property
    def company_name(self) -> str:
        return self.client.company_name if self.client and self.client.company_name else ""

    @property
    def project_name(self) -> str:
        return self.project.project_name if self.project else ""
