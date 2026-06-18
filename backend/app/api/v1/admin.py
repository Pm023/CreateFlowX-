from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, text
import datetime

from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.user import User
from app.models.client import Client
from app.models.project import Project
from app.models.task import Task
from app.models.invoice import Invoice
from app.models.activity_log import ActivityLog
from app.models.system_settings import SystemSettings
from app.schemas.user import UserOut, UserStatusUpdate
from app.schemas.system_settings import SystemSettingsOut, SystemSettingsUpdate

router = APIRouter()

month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

@router.get("/dashboard")
def read_admin_dashboard_stats(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Platform-wide business metrics, status indicators, and trends for Founder Control Center.
    """
    # 1. Core Statistics
    total_users = db.query(User).filter(User.is_deleted == False).count()
    active_users = db.query(User).filter(User.is_deleted == False, User.status == "active").count()
    total_clients = db.query(Client).count()
    total_projects = db.query(Project).count()
    total_tasks = db.query(Task).count()
    completed_tasks = db.query(Task).filter(Task.status == "Completed").count()
    total_invoices = db.query(Invoice).count()
    total_revenue = db.query(func.sum(Invoice.amount)).filter(Invoice.status == "Paid").scalar() or 0.0

    # 2. SaaS Metrics additions: New users this week
    start_of_week = datetime.datetime.now() - datetime.timedelta(days=7)
    new_users_this_week = db.query(User).filter(
        User.is_deleted == False, 
        User.created_at >= start_of_week
    ).count()

    # 3. Platform Growth Calculation (Month-Over-Month User Registrations)
    today = datetime.date.today()
    start_of_this_month = datetime.datetime(today.year, today.month, 1)
    
    this_month_users = db.query(User).filter(
        User.is_deleted == False,
        User.created_at >= start_of_this_month
    ).count()
    
    previous_users = db.query(User).filter(
        User.is_deleted == False,
        User.created_at < start_of_this_month
    ).count()

    if previous_users > 0:
        growth_percentage = (this_month_users / previous_users) * 100.0
    else:
        growth_percentage = 100.0 if this_month_users > 0 else 0.0

    # 4. Last 6 Months Growth Trend Data
    trend_months = []
    for i in range(5, -1, -1):
        y = today.year
        m = today.month - i
        while m <= 0:
            m += 12
            y -= 1
        trend_months.append({
            "year": y,
            "month": m,
            "label": f"{month_names[m-1]} {y}",
            "user_count": 0,
            "project_count": 0,
            "revenue": 0.0
        })

    # Fetch User Signups for Trends
    users = db.query(User).filter(User.is_deleted == False).all()
    for u in users:
        u_date = u.created_at
        for tm in trend_months:
            if u_date.year == tm["year"] and u_date.month == tm["month"]:
                tm["user_count"] += 1

    # Fetch Project Creations for Trends
    projects = db.query(Project).all()
    for p in projects:
        p_date = p.created_at
        for tm in trend_months:
            if p_date.year == tm["year"] and p_date.month == tm["month"]:
                tm["project_count"] += 1

    # Fetch Paid Invoices for Revenue Trends
    paid_invoices = db.query(Invoice).filter(Invoice.status == "Paid").all()
    for inv in paid_invoices:
        inv_date = inv.paid_date or inv.created_at
        for tm in trend_months:
            if inv_date.year == tm["year"] and inv_date.month == tm["month"]:
                tm["revenue"] += inv.amount

    user_trend = []
    project_trend = []
    revenue_trend = []

    for tm in trend_months:
        user_trend.append({"month": tm["label"], "count": tm["user_count"]})
        project_trend.append({"month": tm["label"], "count": tm["project_count"]})
        revenue_trend.append({"month": tm["label"], "amount": tm["revenue"]})

    # 5. Invoice Status Distribution
    status_counts = db.query(
        Invoice.status,
        func.count(Invoice.id).label("count"),
        func.sum(Invoice.amount).label("amount")
    ).group_by(Invoice.status).all()

    distribution = []
    for sc in status_counts:
        distribution.append({
            "status": sc[0],
            "count": sc[1],
            "amount": sc[2] or 0.0
        })

    # 6. Recent Registrations (5 Newest)
    recent_users = db.query(User).filter(User.is_deleted == False).order_by(User.created_at.desc()).limit(5).all()
    recent_registrations = []
    for ru in recent_users:
        recent_registrations.append({
            "full_name": ru.full_name,
            "username": ru.username,
            "email": ru.email,
            "created_at": ru.created_at
        })

    # 7. Platform Activity Feed (10 Newest)
    logs_query = db.query(
        ActivityLog.id,
        ActivityLog.title,
        ActivityLog.description,
        ActivityLog.created_at,
        User.full_name
    ).outerjoin(User, ActivityLog.user_id == User.id).order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).limit(10).all()
    
    activity_feed = []
    for log in logs_query:
        activity_feed.append({
            "title": log[1],
            "description": log[2],
            "created_at": log[3],
            "user_full_name": log[4] or "System"
        })

    # 8. Dynamic Founder Insights
    founder_insights = []
    founder_insights.append(f"Platform user base has registered a growth of {round(growth_percentage, 1)}% this month.")
    
    if total_tasks > 0:
        completion_rate = round((completed_tasks / total_tasks) * 100, 1)
        founder_insights.append(f"Platform productivity benchmarks: {completion_rate}% task completion rate across active creator boards.")
    else:
        founder_insights.append("Productivity indicators will generate once tasks are configured by active users.")
        
    if total_invoices > 0:
        paid_inv_count = db.query(Invoice).filter(Invoice.status == "Paid").count()
        payment_rate = round((paid_inv_count / total_invoices) * 100, 1)
        founder_insights.append(f"Billing health: {payment_rate}% of all system invoices have been successfully paid.")
    else:
        founder_insights.append("Revenue indicators will generate upon user invoice issuances.")
        
    if total_users > 0:
        projects_ratio = round(total_projects / total_users, 1)
        founder_insights.append(f"Creator Engagement check: Users initialize an average of {projects_ratio} projects per profile.")

    return {
        "stats": {
            "total_users": total_users,
            "active_users": active_users,
            "total_projects": total_projects,
            "total_tasks": total_tasks,
            "total_invoices": total_invoices,
            "total_revenue": total_revenue,
            "new_users_this_week": new_users_this_week,
            "growth_percentage": round(growth_percentage, 1)
        },
        "charts": {
            "user_growth": user_trend,
            "project_creation": project_trend,
            "revenue_trend": revenue_trend,
            "invoice_status": distribution
        },
        "recent_registrations": recent_registrations,
        "activity_feed": activity_feed,
        "founder_insights": founder_insights
    }

@router.get("/users")
def list_platform_users(
    search: str = None,
    role: str = None,
    status: str = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Search, filter, and list users registered on the platform.
    """
    query = db.query(User).filter(User.is_deleted == False)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                User.full_name.ilike(search_filter),
                User.email.ilike(search_filter),
                User.username.ilike(search_filter)
            )
        )

    if role:
        query = query.filter(User.role == role)

    if status:
        query = query.filter(User.status == status)

    return query.order_by(User.created_at.desc()).all()

