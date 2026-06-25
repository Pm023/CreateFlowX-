from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# UserSettings Schemas
class UserSettingsBase(BaseModel):
    theme: Optional[str] = "light"
    currency: Optional[str] = "INR"
    date_format: Optional[str] = "DD/MM/YYYY"

class UserSettingsUpdate(UserSettingsBase):
    pass

class UserSettingsOut(UserSettingsBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# User Schemas
class UserBase(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    username: Optional[str] = None
    profession: Optional[str] = "Freelancer"
    status: Optional[str] = "active"
    is_active: Optional[bool] = True
    is_deleted: Optional[bool] = False
    last_password_change: Optional[datetime] = None

class UserCreate(UserBase):
    email: str
    password: str
    full_name: Optional[str] = None

class UserUpdate(UserBase):
    password: Optional[str] = None

class UserProfileUpdate(BaseModel):
    full_name: str
    username: str
    profession: Optional[str] = None

class UserStatusUpdate(BaseModel):
    status: str

class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class UserInDBBase(UserBase):
    id: int
    role: str
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Additional properties to return via API
class UserOut(UserInDBBase):
    settings: Optional[UserSettingsOut] = None

# Additional properties stored in DB
class UserInDB(UserInDBBase):
    hashed_password: str

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut

class TokenPayload(BaseModel):
    sub: Optional[str] = None
