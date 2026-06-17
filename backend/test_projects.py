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

def test_project_module():
    print("=====================================================")
    print("   Starting CreateFlowX Project Management API Test")
    print("=====================================================\n")

    # 1. Setup mock users
    u1_email, u1_pass, u1_name = "creator_p1@test.com", "password123", "Creator Project One"
    u2_email, u2_pass, u2_name = "creator_p2@test.com", "password123", "Creator Project Two"

    print("[STEP 1] Setting up mock test users...")
    # Ignore bad request if already exists, just register to make sure
    make_request(f"{BASE_URL}/auth/register", {"email": u1_email, "password": u1_pass, "full_name": u1_name})
    make_request(f"{BASE_URL}/auth/register", {"email": u2_email, "password": u2_pass, "full_name": u2_name})

    u1_res, _ = make_request(f"{BASE_URL}/auth/login", {"email": u1_email, "password": u1_pass})
    u2_res, _ = make_request(f"{BASE_URL}/auth/login", {"email": u2_email, "password": u2_pass})
    
    t1 = u1_res["access_token"]
    t2 = u2_res["access_token"]
    
    h1 = {"Authorization": f"Bearer {t1}"}
    h2 = {"Authorization": f"Bearer {t2}"}
    print("  [OK] Mock users configured and JWT tokens issued.\n")

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

    # 2. Setup Clients
    print("[STEP 2] Creating clients for each user...")
    c1_res, _ = make_request(f"{BASE_URL}/clients/", {"client_name": "Client of Creator 1"}, h1, "POST")
    c2_res, _ = make_request(f"{BASE_URL}/clients/", {"client_name": "Client of Creator 2"}, h2, "POST")
    
    c1_id = c1_res["id"]
    c2_id = c2_res["id"]
    print(f"  [OK] Client 1 (ID: {c1_id}) and Client 2 (ID: {c2_id}) created.\n")

    # 3. Test Security Boundary for Client Association
    print("[STEP 3] Testing cross-tenant client association protection...")
    bad_project_payload = {
        "project_name": "Unauthorized Project",
        "client_id": c2_id, # Creator 1 attempting to use Creator 2's client
        "description": "Should fail security boundary check",
        "status": "Not Started",
        "priority": "High"
    }
    res, status = make_request(f"{BASE_URL}/projects/", bad_project_payload, h1, "POST")
    assert status == 404, f"Security Breach! Creator 1 associated project with Creator 2's client (status: {status})"
    print("  [OK] Success: Cross-tenant client creation blocked (Returned 404).\n")

    # 4. Create projects
    print("[STEP 4] Creating projects for Creator 1 and Creator 2...")
    deadline_date = (date.today() + timedelta(days=5)).isoformat()
    
    p1_payload = {
        "project_name": "Website Redesign CFX",
        "client_id": c1_id,
        "description": "Redesigning corporate website to responsive design system",
        "status": "In Progress",
        "priority": "High",
        "deadline": deadline_date,
        "progress": 25
    }
    p1_res, status = make_request(f"{BASE_URL}/projects/", p1_payload, h1, "POST")
    assert status == 201, f"Failed project create: {status}"
    p1_id = p1_res["id"]
    print(f"  [OK] Project 1 created (ID: {p1_id}, Name: {p1_res['project_name']})")

    p2_payload = {
        "project_name": "Mobile App UI Development",
        "client_id": c2_id,
        "description": "Flutter design templates",
        "status": "Not Started",
        "priority": "Medium",
        "progress": 0
    }
    p2_res, status = make_request(f"{BASE_URL}/projects/", p2_payload, h2, "POST")
    assert status == 201
    p2_id = p2_res["id"]
    print(f"  [OK] Project 2 created (ID: {p2_id}, Name: {p2_res['project_name']})\n")

    # 5. Multi-Tenant Project Isolation Checks
    print("[STEP 5] Testing Multi-Tenant Project Isolation guards...")
    
    # Creator 1 attempts to fetch Creator 2's Project
    print("  a. Asserting Creator 1 cannot view Creator 2's project...")
    res, status = make_request(f"{BASE_URL}/projects/{p2_id}", None, h1, "GET")
    assert status == 404, f"Security Breach! Creator 1 could read Creator 2's project (status: {status})"
    print("     [OK] Success: Access Denied (Returned 404).")

    # Creator 2 attempts to fetch Creator 1's Project
    print("  b. Asserting Creator 2 cannot view Creator 1's project...")
    res, status = make_request(f"{BASE_URL}/projects/{p1_id}", None, h2, "GET")
    assert status == 404, f"Security Breach! Creator 2 could read Creator 1's project (status: {status})"
    print("     [OK] Success: Access Denied (Returned 404).")

    # Creator 2 attempts to update Creator 1's Project
    print("  c. Asserting Creator 2 cannot update Creator 1's project...")
    res, status = make_request(f"{BASE_URL}/projects/{p1_id}", {"project_name": "Hacked project"}, h2, "PUT")
    assert status == 404, f"Security Breach! Creator 2 could update Creator 1's project (status: {status})"
    print("     [OK] Success: Access Denied (Returned 404).")

    # Creator 2 attempts to delete Creator 1's Project
    print("  d. Asserting Creator 2 cannot delete Creator 1's project...")
    res, status = make_request(f"{BASE_URL}/projects/{p1_id}", None, h2, "DELETE")
    assert status == 404, f"Security Breach! Creator 2 could delete Creator 1's project (status: {status})"
    print("     [OK] Success: Access Denied (Returned 404).\n")

    # 6. Test Searches, Filters, and Lists
    print("[STEP 6] Testing Search and Filters...")
    
    # Creator 1 lists all projects (should return 1)
    list_res, status = make_request(f"{BASE_URL}/projects/", None, h1, "GET")
    assert status == 200
    assert len(list_res) == 1, f"Expected 1 project, got {len(list_res)}"
    assert list_res[0]["project_name"] == "Website Redesign CFX"
    # Ensure client relationships serialize correctly
    assert list_res[0]["client_name"] == "Client of Creator 1"
    print("  [OK] List returns user-owned projects only with client names.")

    # Search hit
    search_res, status = make_request(f"{BASE_URL}/projects/?search=CFX", None, h1, "GET")
    assert len(search_res) == 1
    # Search by client name
    search_res2, status = make_request(f"{BASE_URL}/projects/?search=Creator%201", None, h1, "GET")
    assert len(search_res2) == 1
    # Search miss
    search_res3, status = make_request(f"{BASE_URL}/projects/?search=Mobile", None, h1, "GET")
    assert len(search_res3) == 0
    print("  [OK] Search by project name and client name verified.")

    # Filter status and priority
    filter_res, _ = make_request(f"{BASE_URL}/projects/?status=In%20Progress", None, h1, "GET")
    assert len(filter_res) == 1
    filter_res2, _ = make_request(f"{BASE_URL}/projects/?status=Not%20Started", None, h1, "GET")
    assert len(filter_res2) == 0
    filter_res3, _ = make_request(f"{BASE_URL}/projects/?priority=High", None, h1, "GET")
    assert len(filter_res3) == 1
    filter_res4, _ = make_request(f"{BASE_URL}/projects/?priority=Low", None, h1, "GET")
    assert len(filter_res4) == 0
    print("  [OK] Filters by status and priority verified.\n")

    # 7. Dashboard stats integration check
    print("[STEP 7] Testing Dashboard Stats API...")
    stats_res, status = make_request(f"{BASE_URL}/projects/stats", None, h1, "GET")
    assert status == 200
    assert stats_res["total_projects"] == 1
    assert stats_res["active_projects"] == 1 # Status is "In Progress"
    assert stats_res["completed_projects"] == 0
    assert len(stats_res["upcoming_deadlines"]) == 1
    assert stats_res["upcoming_deadlines"][0]["project_name"] == "Website Redesign CFX"
    print("  [OK] Dashboard statistics parsed successfully.\n")

    # 8. Test Updates and Deletes
    print("[STEP 8] Testing Project updates and deletes...")
    
    # Update progress and status (manual progress edit should be ignored)
    update_payload = {
        "status": "Completed",
        "progress": 100
    }
    update_res, status = make_request(f"{BASE_URL}/projects/{p1_id}", update_payload, h1, "PUT")
    assert status == 200
    assert update_res["status"] == "Completed"
    assert update_res["progress"] == 0  # Ignored manual progress edits
    print("  [OK] Project details updated successfully (manual progress ignored).")

    # Delete project
    delete_res, status = make_request(f"{BASE_URL}/projects/{p1_id}", None, h1, "DELETE")
    assert status == 200
    
    # Verify not found
    res, status = make_request(f"{BASE_URL}/projects/{p1_id}", None, h1, "GET")
    assert status == 404
    print("  [OK] Project deleted successfully and verified.\n")

    print("=====================================================")
    print(" [SUCCESS] All Project Management security & CRUD tests passed!")
    print("=====================================================")

if __name__ == "__main__":
    test_project_module()