@router.get("/users/{user_id}", response_model=UserOut)
def read_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Retrieve deep details of a specific user.
    """
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found on the platform."
        )
    return user

@router.put("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    status_in: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Suspend or reactivate a platform user account.
    """
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot suspend or reactivate your own administrative account."
        )

    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    status_val = status_in.status.strip().lower()
    if status_val not in ("active", "suspended"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be either 'active' or 'suspended'."
        )

    old_status = user.status
    user.status = status_val
    
    # If suspended, we also turn off is_active to block credentials session validation
    if status_val == "suspended":
        user.is_active = False
        action_title = "User Suspended"
        action_desc = f"User account {user.email} was suspended by administrative action."
    else:
        user.is_active = True
        action_title = "User Reactivated"
        action_desc = f"User account {user.email} was reactivated by administrative action."

    db.commit()
    db.refresh(user)

    # Activity Log
    from app.crud.activity_log import create_activity_log
    create_activity_log(
        db=db,
        user_id=current_admin.id,
        action_type="update",
        entity_type="user",
        entity_id=user.id,
        title=action_title,
        description=action_desc
    )

    return {"message": f"User status updated from {old_status} to {status_val} successfully."}

@router.get("/settings", response_model=SystemSettingsOut)
def read_system_settings(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Get current global system configurations.
    """
    settings = db.query(SystemSettings).first()
    if not settings:
        settings = SystemSettings(
            platform_name="CreateFlowX",
            registration_open=True,
            maintenance_mode=False,
            announcement_banner=None
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

@router.put("/settings", response_model=SystemSettingsOut)
def update_system_settings(
    settings_in: SystemSettingsUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Update global system settings (maintenance mode, announcement banner, registration control).
    """
    settings = db.query(SystemSettings).first()
    if not settings:
        settings = SystemSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)

    update_data = settings_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)

    db.commit()
    db.refresh(settings)

    # Activity Log
    from app.crud.activity_log import create_activity_log
    create_activity_log(
        db=db,
        user_id=current_admin.id,
        action_type="update",
        entity_type="system",
        entity_id=settings.id,
        title="System Settings Updated",
        description=f"Global configuration modified: platform_name='{settings.platform_name}', registration_open={settings.registration_open}, maintenance_mode={settings.maintenance_mode}."
    )

    return settings

