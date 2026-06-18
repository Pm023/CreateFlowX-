from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1.router import api_router
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.client import Client
from app.models.project import Project
from app.models.task import Task
from app.models.notification import Notification
from app.models.invoice import Invoice
from app.models.activity_log import ActivityLog
from app.models.system_settings import SystemSettings


# Automatically create tables in SQLite on application startup
# For production PostgreSQL, we would transition to Alembic migrations.
Base.metadata.create_all(bind=engine)

def seed_initial_data():
    from app.core.database import SessionLocal
    from app.models.user import User
    from app.models.user_settings import UserSettings
    from app.core.security import get_password_hash
    
    db = SessionLocal()
    try:
        # 1. Seed System Settings
        sys_settings = db.query(SystemSettings).first()
        if not sys_settings:
            sys_settings = SystemSettings(
                platform_name="CreateFlowX",
                registration_open=True,
                maintenance_mode=False,
                announcement_banner="Welcome to CreateFlowX v1.0! Empowering Creators."
            )
            db.add(sys_settings)
            db.commit()
            print("Seeded default SystemSettings.")

        # 2. Seed Admin User
        admin_user = db.query(User).filter(User.role == "admin").first()
        if not admin_user:
            admin_user = User(
                email="admin@createflowx.com",
                hashed_password=get_password_hash("AdminPassword123!"),
                full_name="Platform Administrator",
                username="admin",
                role="admin",
                status="active",
                is_active=True,
                is_verified=True,
                is_deleted=False
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            
            # Seed admin user settings
            admin_settings = UserSettings(
                user_id=admin_user.id,
                theme="dark",
                currency="USD",
                date_format="YYYY-MM-DD"
            )
            db.add(admin_settings)
            db.commit()
            print("Seeded platform administrator account (admin@createflowx.com).")
    except Exception as e:
        print(f"Error seeding initial data: {e}")
    finally:
        db.close()

seed_initial_data()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="CreateFlowX (CFX) - Workflow & Collaboration Platform for Creators & Freelancers",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Set up CORS middleware to permit frontend JavaScript to query APIs
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register the main API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    """
    Root status check endpoint.
    """
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": "1.0.0"
    }
