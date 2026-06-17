from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ClientBase(BaseModel):
    client_name: Optional[str] = None
    company_name: Optional[str] = None
    notes: Optional[str] = None

class ClientCreate(ClientBase):
    client_name: str # Client name is required on creation

class ClientUpdate(ClientBase):
    pass

class ClientInDBBase(ClientBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ClientOut(ClientInDBBase):
    pass
