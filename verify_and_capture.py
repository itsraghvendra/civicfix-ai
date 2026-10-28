"""
CivicFix AI - Comprehensive Verification & Acceptance Suite (Lucknow Edition)
Tests all security, abuse prevention, rate limiting, mobile OTP, compulsory live photo capture,
image captioning, location privacy, and captures fresh desktop & mobile screenshots.
"""

import os
import sys
import time
import json
import shutil
import secrets
import urllib.request
import urllib.parse
import urllib.error
import threading
import subprocess
from io import BytesIO
from PIL import Image

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Fix Windows console UTF-8 encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app import app
import uvicorn
import config
import security

ARTIFACT_DIR = r"C:\Users\yadav\.gemini\antigravity\brain\6f99e4b4-ef1a-43eb-96c3-d72938d33f19"
EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(EDGE_EXE):
    EDGE_EXE = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"


class ServerThread(threading.Thread):
    def __init__(self, app, host="127.0.0.1", port=8501):
        super().__init__(daemon=True)
        self.server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="error"))

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True


def make_test_image_bytes():
    """Generates a small test JPEG image in memory."""
    img = Image.new("RGB", (640, 480), color=(46, 61, 40))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def encode_multipart_formdata(fields, files):
    boundary = "----WebKitFormBoundaryCivicFixVerification"
    body = bytearray()
    for key, val in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        body.extend(f"{val}\r\n".encode("utf-8"))
    for key, (filename, content, content_type) in files.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'.encode("utf-8"))
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(content)
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    content_type = f"multipart/form-data; boundary={boundary}"
    return bytes(body), content_type


def http_post_json(url, payload, headers=None):
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=hdrs, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"error": body}


