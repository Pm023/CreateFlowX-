from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union

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

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        # Convert postgres:// to postgresql:// for SQLAlchemy compatibility
        if self.DATABASE_URL.startswith("postgres://"):
            return self.DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return self.DATABASE_URL

    # CORS Origins
    # Allow all origins for local MVP development, specify domains in production
    BACKEND_CORS_ORIGINS: Union[List[str], str] = ["*"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
