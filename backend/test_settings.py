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
        return e.code, json.loads(e.read().decode())

def test_settings_flow():
    email = "settings_tester@example.com"
    password = "testerPassword123!"
    new_password = "newTesterPassword123!"
    name = "Settings Tester"
    
    print("---------------------------------------------")
    print("  Starting CreateFlowX Settings & Security Test")
    print("---------------------------------------------")
    
    # 1. Register User
    print("\n[STEP 1] Testing /auth/register...")
    status, res = make_request(f"{BASE_URL}/auth/register", method="POST", data={
        "email": email,
        "password": password,
        "full_name": name
    })
    if status in (200, 201):
        print(f"  [OK] User registered successfully: {res['email']}")
    elif status == 400 and "already registered" in res.get("detail", ""):
        print("  [INFO] User already registered, proceeding to login...")
    else:
        print(f"  [FAIL] Registration failed (status {status}): {res}")
        sys.exit(1)
        
    # 2. Login User (Original Password)
    print("\n[STEP 2] Testing /auth/login...")
    status, res = make_request(f"{BASE_URL}/auth/login", method="POST", data={
        "email": email,
        "password": password
    })
    if status == 200:
        token = res["access_token"]
        print(f"  [OK] Login successful. Token obtained.")
    else:
        print(f"  [FAIL] Login failed: {res}")
        sys.exit(1)
        
    # 3. Read profile & default settings
    print("\n[STEP 3] Reading default settings...")
    status, settings = make_request(f"{BASE_URL}/settings/", method="GET", token=token)
    if status == 200:
        print(f"  [OK] Default settings retrieved: theme={settings.get('theme')}, currency={settings.get('currency')}, format={settings.get('date_format')}")
    else:
        print(f"  [FAIL] Failed to retrieve settings: {settings}")
        sys.exit(1)
        
    # 4. Update Profile
    print("\n[STEP 4] Updating profile details (Full Name and Username)...")
    status, profile = make_request(f"{BASE_URL}/users/me", method="PUT", token=token, data={
        "full_name": "Settings Tester Updated",
        "username": "tester_settings_user"
    })
    if status == 200:
        print(f"  [OK] Profile updated: name={profile.get('full_name')}, username={profile.get('username')}")
    else:
        print(f"  [FAIL] Profile update failed: {profile}")
        sys.exit(1)
        
    # 5. Try updating profile with validation failure (empty full_name)
    print("\n[STEP 5] Testing profile validation constraints...")
    status, err = make_request(f"{BASE_URL}/users/me", method="PUT", token=token, data={
        "full_name": "",
        "username": "tester_settings_user"
    })
    if status == 400:
        print(f"  [OK] Invalid name correctly rejected: {err.get('detail')}")
    else:
        print(f"  [FAIL] Expected validation failure, but got status {status}: {err}")
        sys.exit(1)

    # 6. Update Settings Preferences
    print("\n[STEP 6] Updating workspace settings preferences...")
    status, settings = make_request(f"{BASE_URL}/settings/", method="PUT", token=token, data={
        "theme": "dark",
        "currency": "EUR",
        "date_format": "YYYY-MM-DD"
    })
    if status == 200:
        print(f"  [OK] Settings updated: theme={settings.get('theme')}, currency={settings.get('currency')}, format={settings.get('date_format')}")
        assert settings.get("theme") == "dark"
        assert settings.get("currency") == "EUR"
        assert settings.get("date_format") == "YYYY-MM-DD"
    else:
        print(f"  [FAIL] Settings update failed: {settings}")
        sys.exit(1)

    # 7. Update Password (Validation Failure - mismatched confirmation)
    print("\n[STEP 7] Testing password validation: mismatched confirmation...")
    status, err = make_request(f"{BASE_URL}/users/me/password", method="PUT", token=token, data={
        "current_password": password,
        "new_password": new_password,
        "confirm_password": "differentPassword123!"
    })
    if status == 400:
        print(f"  [OK] Password mismatch correctly rejected: {err.get('detail')}")
    else:
        print(f"  [FAIL] Expected validation failure, but got status {status}: {err}")
        sys.exit(1)

    # 8. Update Password (Success)
    print("\n[STEP 8] Updating account password...")
    status, msg = make_request(f"{BASE_URL}/users/me/password", method="PUT", token=token, data={
        "current_password": password,
        "new_password": new_password,
        "confirm_password": new_password
    })
    if status == 200:
        print(f"  [OK] Password updated: {msg.get('message')}")
    else:
        print(f"  [FAIL] Password update failed: {msg}")
        sys.exit(1)

    # 9. Verify authentication with new password works
    print("\n[STEP 9] Verifying login with the new password...")
    status, res = make_request(f"{BASE_URL}/auth/login", method="POST", data={
        "email": email,
        "password": new_password
    })
    if status == 200:
        token = res["access_token"]
        print("  [OK] Login successful with new password.")
    else:
        print(f"  [FAIL] Login failed with new password: {res}")
        sys.exit(1)

    # 10. Soft-delete user account (Danger Zone)
    print("\n[STEP 10] Deleting account (Soft-Delete/Danger Zone)...")
    status, msg = make_request(f"{BASE_URL}/users/me", method="DELETE", token=token)
    if status == 200:
        print(f"  [OK] Account soft-delete request succeeded: {msg.get('message')}")
    else:
        print(f"  [FAIL] Soft-delete request failed: {msg}")
        sys.exit(1)

    # 11. Verify login is deactivated for the deleted user
    print("\n[STEP 11] Verifying login is deactivated for soft-deleted profile...")
    status, res = make_request(f"{BASE_URL}/auth/login", method="POST", data={
        "email": email,
        "password": new_password
    })
    if status == 400:
        print(f"  [OK] Login correctly denied: {res.get('detail')}")
    else:
        print(f"  [FAIL] Expected login failure for deactivated account, but got status {status}: {res}")
        sys.exit(1)

    print("\n=============================================")
    print(" [SUCCESS] All settings & security flow tests passed!")
    print("=============================================")

if __name__ == "__main__":
    test_settings_flow()
