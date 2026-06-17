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

def test_notifications_module():
    print("=====================================================")
    print("   Starting CreateFlowX Notifications API Test")
    print("=====================================================\n")

    # 1. Setup mock users
    u1_email, u1_pass, u1_name = "creator_n1@test.com", "password123", "Creator Notif One"
    u2_email, u2_pass, u2_name = "creator_n2@test.com", "password123", "Creator Notif Two"

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

    # Cleanup previous notifications, tasks, projects, and clients for these users to ensure clean state
    print("[CLEANUP] Cleaning up existing data for test users...")
    for h in [h1, h2]:
        # Clean notifications
        notifs, _ = make_request(f"{BASE_URL}/notifications/", None, h, "GET")
        if isinstance(notifs, list):
            for notif in notifs:
                make_request(f"{BASE_URL}/notifications/{notif['id']}", None, h, "DELETE")
                
        # Clean tasks
        existing_tasks, _ = make_request(f"{BASE_URL}/tasks/", None, h, "GET")
        if isinstance(existing_tasks, list):
            for task in existing_tasks:
                make_request(f"{BASE_URL}/tasks/{task['id']}", None, h, "DELETE")
                
        # Clean projects
        existing_projects, _ = make_request(f"{BASE_URL}/projects/", None, h, "GET")
        if isinstance(existing_projects, list):
            for proj in existing_projects:
                make_request(f"{BASE_URL}/projects/{proj['id']}", None, h, "DELETE")
                
        # Clean clients
        existing_clients, _ = make_request(f"{BASE_URL}/clients/", None, h, "GET")
        if isinstance(existing_clients, list):
            for client in existing_clients:
                make_request(f"{BASE_URL}/clients/{client['id']}", None, h, "DELETE")
    print("  [OK] Cleanup complete.\n")

    # 2. Test Activity Logs generation
    print("[STEP 2] Testing activity log notifications creation...")
    
    # Registering client
    c1_res, c1_status = make_request(f"{BASE_URL}/clients/", {"client_name": "Notif Client"}, h1, "POST")
    assert c1_status == 201 or c1_status == 200
    c1_id = c1_res["id"]
    
    # Verify client_added activity is logged
    notifs, _ = make_request(f"{BASE_URL}/notifications/?notification_type=client_added", None, h1, "GET")
    assert len(notifs) == 1, "Expected 1 notification of type client_added"
    assert "Client Added" in notifs[0]["title"]
    assert "Notif Client" in notifs[0]["message"]
    print("  [OK] Client creation activity logged.")

    # Creating project
    p_res, p_status = make_request(f"{BASE_URL}/projects/", {
        "project_name": "Notif Project",
        "client_id": c1_id,
        "deadline": None,
        "status": "Not Started"
    }, h1, "POST")
    assert p_status == 201 or p_status == 200
    p_id = p_res["id"]
    
    # Verify project_created activity is logged
    notifs, _ = make_request(f"{BASE_URL}/notifications/?notification_type=project_created", None, h1, "GET")
    assert len(notifs) == 1, "Expected 1 notification of type project_created"
    assert "Project Created" in notifs[0]["title"]
    assert "Notif Project" in notifs[0]["message"]
    print("  [OK] Project creation activity logged.")

    # Creating task
    t_res, t_status = make_request(f"{BASE_URL}/tasks/", {
        "task_name": "Notif Task",
        "project_id": p_id,
        "deadline": None,
        "status": "To Do"
    }, h1, "POST")
    assert t_status == 201 or t_status == 200
    t_id = t_res["id"]
    
    # Verify task_created activity is logged
    notifs, _ = make_request(f"{BASE_URL}/notifications/?notification_type=task_created", None, h1, "GET")
    assert len(notifs) == 1, "Expected 1 notification of type task_created"
    assert "Task Created" in notifs[0]["title"]
    assert "Notif Task" in notifs[0]["message"]
    print("  [OK] Task creation activity logged.")

    # Update task to Completed
    _, status = make_request(f"{BASE_URL}/tasks/{t_id}", {
        "task_name": "Notif Task",
        "project_id": p_id,
        "status": "Completed"
    }, h1, "PUT")
    assert status == 200
    
    # Verify task_completed activity is logged
    notifs, _ = make_request(f"{BASE_URL}/notifications/?notification_type=task_completed", None, h1, "GET")
    assert len(notifs) == 1, "Expected 1 notification of type task_completed"
    assert "Task Completed" in notifs[0]["title"]
    print("  [OK] Task completion activity logged.")

    # Update project to Completed
    _, status = make_request(f"{BASE_URL}/projects/{p_id}", {
        "project_name": "Notif Project",
        "client_id": c1_id,
        "status": "Completed"
    }, h1, "PUT")
    assert status == 200
    
    # Verify project_completed activity is logged
    notifs, _ = make_request(f"{BASE_URL}/notifications/?notification_type=project_completed", None, h1, "GET")
    assert len(notifs) == 1, "Expected 1 notification of type project_completed"
    assert "Project Completed" in notifs[0]["title"]
    print("  [OK] Project completion activity logged.\n")

    # 3. Test Deadline alerts & Scanner Logic
    print("[STEP 3] Testing deadline alerts scanner generation...")
    today = date.today()
    
    # Create non-completed project with deadline 7 days out
    p7_res, _ = make_request(f"{BASE_URL}/projects/", {
        "project_name": "Proj Due 7 Days",
        "client_id": c1_id,
        "deadline": (today + timedelta(days=7)).isoformat(),
        "status": "In Progress"
    }, h1, "POST")
    p7_id = p7_res["id"]
    
    # Create non-completed task with deadline 3 days out
    t3_res, _ = make_request(f"{BASE_URL}/tasks/", {
        "task_name": "Task Due 3 Days",
        "project_id": p_id,
        "deadline": (today + timedelta(days=3)).isoformat(),
        "status": "In Progress"
    }, h1, "POST")
    t3_id = t3_res["id"]

    # Create non-completed task with overdue deadline (e.g. 1 day ago)
    to_res, _ = make_request(f"{BASE_URL}/tasks/", {
        "task_name": "Overdue Task",
        "project_id": p_id,
        "deadline": (today - timedelta(days=1)).isoformat(),
        "status": "In Progress"
    }, h1, "POST")
    to_id = to_res["id"]

    # Retrieve notifications (triggers scanner)
    all_notifs, _ = make_request(f"{BASE_URL}/notifications/", None, h1, "GET")
    
    # Inspect scan results
    upcoming_tasks = [n for n in all_notifs if n["notification_type"] == "upcoming_task"]
    overdue_tasks = [n for n in all_notifs if n["notification_type"] == "overdue_task"]
    upcoming_projects = [n for n in all_notifs if n["notification_type"] == "upcoming_project"]
    
    assert len(upcoming_tasks) >= 1, "Expected at least 1 upcoming task alert"
    assert any("Task Due 3 Days" in n["message"] for n in upcoming_tasks)
    
    assert len(overdue_tasks) >= 1, "Expected at least 1 overdue task alert"
    assert any("Overdue Task" in n["message"] for n in overdue_tasks)
    
    assert len(upcoming_projects) >= 1, "Expected at least 1 upcoming project alert"
    assert any("Proj Due 7 Days" in n["message"] for n in upcoming_projects)
    print("  [OK] Deadline scanner correctly generated upcoming and overdue alerts.\n")

    # 4. Test De-duplication Check
    print("[STEP 4] Testing scanner de-duplication...")
    pre_count = len(all_notifs)
    # Trigger scanner again by listing notifications
    post_notifs, _ = make_request(f"{BASE_URL}/notifications/", None, h1, "GET")
    post_count = len(post_notifs)
    assert pre_count == post_count, f"Scanner duplicate alerts check failed! Pre-count {pre_count} != Post-count {post_count}"
    print("  [OK] De-duplication confirmed: no duplicate alerts generated.\n")

    # 5. Test Workspace Isolation
    print("[STEP 5] Testing tenant workspace isolation...")
    u2_notifs, _ = make_request(f"{BASE_URL}/notifications/", None, h2, "GET")
    # User 2 shouldn't see User 1's notifications
    for notif in u2_notifs:
        assert notif["title"] not in ["Client Added", "Project Created", "Task Created"], f"User 2 leaked User 1 notification: {notif}"
    print("  [OK] Workspace isolation validated.\n")

    # 6. Test Stats API
    print("[STEP 6] Testing Stats API...")
    stats, _ = make_request(f"{BASE_URL}/notifications/stats", None, h1, "GET")
    assert stats["unread_count"] > 0
    assert stats["total_count"] == post_count
    print(f"  [OK] Stats: {stats['unread_count']} unread out of {stats['total_count']} total.")

    # 7. Test Read & Delete Actions
    print("[STEP 7] Testing Read and Delete actions...")
    # Find an unread notification
    target_notif = next(n for n in post_notifs if not n["is_read"])
    notif_id = target_notif["id"]
    
    # Mark target notification as read
    read_res, status = make_request(f"{BASE_URL}/notifications/{notif_id}/read", None, h1, "PUT")
    assert status == 200
    assert read_res["is_read"] is True
    
    # Verify unread stats decremented
    new_stats, _ = make_request(f"{BASE_URL}/notifications/stats", None, h1, "GET")
    assert new_stats["unread_count"] == stats["unread_count"] - 1
    print("  [OK] Marking single notification as read matches expected updates.")

    # Mark all read
    _, status = make_request(f"{BASE_URL}/notifications/read-all", None, h1, "PUT")
    assert status == 200
    final_stats, _ = make_request(f"{BASE_URL}/notifications/stats", None, h1, "GET")
    assert final_stats["unread_count"] == 0
    print("  [OK] Marking all as read clears unread counts.")

    # Delete notification
    _, status = make_request(f"{BASE_URL}/notifications/{notif_id}", None, h1, "DELETE")
    assert status == 200
    
    # Verify deleted notification is gone
    final_notifs, _ = make_request(f"{BASE_URL}/notifications/", None, h1, "GET")
    assert not any(n["id"] == notif_id for n in final_notifs)
    print("  [OK] Deleting notification removes it from list.")

    print("\n=====================================================")
    print(" [SUCCESS] All Notification Module API tests passed!")
    print("=====================================================")

if __name__ == "__main__":
    test_notifications_module()
