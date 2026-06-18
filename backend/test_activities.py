import urllib.request
import json
import sys
import datetime
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

def test_activities_module():
    print("=====================================================")
    print("   Starting CreateFlowX Activities API Test")
    print("=====================================================\n")

    # Generate unique emails based on timestamp to avoid collisions
    suffix = str(int(datetime.datetime.now().timestamp()))
    u1_email = f"creator_act1_{suffix}@test.com"
    u2_email = f"creator_act2_{suffix}@test.com"
    u1_pass, u1_name = "password123", "Creator Act One"
    u2_pass, u2_name = "password123", "Creator Act Two"

    print(f"[STEP 1] Registering mock test users: {u1_email} & {u2_email}...")
    reg1_res, reg1_status = make_request(f"{BASE_URL}/auth/register", {"email": u1_email, "password": u1_pass, "full_name": u1_name})
    assert reg1_status == 201, f"Failed to register u1: {reg1_res}"
    reg2_res, reg2_status = make_request(f"{BASE_URL}/auth/register", {"email": u2_email, "password": u2_pass, "full_name": u2_name})
    assert reg2_status == 201, f"Failed to register u2: {reg2_res}"

    print("[STEP 2] Logging in mock test users...")
    u1_res, u1_log_status = make_request(f"{BASE_URL}/auth/login", {"email": u1_email, "password": u1_pass})
    assert u1_log_status == 200, f"Login failed for u1: {u1_res}"
    u2_res, u2_log_status = make_request(f"{BASE_URL}/auth/login", {"email": u2_email, "password": u2_pass})
    assert u2_log_status == 200, f"Login failed for u2: {u2_res}"
    
    t1 = u1_res["access_token"]
    t2 = u2_res["access_token"]
    
    h1 = {"Authorization": f"Bearer {t1}"}
    h2 = {"Authorization": f"Bearer {t2}"}
    print("  [OK] Mock users logged in.\n")

    # 3. Verify register & login logs exist for user 1
    print("[STEP 3] Verifying auto-logged authentication events...")
    activities, act_status = make_request(f"{BASE_URL}/activities/", None, h1, "GET")
    assert act_status == 200
    assert len(activities) >= 2, f"Expected at least 2 activities, got: {activities}"
    
    # Check that register and login activities exist (order is newest first, so index 0 = login, index 1 = register)
    assert activities[0]["action_type"] == "login"
    assert activities[0]["entity_type"] == "user"
    assert "User Logged In" in activities[0]["title"]

    assert activities[1]["action_type"] == "register"
    assert activities[1]["entity_type"] == "user"
    assert "Account Registered" in activities[1]["title"]
    print("  [OK] Auth events logged successfully.\n")

    # 4. Test Client CRUD Activity Logging
    print("[STEP 4] Testing Client CRUD activity logs...")
    c_res, c_status = make_request(f"{BASE_URL}/clients/", {"client_name": "Test Act Client", "company_name": "Test Company"}, h1, "POST")
    assert c_status == 201 or c_status == 200
    c_id = c_res["id"]

    # Verify Client Creation Log
    activities, _ = make_request(f"{BASE_URL}/activities/?entity_type=client", None, h1, "GET")
    assert len(activities) == 1
    assert activities[0]["action_type"] == "create"
    assert activities[0]["entity_id"] == c_id
    assert "Client Created" in activities[0]["title"]
    assert "Test Act Client" in activities[0]["description"]

    # Update Client
    update_res, update_status = make_request(f"{BASE_URL}/clients/{c_id}", {"client_name": "Updated Act Client"}, h1, "PUT")
    assert update_status == 200

    # Verify Client Update Log
    activities, _ = make_request(f"{BASE_URL}/activities/?entity_type=client", None, h1, "GET")
    assert len(activities) == 2
    assert activities[0]["action_type"] == "update"
    assert activities[0]["entity_id"] == c_id
    assert "Client Updated" in activities[0]["title"]
    assert "Updated Act Client" in activities[0]["description"]
    print("  [OK] Client create & update logged successfully.\n")

    # 5. Test Project CRUD Activity Logging
    print("[STEP 5] Testing Project CRUD activity logs...")
    p_res, p_status = make_request(f"{BASE_URL}/projects/", {
        "project_name": "Test Act Project",
        "client_id": c_id,
        "deadline": None,
        "status": "Not Started"
    }, h1, "POST")
    assert p_status == 201 or p_status == 200
    p_id = p_res["id"]

    # Verify Project Creation Log
    activities, _ = make_request(f"{BASE_URL}/activities/?entity_type=project", None, h1, "GET")
    assert len(activities) == 1
    assert activities[0]["action_type"] == "create"
    assert activities[0]["entity_id"] == p_id
    assert "Project Created" in activities[0]["title"]

    # Update Project to Completed
    _, up_status = make_request(f"{BASE_URL}/projects/{p_id}", {
        "project_name": "Test Act Project",
        "client_id": c_id,
        "status": "Completed"
    }, h1, "PUT")
    assert up_status == 200

    # Verify Project Completion Log
    activities, _ = make_request(f"{BASE_URL}/activities/?entity_type=project", None, h1, "GET")
    assert len(activities) == 2
    assert activities[0]["action_type"] == "complete"
    assert activities[0]["entity_id"] == p_id
    assert "Project Completed" in activities[0]["title"]
    print("  [OK] Project create & complete logged successfully.\n")

    # 6. Test Task CRUD Activity Logging
    print("[STEP 6] Testing Task CRUD activity logs...")
    t_res, t_status = make_request(f"{BASE_URL}/tasks/", {
        "task_name": "Test Act Task",
        "project_id": p_id,
        "deadline": None,
        "status": "To Do"
    }, h1, "POST")
    assert t_status == 201 or t_status == 200
    t_id = t_res["id"]

    # Verify Task Creation Log
    activities, _ = make_request(f"{BASE_URL}/activities/?entity_type=task", None, h1, "GET")
    assert len(activities) == 1
    assert activities[0]["action_type"] == "create"
    assert activities[0]["entity_id"] == t_id
    assert "Task Created" in activities[0]["title"]

    # Update Task to Completed
    _, ut_status = make_request(f"{BASE_URL}/tasks/{t_id}", {
        "task_name": "Test Act Task",
        "project_id": p_id,
        "status": "Completed"
    }, h1, "PUT")
    assert ut_status == 200

    # Verify Task Completion Log
    activities, _ = make_request(f"{BASE_URL}/activities/?entity_type=task", None, h1, "GET")
    assert len(activities) == 2
    assert activities[0]["action_type"] == "complete"
    assert activities[0]["entity_id"] == t_id
    assert "Task Completed" in activities[0]["title"]
    print("  [OK] Task create & complete logged successfully.\n")

    # 7. Test Invoice CRUD Activity Logging
    print("[STEP 7] Testing Invoice CRUD activity logs...")
    inv_res, inv_status = make_request(f"{BASE_URL}/invoices/", {
        "client_id": c_id,
        "project_id": p_id,
        "title": "Test Act Invoice",
        "amount": 500.0,
        "status": "Draft",
        "issue_date": date.today().isoformat(),
        "due_date": (date.today() + timedelta(days=15)).isoformat()
    }, h1, "POST")
    assert inv_status == 201 or inv_status == 200, f"Invoice creation failed: {inv_res}"
    inv_id = inv_res["id"]

    # Verify Invoice Creation Log
    activities, _ = make_request(f"{BASE_URL}/activities/?entity_type=invoice", None, h1, "GET")
    assert len(activities) == 1
    assert activities[0]["action_type"] == "create"
    assert activities[0]["entity_id"] == inv_id
    assert "Invoice Created" in activities[0]["title"]

    # Mark Invoice as Paid
    _, uinv_status = make_request(f"{BASE_URL}/invoices/{inv_id}", {
        "client_id": c_id,
        "project_id": p_id,
        "title": "Test Act Invoice",
        "amount": 500.0,
        "status": "Paid",
        "issue_date": date.today().isoformat(),
        "due_date": (date.today() + timedelta(days=15)).isoformat()
    }, h1, "PUT")
    assert uinv_status == 200

    # Verify Invoice Paid Log
    activities, _ = make_request(f"{BASE_URL}/activities/?entity_type=invoice", None, h1, "GET")
    assert len(activities) == 2
    assert activities[0]["action_type"] == "paid"
    assert activities[0]["entity_id"] == inv_id
    assert "Invoice Paid" in activities[0]["title"]
    print("  [OK] Invoice create & paid logged successfully.\n")

    # 8. Test search and date filtering
    print("[STEP 8] Testing activities filtering & search...")
    # Search by keyword
    search_res, _ = make_request(f"{BASE_URL}/activities/?search=Updated", None, h1, "GET")
    assert len(search_res) >= 1
    assert any("Updated Act Client" in act["description"] for act in search_res)

    # Time filter test
    today_res, _ = make_request(f"{BASE_URL}/activities/?time_filter=today", None, h1, "GET")
    assert len(today_res) > 0

    week_res, _ = make_request(f"{BASE_URL}/activities/?time_filter=week", None, h1, "GET")
    assert len(week_res) >= len(today_res)
    print("  [OK] Filters and search queries validated.\n")

    # 9. Verify deletion logs
    print("[STEP 9] Testing deletion event logging...")
    # Delete invoice
    _, d_inv_status = make_request(f"{BASE_URL}/invoices/{inv_id}", None, h1, "DELETE")
    assert d_inv_status == 200
    
    # Delete task
    _, d_task_status = make_request(f"{BASE_URL}/tasks/{t_id}", None, h1, "DELETE")
    assert d_task_status == 200

    # Delete project
    _, d_proj_status = make_request(f"{BASE_URL}/projects/{p_id}", None, h1, "DELETE")
    assert d_proj_status == 200

    # Delete client
    _, d_client_status = make_request(f"{BASE_URL}/clients/{c_id}", None, h1, "DELETE")
    assert d_client_status == 200

    # Check that delete logs are generated
    activities, _ = make_request(f"{BASE_URL}/activities/", None, h1, "GET")
    # Verify that the newest activity is client deleted, followed by project deleted, task deleted, invoice deleted
    deleted_actions = [act for act in activities if act["action_type"] == "delete"]
    assert len(deleted_actions) == 4, f"Expected 4 deletion activities, got {len(deleted_actions)}: {deleted_actions}"
    assert deleted_actions[0]["entity_type"] == "client"
    assert deleted_actions[1]["entity_type"] == "project"
    assert deleted_actions[2]["entity_type"] == "task"
    assert deleted_actions[3]["entity_type"] == "invoice"
    print("  [OK] Deletion activity logging validated.\n")

    # 10. Verify workspace separation
    print("[STEP 10] Testing tenant activities isolation...")
    u2_activities, _ = make_request(f"{BASE_URL}/activities/", None, h2, "GET")
    # User 2 shouldn't see User 1's activities
    for act in u2_activities:
        assert act["user_id"] == reg2_res["id"], f"User 2 leaked User 1 activity: {act}"
        assert "Test Act" not in act["title"] and "Test Act" not in act["description"], f"User 2 leaked User 1 activity content: {act}"
    print("  [OK] Strict multi-tenant isolation validated.\n")

    print("=====================================================")
    print(" [SUCCESS] All Activity Module API tests passed!")
    print("=====================================================")

if __name__ == "__main__":
    test_activities_module()