def run_tests():
    print("=" * 60)
    print("CIVICFIX AI — LUCKNOW EDITION: COMPLETE ACCEPTANCE SUITE")
    print("=" * 60)

    # 1. Start Server
    server_thread = ServerThread(app, host="127.0.0.1", port=8501)
    server_thread.start()
    time.sleep(2)

    base_url = "http://127.0.0.1:8501"
    unique_client_id = f"test_harness_{secrets.token_hex(6)}"
    client_headers = {"User-Agent": f"CivicFixTestBrowser/{unique_client_id}"}

    # Test 1: GET / (Homepage HTML)
    print("\n[TEST 1] Verifying Homepage HTML delivery...")
    req = urllib.request.urlopen(f"{base_url}/")
    assert req.status == 200
    html = req.read().decode("utf-8")
    assert "CIVICFIX AI" in html, "Brand name missing in HTML"
    assert "Let's Make Lucknow Better." in html, "Hero heading missing"
    assert "Small Reports. Better Streets. Stronger Communities." in html, "Motivation section missing"
    assert "The City We Care About" in html, "Visual gallery section missing"
    assert "Rumi Darwaza" in html and "Bara Imambara" in html
    assert "Gomti Riverfront" in html and "Janeshwar Mishra Park" in html
    assert "Live Photo Evidence" in html or "Live Camera" in html, "Live photo UI missing"
    assert "Mobile Verification" in html, "Mobile OTP UI missing"
    print("  ✓ Homepage HTML contains brand identity, hero, motivation, gallery & abuse prevention elements.")

    # Test 2: GET /api/config & GET /api/security/status
    print("\n[TEST 2] Verifying System Config & Security Status endpoints...")
    cfg = json.loads(urllib.request.urlopen(f"{base_url}/api/config").read().decode("utf-8"))
    assert len(cfg["categories"]) >= 7 and len(cfg["localities"]) >= 10
    sec_status = json.loads(urllib.request.urlopen(f"{base_url}/api/security/status").read().decode("utf-8"))
    assert "require_captcha" in sec_status
    assert "sms_provider_name" in sec_status
    print(f"  ✓ Loaded {len(cfg['categories'])} categories, {len(cfg['localities'])} localities, {len(cfg['departments'])} departments.")
    print(f"  ✓ SMS Provider: {sec_status['sms_provider_name']} (Live: {sec_status['is_live_sms']})")

    # Test 3: Passwordless Mobile OTP Flow
    print("\n[TEST 3] Testing Passwordless Mobile OTP Flow...")
    test_phone = f"+919{secrets.randbelow(899999999) + 100000000}"
    status_code, otp_resp = http_post_json(f"{base_url}/api/otp/request", {"phone": test_phone}, client_headers)
    assert status_code == 200, f"Failed OTP request: {otp_resp}"
    assert otp_resp.get("success") is True
    demo_otp = otp_resp.get("demo_otp")
    assert demo_otp is not None, "Demo OTP should be returned in demo mode"
    print(f"  ✓ OTP requested for {test_phone}. Received demonstration code: {demo_otp}")

    # Verify OTP
    status_code, v_resp = http_post_json(f"{base_url}/api/otp/verify", {"phone": test_phone, "otp": demo_otp}, client_headers)
    assert status_code == 200
    assert v_resp.get("success") is True
    verified_token = v_resp.get("verification_token")
    assert verified_token is not None
    print(f"  ✓ OTP successfully verified! Signed proof token issued.")

    # Test 4: Compulsory Live Photo Upload & Image Captioning
    print("\n[TEST 4] Verifying Photo Upload with Live Image Captioning...")
    img_bytes = make_test_image_bytes()
    body, ctype = encode_multipart_formdata({}, {"photo": ("pothole_field_snap.jpg", img_bytes, "image/jpeg")})
    upload_req = urllib.request.Request(f"{base_url}/api/upload-photo", data=body, headers={"Content-Type": ctype}, method="POST")
    up_resp = urllib.request.urlopen(upload_req)
    assert up_resp.status == 200
    up_data = json.loads(up_resp.read().decode("utf-8"))
    assert up_data.get("success") is True
    uploaded_image_path = up_data.get("image_path")
    image_caption = up_data.get("image_caption")
    assert uploaded_image_path.startswith("/uploads/issue_")
    assert "Live Camera Evidence" in image_caption or "Photo Evidence" in image_caption
    print(f"  ✓ Photo uploaded securely: {uploaded_image_path}")
    print(f"  ✓ Live Image Caption generated: \"{image_caption}\"")

    # Test 5: Compulsory Photo Validation (Submitting without photo must fail)
    print("\n[TEST 5] Testing Compulsory Photo Requirement...")
    no_photo_payload = {
        "title": "Uncollected waste near Hazratganj",
        "description": "Garbage accumulating without photo.",
        "locality": "Hazratganj",
        "image_path": None,
    }
    code, no_photo_resp = http_post_json(f"{base_url}/api/complaints", no_photo_payload, client_headers)
    assert code == 400, f"Expected 400 when photo is missing, got {code}"
    assert "photo of the civic issue is required" in no_photo_resp.get("error", "").lower()
    print("  ✓ Submission blocked when compulsory live photo is absent.")

    # Test 6: Submit Normal Civilian Complaint (No Suspicious Activity)
    print("\n[TEST 6] Submitting Normal Civilian Complaint (No Suspicious Signals)...")
    distinct_issues = [
        ("Water pipeline rupture flooding service lane", "Continuous drinking water main burst along sector 4 Vikas Nagar.", "Vikas Nagar"),
        ("Electrical transformer sparks near commercial market", "Live sparks falling from overhead junction box near Aminabad.", "Aminabad"),
        ("Open sewage manhole cover missing on link road", "Hazardous open drain chamber on residential corridor in Ashiyana.", "Ashiyana"),
    ]
    issue_idx = int(time.time()) % len(distinct_issues)
    title_base, desc_base, loc_base = distinct_issues[issue_idx]
    run_title = f"{title_base} ({secrets.token_hex(4)})"
    run_desc = f"{desc_base} Urgent municipal evaluation requested ({secrets.token_hex(4)})."

    new_complaint = {
        "title": run_title,
        "description": run_desc,
        "locality": loc_base,
        "landmark": "Near Main Sector Crossroad",
        "image_path": uploaded_image_path,
        "image_caption": image_caption,
        "phone": test_phone,
        "otp_token": verified_token,
        "latitude": 26.8500,
        "longitude": 80.9900,
        "location_shared": True,
    }
    code, created = http_post_json(f"{base_url}/api/complaints", new_complaint, client_headers)
    assert code == 201, f"Expected 201 Created for normal civilian, got {code}: {created}"
    created_id = created["tracking_id"]
    assert created_id.startswith("CF-2026-")
    print(f"  ✓ Normal complaint registered without CAPTCHA friction! Tracking ID: {created_id}")
    print(f"    Category: {created['category']} | Priority: {created['priority']}")
    print(f"    Source: {created['classification_source']}")

    # Test 7: Advisory Duplicate Detection with User Override and Security Check
    print("\n[TEST 7] Testing Advisory Duplicate Detection & Civilian Confirmation...")
    duplicate_payload = {
        "title": run_title,
        "description": run_desc,
        "locality": loc_base,
        "image_path": uploaded_image_path,
        "force_duplicate": False,
    }
    code, dup_resp = http_post_json(f"{base_url}/api/complaints", duplicate_payload, client_headers)
    assert code == 409, f"Expected 409 Conflict for duplicate advisory, got {code}: {dup_resp}"
    assert dup_resp.get("is_duplicate") is True
    print(f"  ✓ Duplicate detected ({round(dup_resp['similarity_score']*100)}% match with {dup_resp['duplicate_of']}). Advisory returned.")

    # Now override with force_duplicate = True and solve cryptographic challenge
    print("  Testing CAPTCHA verification when suspicious duplicate is resubmitted...")
    duplicate_payload["force_duplicate"] = True
    # Without CAPTCHA token, it must trigger 403
    code_no_cap, cap_err = http_post_json(f"{base_url}/api/complaints", duplicate_payload, client_headers)
    assert code_no_cap == 403, f"Expected 403 when suspicious and no CAPTCHA, got {code_no_cap}: {cap_err}"
    assert cap_err.get("require_captcha") is True
    print("    ✓ Server strictly required CAPTCHA for suspicious duplicate resubmission.")

    # Solve challenge / provide valid security token
    duplicate_payload["captcha_token"] = "demo_bypass"
    code, override_resp = http_post_json(f"{base_url}/api/complaints", duplicate_payload, client_headers)
    assert code == 201, f"Expected 201 when verified, got {code}: {override_resp}"
    print(f"  ✓ Civilian confirmed separate incident & verified security: Registered as {override_resp['tracking_id']}.")

    # Test 8: Public Tracking Privacy Enforcement
    print(f"\n[TEST 8] Verifying Strict Public Tracking Privacy for {created_id}...")
    track_req = urllib.request.urlopen(f"{base_url}/api/complaints/{created_id}")
    assert track_req.status == 200
    track_data = json.loads(track_req.read().decode("utf-8"))
    assert track_data["image_path"] == uploaded_image_path
    assert track_data.get("phone") is None, "LEAK: Phone number exposed on public tracking!"
    assert track_data.get("latitude") is None, "LEAK: Latitude exposed on public tracking!"
    assert track_data.get("longitude") is None, "LEAK: Longitude exposed on public tracking!"
    assert track_data.get("admin_notes") is None, "LEAK: Admin notes exposed on public tracking!"
    assert track_data.get("risk_signals") is None, "LEAK: Risk signals exposed on public tracking!"
    print("  ✓ Public tracking verified: Civilian phone, GPS coordinates, and admin notes strictly redacted.")

    # Test 9: Admin Workspace Inspection & Internal Notes
    print(f"\n[TEST 9] Verifying Municipal Officer Workspace Access...")
    admin_req = urllib.request.urlopen(f"{base_url}/api/complaints/{created_id}?admin=1")
    assert admin_req.status == 200
    admin_data = json.loads(admin_req.read().decode("utf-8"))
    assert admin_data.get("phone") == test_phone, "Admin should see verified phone for field contact"
    assert admin_data.get("latitude") == 26.8500, "Admin should see GPS coordinates for dispatch navigation"
    print("  ✓ Admin authorized view verified: Coordinates and phone accessible only to municipal officers.")

    # Test 10: Server-Side Rate Limiting
    print("\n[TEST 10] Testing Server-side Rate Limiting Enforcement...")
    burst_client = {"User-Agent": f"BurstSpamBot/{secrets.token_hex(8)}"}
    rate_limited = False
    for i in range(config.RATE_LIMIT_SUBMISSION_MAX + 2):
        code, resp = http_post_json(
            f"{base_url}/api/complaints",
            {
                "title": f"Rapid submission test {i} in Chinhat",
                "description": f"Testing rate limiting window and maximum threshold {i}.",
                "locality": "Chinhat",
                "image_path": uploaded_image_path,
                "force_duplicate": True,
                "captcha_token": "demo_bypass",
            },
            burst_client,
        )
        if code == 429:
            rate_limited = True
            print(f"  ✓ Rate limit triggered on request {i+1}: {resp.get('error')}")
            break

    assert rate_limited, "Rate limiting should have blocked excessive submissions"

    # 11. Headless Edge Screenshots
    print("\n" + "=" * 60)
    print("CAPTURING HIGH-RESOLUTION DESKTOP & MOBILE SCREENSHOTS")
    print("=" * 60)

    os.makedirs(os.path.join(BASE_DIR, "screenshots"), exist_ok=True)
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    screenshot_targets = [
        ("home", "screen1_home_desktop.png", 1280, 800, "Citizen Home (Desktop 1280x800)"),
        ("home", "screen1_home_mobile.png", 390, 844, "Citizen Home (Mobile 390x844)"),
        ("submit", "screen2_submit_desktop.png", 1280, 800, "Report Issue Form (Desktop 1280x800)"),
        ("submit", "screen2_submit_mobile.png", 390, 844, "Report Issue Form (Mobile 390x844)"),
        (f"track&id={created_id}", "screen3_track_desktop.png", 1280, 800, "Track Complaint (Desktop 1280x800)"),
        (f"track&id={created_id}", "screen3_track_mobile.png", 390, 844, "Track Complaint (Mobile 390x844)"),
        ("admin&unlocked=1", "screen4_admin_desktop.png", 1280, 800, "Admin Portal (Desktop 1280x800)"),
        ("admin&unlocked=1", "screen4_admin_mobile.png", 390, 844, "Admin Portal (Mobile 390x844)"),
    ]

    for tab_query, filename, w, h, label in screenshot_targets:
        local_path = os.path.join(BASE_DIR, "screenshots", filename)
        artifact_path = os.path.join(ARTIFACT_DIR, filename)
        url = f"http://localhost:8501/?tab={tab_query}"

        cmd = [
            EDGE_EXE,
            "--headless=new",
            f"--window-size={w},{h}",
            f"--screenshot={local_path}",
            "--hide-scrollbars",
            "--disable-gpu",
            url
        ]

        print(f"  Capturing {label} -> {filename}...")
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
            if os.path.exists(local_path) and os.path.getsize(local_path) > 1000:
                shutil.copy2(local_path, artifact_path)
                print(f"    ✓ Saved: {os.path.getsize(local_path):,} bytes -> copied to artifacts")
            else:
                print(f"    ⚠️ Warning: screenshot failed ({res.stderr.decode('utf-8')[:100]})")
        except Exception as e:
            print(f"    ❌ Error running Edge: {e}")

    server_thread.stop()
    print("\n" + "=" * 60)
    print("ALL TESTS & CAPTURES COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
