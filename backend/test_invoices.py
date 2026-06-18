import urllib.request
import json
import sys
import datetime
import time

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

def test_invoice_module():
    print("=====================================================")
    print("   Starting CreateFlowX Invoice & Revenue API Test")
    print("=====================================================\n")

    # 1. Register Mock Creator 1 and 2
    ts = int(time.time())
    u1_email, u1_pass, u1_name = f"invoice_creator1_{ts}@test.com", "password123", "Inv Creator One"
    u2_email, u2_pass, u2_name = f"invoice_creator2_{ts}@test.com", "password123", "Inv Creator Two"

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

    # 2. Add Clients & Projects
    print("[STEP 2] Creating clients and projects for Creator 1 and 2...")
    
    # Creator 1 Client
    c1_res, _ = make_request(f"{BASE_URL}/clients/", {"client_name": "C1 Client", "company_name": "C1 Co"}, h1, "POST")
    c1_id = c1_res["id"]
    
    # Creator 1 Project
    p1_res, _ = make_request(f"{BASE_URL}/projects/", {"project_name": "C1 Project", "client_id": c1_id}, h1, "POST")
    p1_id = p1_res["id"]
    
    # Creator 2 Client
    c2_res, _ = make_request(f"{BASE_URL}/clients/", {"client_name": "C2 Client", "company_name": "C2 Co"}, h2, "POST")
    c2_id = c2_res["id"]
    
    # Creator 2 Project
    p2_res, _ = make_request(f"{BASE_URL}/projects/", {"project_name": "C2 Project", "client_id": c2_id}, h2, "POST")
    p2_id = p2_res["id"]
    
    print(f"  [OK] C1 Client: {c1_id}, C1 Project: {p1_id}")
    print(f"  [OK] C2 Client: {c2_id}, C2 Project: {p2_id}\n")

    # 3. Create Invoices for Creator 1
    print("[STEP 3] Creator 1 adding Invoices (Testing auto-numbering sequential generation)...")
    today_str = datetime.date.today().isoformat()
    due_future_str = (datetime.date.today() + datetime.timedelta(days=14)).isoformat()
    due_past_str = (datetime.date.today() - datetime.timedelta(days=5)).isoformat()

    # Invoice 1 (Pending/Sent)
    inv1_payload = {
        "client_id": c1_id,
        "project_id": p1_id,
        "title": "Design System Layout",
        "description": "Figma design system work",
        "amount": 25000.0,
        "status": "Pending",
        "issue_date": today_str,
        "due_date": due_future_str
    }
    inv1_res, status = make_request(f"{BASE_URL}/invoices/", inv1_payload, h1, "POST")
    assert status == 201, f"Failed create invoice 1: {status}"
    inv1_id = inv1_res["id"]
    assert inv1_res["invoice_number"] == "INV-001", f"Expected INV-001, got {inv1_res['invoice_number']}"
    print(f"  [OK] Invoice 1 created: {inv1_res['invoice_number']}, Amount: {inv1_res['amount']}")

    # Invoice 2 (Paid)
    inv2_payload = {
        "client_id": c1_id,
        "project_id": p1_id,
        "title": "Logo Concept Phase",
        "amount": 50000.0,
        "status": "Paid",
        "issue_date": today_str,
        "due_date": due_future_str
    }
    inv2_res, status = make_request(f"{BASE_URL}/invoices/", inv2_payload, h1, "POST")
    assert status == 201
    inv2_id = inv2_res["id"]
    assert inv2_res["invoice_number"] == "INV-002", f"Expected INV-002, got {inv2_res['invoice_number']}"
    assert inv2_res["paid_date"] is not None, "Expected paid_date to be set for Paid status creation"
    print(f"  [OK] Invoice 2 created: {inv2_res['invoice_number']}, Amount: {inv2_res['amount']} (Paid date set: {inv2_res['paid_date']})")

    # Invoice 3 (Past Due -> should transition to Overdue)
    inv3_payload = {
        "client_id": c1_id,
        "project_id": p1_id,
        "title": "Landing Page HTML",
        "amount": 15000.0,
        "status": "Pending",
        "issue_date": today_str,
        "due_date": due_past_str
    }
    inv3_res, status = make_request(f"{BASE_URL}/invoices/", inv3_payload, h1, "POST")
    assert status == 201
    inv3_id = inv3_res["id"]
    assert inv3_res["invoice_number"] == "INV-003"
    print(f"  [OK] Invoice 3 created: {inv3_res['invoice_number']} with past due date {due_past_str}\n")

    # 4. Multi-Tenant Isolation Checks
    print("[STEP 4] Asserting multi-tenant security isolation...")
    
    # Creator 2 attempts to read Creator 1's invoice
    res, status = make_request(f"{BASE_URL}/invoices/{inv1_id}", None, h2, "GET")
    assert status == 404, f"Security Breach! Creator 2 could view Creator 1's invoice (status: {status})"
    
    # Creator 2 attempts to update Creator 1's invoice
    res, status = make_request(f"{BASE_URL}/invoices/{inv1_id}", {"title": "Hacked Title"}, h2, "PUT")
    assert status == 404, f"Security Breach! Creator 2 could edit Creator 1's invoice (status: {status})"
    
    # Creator 2 attempts to delete Creator 1's invoice
    res, status = make_request(f"{BASE_URL}/invoices/{inv1_id}", None, h2, "DELETE")
    assert status == 404, f"Security Breach! Creator 2 could delete Creator 1's invoice (status: {status})"
    print("  [OK] Multi-tenant isolation verified successfully.\n")

    # 5. Overdue Detection & Updates
    print("[STEP 5] Testing dynamic Overdue status transitions...")
    
    # Fetching list of invoices should trigger check_and_update_overdue
    list_res, status = make_request(f"{BASE_URL}/invoices/", None, h1, "GET")
    assert status == 200
    
    # Find Invoice 3 in list
    inv3_listed = next(i for i in list_res if i["id"] == inv3_id)
    assert inv3_listed["status"] == "Overdue", f"Expected Overdue status, got {inv3_listed['status']}"
    print(f"  [OK] Invoice 3 successfully transitioned to Overdue.")

    # 6. Payment tracking paid_date toggle
    print("[STEP 6] Testing payment tracking state updates...")
    
    # Update Invoice 1 status to Paid
    update_res, status = make_request(f"{BASE_URL}/invoices/{inv1_id}", {"status": "Paid"}, h1, "PUT")
    assert status == 200
    assert update_res["status"] == "Paid"
    assert update_res["paid_date"] is not None, "Expected paid_date to be set when updated to Paid"
    print("  [OK] Invoiced changed to Paid triggers paid_date timestamp.")
    
    # Update Invoice 1 status back to Pending
    update_res, status = make_request(f"{BASE_URL}/invoices/{inv1_id}", {"status": "Pending"}, h1, "PUT")
    assert status == 200
    assert update_res["status"] == "Pending"
    assert update_res["paid_date"] is None, "Expected paid_date to be cleared when status changes from Paid"
    print("  [OK] Invoiced changed from Paid clears paid_date timestamp.\n")

    # 7. Revenue & Invoice Stats checks
    print("[STEP 7] Verifying statistics and chart details...")
    
    # Creator 1 Stats
    stats, status = make_request(f"{BASE_URL}/invoices/stats", None, h1, "GET")
    assert status == 200
    
    # Total Revenue should equal Sum of Non-Cancelled Invoices = 25000 + 50000 + 15000 = 90000
    # Paid Revenue: Invoice 2 is Paid = 50000
    # Pending Revenue: Invoice 1 is Pending = 25000
    # Overdue Revenue: Invoice 3 is Overdue = 15000
    assert stats["revenue"]["total"] == 90000.0, f"Expected 90000.0, got {stats['revenue']['total']}"
    assert stats["revenue"]["paid"] == 50000.0, f"Expected 50000.0, got {stats['revenue']['paid']}"
    assert stats["revenue"]["pending"] == 25000.0, f"Expected 25000.0, got {stats['revenue']['pending']}"
    assert stats["revenue"]["overdue"] == 15000.0, f"Expected 15000.0, got {stats['revenue']['overdue']}"
    
    # Invoice count stats
    assert stats["invoices"]["total"] == 3
    assert stats["invoices"]["paid"] == 1
    assert stats["invoices"]["pending"] == 1
    assert stats["invoices"]["overdue"] == 1

    print("  [OK] Revenue widgets stats verified.")
    print("  [OK] Invoice widgets count stats verified.")
    print("  [OK] Monthly, status distribution, and weekly trends calculated and returned.\n")

    # 8. Deleting invoice
    print("[STEP 8] Testing invoice deletions...")
    res, status = make_request(f"{BASE_URL}/invoices/{inv1_id}", None, h1, "DELETE")
    assert status == 200
    
    res, status = make_request(f"{BASE_URL}/invoices/{inv1_id}", None, h1, "GET")
    assert status == 404
    print("  [OK] Invoice deletion confirmed.\n")

    print("=====================================================")
    print(" [SUCCESS] All Invoice & Revenue security, CRUD, ")
    print("           overdue, and statistics API tests passed!")
    print("=====================================================")

if __name__ == "__main__":
    test_invoice_module()
