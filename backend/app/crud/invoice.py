from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import List, Optional
import datetime
from app.models.invoice import Invoice
from app.models.client import Client
from app.models.project import Project
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate

def get_invoice_by_id(db: Session, invoice_id: int, user_id: int) -> Optional[Invoice]:
    """
    Fetches an invoice by ID, restricted by user_id to enforce multi-tenant isolation.
    """
    return db.query(Invoice).options(
        joinedload(Invoice.client),
        joinedload(Invoice.project)
    ).filter(
        Invoice.id == invoice_id,
        Invoice.user_id == user_id
    ).first()

def get_invoices(
    db: Session,
    user_id: int,
    search: Optional[str] = None,
    status: Optional[str] = None,
    client_id: Optional[int] = None,
    project_id: Optional[int] = None
) -> List[Invoice]:
    """
    Retrieves all invoices belonging to a user, executing dynamic overdue updates first,
    with optional filtering and search parameters.
    """
    # 1. Run dynamic overdue updates
    check_and_update_overdue(db, user_id=user_id)

    # 2. Build Query
    query = db.query(Invoice).options(
        joinedload(Invoice.client),
        joinedload(Invoice.project)
    ).filter(Invoice.user_id == user_id)

    if search:
        search_filter = f"%{search}%"
        # Outer join on Client and Project to search across client names, company names, and project names
        query = query.outerjoin(Client, Invoice.client_id == Client.id)\
                     .outerjoin(Project, Invoice.project_id == Project.id)\
                     .filter(
                         or_(
                             Invoice.invoice_number.ilike(search_filter),
                             Invoice.title.ilike(search_filter),
                             Client.client_name.ilike(search_filter),
                             Client.company_name.ilike(search_filter),
                             Project.project_name.ilike(search_filter)
                         )
                     )

    if status:
        query = query.filter(Invoice.status == status)

    if client_id is not None:
        query = query.filter(Invoice.client_id == client_id)

    if project_id is not None:
        query = query.filter(Invoice.project_id == project_id)

    return query.order_by(Invoice.created_at.desc()).all()

def generate_invoice_number(db: Session, user_id: int) -> str:
    """
    Generates a unique, sequential invoice number for a given user.
    E.g., INV-001, INV-002, etc.
    """
    last_invoice = db.query(Invoice).filter(Invoice.user_id == user_id).order_by(Invoice.id.desc()).first()
    if not last_invoice:
        return "INV-001"
    
    number_str = last_invoice.invoice_number
    if number_str.startswith("INV-"):
        try:
            num = int(number_str.split("-")[1])
            return f"INV-{num + 1:03d}"
        except (ValueError, IndexError):
            pass
            
    return f"INV-{last_invoice.id + 1:03d}"

def create_invoice(db: Session, obj_in: InvoiceCreate, user_id: int) -> Invoice:
    """
    Creates a new invoice record, auto-generates invoice number, and dispatches a notification.
    """
    invoice_num = generate_invoice_number(db, user_id=user_id)
    
    db_obj = Invoice(
        user_id=user_id,
        client_id=obj_in.client_id,
        project_id=obj_in.project_id,
        invoice_number=invoice_num,
        title=obj_in.title.strip(),
        description=obj_in.description.strip() if obj_in.description else None,
        amount=obj_in.amount,
        status=obj_in.status.strip() if obj_in.status else "Draft",
        issue_date=obj_in.issue_date,
        due_date=obj_in.due_date,
        paid_date=datetime.datetime.now() if obj_in.status == "Paid" else None
    )
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    # Dispatch invoice_created notification/activity
    from app.services.dispatcher import dispatcher
    dispatcher.dispatch(
        db=db,
        user_id=user_id,
        notification_type="invoice_created",
        title="Invoice Created",
        message=f"Invoice \"{db_obj.invoice_number}\" for {db_obj.client_name} was created.",
        project_id=db_obj.project_id
    )

    from app.crud.activity_log import create_activity_log
    create_activity_log(
        db=db,
        user_id=user_id,
        action_type="create",
        entity_type="invoice",
        entity_id=db_obj.id,
        title="Invoice Created",
        description=f"Invoice '{db_obj.invoice_number}' was created."
    )

    return db_obj

