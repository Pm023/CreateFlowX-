from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "CreateFlowX"
    API_V1_STR: str = "/api/v1"
    
    # Security Configuration
    # In production, these must be overridden by environment variables
    SECRET_KEY: str = "supersecretkeythatisextremelysecureandhardtoguessforcreateflowxmvp123!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 1 week expiration for easier development testing

    # Database Configuration
    DATABASE_URL: str = "sqlite:///./cfx.db"

    # CORS Origins
    # Allow all origins for local MVP development, specify domains in production
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
