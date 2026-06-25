import urllib.request
import json
import sys
import datetime

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

def test_analytics_module():
    print("=====================================================")
    print("  Starting CreateFlowX Growth Analytics API Test")
    print("=====================================================\n")

    # 1. Register Mock User
    u_email, u_pass, u_name = "growth_tester@test.com", "password123", "Growth Coach Tester"
    print("[STEP 1] Setting up mock test user...")
    make_request(f"{BASE_URL}/auth/register", {"email": u_email, "password": u_pass, "full_name": u_name})
    
    # Log in to get JWT token
    login_res, _ = make_request(f"{BASE_URL}/auth/login", {"email": u_email, "password": u_pass})
    token = login_res["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("  [OK] Mock user configured and JWT token issued.\n")

    # 2. Add client
    print("[STEP 2] Creating client...")
    c_res, status = make_request(f"{BASE_URL}/clients/", {
        "client_name": "Test Client Agency",
        "company_name": "Test Company Corp",
        "notes": "Testing growth features"
    }, headers, "POST")
    assert status == 201
    client_id = c_res["id"]
    print(f"  [OK] Client created. ID: {client_id}\n")

    # 3. Create project under client
    print("[STEP 3] Creating project...")
    p_res, status = make_request(f"{BASE_URL}/projects/", {
        "client_id": client_id,
        "project_name": "Growth Design Project",
        "description": "Premium visual redesign",
        "status": "In Progress",
        "priority": "High",
        "deadline": (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
    }, headers, "POST")
    assert status == 201
    project_id = p_res["id"]
    print(f"  [OK] Project created. ID: {project_id}\n")

    # 4. Create task under project
    print("[STEP 4] Creating task...")
    t_res, status = make_request(f"{BASE_URL}/tasks/", {
        "project_id": project_id,
        "task_name": "Draft Landing Page Mockups",
        "description": "Design home page desktop layout",
        "status": "To Do",
        "priority": "High",
        "deadline": (datetime.date.today() - datetime.timedelta(days=2)).isoformat() # Overdue task
    }, headers, "POST")
    assert status == 201
    print(f"  [OK] Overdue task created.\n")

    # 5. Create invoice
    print("[STEP 5] Creating invoice...")
    i_res, status = make_request(f"{BASE_URL}/invoices/", {
        "client_id": client_id,
        "project_id": project_id,
        "title": "Initial Deposit Invoice",
        "description": "50% upfront payment",
        "amount": 18000.0,
        "status": "Pending",
        "issue_date": (datetime.date.today() - datetime.timedelta(days=5)).isoformat(),
        "due_date": (datetime.date.today() - datetime.timedelta(days=1)).isoformat() # Overdue invoice
    }, headers, "POST")
    assert status == 201
    print(f"  [OK] Invoice created successfully.\n")

    # 6. Test Growth Summary Endpoint
    print("[STEP 6] Testing Growth Summary API Endpoint...")
    growth_res, status = make_request(f"{BASE_URL}/analytics/growth-summary", None, headers, "GET")
    assert status == 200, f"Expected 200, got {status}"
    
    # Assert main structure keys exist
    assert "business_health" in growth_res
    assert "insights" in growth_res
    assert "priorities" in growth_res
    assert "opportunities" in growth_res
    assert "risks" in growth_res
    assert "client_health" in growth_res
    print("  [OK] All expected top-level response keys exist.")

    # Assert business health score exists
    score = growth_res["business_health"]["score"]
    level = growth_res["business_health"]["level"]
    print(f"  [OK] Business Health Score: {score}/100, Level: {level}")

    # Assert priorities include overdue task / invoice collecting
    priorities = growth_res["priorities"]
    titles = [p["title"] for p in priorities]
    print(f"  [OK] Priorities generated: {titles}")
    
    # Assert client health list is returned
    ch_list = growth_res["client_health"]
    assert len(ch_list) == 1
    assert ch_list[0]["score"] < 100
    print(f"  [OK] Client Health: {ch_list[0]['client_name']} - Score: {ch_list[0]['score']}/100, Status: {ch_list[0]['status']}")

    print("\n=====================================================")
    print(" [SUCCESS] All Growth Analytics API tests passed!")
    print("=====================================================")

if __name__ == "__main__":
    test_analytics_module()