def update_invoice(db: Session, db_invoice: Invoice, obj_in: InvoiceUpdate) -> Invoice:
    """
    Updates details of an invoice. Tracks status changes to automatically manage paid_date
    timestamps and trigger notification updates.
    """
    old_status = db_invoice.status
    update_data = obj_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if isinstance(value, str):
            setattr(db_invoice, field, value.strip())
        else:
            setattr(db_invoice, field, value)

    # Automatically manage paid_date when status changes to Paid
    if db_invoice.status == "Paid" and old_status != "Paid":
        db_invoice.paid_date = datetime.datetime.now()
    elif db_invoice.status != "Paid":
        db_invoice.paid_date = None

    db.commit()
    db.refresh(db_invoice)

    from app.crud.activity_log import create_activity_log
    # Dispatch notification on status transitions
    if db_invoice.status != old_status:
        from app.services.dispatcher import dispatcher
        if db_invoice.status == "Paid":
            dispatcher.dispatch(
                db=db,
                user_id=db_invoice.user_id,
                notification_type="invoice_paid",
                title="Invoice Paid",
                message=f"Invoice \"{db_invoice.invoice_number}\" has been marked as Paid.",
                project_id=db_invoice.project_id
            )
        elif db_invoice.status == "Overdue":
            dispatcher.dispatch(
                db=db,
                user_id=db_invoice.user_id,
                notification_type="invoice_overdue",
                title="Invoice Overdue",
                message=f"Invoice \"{db_invoice.invoice_number}\" is now Overdue.",
                project_id=db_invoice.project_id
            )

    if db_invoice.status == "Paid" and old_status != "Paid":
        create_activity_log(
            db=db,
            user_id=db_invoice.user_id,
            action_type="paid",
            entity_type="invoice",
            entity_id=db_invoice.id,
            title="Invoice Paid",
            description=f"Invoice '{db_invoice.invoice_number}' was paid."
        )
    else:
        create_activity_log(
            db=db,
            user_id=db_invoice.user_id,
            action_type="update",
            entity_type="invoice",
            entity_id=db_invoice.id,
            title="Invoice Updated",
            description=f"Invoice '{db_invoice.invoice_number}' was updated."
        )

    return db_invoice

def delete_invoice(db: Session, db_invoice: Invoice) -> Invoice:
    """
    Deletes the invoice from the database.
    """
    user_id = db_invoice.user_id
    invoice_id = db_invoice.id
    invoice_number = db_invoice.invoice_number

    db.delete(db_invoice)
    db.commit()

    from app.crud.activity_log import create_activity_log
    create_activity_log(
        db=db,
        user_id=user_id,
        action_type="delete",
        entity_type="invoice",
        entity_id=invoice_id,
        title="Invoice Deleted",
        description=f"Invoice '{invoice_number}' was deleted."
    )

    return db_invoice

def check_and_update_overdue(db: Session, user_id: int):
    """
    Transition status to Overdue if due_date is in the past and current status is not Paid/Cancelled.
    Only dispatches a notification when the invoice transitions.
    """
    today = datetime.date.today()
    from app.services.dispatcher import dispatcher
    from app.crud.activity_log import create_activity_log

    overdue_invoices = db.query(Invoice).filter(
        Invoice.user_id == user_id,
        Invoice.due_date < today,
        Invoice.status.in_(["Draft", "Sent", "Pending"])
    ).all()

    for inv in overdue_invoices:
        inv.status = "Overdue"
        dispatcher.dispatch(
            db=db,
            user_id=user_id,
            notification_type="invoice_overdue",
            title="Invoice Overdue Alert",
            message=f"Invoice \"{inv.invoice_number}\" for client \"{inv.client_name}\" is overdue (Due: {inv.due_date}).",
            project_id=inv.project_id
        )

        create_activity_log(
            db=db,
            user_id=user_id,
            action_type="update",
            entity_type="invoice",
            entity_id=inv.id,
            title="Invoice Overdue",
            description=f"Invoice '{inv.invoice_number}' is now Overdue."
        )

    if overdue_invoices:
        db.commit()

