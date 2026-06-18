import urllib.request
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1"

def make_request(url, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    encoded_data = None
    if data is not None:
        encoded_data = json.dumps(data).encode("utf-8")
        
    req = urllib.request.Request(
        url,
        data=encoded_data,
        headers=headers,
        method=method
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode())
        except Exception:
            body = {"detail": "Failed to decode error body"}
        return e.code, body

def test_admin_flow():
    admin_email = "admin@createflowx.com"
    admin_password = "AdminPassword123!"
    
    user_email = "user_for_admin_test@example.com"
    user_password = "userPassword123!"
    user_name = "Regular User Tester"
    
    print("--------------------------------------------------")
    print("  Starting CreateFlowX Admin Panel Integration Test")
    print("--------------------------------------------------")
    
    # 1. Login Admin
    print("\n[STEP 1] Logging in as platform administrator...")
    status, res = make_request(f"{BASE_URL}/auth/login", method="POST", data={
        "email": admin_email,
        "password": admin_password
    })
    if status == 200:
        admin_token = res["access_token"]
        print(f"  [OK] Admin login successful. Token acquired.")
    else:
        print(f"  [FAIL] Admin login failed (status {status}): {res}")
        sys.exit(1)

    # 2. Register Regular User
    print("\n[STEP 2] Registering regular tester user...")
    status, res = make_request(f"{BASE_URL}/auth/register", method="POST", data={
        "email": user_email,
        "password": user_password,
        "full_name": user_name
    })
    if status in (200, 201):
        print(f"  [OK] Regular user registered successfully: {res['email']}")
    elif status == 400 and "already registered" in res.get("detail", ""):
        print("  [INFO] Regular user already registered.")
    else:
        print(f"  [FAIL] Registration failed (status {status}): {res}")
        sys.exit(1)

    # 3. Login Regular User
    print("\n[STEP 3] Logging in as regular user...")
    status, res = make_request(f"{BASE_URL}/auth/login", method="POST", data={
        "email": user_email,
        "password": user_password
    })
    if status == 200:
        user_token = res["access_token"]
        user_id = res["user"]["id"]
        print(f"  [OK] User login successful. Token acquired. User ID: {user_id}")
    else:
        print(f"  [FAIL] User login failed (status {status}): {res}")
        sys.exit(1)

    # 4. Access Control Check: User tries to access Admin Dashboard
    print("\n[STEP 4] Verifying access control: User queries admin API...")
    status, res = make_request(f"{BASE_URL}/admin/dashboard", method="GET", token=user_token)
    if status == 403:
        print(f"  [OK] Access correctly denied: {res.get('detail')}")
    else:
        print(f"  [FAIL] Access control bypassed! Expected 403, but got status {status}: {res}")
        sys.exit(1)

    # 5. Admin queries Admin Dashboard
    print("\n[STEP 5] Admin querying platform dashboard stats...")
    status, dashboard = make_request(f"{BASE_URL}/admin/dashboard", method="GET", token=admin_token)
    if status == 200:
        stats = dashboard.get("stats", {})
        print(f"  [OK] Dashboard statistics retrieved: total_users={stats.get('total_users')}, total_revenue={stats.get('total_revenue')}")
    else:
        print(f"  [FAIL] Admin dashboard stats fetch failed (status {status}): {dashboard}")
        sys.exit(1)

    # 6. Admin modifies Platform settings (Disable Registration)
    print("\n[STEP 6] Admin disabling open registrations...")
    status, settings = make_request(f"{BASE_URL}/admin/settings", method="PUT", token=admin_token, data={
        "platform_name": "CreateFlowX Admin Mode",
        "registration_open": False,
        "maintenance_mode": False,
        "announcement_banner": "Platform settings updated."
    })
    if status == 200:
        print(f"  [OK] Settings saved: platform_name='{settings.get('platform_name')}', registration_open={settings.get('registration_open')}")
        assert settings.get("registration_open") is False
    else:
        print(f"  [FAIL] Settings update failed: {settings}")
        sys.exit(1)

    # 7. Check Registration Blocked
    print("\n[STEP 7] Verifying new registrations are blocked...")
    status, res = make_request(f"{BASE_URL}/auth/register", method="POST", data={
        "email": "another_tester@example.com",
        "password": "somePassword123!",
        "full_name": "Blocked Registrant"
    })
    if status == 400 and "closed" in res.get("detail", "").lower():
        print(f"  [OK] Registration correctly blocked: {res.get('detail')}")
    else:
        print(f"  [FAIL] Expected registration closure error, but got status {status}: {res}")
        sys.exit(1)

    # 8. Re-enable registrations
    print("\n[STEP 8] Admin re-enabling registrations...")
    status, settings = make_request(f"{BASE_URL}/admin/settings", method="PUT", token=admin_token, data={
        "platform_name": "CreateFlowX",
        "registration_open": True,
        "maintenance_mode": False,
        "announcement_banner": "Registrations open."
    })
    if status == 200:
        print("  [OK] Registration re-opened.")
    else:
        print(f"  [FAIL] Re-opening failed: {settings}")
        sys.exit(1)

    # 9. Admin enables Maintenance Mode
    print("\n[STEP 9] Admin enabling Maintenance Mode...")
    status, settings = make_request(f"{BASE_URL}/admin/settings", method="PUT", token=admin_token, data={
        "platform_name": "CreateFlowX",
        "registration_open": True,
        "maintenance_mode": True,
        "announcement_banner": "Platform undergoing maintenance."
    })
    if status == 200:
        print("  [OK] Maintenance mode activated.")
    else:
        print(f"  [FAIL] Enabling maintenance mode failed: {settings}")
        sys.exit(1)

    # 10. Check Regular User Access blocked during maintenance
    print("\n[STEP 10] Checking regular user access blocked during maintenance...")
    status, res = make_request(f"{BASE_URL}/auth/login", method="POST", data={
        "email": user_email,
        "password": user_password
    })
    if status == 503:
        print(f"  [OK] Login blocked with 503: {res.get('detail')}")
    else:
        print(f"  [FAIL] Expected login block with 503, but got status {status}: {res}")
        sys.exit(1)

    # 11. Disable Maintenance Mode
    print("\n[STEP 11] Admin disabling Maintenance Mode...")
    status, settings = make_request(f"{BASE_URL}/admin/settings", method="PUT", token=admin_token, data={
        "platform_name": "CreateFlowX",
        "registration_open": True,
        "maintenance_mode": False,
        "announcement_banner": ""
    })
    if status == 200:
        print("  [OK] Maintenance mode deactivated.")
    else:
        print(f"  [FAIL] Disabling maintenance mode failed: {settings}")
        sys.exit(1)

    # 12. Admin suspends User
    print("\n[STEP 12] Admin suspending regular user profile...")
    status, msg = make_request(f"{BASE_URL}/admin/users/{user_id}/status", method="PUT", token=admin_token, data={
        "status": "suspended"
    })
    if status == 200:
        print(f"  [OK] User suspended: {msg.get('message')}")
    else:
        print(f"  [FAIL] Suspension failed: {msg}")
        sys.exit(1)

    # 13. Verify Suspended User login is blocked
    print("\n[STEP 13] Verifying suspended user login is denied...")
    status, res = make_request(f"{BASE_URL}/auth/login", method="POST", data={
        "email": user_email,
        "password": user_password
    })
    if status == 403:
        print(f"  [OK] Login correctly denied with 403: {res.get('detail')}")
    else:
        print(f"  [FAIL] Expected login block with 403, but got status {status}: {res}")
        sys.exit(1)

    # 14. Admin reactivates User
    print("\n[STEP 14] Admin reactivating regular user profile...")
    status, msg = make_request(f"{BASE_URL}/admin/users/{user_id}/status", method="PUT", token=admin_token, data={
        "status": "active"
    })
    if status == 200:
        print(f"  [OK] User reactivated: {msg.get('message')}")
    else:
        print(f"  [FAIL] Reactivation failed: {msg}")
        sys.exit(1)

    # 15. Verify Reactivated User login works again
    print("\n[STEP 15] Verifying reactivated user login works again...")
    status, res = make_request(f"{BASE_URL}/auth/login", method="POST", data={
        "email": user_email,
        "password": user_password
    })
    if status == 200:
        print("  [OK] Login successful after reactivation.")
    else:
        print(f"  [FAIL] Login failed after reactivation: {res}")
        sys.exit(1)

    # 16. Admin reads activity logs
    print("\n[STEP 16] Admin reading platform activity logs...")
    status, logs = make_request(f"{BASE_URL}/admin/activity-logs", method="GET", token=admin_token)
    if status == 200:
        print(f"  [OK] Activity logs retrieved. Total events: {len(logs)}")
        if len(logs) > 0:
            print(f"      Latest event: '{logs[0]['title']}' by {logs[0]['user_full_name']}")
    else:
        print(f"  [FAIL] Failed to retrieve activity logs: {logs}")
        sys.exit(1)

    print("\n==================================================")
    print(" [SUCCESS] All admin role & settings tests passed!")
    print("==================================================")

if __name__ == "__main__":
    test_admin_flow()
