import urllib.request
import json
import sys

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

def test_client_module():
    print("=====================================================")
    print("   Starting CreateFlowX Client Management API Test")
    print("=====================================================\n")

    # 1. Register Mock Creator 1 and 2
    u1_email, u1_pass, u1_name = "creator1@test.com", "password123", "Creator One"
    u2_email, u2_pass, u2_name = "creator2@test.com", "password123", "Creator Two"

    print("[STEP 1] Setting up mock test users...")
    make_request(f"{BASE_URL}/auth/register", {"email": u1_email, "password": u1_pass, "full_name": u1_name})
    make_request(f"{BASE_URL}/auth/register", {"email": u2_email, "password": u2_pass, "full_name": u2_name})

    # Log in both to fetch JWT tokens
    u1_res, _ = make_request(f"{BASE_URL}/auth/login", {"email": u1_email, "password": u1_pass})
    u2_res, _ = make_request(f"{BASE_URL}/auth/login", {"email": u2_email, "password": u2_pass})
    
    t1 = u1_res["access_token"]
    t2 = u2_res["access_token"]
    
    h1 = {"Authorization": f"Bearer {t1}"}
    h2 = {"Authorization": f"Bearer {t2}"}
    print("  [OK] Mock users configured and JWT tokens issued.\n")

    # 2. Creator 1 Creates Client 1
    print("[STEP 2] Creator 1 adding Client...")
    c1_payload = {
        "client_name": "Global Corp LLC",
        "company_name": "Global Corp",
        "notes": "Premium enterprise billing notes."
    }
    c1_res, status = make_request(f"{BASE_URL}/clients/", c1_payload, h1, "POST")
    assert status == 201, f"Failed client create: {status}"
    c1_id = c1_res["id"]
    print(f"  [OK] Client created successfully. ID: {c1_id}, Name: {c1_res['client_name']}\n")

    # 3. Creator 2 Creates Client 2
    print("[STEP 3] Creator 2 adding Client...")
    c2_payload = {
        "client_name": "Indie Game Studio",
        "company_name": "Indie Games",
        "notes": "Direct billing in USD."
    }
    c2_res, status = make_request(f"{BASE_URL}/clients/", c2_payload, h2, "POST")
    assert status == 201
    c2_id = c2_res["id"]
    print(f"  [OK] Client created successfully. ID: {c2_id}, Name: {c2_res['client_name']}\n")

    # 4. Multi-Tenant Data Isolation Checks (CRITICAL)
    print("[STEP 4] Testing Multi-Tenant Data Isolation guards...")
    
    # Creator 1 attempts to fetch Creator 2's Client (Indie Game Studio)
    print("  a. Asserting Creator 1 cannot view Creator 2's client...")
    res, status = make_request(f"{BASE_URL}/clients/{c2_id}", None, h1, "GET")
    assert status == 404, f"Security Breach! Creator 1 could read Creator 2's client (status: {status})"
    print("     [OK] Success: Access Denied (Returned 404).")

    # Creator 2 attempts to fetch Creator 1's Client (Global Corp)
    print("  b. Asserting Creator 2 cannot view Creator 1's client...")
    res, status = make_request(f"{BASE_URL}/clients/{c1_id}", None, h2, "GET")
    assert status == 404, f"Security Breach! Creator 2 could read Creator 1's client (status: {status})"
    print("     [OK] Success: Access Denied (Returned 404).")

    # Creator 2 attempts to update Creator 1's Client (Global Corp)
    print("  c. Asserting Creator 2 cannot update Creator 1's client...")
    res, status = make_request(f"{BASE_URL}/clients/{c1_id}", {"client_name": "Hacked Name"}, h2, "PUT")
    assert status == 404, f"Security Breach! Creator 2 could update Creator 1's client (status: {status})"
    print("     [OK] Success: Access Denied (Returned 404).")

    # Creator 2 attempts to delete Creator 1's Client (Global Corp)
    print("  d. Asserting Creator 2 cannot delete Creator 1's client...")
    res, status = make_request(f"{BASE_URL}/clients/{c1_id}", None, h2, "DELETE")
    assert status == 404, f"Security Breach! Creator 2 could delete Creator 1's client (status: {status})"
    print("     [OK] Success: Access Denied (Returned 404).\n")

    # 5. Testing Searches and Lists
    print("[STEP 5] Testing Lists and Case-Insensitive Client Searches...")
    
    # Creator 1 lists all their clients
    list_res, status = make_request(f"{BASE_URL}/clients/", None, h1, "GET")
    assert status == 200
    # Must only return Creator 1's clients, NOT Creator 2's
    assert len(list_res) == 1, f"Expected 1 client, got {len(list_res)}"
    assert list_res[0]["client_name"] == "Global Corp LLC"
    print("  [OK] List returns user-owned clients only.")

    # Search check
    search_res, status = make_request(f"{BASE_URL}/clients/?search=global", None, h1, "GET")
    assert status == 200
    assert len(search_res) == 1, "Expected search hit for 'global'"
    
    search_res, status = make_request(f"{BASE_URL}/clients/?search=indie", None, h1, "GET")
    assert status == 200
    assert len(search_res) == 0, "Expected search miss for 'indie' on Creator 1's workspace"
    print("  [OK] Case-insensitive searches verified.\n")

    # 6. Test updates and deletions
    print("[STEP 6] Testing Client updates and deletions...")
    
    # Update
    update_res, status = make_request(f"{BASE_URL}/clients/{c1_id}", {"client_name": "Global Corp Incorporated"}, h1, "PUT")
    assert status == 200
    assert update_res["client_name"] == "Global Corp Incorporated"
    print("  [OK] Client updated successfully.")

    # Delete
    delete_res, status = make_request(f"{BASE_URL}/clients/{c1_id}", None, h1, "DELETE")
    assert status == 200
    
    # Verify no longer accessible by anyone
    res, status = make_request(f"{BASE_URL}/clients/{c1_id}", None, h1, "GET")
    assert status == 404
    print("  [OK] Client deleted and verified clean.\n")

    print("=====================================================")
    print(" [SUCCESS] All Client Management security & CRUD tests passed!")
    print("=====================================================")

if __name__ == "__main__":
    test_client_module()