@router.get("/activity-logs")
def list_system_activities(
    category: str = None, # user, financial, system
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Retrieve platform-wide logs, grouped by category of operation.
    """
    query = db.query(
        ActivityLog.id,
        ActivityLog.user_id,
        ActivityLog.action_type,
        ActivityLog.entity_type,
        ActivityLog.entity_id,
        ActivityLog.title,
        ActivityLog.description,
        ActivityLog.created_at,
        User.full_name.label("user_full_name"),
        User.email.label("user_email")
    ).outerjoin(User, ActivityLog.user_id == User.id)

    if category == "user":
        query = query.filter(
            or_(
                ActivityLog.entity_type == "user",
                ActivityLog.action_type == "register"
            )
        )
    elif category == "financial":
        query = query.filter(
            or_(
                ActivityLog.entity_type.in_(["invoice", "client"]),
                ActivityLog.action_type.in_(["paid", "refund"])
            )
        )
    elif category == "system":
        query = query.filter(
            ActivityLog.entity_type.in_(["system", "settings"])
        )

    logs = query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).all()
    
    # Map raw rows to output list of dicts
    result = []
    for log in logs:
        result.append({
            "id": log.id,
            "user_id": log.user_id,
            "action_type": log.action_type,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "title": log.title,
            "description": log.description,
            "created_at": log.created_at,
            "user_full_name": log.user_full_name or "System",
            "user_email": log.user_email or "system@createflowx.internal"
        })
    return result

@router.get("/health")
def system_health_status(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Retrieve technical service monitoring indicators.
    """
    # 1. Database Check
    db_healthy = True
    try:
        db.execute(text("SELECT 1")).scalar()
    except Exception:
        db_healthy = False

    # 2. Total Database Records
    users_count = db.query(User).count()
    clients_count = db.query(Client).count()
    projects_count = db.query(Project).count()
    tasks_count = db.query(Task).count()
    invoices_count = db.query(Invoice).count()
    logs_count = db.query(ActivityLog).count()
    total_records = users_count + clients_count + projects_count + tasks_count + invoices_count + logs_count

    return {
        "services": {
            "database": "Healthy" if db_healthy else "Critical",
            "api": "Healthy"
        },
        "stats": {
            "total_records": total_records,
            "platform_version": "v1.0.0"
        }
    }
