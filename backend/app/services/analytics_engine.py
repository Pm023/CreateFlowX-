import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import List, Dict, Any

from app.models.client import Client
from app.models.project import Project
from app.models.task import Task
from app.models.invoice import Invoice
from app.models.activity_log import ActivityLog

def get_client_last_activity_date(db: Session, client: Client) -> datetime.date:
    """
    Finds the last date of activity for a client.
    """
    dates = []
    
    # 1. Client creation/update
    if client.updated_at:
        dates.append(client.updated_at.date())
    elif client.created_at:
        dates.append(client.created_at.date())
        
    # 2. Invoices
    last_invoice = db.query(Invoice).filter(Invoice.client_id == client.id).order_by(Invoice.updated_at.desc()).first()
    if last_invoice:
        dates.append(last_invoice.updated_at.date() if last_invoice.updated_at else last_invoice.created_at.date())
        if last_invoice.paid_date:
            dates.append(last_invoice.paid_date.date())

    # 3. Projects
    projects = db.query(Project).filter(Project.client_id == client.id).all()
    for proj in projects:
        dates.append(proj.updated_at.date() if proj.updated_at else proj.created_at.date())
        
        # 4. Tasks under this project
        last_task = db.query(Task).filter(Task.project_id == proj.id).order_by(Task.updated_at.desc()).first()
        if last_task:
            dates.append(last_task.updated_at.date() if last_task.updated_at else last_task.created_at.date())
            if last_task.completed_at:
                dates.append(last_task.completed_at.date())

    # 5. Activity logs for this client
    last_log = db.query(ActivityLog).filter(
        ActivityLog.user_id == client.user_id,
        ActivityLog.entity_type == "client",
        ActivityLog.entity_id == client.id
    ).order_by(ActivityLog.created_at.desc()).first()
    if last_log:
        dates.append(last_log.created_at.date())

    if not dates:
        return datetime.date.today() - datetime.timedelta(days=365)
        
    return max(dates)


def calculate_client_health(db: Session, client: Client) -> Dict[str, Any]:
    """
    Calculates Client Health (0-100) and returns score, level (Excellent, Moderate, At Risk),
    color, and reasoning details.
    """
    today = datetime.date.today()
    last_act = get_client_last_activity_date(db, client)
    days_inactive = (today - last_act).days
    
    # 1. Activity (25 pts)
    if days_inactive <= 7:
        act_pts = 25
    elif days_inactive <= 14:
        act_pts = 20
    elif days_inactive <= 30:
        act_pts = 10
    else:
        act_pts = 0

    # 2. Revenue Contribution (25 pts)
    paid_invoices = db.query(Invoice).filter(
        Invoice.client_id == client.id,
        Invoice.status == "Paid"
    ).all()
    total_paid = sum(inv.amount for inv in paid_invoices)
    
    active_projects = db.query(Project).filter(
        Project.client_id == client.id,
        Project.status.in_(["Not Started", "In Progress"])
    ).count()

    if total_paid > 0:
        rev_pts = 25
    elif active_projects > 0:
        rev_pts = 15
    else:
        rev_pts = 5

    # 3. Active Projects (25 pts)
    if active_projects >= 2:
        proj_pts = 25
    elif active_projects == 1:
        proj_pts = 20
    else:
        # Check if has pending tasks under their projects
        has_pending_tasks = db.query(Task).join(Project).filter(
            Project.client_id == client.id,
            Task.status.in_(["To Do", "In Progress"])
        ).count() > 0
        proj_pts = 10 if has_pending_tasks else 0

    # 4. Invoice Status (25 pts)
    overdue_invoices = db.query(Invoice).filter(
        Invoice.client_id == client.id,
        Invoice.status == "Overdue"
    ).count()
    
    total_invoices = db.query(Invoice).filter(
        Invoice.client_id == client.id
    ).count()

    if overdue_invoices == 0:
        inv_pts = 25 if total_invoices > 0 else 20
    elif overdue_invoices == 1:
        inv_pts = 15
    else:
        inv_pts = 0

    score = act_pts + rev_pts + proj_pts + inv_pts
    
    if score >= 80:
        status = "Excellent"
        color = "green"
    elif score >= 50:
        status = "Moderate"
        color = "yellow"
    else:
        status = "At Risk"
        color = "red"

    reasoning = []
    if days_inactive > 14:
        reasoning.append(f"Client has been inactive for {days_inactive} days.")
    else:
        reasoning.append("Client recently active.")
        
    if overdue_invoices > 0:
        reasoning.append(f"Has {overdue_invoices} overdue invoice(s).")
    else:
        reasoning.append("No overdue invoices.")
        
    if active_projects > 0:
        reasoning.append(f"Currently has {active_projects} active project(s).")
    else:
        reasoning.append("No active projects.")

    return {
        "client_id": client.id,
        "client_name": client.client_name,
        "company_name": client.company_name or "",
        "score": score,
        "status": status,
        "color": color,
        "days_inactive": days_inactive,
        "last_activity_date": last_act.isoformat(),
        "total_paid": total_paid,
        "active_projects": active_projects,
        "overdue_invoices_count": overdue_invoices,
        "reasoning": reasoning
    }


