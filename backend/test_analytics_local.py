import sys
import os
import datetime

# Add the backend directory to path so we can import app modules
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.client import Client
from app.models.project import Project
from app.models.task import Task
from app.models.notification import Notification
from app.models.invoice import Invoice
from app.models.activity_log import ActivityLog
from app.models.system_settings import SystemSettings
from app.services.analytics_engine import (

    calculate_business_health_score,
    get_smart_insights,
    get_weekly_priorities,
    get_opportunities_and_risks,
    get_client_health_overview,
    get_growth_summary
)

def run_local_analytics_tests():
    print("=====================================================")
    print("  Starting CreateFlowX Direct Local Analytics Test")
    print("=====================================================\n")

    db = SessionLocal()
    
    # 1. Create a mock user
    test_user_email = f"test_local_{int(datetime.datetime.now().timestamp())}@test.com"
    user = User(
        email=test_user_email,
        hashed_password="hashed_password",
        full_name="Local Analyst Tester",
        username=test_user_email.split("@")[0],
        role="creator",
        status="active",
        is_active=True,
        is_verified=True,
        is_deleted=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"Created test user: {user.email} (ID: {user.id})")

    try:
        # 2. Add client
        client = Client(
            user_id=user.id,
            client_name="Test Agency Group",
            company_name="Tag Corp",
            notes="Testing analytics engine calculations"
        )
        db.add(client)
        db.commit()
        db.refresh(client)
        print(f"Created client: {client.client_name} (ID: {client.id})")

        # 3. Create project
        project = Project(
            user_id=user.id,
            client_id=client.id,
            project_name="Growth Implementation Project",
            description="Transforming the analytics platform",
            status="In Progress",
            priority="High",
            progress=40,
            deadline=datetime.date.today() + datetime.timedelta(days=15)
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        print(f"Created project: {project.project_name} (ID: {project.id})")

        # 4. Create tasks
        task_overdue = Task(
            user_id=user.id,
            project_id=project.id,
            task_name="Write backend test suite",
            description="Create mock tests and runs",
            status="To Do",
            priority="High",
            deadline=datetime.date.today() - datetime.timedelta(days=3)
        )
        task_completed = Task(
            user_id=user.id,
            project_id=project.id,
            task_name="Initialize repository",
            description="Set up structures",
            status="Completed",
            priority="Medium",
            deadline=datetime.date.today() - datetime.timedelta(days=1),
            completed_at=datetime.datetime.now()
        )
        db.add(task_overdue)
        db.add(task_completed)
        db.commit()
        db.refresh(task_overdue)
        db.refresh(task_completed)
        print("Created tasks (1 completed, 1 overdue).")

        # 5. Create invoices
        invoice_overdue = Invoice(
            user_id=user.id,
            client_id=client.id,
            project_id=project.id,
            invoice_number="INV-TEST-001",
            title="Setup Fee Invoice",
            amount=18000.0,
            status="Overdue",
            issue_date=datetime.date.today() - datetime.timedelta(days=20),
            due_date=datetime.date.today() - datetime.timedelta(days=5)
        )
        invoice_paid = Invoice(
            user_id=user.id,
            client_id=client.id,
            project_id=project.id,
            invoice_number="INV-TEST-002",
            title="Design Phase Invoice",
            amount=12000.0,
            status="Paid",
            issue_date=datetime.date.today() - datetime.timedelta(days=35),
            due_date=datetime.date.today() - datetime.timedelta(days=20),
            paid_date=datetime.datetime.now() - datetime.timedelta(days=20)
        )
        db.add(invoice_overdue)
        db.add(invoice_paid)
        db.commit()
        db.refresh(invoice_overdue)
        db.refresh(invoice_paid)
        print("Created invoices (1 paid, 1 overdue).")

        # 6. Test calculations
        print("\n--- Running calculations ---")
        
        # Test business health score
        bh = calculate_business_health_score(db, user.id)
        print(f"Business Health Score: {bh['score']}/100")
        print(f"Business Health Level: {bh['level']}")
        assert 0 <= bh['score'] <= 100
        
        # Test smart insights
        insights = get_smart_insights(db, user.id)
        print(f"Insights Generated: {len(insights)}")
        for insight in insights:
            print(f"  [{insight['category']}] {insight['icon']} {insight['title']}: {insight['message']}")
        
        # Test weekly priorities
        priorities = get_weekly_priorities(db, user.id)
        print(f"Coaching Priorities: {len(priorities)}")
        for pr in priorities:
            print(f"  {pr['priority']}. {pr['title']} - {pr['description']}")
        assert len(priorities) > 0
        
        # Test opportunities and risks
        opps_risks = get_opportunities_and_risks(db, user.id)
        print(f"Opportunities: {len(opps_risks['opportunities'])}")
        for op in opps_risks['opportunities']:
            print(f"  [OPP] {op['title']}: {op['message']}")
        print(f"Risks: {len(opps_risks['risks'])}")
        for rk in opps_risks['risks']:
            print(f"  [RISK] {rk['title']}: {rk['message']}")

        # Test client health scoreboard
        client_health = get_client_health_overview(db, user.id)
        print(f"Client Health Overview (Count: {len(client_health)}):")
        for ch in client_health:
            print(f"  Client: {ch['client_name']} - Score: {ch['score']}/100, Level: {ch['status']}")
            assert 0 <= ch['score'] <= 100

        # Test full summary
        summary = get_growth_summary(db, user.id)
        assert "revenue" in summary
        assert "charts" in summary
        print("\n[SUCCESS] Growth Engine data verified successfully!")

    finally:
        # Clean up database records
        print("\nCleaning up test records...")
        db.query(Invoice).filter(Invoice.user_id == user.id).delete()
        db.query(Task).filter(Task.user_id == user.id).delete()
        db.query(Project).filter(Project.user_id == user.id).delete()
        db.query(Client).filter(Client.user_id == user.id).delete()
        db.query(User).filter(User.id == user.id).delete()
        db.commit()
        db.close()
        print("Database cleanup completed.")

if __name__ == "__main__":
    run_local_analytics_tests()
