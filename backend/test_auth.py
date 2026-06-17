import urllib.request
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_auth():
    email = "developer@example.com"
    password = "developerPassword123!"
    name = "Developer Test"
    
    print("---------------------------------------------")
    print("  Starting CreateFlowX API Authentication Test")
    print("---------------------------------------------")
    
    # 1. Register User
    print("\n[STEP 1] Testing /auth/register...")
    reg_data = json.dumps({
        "email": email,
        "password": password,
        "full_name": name
    }).encode("utf-8")
    
    req = urllib.request.Request(
        f"{BASE_URL}/auth/register",
        data=reg_data,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            print("  [OK] Success! User Registered:")
            print(f"      ID: {res['id']}, Email: {res['email']}, Name: {res['full_name']}")
    except urllib.error.HTTPError as e:
        error_info = e.read().decode()
        if "already registered" in error_info:
            print("  [INFO] Info: User already registered, proceeding to check login...")
        else:
            print("  [FAIL] Fail! Registration Error:", error_info)
            sys.exit(1)
        
    # 2. Login User
    print("\n[STEP 2] Testing /auth/login...")
    login_data = json.dumps({
        "email": email,
        "password": password
    }).encode("utf-8")
    
    req = urllib.request.Request(
        f"{BASE_URL}/auth/login",
        data=login_data,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            print("  [OK] Success! Token Acquired:")
            print(f"      Token: {res['access_token'][:30]}... [Truncated]")
            token = res["access_token"]
    except urllib.error.HTTPError as e:
        print("  [FAIL] Fail! Login Error:", e.read().decode())
        sys.exit(1)
        
    # 3. Read Profile
    print("\n[STEP 3] Testing /auth/me (Bearer Token Validation)...")
    req = urllib.request.Request(
        f"{BASE_URL}/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            print("  [OK] Success! Profile Retrieved:")
            print(f"      Authenticated User Email: {res['email']}, Role: {res['role']}")
    except urllib.error.HTTPError as e:
        print("  [FAIL] Fail! Auth Guard Error:", e.read().decode())
        sys.exit(1)

    print("\n=============================================")
    print(" [SUCCESS] All API Authentication checks passed!")
    print("=============================================")

if __name__ == "__main__":
    test_auth()