def calculate_business_health_score(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Calculates Business Health Score (0-100) based on five 20-point factors.
    """
    today = datetime.date.today()
    
    # 1. Revenue Trend (20 points)
    # Fetch invoices for past 6 months
    invoices = db.query(Invoice).filter(
        Invoice.user_id == user_id,
        Invoice.status != "Cancelled"
    ).all()
    
    months_rev = [0.0] * 6
    for i in range(6):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        # Sum invoice amount for this month
        months_rev[i] = sum(
            inv.amount for inv in invoices 
            if inv.issue_date.year == year and inv.issue_date.month == month
        )
        
    current_month_rev = months_rev[0]
    prev_months = [m for m in months_rev[1:] if m > 0]
    avg_prev_rev = sum(prev_months) / len(prev_months) if prev_months else 0.0
    
    if current_month_rev >= avg_prev_rev and avg_prev_rev > 0:
        rev_score = 20
        rev_reason = "Revenue is growing compared to historical averages."
    elif avg_prev_rev > 0:
        ratio = current_month_rev / avg_prev_rev
        if ratio >= 0.8:
            rev_score = 15
            rev_reason = "Revenue has a slight decline but remains stable."
        elif ratio >= 0.5:
            rev_score = 10
            rev_reason = "Revenue is moderately lower than historical averages."
        else:
            rev_score = 5
            rev_reason = "Revenue has declined significantly this month."
    else:
        # No historical data or current revenue
        rev_score = 12
        rev_reason = "Revenue is stable with limited historical records."

    # 2. Client Activity (20 points)
    clients = db.query(Client).filter(Client.user_id == user_id).all()
    total_clients = len(clients)
    if total_clients == 0:
        client_score = 20
        client_reason = "No clients registered yet (neutral activity)."
    else:
        active_count = 0
        for c in clients:
            last_act = get_client_last_activity_date(db, c)
            if (today - last_act).days <= 14:
                active_count += 1
        active_ratio = active_count / total_clients
        client_score = int(20 * active_ratio)
        if active_ratio >= 0.7:
            client_reason = "High client engagement with regular interactions."
        elif active_ratio >= 0.4:
            client_reason = "Moderate client activity; some accounts need attention."
        else:
            client_reason = "Low client activity. Follow-up is recommended."

    # 3. Invoice Collection (20 points)
    pending_amount = sum(inv.amount for inv in invoices if inv.status in ["Draft", "Sent", "Pending"])
    overdue_amount = sum(inv.amount for inv in invoices if inv.status == "Overdue")
    
    total_unpaid = pending_amount + overdue_amount
    if total_unpaid == 0:
        invoice_score = 20
        invoice_reason = "All billings are paid up! Excellent collections."
    else:
        overdue_ratio = overdue_amount / total_unpaid
        if overdue_ratio <= 0.1:
            invoice_score = 20
            invoice_reason = "Excellent collection rate; overdue invoices are minimal."
        elif overdue_ratio <= 0.3:
            invoice_score = 15
            invoice_reason = "Healthy invoice collections with small overdue amounts."
        elif overdue_ratio <= 0.5:
            invoice_score = 10
            invoice_reason = "Moderate overdue invoices. Active follow-ups suggested."
        else:
            invoice_score = 5
            invoice_reason = "Critical collection issues; over 50% of unpaid invoices are past due."

    # 4. Project Completion (20 points)
    projects = db.query(Project).filter(Project.user_id == user_id).all()
    total_projects = len(projects)
    if total_projects == 0:
        proj_score = 20
        proj_reason = "No projects tracked yet (neutral status)."
    else:
        # Check projects that are In Progress/Completed and compare on track
        # Let's count progress average
        avg_progress = sum(p.progress for p in projects) / total_projects
        proj_score = int(20 * (avg_progress / 100))
        
        # Check overdue deadlines
        overdue_projects = sum(1 for p in projects if p.status != "Completed" and p.deadline and p.deadline < today)
        if overdue_projects > 0:
            proj_score = max(0, proj_score - (overdue_projects * 2))
            proj_reason = f"Projects are advancing, but {overdue_projects} project(s) past deadline."
        else:
            if avg_progress >= 70:
                proj_reason = "Projects are highly active and progressing quickly."
            else:
                proj_reason = "Projects are moving steadily forward."

    # 5. Task Completion (20 points)
    tasks = db.query(Task).filter(Task.user_id == user_id).all()
    total_tasks = len(tasks)
    if total_tasks == 0:
        task_score = 20
        task_reason = "No tasks created yet (neutral status)."
    else:
        completed_tasks = sum(1 for t in tasks if t.status == "Completed")
        task_ratio = completed_tasks / total_tasks
        task_score = int(20 * task_ratio)
        
        # Deduct if many overdue tasks
        overdue_tasks = sum(1 for t in tasks if t.status != "Completed" and t.deadline and t.deadline < today)
        if overdue_tasks > 0:
            task_score = max(0, task_score - int(overdue_tasks * 0.5))
            task_reason = f"Task completion rate is {int(task_ratio*100)}% with {overdue_tasks} overdue tasks."
        else:
            task_reason = f"Task completion rate is healthy at {int(task_ratio*100)}%."

    total_score = rev_score + client_score + invoice_score + proj_score + task_score
    
    if total_score >= 90:
        level = "Excellent"
        status_color = "green"
    elif total_score >= 80:
        level = "Strong"
        status_color = "green"
    elif total_score >= 70:
        level = "Healthy"
        status_color = "blue"
    elif total_score >= 50:
        level = "Needs Attention"
        status_color = "yellow"
    else:
        level = "At Risk"
        status_color = "red"

    return {
        "score": total_score,
        "level": level,
        "status_color": status_color,
        "breakdown": {
            "revenue": {"score": rev_score, "max": 20, "reason": rev_reason},
            "clients": {"score": client_score, "max": 20, "reason": client_reason},
            "invoices": {"score": invoice_score, "max": 20, "reason": invoice_reason},
            "projects": {"score": proj_score, "max": 20, "reason": proj_reason},
            "tasks": {"score": task_score, "max": 20, "reason": task_reason}
        },
        "reasoning": [rev_reason, client_reason, invoice_reason, proj_reason, task_reason]
    }


def get_smart_insights(db: Session, user_id: int) -> List[Dict[str, Any]]:
    """
    Generates a list of intelligent rule-based insights for the user.
    """
    today = datetime.date.today()
    insights = []
    
    # Fetch database metrics
    invoices = db.query(Invoice).filter(Invoice.user_id == user_id, Invoice.status != "Cancelled").all()
    clients = db.query(Client).filter(Client.user_id == user_id).all()
    projects = db.query(Project).filter(Project.user_id == user_id).all()
    tasks = db.query(Task).filter(Task.user_id == user_id).all()
    
    # ------------------ REVENUE & INVOICE INSIGHTS ------------------
    # Compare revenue: current month vs last month
    months_rev = [0.0] * 6
    for i in range(6):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        months_rev[i] = sum(
            inv.amount for inv in invoices 
            if inv.issue_date.year == year and inv.issue_date.month == month
        )

    current_month_rev = months_rev[0]
    last_month_rev = months_rev[1]
    
    if last_month_rev > 0:
        change_pct = round(((current_month_rev - last_month_rev) / last_month_rev) * 100, 1)
        if change_pct > 0:
            insights.append({
                "category": "Revenue",
                "type": "success",
                "icon": "📈",
                "title": "Revenue Growth",
                "message": f"Revenue increased {change_pct}% compared to last month."
            })
        elif change_pct < 0:
            insights.append({
                "category": "Revenue",
                "type": "warning",
                "icon": "⚠️",
                "title": "Revenue Drop",
                "message": f"Revenue decreased {abs(change_pct)}% compared to last month."
            })
    
    # Consecutive growth months
    consecutive = 0
    # Let's check chronological changes: months_rev is [current_month, last_month, 2_months_ago, ...]
    # chronological is index 5, 4, 3, 2, 1, 0
    for idx in range(len(months_rev) - 1):
        if months_rev[idx] > months_rev[idx+1] and months_rev[idx+1] > 0:
            consecutive += 1
        else:
            break
            
    if consecutive >= 3:
        insights.append({
            "category": "Revenue",
            "type": "success",
            "icon": "🚀",
            "title": "Consistent Growth",
            "message": f"Revenue has grown for {consecutive} consecutive months."
        })

    # Unpaid invoices cash flow
    unpaid_amount = sum(inv.amount for inv in invoices if inv.status in ["Draft", "Sent", "Pending"])
    overdue_count = sum(1 for inv in invoices if inv.status == "Overdue")
    overdue_amount = sum(inv.amount for inv in invoices if inv.status == "Overdue")

    if unpaid_amount > 0:
        insights.append({
            "category": "Invoices",
            "type": "info",
            "icon": "💰",
            "title": "Unpaid Revenue",
            "message": f"₹{unpaid_amount:,.2f} remains unpaid across pending invoices."
        })
        
    if overdue_count > 0:
        insights.append({
            "category": "Invoices",
            "type": "danger",
            "icon": "⚠️",
            "title": "Overdue Invoices",
            "message": f"{overdue_count} invoice(s) totaling ₹{overdue_amount:,.2f} are overdue."
        })

    # ------------------ CLIENT INSIGHTS ------------------
    inactive_clients_count = 0
    for c in clients:
        last_act = get_client_last_activity_date(db, c)
        if (today - last_act).days > 14:
            inactive_clients_count += 1
            
    if inactive_clients_count > 0:
        insights.append({
            "category": "Clients",
            "type": "warning",
            "icon": "⚠️",
            "title": "Inactive Clients",
            "message": f"{inactive_clients_count} client(s) have been inactive for more than 14 days."
        })

    # Top client contribution share
    paid_revenue_total = sum(inv.amount for inv in invoices if inv.status == "Paid")
    if paid_revenue_total > 0:
        client_totals = {}
        for inv in invoices:
            if inv.status == "Paid":
                client_totals[inv.client_id] = client_totals.get(inv.client_id, 0.0) + inv.amount
        
        if client_totals:
            top_client_id = max(client_totals, key=client_totals.get)
            top_client_amount = client_totals[top_client_id]
            top_client_share = round((top_client_amount / paid_revenue_total) * 100, 1)
            
            top_client = db.query(Client).filter(Client.id == top_client_id).first()
            top_client_name = top_client.client_name if top_client else "Independent Client"
            
            if top_client_share >= 40:
                insights.append({
                    "category": "Clients",
                    "type": "info",
                    "icon": "💡",
                    "title": "Revenue Concentration",
                    "message": f"Your top client ({top_client_name}) generated {top_client_share}% of total paid revenue."
                })

    # Gained clients this month
    start_of_month = today.replace(day=1)
    new_clients = sum(1 for c in clients if c.created_at.date() >= start_of_month)
    if new_clients > 0:
        insights.append({
            "category": "Clients",
            "type": "success",
            "icon": "🚀",
            "title": "New Clients Acquired",
            "message": f"You gained {new_clients} new client(s) this month."
        })

    # ------------------ PRODUCTIVITY INSIGHTS ------------------
    # Task completion rates comparison (this month vs last month)
    tasks_created_this_month = sum(1 for t in tasks if t.created_at.date() >= start_of_month)
    tasks_completed_this_month = sum(1 for t in tasks if t.completed_at and t.completed_at.date() >= start_of_month)
    
    # Tasks last month
    first_of_last_month = (start_of_month - datetime.timedelta(days=1)).replace(day=1)
    tasks_created_last_month = sum(1 for t in tasks if first_of_last_month <= t.created_at.date() < start_of_month)
    tasks_completed_last_month = sum(1 for t in tasks if t.completed_at and first_of_last_month <= t.completed_at.date() < start_of_month)
    
    rate_this_month = (tasks_completed_this_month / tasks_created_this_month) if tasks_created_this_month > 0 else 0.0
    rate_last_month = (tasks_completed_last_month / tasks_created_last_month) if tasks_created_last_month > 0 else 0.0
    
    diff_rate = round((rate_this_month - rate_last_month) * 100, 1)
    if diff_rate > 0:
        insights.append({
            "category": "Productivity",
            "type": "success",
            "icon": "✅",
            "title": "Task Efficiency Up",
            "message": f"Task completion rate improved by {diff_rate}% compared to last month."
        })
    elif diff_rate < 0:
        insights.append({
            "category": "Productivity",
            "type": "warning",
            "icon": "⚠️",
            "title": "Task Efficiency Down",
            "message": f"Task completion rate decreased by {abs(diff_rate)}% compared to last month."
        })

    # Projects completed faster
    completed_projects_this_month = [
        p for p in projects 
        if p.status == "Completed" and p.updated_at.date() >= start_of_month
    ]
    completed_projects_prev = [
        p for p in projects 
        if p.status == "Completed" and p.updated_at.date() < start_of_month
    ]
    
    def get_avg_duration(projs):
        durations = []
        for p in projs:
            c_date = p.created_at.date()
            u_date = p.updated_at.date()
            durations.append((u_date - c_date).days)
        return sum(durations) / len(durations) if durations else 0.0

    avg_this = get_avg_duration(completed_projects_this_month)
    avg_prev = get_avg_duration(completed_projects_prev)
    
    if avg_this > 0 and avg_prev > 0 and avg_this < avg_prev:
        insights.append({
            "category": "Productivity",
            "type": "success",
            "icon": "🚀",
            "title": "Project Delivery Speed",
            "message": "Projects are being completed faster than last month."
        })

    # Default insight if list is empty
    if not insights:
        insights.append({
            "category": "General",
            "type": "info",
            "icon": "💡",
            "title": "Steady Operations",
            "message": "Business is operating smoothly. Keep tracking clients and invoicing on time to generate growth insights."
        })

    return insights


def get_weekly_priorities(db: Session, user_id: int) -> List[Dict[str, Any]]:
    """
    Generates dynamic Growth Coach Priorities.
    """
    today = datetime.date.today()
    priorities = []
    
    # 1. Inactive clients priority
    clients = db.query(Client).filter(Client.user_id == user_id).all()
    inactive_clients = []
    for c in clients:
        last_act = get_client_last_activity_date(db, c)
        if (today - last_act).days > 14:
            inactive_clients.append(c)
            
    if inactive_clients:
        priorities.append({
            "id": "inactive_clients",
            "priority": 1,
            "title": "Re-engage Inactive Accounts",
            "description": f"Follow up with {len(inactive_clients)} client(s) who have been inactive for more than 14 days.",
            "icon": "ri-user-follow-line",
            "action_text": "View Inactive Clients",
            "action_link": "clients.html"
        })

    # 2. Collect unpaid invoices priority
    overdue_invoices = db.query(Invoice).filter(
        Invoice.user_id == user_id,
        Invoice.status == "Overdue"
    ).all()
    
    if overdue_invoices:
        total_overdue = sum(inv.amount for inv in overdue_invoices)
        priorities.append({
            "id": "collect_overdue",
            "priority": 2,
            "title": "Collect Overdue Invoices",
            "description": f"Collect ₹{total_overdue:,.2f} from {len(overdue_invoices)} overdue invoice(s) past their deadline.",
            "icon": "ri-money-dollar-box-line",
            "action_text": "Collect Payments",
            "action_link": "invoices.html"
        })
    else:
        pending_invoices = db.query(Invoice).filter(
            Invoice.user_id == user_id,
            Invoice.status.in_(["Draft", "Sent", "Pending"])
        ).all()
        if pending_invoices:
            total_pending = sum(inv.amount for inv in pending_invoices)
            priorities.append({
                "id": "collect_pending",
                "priority": 2,
                "title": "Review Pending Billings",
                "description": f"Follow up on pending invoices totaling ₹{total_pending:,.2f} to accelerate cash flow.",
                "icon": "ri-mail-send-line",
                "action_text": "View Invoices",
                "action_link": "invoices.html"
            })

    # 3. Task completion priority
    overdue_tasks = db.query(Task).filter(
        Task.user_id == user_id,
        Task.status != "Completed",
        Task.deadline < today
    ).all()
    
    if overdue_tasks:
        priorities.append({
            "id": "overdue_tasks",
            "priority": 3,
            "title": "Resolve Overdue Tasks",
            "description": f"Complete {len(overdue_tasks)} overdue task(s) past their scheduled deadline.",
            "icon": "ri-time-line",
            "action_text": "Go to Tasks",
            "action_link": "tasks.html"
        })
    else:
        high_tasks = db.query(Task).filter(
            Task.user_id == user_id,
            Task.status != "Completed",
            Task.priority == "High"
        ).all()
        if high_tasks:
            priorities.append({
                "id": "high_priority_tasks",
                "priority": 3,
                "title": "Execute High Priority Tasks",
                "description": f"Address {len(high_tasks)} high-priority task(s) scheduled on active projects.",
                "icon": "ri-fire-line",
                "action_text": "Go to Tasks",
                "action_link": "tasks.html"
            })

    # 4. Start Unstarted projects priority
    not_started_projects = db.query(Project).filter(
        Project.user_id == user_id,
        Project.status == "Not Started"
    ).all()
    
    if not_started_projects:
        priorities.append({
            "id": "unstarted_projects",
            "priority": 4,
            "title": "Kickoff Unstarted Projects",
            "description": f"Launch {len(not_started_projects)} project(s) currently marked as 'Not Started'.",
            "icon": "ri-play-circle-line",
            "action_text": "View Projects",
            "action_link": "projects.html"
        })

    # Default priorities if nothing is outstanding
    if not priorities:
        priorities.append({
            "id": "default_business_growth",
            "priority": 1,
            "title": "Add New Leads and Projects",
            "description": "Create new clients and initiate draft scopes to keep your business pipeline growing.",
            "icon": "ri-rocket-line",
            "action_text": "Create Client",
            "action_link": "clients.html"
        })

    priorities.sort(key=lambda x: x["priority"])
    return priorities


def get_opportunities_and_risks(db: Session, user_id: int) -> Dict[str, List[Dict[str, Any]]]:
    """
    Identifies Growth Opportunities and Business Risks.
    """
    today = datetime.date.today()
    opportunities = []
    risks = []
    
    invoices = db.query(Invoice).filter(Invoice.user_id == user_id, Invoice.status != "Cancelled").all()
    clients = db.query(Client).filter(Client.user_id == user_id).all()
    projects = db.query(Project).filter(Project.user_id == user_id).all()
    tasks = db.query(Task).filter(Task.user_id == user_id).all()
    
    # ------------------ OPPORTUNITIES ------------------
    # 1. Repeat Client Upsell Opportunity
    for c in clients:
        completed_projs = db.query(Project).filter(
            Project.client_id == c.id,
            Project.status == "Completed"
        ).count()
        if completed_projs >= 3:
            opportunities.append({
                "type": "upsell",
                "icon": "💡",
                "title": "Repeat Client Opportunity",
                "message": f"Client '{c.client_name}' has completed {completed_projs} projects. Consider offering a premium package or retainer."
            })
            
    # 2. Revenue Collection Opportunity
    pending_amount = sum(inv.amount for inv in invoices if inv.status in ["Draft", "Sent", "Pending", "Overdue"])
    if pending_amount > 0:
        opportunities.append({
            "type": "cash_flow",
            "icon": "💰",
            "title": "Revenue Opportunity",
            "message": f"Collecting all pending/overdue invoices would increase cash flow by ₹{pending_amount:,.2f}."
        })
        
    # 3. Client Inactivity Retention Opportunity
    inactive_clients_count = 0
    for c in clients:
        last_act = get_client_last_activity_date(db, c)
        if (today - last_act).days > 14:
            inactive_clients_count += 1
            
    if inactive_clients_count > 0:
        opportunities.append({
            "type": "retention",
            "icon": "💡",
            "title": "Retention Opportunity",
            "message": f"{inactive_clients_count} client(s) have not interacted recently. Re-connect to see if they have new design or development requirements."
        })
        
    if not opportunities:
        opportunities.append({
            "type": "general",
            "icon": "💡",
            "title": "Pipeline Opportunity",
            "message": "Ask existing clients for feedback and referrals to expand your pipeline."
        })

    # ------------------ RISKS ------------------
    # 1. Revenue Concentration Risk
    paid_revenue_total = sum(inv.amount for inv in invoices if inv.status == "Paid")
    if paid_revenue_total > 0:
        client_totals = {}
        for inv in invoices:
            if inv.status == "Paid":
                client_totals[inv.client_id] = client_totals.get(inv.client_id, 0.0) + inv.amount
                
        if client_totals:
            top_client_id = max(client_totals, key=client_totals.get)
            top_client_amount = client_totals[top_client_id]
            top_client_share = round((top_client_amount / paid_revenue_total) * 100, 1)
            
            top_client = db.query(Client).filter(Client.id == top_client_id).first()
            top_client_name = top_client.client_name if top_client else "Independent Client"
            
            if top_client_share >= 50:
                risks.append({
                    "type": "revenue_concentration",
                    "icon": "⚠️",
                    "title": "Revenue Concentration Risk",
                    "message": f"One client ({top_client_name}) contributes {top_client_share}% of total paid revenue. Diversifying your client base is recommended to mitigate risks."
                })

    # 2. Invoice Collection Risk
    overdue_amount = sum(inv.amount for inv in invoices if inv.status == "Overdue")
    unpaid_amount_all = sum(inv.amount for inv in invoices if inv.status in ["Draft", "Sent", "Pending", "Overdue"])
    
    if unpaid_amount_all > 0:
        overdue_ratio = overdue_amount / unpaid_amount_all
        if overdue_ratio >= 0.3:
            risks.append({
                "type": "invoice_collection",
                "icon": "⚠️",
                "title": "Invoice Collection Risk",
                "message": f"More than {round(overdue_ratio*100)}% of pending invoice value is currently Overdue (₹{overdue_amount:,.2f}). Set strict payment terms or send auto-reminders."
            })

    # 3. Client Inactivity Risk
    total_clients = len(clients)
    if total_clients > 0:
        inactive_ratio = inactive_clients_count / total_clients
        if inactive_ratio >= 0.3:
            risks.append({
                "type": "client_inactivity",
                "icon": "⚠️",
                "title": "Client Inactivity Risk",
                "message": f"{inactive_clients_count} out of {total_clients} clients ({round(inactive_ratio*100)}%) show no recent activity. They may be churning."
            })

    # 4. Project Deadline Risk
    overdue_projects_count = db.query(Project).filter(
        Project.user_id == user_id,
        Project.status != "Completed",
        Project.deadline < today
    ).count()
    
    if overdue_projects_count > 0:
        risks.append({
            "type": "project_delay",
            "icon": "⚠️",
            "title": "Project Delay Risk",
            "message": f"{overdue_projects_count} project(s) are past their schedule deadline but not marked as Completed."
        })

    if not risks:
        risks.append({
            "type": "general",
            "icon": "🛡️",
            "title": "No Direct Risks Detected",
            "message": "All project timelines and collections appear stable. Continue regular updates."
        })

    return {
        "opportunities": opportunities,
        "risks": risks
    }


def get_client_health_overview(db: Session, user_id: int) -> List[Dict[str, Any]]:
    """
    Calculates health scores and indicators for all clients.
    """
    clients = db.query(Client).filter(Client.user_id == user_id).all()
    overview = []
    for c in clients:
        overview.append(calculate_client_health(db, c))
    
    overview.sort(key=lambda x: x["score"])
    return overview


def get_growth_summary(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Orchestrates all rule calculations into a unified Growth and Business Analytics object.
    """
    from app.crud.invoice import get_revenue_statistics
    
    health_score = calculate_business_health_score(db, user_id)
    insights = get_smart_insights(db, user_id)
    priorities = get_weekly_priorities(db, user_id)
    opps_and_risks = get_opportunities_and_risks(db, user_id)
    client_health = get_client_health_overview(db, user_id)
    
    invoice_stats = get_revenue_statistics(db, user_id=user_id)
    
    return {
        "business_health": health_score,
        "insights": insights,
        "priorities": priorities,
        "opportunities": opps_and_risks["opportunities"],
        "risks": opps_and_risks["risks"],
        "client_health": client_health,
        "revenue": invoice_stats["revenue"],
        "invoices": invoice_stats["invoices"],
        "charts": invoice_stats["charts"]
    }