def get_revenue_statistics(db: Session, user_id: int) -> dict:
    """
    Calculates all metrics, status distributions, monthly breakdowns, and weekly trends.
    """
    # 1. Update overdue records before calculating stats
    check_and_update_overdue(db, user_id=user_id)

    # Fetch all invoices for this user
    all_invoices = db.query(Invoice).options(joinedload(Invoice.client)).filter(Invoice.user_id == user_id).all()

    # Metrics totals
    total_rev = 0.0
    paid_rev = 0.0
    pending_rev = 0.0
    overdue_rev = 0.0

    total_count = 0
    paid_count = 0
    pending_count = 0
    overdue_count = 0

    status_distribution_map = {
        "Draft": {"count": 0, "amount": 0.0},
        "Sent": {"count": 0, "amount": 0.0},
        "Pending": {"count": 0, "amount": 0.0},
        "Paid": {"count": 0, "amount": 0.0},
        "Overdue": {"count": 0, "amount": 0.0},
        "Cancelled": {"count": 0, "amount": 0.0}
    }

    # Accrual metrics grouping
    for inv in all_invoices:
        status = inv.status
        amount = inv.amount

        # Update distribution helper
        if status in status_distribution_map:
            status_distribution_map[status]["count"] += 1
            status_distribution_map[status]["amount"] += amount

        if status == "Cancelled":
            continue

        total_rev += amount
        total_count += 1

        if status == "Paid":
            paid_rev += amount
            paid_count += 1
        elif status == "Overdue":
            overdue_rev += amount
            overdue_count += 1
        elif status in ["Draft", "Sent", "Pending"]:
            pending_rev += amount
            pending_count += 1

    # 1. Monthly Revenue (Past 6 Months)
    today = datetime.date.today()
    months = []
    # Build list of past 6 months (chronological)
    for i in range(5, -1, -1):
        # Subtract months
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        months.append((year, month))

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly_revenue = []

    for y, m in months:
        monthly_total = sum(inv.amount for inv in all_invoices if inv.status != "Cancelled" and inv.issue_date.year == y and inv.issue_date.month == m)
        monthly_revenue.append({
            "month": f"{month_names[m-1]} {y}",
            "amount": monthly_total
        })

    # 2. Invoice Status Distribution
    status_distribution = [
        {
            "status": status,
            "count": data["count"],
            "amount": data["amount"]
        }
        for status, data in status_distribution_map.items()
    ]

    # 3. Revenue Trend (Weekly cumulative for current month)
    curr_month_invoices = [
        inv for inv in all_invoices
        if inv.status != "Cancelled" and inv.issue_date.year == today.year and inv.issue_date.month == today.month
    ]

    # Divide month into 4 weeks
    week_totals = [0.0] * 4
    for inv in curr_month_invoices:
        day = inv.issue_date.day
        if day <= 7:
            week_totals[0] += inv.amount
        elif day <= 14:
            week_totals[1] += inv.amount
        elif day <= 21:
            week_totals[2] += inv.amount
        else:
            week_totals[3] += inv.amount

    # Cumulative trend
    revenue_trend = []
    cumulative = 0.0
    for idx, amt in enumerate(week_totals):
        cumulative += amt
        revenue_trend.append({
            "week": f"Week {idx + 1}",
            "amount": cumulative
        })

    # 4. Client Contributions (Future ready details)
    client_totals = {}
    for inv in all_invoices:
        if inv.status == "Cancelled":
            continue
        c_id = inv.client_id
        c_name = inv.client_name or "Independent Client"
        comp_name = inv.company_name or ""
        display_name = f"{c_name} ({comp_name})" if comp_name else c_name
        
        if c_id not in client_totals:
            client_totals[c_id] = {"name": display_name, "paid_amount": 0.0, "total_amount": 0.0}
        
        client_totals[c_id]["total_amount"] += inv.amount
        if inv.status == "Paid":
            client_totals[c_id]["paid_amount"] += inv.amount

    client_contribution = []
    for c_id, stats in client_totals.items():
        percentage = (stats["paid_amount"] / paid_rev * 100) if paid_rev > 0 else 0.0
        client_contribution.append({
            "client_id": c_id,
            "client_name": stats["name"],
            "paid_amount": stats["paid_amount"],
            "total_amount": stats["total_amount"],
            "contribution_percentage": round(percentage, 2)
        })

    # Sort clients by paid amount descending
    client_contribution.sort(key=lambda x: x["paid_amount"], reverse=True)

    return {
        "revenue": {
            "total": total_rev,
            "paid": paid_rev,
            "pending": pending_rev,
            "overdue": overdue_rev
        },
        "invoices": {
            "total": total_count,
            "paid": paid_count,
            "pending": pending_count,
            "overdue": overdue_count
        },
        "charts": {
            "monthly_revenue": monthly_revenue,
            "status_distribution": status_distribution,
            "revenue_trend": revenue_trend
        },
        "analytics": {
            "client_contribution": client_contribution,
            "top_paying_clients": client_contribution[:5]
        }
    }
