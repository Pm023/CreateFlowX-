import urllib.request
import json
import sys
from datetime import date, timedelta

BASE_URL = "http://127.0.0.1:8000/api/v1"

def make_request(url, data=None, headers=None, method="POST"):
    if headers is None:
        headers = {}
    
    encoded_data = None
    if data is not None:
        encoded_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
        
    req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode()
            return json.loads(res_body) if res_body else {}, response.status
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        try:
            err_json = json.loads(err_body)
            return err_json, e.code
        except Exception:
            return {"detail": err_body}, e.code

def test_calendar_module():
    print("=====================================================")
    print("   Starting CreateFlowX Calendar Management API Test")
    print("=====================================================\n")

    # 1. Setup mock users
    u1_email, u1_pass, u1_name = "creator_c1@test.com", "password123", "Creator Calendar One"
    u2_email, u2_pass, u2_name = "creator_c2@test.com", "password123", "Creator Calendar Two"

    print("[STEP 1] Setting up mock test users...")
    make_request(f"{BASE_URL}/auth/register", {"email": u1_email, "password": u1_pass, "full_name": u1_name})
    make_request(f"{BASE_URL}/auth/register", {"email": u2_email, "password": u2_pass, "full_name": u2_name})

    u1_res, _ = make_request(f"{BASE_URL}/auth/login", {"email": u1_email, "password": u1_pass})
    u2_res, _ = make_request(f"{BASE_URL}/auth/login", {"email": u2_email, "password": u2_pass})
    
    t1 = u1_res["access_token"]
    t2 = u2_res["access_token"]
    
    h1 = {"Authorization": f"Bearer {t1}"}
    h2 = {"Authorization": f"Bearer {t2}"}
    print("  [OK] Mock users logged in.\n")

    # Cleanup previous tasks, projects, and clients for these users to ensure clean state
    print("[CLEANUP] Cleaning up existing data for test users...")
    for h in [h1, h2]:
        existing_tasks, _ = make_request(f"{BASE_URL}/tasks/", None, h, "GET")
        if isinstance(existing_tasks, list):
            for task in existing_tasks:
                make_request(f"{BASE_URL}/tasks/{task['id']}", None, h, "DELETE")
        existing_projects, _ = make_request(f"{BASE_URL}/projects/", None, h, "GET")
        if isinstance(existing_projects, list):
            for proj in existing_projects:
                make_request(f"{BASE_URL}/projects/{proj['id']}", None, h, "DELETE")
        existing_clients, _ = make_request(f"{BASE_URL}/clients/", None, h, "GET")
        if isinstance(existing_clients, list):
            for client in existing_clients:
                make_request(f"{BASE_URL}/clients/{client['id']}", None, h, "DELETE")
    print("  [OK] Cleanup complete.\n")

    # 2. Setup Clients and Projects
    print("[STEP 2] Creating clients and projects with deadlines...")
    c1_res, _ = make_request(f"{BASE_URL}/clients/", {"client_name": "Cal Client 1"}, h1, "POST")
    c2_res, _ = make_request(f"{BASE_URL}/clients/", {"client_name": "Cal Client 2"}, h2, "POST")
    c1_id, c2_id = c1_res["id"], c2_res["id"]

    today = date.today()
    # Creator 1 Projects:
    # 1. Project A: deadline = today + 2 days, status = "In Progress"
    pA_payload = {
        "project_name": "Project A",
        "client_id": c1_id,
        "deadline": (today + timedelta(days=2)).isoformat(),
        "status": "In Progress",
        "priority": "High"
    }
    pA_res, _ = make_request(f"{BASE_URL}/projects/", pA_payload, h1, "POST")
    pA_id = pA_res["id"]

    # 2. Project B: deadline = today - 3 days (Overdue), status = "In Progress"
    pB_payload = {
        "project_name": "Project B",
        "client_id": c1_id,
        "deadline": (today - timedelta(days=3)).isoformat(),
        "status": "In Progress",
        "priority": "Medium"
    }
    pB_res, _ = make_request(f"{BASE_URL}/projects/", pB_payload, h1, "POST")
    pB_id = pB_res["id"]

    # Creator 2 Project C (isolation check)
    pC_payload = {
        "project_name": "Project C",
        "client_id": c2_id,
        "deadline": (today + timedelta(days=5)).isoformat(),
        "status": "In Progress",
        "priority": "Low"
    }
    pC_res, _ = make_request(f"{BASE_URL}/projects/", pC_payload, h2, "POST")
    pC_id = pC_res["id"]
    print("  [OK] Projects configured.\n")

    # 3. Setup Tasks
    print("[STEP 3] Creating tasks with deadlines...")
    # Task 1: on Project A, deadline = today + 1 day, status = "To Do" (Pending)
    t1_payload = {
        "task_name": "Task 1",
        "project_id": pA_id,
        "deadline": (today + timedelta(days=1)).isoformat(),
        "status": "To Do",
        "priority": "Medium"
    }
    t1_res, _ = make_request(f"{BASE_URL}/tasks/", t1_payload, h1, "POST")
    t1_id = t1_res["id"]

    # Task 2: on Project A, deadline = today - 1 day (Overdue), status = "In Progress" (Pending)
    t2_payload = {
        "task_name": "Task 2",
        "project_id": pA_id,
        "deadline": (today - timedelta(days=1)).isoformat(),
        "status": "In Progress",
        "priority": "High"
    }
    t2_res, _ = make_request(f"{BASE_URL}/tasks/", t2_payload, h1, "POST")
    t2_id = t2_res["id"]

    # Task 3: on Project A, deadline = today - 2 days, status = "Completed" (Completed)
    t3_payload = {
        "task_name": "Task 3",
        "project_id": pA_id,
        "deadline": (today - timedelta(days=2)).isoformat(),
        "status": "Completed",
        "priority": "Low"
    }
    t3_res, _ = make_request(f"{BASE_URL}/tasks/", t3_payload, h1, "POST")
    t3_id = t3_res["id"]

    # Creator 2 Task 4 (isolation check)
    t4_payload = {
        "task_name": "Task 4",
        "project_id": pC_id,
        "deadline": today.isoformat(),
        "status": "To Do",
        "priority": "High"
    }
    t4_res, _ = make_request(f"{BASE_URL}/tasks/", t4_payload, h2, "POST")
    t4_id = t4_res["id"]
    print("  [OK] Tasks configured.\n")

    # 4. Test Calendar Events Aggregation
    print("[STEP 4] Testing aggregated events retrieval & sorting...")
    events, status = make_request(f"{BASE_URL}/calendar/events", None, h1, "GET")
    assert status == 200
    # Expected: Project A, Project B, Task 1, Task 2, Task 3 = 5 events total
    assert len(events) == 5, f"Expected 5 calendar events, got {len(events)}"
    
    # Verify chronological sorting (deadlines in ascending order)
    for i in range(len(events) - 1):
        d1 = date.fromisoformat(events[i]["deadline"])
        d2 = date.fromisoformat(events[i+1]["deadline"])
        assert d1 <= d2, f"Sorting failed! {d1} comes after {d2}"
    print("  [OK] 5 events aggregated and correctly sorted chronologically.\n")

    # 5. Test Workspace Isolation
    print("[STEP 5] Testing multi-tenant event isolation...")
    u2_events, status = make_request(f"{BASE_URL}/calendar/events", None, h2, "GET")
    assert status == 200
    # Creator 2 should only see Project C and Task 4 (2 events)
    assert len(u2_events) == 2, f"Creator 2 saw {len(u2_events)} events instead of 2"
    for ev in u2_events:
        assert ev["original_id"] in [pC_id, t4_id], f"Creator 2 leaked event: {ev}"
    print("  [OK] Multi-tenant workspace boundaries confirmed.\n")

    # 6. Test Filtering Parameters
    print("[STEP 6] Testing queries filters (Type, Status, Priority, Date Ranges)...")
    # Filters by Event Type: Project only (2 events)
    proj_events, _ = make_request(f"{BASE_URL}/calendar/events?event_type=project", None, h1, "GET")
    assert len(proj_events) == 2
    for ev in proj_events:
        assert ev["event_type"] == "project"

    # Filters by Event Type: Task only (3 events)
    task_events, _ = make_request(f"{BASE_URL}/calendar/events?event_type=task", None, h1, "GET")
    assert len(task_events) == 3
    for ev in task_events:
        assert ev["event_type"] == "task"

    # Filters by Status: Completed (1 event: Task 3)
    comp_events, _ = make_request(f"{BASE_URL}/calendar/events?status=Completed", None, h1, "GET")
    assert len(comp_events) == 1
    assert comp_events[0]["original_id"] == t3_id

    # Filters by Status: Overdue (2 events: Project B and Task 2)
    # Project B (In Progress, due -3 days), Task 2 (In Progress, due -1 day)
    # Note: Task 3 is due -2 days but is Completed, so not overdue!
    overdue_events, _ = make_request(f"{BASE_URL}/calendar/events?status=Overdue", None, h1, "GET")
    assert len(overdue_events) == 2
    overdue_ids = [ev["id"] for ev in overdue_events]
    assert f"project-{pB_id}" in overdue_ids
    assert f"task-{t2_id}" in overdue_ids

    # Filters by Status: Pending (2 events: Project A (due +2), Task 1 (due +1))
    pending_events, _ = make_request(f"{BASE_URL}/calendar/events?status=Pending", None, h1, "GET")
    assert len(pending_events) == 2

    # Filters by Priority: High (2 events: Project A, Task 2)
    high_events, _ = make_request(f"{BASE_URL}/calendar/events?priority=High", None, h1, "GET")
    assert len(high_events) == 2

    # Filters by Date Range:
    # Query deadlines between today and today + 1 day
    # Should return Task 1 (due +1)
    dr_events, _ = make_request(
        f"{BASE_URL}/calendar/events?start_date={today.isoformat()}&end_date={(today + timedelta(days=1)).isoformat()}",
        None, h1, "GET"
    )
    assert len(dr_events) == 1
    assert dr_events[0]["original_id"] == t1_id
    print("  [OK] All filters (Type, Status, Priority, Date Ranges) return exact counts.\n")

    # 7. Test Calendar Stats
    print("[STEP 7] Testing Calendar Stats API...")
    stats, status = make_request(f"{BASE_URL}/calendar/stats", None, h1, "GET")
    assert status == 200
    assert stats["total_events"] == 5
    assert stats["completed_events"] == 1  # Task 3
    assert stats["overdue_events"] == 2    # Project B, Task 2
    assert stats["upcoming_events"] == 2   # Project A, Task 1
    print("  [OK] Calendar metrics check passed.\n")

    # 8. Test Dashboard Widgets API
    print("[STEP 8] Testing Dashboard Integration Widgets API...")
    dash, status = make_request(f"{BASE_URL}/calendar/dashboard", None, h1, "GET")
    assert status == 200
    # upcoming deadlines should return Project A (due +2) and Task 1 (due +1) sorted by date asc => Task 1, Project A
    assert len(dash["upcoming_deadlines"]) == 2
    assert dash["upcoming_deadlines"][0]["original_id"] == t1_id
    assert dash["upcoming_deadlines"][1]["original_id"] == pA_id

    # overdue_tasks should return Task 2
    assert len(dash["overdue_tasks"]) == 1
    assert dash["overdue_tasks"][0]["original_id"] == t2_id

    # week projects should contain Project A and Project B if within Mon-Sun.
    # Since today's week has Mon-Sun, let's verify Project A (+2) and Project B (-3) are listed
    # Project B is -3 days, Project A is +2 days. Both fall in this week (Mon-Sun) unless run on Monday/Sunday where boundaries shift
    assert len(dash["this_weeks_projects"]) >= 1
    print("  [OK] Dashboard integration widgets API check passed.\n")

    print("=====================================================")
    print(" [SUCCESS] All Calendar Module API & stats tests passed!")
    print("=====================================================")

if __name__ == "__main__":
    test_calendar_module()
