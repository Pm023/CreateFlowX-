from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SystemSettingsBase(BaseModel):
    platform_name: str = "CreateFlowX"
    registration_open: bool = True
    maintenance_mode: bool = False
    announcement_banner: Optional[str] = None

class SystemSettingsUpdate(SystemSettingsBase):
    pass

class SystemSettingsOut(SystemSettingsBase):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True
