import urllib.request
import json
import sys
from datetime import date, timedelta

BASE_URL = "http://127.0.0.1:8000/api/v1"

def make_request(url, data=None, headers=None, method="POST"):
    """
    Helper to perform HTTP requests and return parsed JSON data or HTTP status.
    """
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

def test_task_module():
    print("=====================================================")
    print("   Starting CreateFlowX Task Management API Test")
    print("=====================================================\n")

    # 1. Setup mock users
    u1_email, u1_pass, u1_name = "creator_t1@test.com", "password123", "Creator Task One"
    u2_email, u2_pass, u2_name = "creator_t2@test.com", "password123", "Creator Task Two"

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
    existing_tasks, _ = make_request(f"{BASE_URL}/tasks/", None, h1, "GET")
    if isinstance(existing_tasks, list):
        for task in existing_tasks:
            make_request(f"{BASE_URL}/tasks/{task['id']}", None, h1, "DELETE")
    existing_tasks2, _ = make_request(f"{BASE_URL}/tasks/", None, h2, "GET")
    if isinstance(existing_tasks2, list):
        for task in existing_tasks2:
            make_request(f"{BASE_URL}/tasks/{task['id']}", None, h2, "DELETE")

    existing_projects, _ = make_request(f"{BASE_URL}/projects/", None, h1, "GET")
    if isinstance(existing_projects, list):
        for proj in existing_projects:
            make_request(f"{BASE_URL}/projects/{proj['id']}", None, h1, "DELETE")
    existing_projects2, _ = make_request(f"{BASE_URL}/projects/", None, h2, "GET")
    if isinstance(existing_projects2, list):
        for proj in existing_projects2:
            make_request(f"{BASE_URL}/projects/{proj['id']}", None, h2, "DELETE")

    existing_clients, _ = make_request(f"{BASE_URL}/clients/", None, h1, "GET")
    if isinstance(existing_clients, list):
        for client in existing_clients:
            make_request(f"{BASE_URL}/clients/{client['id']}", None, h1, "DELETE")
    existing_clients2, _ = make_request(f"{BASE_URL}/clients/", None, h2, "GET")
    if isinstance(existing_clients2, list):
        for client in existing_clients2:
            make_request(f"{BASE_URL}/clients/{client['id']}", None, h2, "DELETE")
    print("  [OK] Cleanup complete.\n")

    # 2. Setup Clients and Projects
    print("[STEP 2] Creating clients and projects...")
    c1_res, _ = make_request(f"{BASE_URL}/clients/", {"client_name": "Client 1"}, h1, "POST")
    c2_res, _ = make_request(f"{BASE_URL}/clients/", {"client_name": "Client 2"}, h2, "POST")
    c1_id, c2_id = c1_res["id"], c2_res["id"]

    p1_res, _ = make_request(f"{BASE_URL}/projects/", {"project_name": "Project A", "client_id": c1_id}, h1, "POST")
    p2_res, _ = make_request(f"{BASE_URL}/projects/", {"project_name": "Project B", "client_id": c2_id}, h2, "POST")
    p1_id, p2_id = p1_res["id"], p2_res["id"]
    print(f"  [OK] Project A (ID: {p1_id}) and Project B (ID: {p2_id}) created.\n")

    # 3. Test Security Boundary for Project Association
    print("[STEP 3] Testing cross-tenant project association protection...")
    bad_task_payload = {
        "task_name": "Hack Task",
        "project_id": p2_id, # Creator 1 trying to add task to Creator 2's project
        "status": "To Do"
    }
    res, status = make_request(f"{BASE_URL}/tasks/", bad_task_payload, h1, "POST")
    assert status == 404, f"Security Breach! Task associated with project from another workspace (status: {status})"
    print("  [OK] Success: Cross-workspace project association blocked.\n")

    # 4. Create tasks and check dynamic project progress recalculation
    print("[STEP 4] Creating tasks and verifying auto-calculated project progress...")
    
    # Check initial progress is 0
    p1_data, _ = make_request(f"{BASE_URL}/projects/{p1_id}", None, h1, "GET")
    assert p1_data["progress"] == 0, f"Expected initial project progress to be 0, got {p1_data['progress']}"

    # Create Task 1 (status: To Do)
    t1_payload = {
        "task_name": "Design Wireframes",
        "project_id": p1_id,
        "description": "Figma mockups",
        "status": "To Do",
        "priority": "High",
        "deadline": (date.today() + timedelta(days=2)).isoformat()
    }
    t1_res, status = make_request(f"{BASE_URL}/tasks/", t1_payload, h1, "POST")
    assert status == 201
    t1_id = t1_res["id"]
    print(f"  a. Task 1 created (ID: {t1_id}, Status: To Do).")

    # Project progress should still be 0% (0 of 1 task completed)
    p1_data, _ = make_request(f"{BASE_URL}/projects/{p1_id}", None, h1, "GET")
    assert p1_data["progress"] == 0, f"Expected project progress 0%, got {p1_data['progress']}"
    print(f"     Project progress: {p1_data['progress']}% (0/1 completed) - [OK]")

    # Create Task 2 (status: Completed)
    t2_payload = {
        "task_name": "Setup Repository",
        "project_id": p1_id,
        "status": "Completed",
        "priority": "Medium"
    }
    t2_res, status = make_request(f"{BASE_URL}/tasks/", t2_payload, h1, "POST")
    assert status == 201
    t2_id = t2_res["id"]
    assert t2_res["completed_at"] is not None, "completed_at should be saved automatically"
    print(f"  b. Task 2 created (ID: {t2_id}, Status: Completed). Completed_at set: {t2_res['completed_at'] != None}")

    # Project progress should be 50% (1 of 2 tasks completed)
    p1_data, _ = make_request(f"{BASE_URL}/projects/{p1_id}", None, h1, "GET")
    assert p1_data["progress"] == 50, f"Expected project progress 50%, got {p1_data['progress']}"
    print(f"     Project progress: {p1_data['progress']}% (1/2 completed) - [OK]\n")

    # 5. Status Transition and completed_at checks
    print("[STEP 5] Testing status transition completed_at hooks...")
    # Update Task 1 status to Completed
    t1_update_payload = {"status": "Completed"}
    t1_res, status = make_request(f"{BASE_URL}/tasks/{t1_id}", t1_update_payload, h1, "PUT")
    assert status == 200
    assert t1_res["status"] == "Completed"
    assert t1_res["completed_at"] is not None
    print(f"  a. Updated Task 1 to Completed. Completed_at set: {t1_res['completed_at'] != None}")

    # Project progress should be 100% (2 of 2 tasks completed)
    p1_data, _ = make_request(f"{BASE_URL}/projects/{p1_id}", None, h1, "GET")
    assert p1_data["progress"] == 100, f"Expected project progress 100%, got {p1_data['progress']}"
    print(f"     Project progress: {p1_data['progress']}% (2/2 completed) - [OK]")

    # Transition Task 1 back to In Progress
    t1_update_payload = {"status": "In Progress"}
    t1_res, status = make_request(f"{BASE_URL}/tasks/{t1_id}", t1_update_payload, h1, "PUT")
    assert status == 200
    assert t1_res["status"] == "In Progress"
    assert t1_res["completed_at"] is None
    print("  b. Rolled back Task 1 to In Progress. Completed_at cleared (None).")

    # Project progress should go back to 50%
    p1_data, _ = make_request(f"{BASE_URL}/projects/{p1_id}", None, h1, "GET")
    assert p1_data["progress"] == 50, f"Expected project progress 50%, got {p1_data['progress']}"
    print(f"     Project progress: {p1_data['progress']}% (1/2 completed) - [OK]\n")

    # 6. Multi-Tenant Task Isolation Checks
    print("[STEP 6] Testing Multi-Tenant Task Isolation guards...")
    
    # Creator 2 attempts to fetch Creator 1's Task
    res, status = make_request(f"{BASE_URL}/tasks/{t1_id}", None, h2, "GET")
    assert status == 404
    # Creator 2 attempts to update Creator 1's Task
    res, status = make_request(f"{BASE_URL}/tasks/{t1_id}", {"task_name": "Hacked Task"}, h2, "PUT")
    assert status == 404
    # Creator 2 attempts to delete Creator 1's Task
    res, status = make_request(f"{BASE_URL}/tasks/{t1_id}", None, h2, "DELETE")
    assert status == 404
    print("  [OK] Success: Multi-tenant access controls verify isolation (Returned 404).\n")

    # 7. Lists, Searches, and Filters
    print("[STEP 7] Testing search and filters on Task list...")
    # List tasks (returns 2)
    list_res, _ = make_request(f"{BASE_URL}/tasks/", None, h1, "GET")
    assert len(list_res) == 2
    # Search hit
    search_res, _ = make_request(f"{BASE_URL}/tasks/?search=Wireframes", None, h1, "GET")
    assert len(search_res) == 1
    # Search project name
    search_res2, _ = make_request(f"{BASE_URL}/tasks/?search=Project%20A", None, h1, "GET")
    assert len(search_res2) == 2
    # Filter status
    filter_res, _ = make_request(f"{BASE_URL}/tasks/?status=Completed", None, h1, "GET")
    assert len(filter_res) == 1
    print("  [OK] Lists, search by name/project, and filters verified.\n")

    # 8. Dashboard stats integration check
    print("[STEP 8] Testing Dashboard Stats API...")
    stats_res, status = make_request(f"{BASE_URL}/tasks/stats", None, h1, "GET")
    assert status == 200
    assert stats_res["total_tasks"] == 2
    assert stats_res["pending_tasks"] == 1
    assert stats_res["completed_tasks"] == 1
    assert len(stats_res["upcoming_deadlines"]) == 1
    print("  [OK] Task statistics values correct.\n")

    # 9. Test Deletions
    print("[STEP 9] Testing Task deletions and progress update...")
    # Delete Task 1 (the remaining pending task)
    res, status = make_request(f"{BASE_URL}/tasks/{t1_id}", None, h1, "DELETE")
    assert status == 200

    # Project progress should now become 100% (1/1 task completed)
    p1_data, _ = make_request(f"{BASE_URL}/projects/{p1_id}", None, h1, "GET")
    assert p1_data["progress"] == 100, f"Expected project progress 100%, got {p1_data['progress']}"
    print(f"  [OK] Task deleted. Project progress recalculated to {p1_data['progress']}% (1/1 completed).\n")

    print("=====================================================")
    print(" [SUCCESS] All Task Management security & CRUD tests passed!")
    print("=====================================================")

if __name__ == "__main__":
    test_task_module()
