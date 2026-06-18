from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional

class InvoiceBase(BaseModel):
    client_id: int
    project_id: int
    title: str = Field(..., max_length=150)
    description: Optional[str] = None
    amount: float = Field(..., gte=0.0)
    status: str = Field("Draft", max_length=50)
    issue_date: date
    due_date: date

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceUpdate(BaseModel):
    client_id: Optional[int] = None
    project_id: Optional[int] = None
    title: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = None
    amount: Optional[float] = Field(None, gte=0.0)
    status: Optional[str] = Field(None, max_length=50)
    issue_date: Optional[date] = None
    due_date: Optional[date] = None

class InvoiceOut(InvoiceBase):
    id: int
    user_id: int
    invoice_number: str
    paid_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    client_name: Optional[str] = None
    company_name: Optional[str] = None
    project_name: Optional[str] = None

    class Config:
        from_attributes = True
