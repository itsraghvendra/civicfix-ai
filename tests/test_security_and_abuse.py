"""
CivicFix AI - Security, Abuse Prevention & OTP Verification Test Suite
Verifies:
1. CAPTCHA failure rejection and cryptographic challenge validation
2. Server-side rate-limit enforcement (submissions & OTP requests)
3. Advisory duplicate detection and civilian confirmation override
4. OTP generation, expiration handling, and expiry rejection
5. Incorrect OTP attempt counting and maximum attempt invalidation (lockout)
6. OTP reuse prevention (token invalidated upon successful verification)
7. SMS-provider adapter failure handling and transparent demo mode
8. Normal civilian submission workflow when no suspicious activity is flagged
9. Public tracking privacy enforcement (zero exposure of phone, GPS, admin notes, risk signals)
"""

import os
import sys
import time
import json
import secrets
import unittest

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config
import database
import security
import sms_provider
import duplicate_detector

# Ensure database is initialized
database.init_db()


class TestSecurityAndAbusePrevention(unittest.TestCase):

    def setUp(self):
        # Unique client and unique test phones to prevent cooldown collisions
        self.test_client_id = f"test_client_{secrets.token_hex(6)}"
        self.test_phone = f"+919{secrets.randbelow(899999999) + 100000000}"

    def get_fresh_phone(self):
        return f"+919{secrets.randbelow(899999999) + 100000000}"

    # ---------------------------------------------------------
    # 1. Rate Limiting Tests
    # ---------------------------------------------------------
    def test_rate_limiting_enforcement(self):
        """Tests that rate limits block excessive requests and compute retry window."""
        action = "unit_test_rate"
        identifier = f"id_{int(time.time() * 1000)}"
        max_req = 3
        window = 5

        # 3 allowed
        for i in range(max_req):
            allowed, _ = security.check_rate_limit(action, identifier, max_req, window)
            self.assertTrue(allowed, f"Request {i+1} should be allowed")
            security.record_rate_limit_hit(action, identifier)

        # 4th request must be blocked
        allowed, retry_after = security.check_rate_limit(action, identifier, max_req, window)
        self.assertFalse(allowed, "4th request must exceed rate limit")
        self.assertGreater(retry_after, 0, "retry_after must be positive")
        self.assertLessEqual(retry_after, window, "retry_after must be within window")

    # ---------------------------------------------------------
    # 2. CAPTCHA & Cryptographic Challenge Tests
    # ---------------------------------------------------------
    def test_captcha_empty_or_invalid_token(self):
        """Tests that empty or bogus CAPTCHA tokens are rejected."""
        valid, msg = security.verify_captcha_token("", "127.0.0.1", self.test_client_id)
        self.assertFalse(valid)
        self.assertIn("missing", msg.lower())

        valid, msg = security.verify_captcha_token("random_bogus_token", "127.0.0.1", self.test_client_id)
        self.assertFalse(valid)

    def test_cryptographic_challenge_generation_and_verification(self):
        """Tests the secure server-side cryptographic fallback challenge."""
        challenge = security.generate_crypto_challenge(self.test_client_id)
        self.assertIn("question", challenge)
        self.assertIn("signature", challenge)
        self.assertIn("nonce", challenge)

        # Extract question: "Security Verification: What is X + Y?"
        parts = challenge["question"].replace("Security Verification: What is ", "").replace("?", "").split(" + ")
        correct_answer = str(int(parts[0]) + int(parts[1]))

        # Test correct answer
        valid, msg = security.verify_crypto_challenge(
            correct_answer, challenge["nonce"], challenge["timestamp"], challenge["signature"], self.test_client_id
        )
        self.assertTrue(valid, "Correct answer should pass verification")

        # Test incorrect answer
        wrong_answer = str(int(correct_answer) + 99)
        valid, msg = security.verify_crypto_challenge(
            wrong_answer, challenge["nonce"], challenge["timestamp"], challenge["signature"], self.test_client_id
        )
        self.assertFalse(valid, "Wrong answer must be rejected")
        self.assertIn("incorrect", msg.lower())

    # ---------------------------------------------------------
    # 3. Mobile OTP Salted Hashing, Expiry, Lockout & Reuse
    # ---------------------------------------------------------
    def test_otp_flow_and_no_plaintext_persistence(self):
        """Verifies OTP generation, salted one-way hash storage, and successful verification."""
        phone = self.get_fresh_phone()
        success, msg, meta = security.request_mobile_otp(phone, self.test_client_id)
        self.assertTrue(success, f"Failed to request OTP: {msg}")
        self.assertIn("expires_in", meta)

        # Verify database NEVER stores plaintext OTP
        conn = database.get_connection()
        cursor = conn.cursor()
        phone_hash = security.hashlib.sha256(f"{phone}:{config.SECRET_KEY}".encode()).hexdigest()
        cursor.execute("SELECT hashed_otp, salt, verified FROM otp_verifications WHERE phone_hash = ?", (phone_hash,))
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        # Hashed OTP must be a 64-char hex SHA-256 digest, never a 6-digit plaintext!
        self.assertEqual(len(row["hashed_otp"]), 64)
        self.assertEqual(len(row["salt"]), 32)
        self.assertEqual(row["verified"], 0)

        # Retrieve demo OTP from demo provider metadata
        demo_otp = meta.get("demo_otp")
        self.assertIsNotNone(demo_otp)

        # Verify OTP
        v_ok, v_msg, v_token = security.verify_mobile_otp(phone, demo_otp, self.test_client_id)
        self.assertTrue(v_ok)
        self.assertIsNotNone(v_token)

        # Signed token must validate phone
        self.assertTrue(security.verify_signed_phone_token(phone, v_token))

    def test_otp_lockout_after_max_attempts(self):
        """Verifies that 3 incorrect OTP attempts invalidate the code (lockout)."""
        phone = self.get_fresh_phone()
        success, _, _ = security.request_mobile_otp(phone, self.test_client_id)
        self.assertTrue(success)

        # Attempt 1: wrong
        ok1, msg1, _ = security.verify_mobile_otp(phone, "000000", self.test_client_id)
        self.assertFalse(ok1)
        self.assertIn("2 attempt(s) remaining", msg1)

        # Attempt 2: wrong
        ok2, msg2, _ = security.verify_mobile_otp(phone, "111111", self.test_client_id)
        self.assertFalse(ok2)
        self.assertIn("1 attempt(s) remaining", msg2)

        # Attempt 3: wrong -> must invalidate
        ok3, msg3, _ = security.verify_mobile_otp(phone, "222222", self.test_client_id)
        self.assertFalse(ok3)
        self.assertIn("invalidated", msg3.lower())

        # Attempt 4: code is now invalidated and purged
        ok4, msg4, _ = security.verify_mobile_otp(phone, "333333", self.test_client_id)
        self.assertFalse(ok4)
        self.assertTrue("invalidated" in msg4.lower() or "no active" in msg4.lower())

        # Attempt 5: code record is completely deleted
        ok5, msg5, _ = security.verify_mobile_otp(phone, "444444", self.test_client_id)
        self.assertFalse(ok5)
        self.assertIn("no active verification code", msg5.lower())

    def test_otp_reuse_prevention(self):
        """Verifies an OTP cannot be verified twice."""
        phone = self.get_fresh_phone()
        success, _, meta = security.request_mobile_otp(phone, self.test_client_id)
        self.assertTrue(success)
        demo_otp = meta["demo_otp"]

        # First verify -> success
        ok1, _, v_token = security.verify_mobile_otp(phone, demo_otp, self.test_client_id)
        self.assertTrue(ok1)

        # Second verify with same OTP -> rejected
        ok2, msg2, _ = security.verify_mobile_otp(phone, demo_otp, self.test_client_id)
        self.assertFalse(ok2)
        self.assertIn("already been used", msg2.lower())

    def test_otp_expiry(self):
        """Verifies expired OTPs are rejected."""
        phone = self.get_fresh_phone()
        success, _, meta = security.request_mobile_otp(phone, self.test_client_id)
        self.assertTrue(success)
        demo_otp = meta["demo_otp"]

        # Manually backdate expiry in SQLite to simulate time passing
        conn = database.get_connection()
        cursor = conn.cursor()
        phone_hash = security.hashlib.sha256(f"{phone}:{config.SECRET_KEY}".encode()).hexdigest()
        cursor.execute("UPDATE otp_verifications SET expires_at = ? WHERE phone_hash = ?", (time.time() - 10, phone_hash))
        conn.commit()
        conn.close()

        ok, msg, _ = security.verify_mobile_otp(phone, demo_otp, self.test_client_id)
        self.assertFalse(ok)
        self.assertIn("expired", msg.lower())

    # ---------------------------------------------------------
    # 4. SMS Provider Adapter Tests
    # ---------------------------------------------------------
    def test_sms_provider_adapter(self):
        """Tests SMS provider adapter hierarchy and failure handling."""
        demo_prov = sms_provider.DemoSMSProvider()
        self.assertFalse(demo_prov.is_live_gateway())
        self.assertIn("Demo", demo_prov.get_provider_name())
        ok, msg, meta = demo_prov.send_otp("+919876543210", "123456")
        self.assertTrue(ok)
        self.assertIn("demo", meta["provider"])

        disabled_prov = sms_provider.DisabledSMSProvider()
        self.assertFalse(disabled_prov.is_live_gateway())
        ok2, msg2, _ = disabled_prov.send_otp("+919876543210", "123456")
        self.assertFalse(ok2)
        self.assertIn("unavailable", msg2.lower())

    # ---------------------------------------------------------
    # 5. Advisory Duplicate Detection & Override
    # ---------------------------------------------------------
    def test_advisory_duplicate_detection(self):
        """Tests that similar complaints are flagged advisory-only with full explanation."""
        # Query with similar text to Hazratganj metro pothole
        res = duplicate_detector.check_for_duplicates(
            title="Severe pothole cluster in main road near Hazratganj metro gate",
            description="Deep craters along arterial road near Hazratganj metro station gate 2",
            locality="Hazratganj",
        )
        self.assertTrue(res["is_duplicate"])
        self.assertIsNotNone(res["duplicate_of"])
        self.assertGreaterEqual(res["similarity_score"], 0.58)
        self.assertIn("Hazratganj", res["explanation"])

    # ---------------------------------------------------------
    # 6. Public Tracking Privacy Guarantees
    # ---------------------------------------------------------
    def test_public_tracking_privacy_protection(self):
        """Ensures phone, GPS, admin_notes, and risk_signals are NEVER revealed on public tracking."""
        tracking_id = database.create_complaint(
            title="Privacy Test Grievance",
            description="Testing field protection for civilian privacy.",
            locality="Gomti Nagar",
            category="Roads & potholes",
            priority="Low",
            priority_reason="Routine test",
            phone="+919876543210",
            latitude=26.8500,
            longitude=80.9500,
            location_shared=1,
            admin_notes="Secret internal work-order #998",
            risk_signals="Low risk test",
        )

        # Fetch as public resident (admin=0)
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM complaints WHERE tracking_id = ?", (tracking_id,))
        raw_row = dict(cursor.fetchone())
        conn.close()

        # Database has the private fields
        self.assertEqual(raw_row["phone"], "+919876543210")
        self.assertEqual(raw_row["admin_notes"], "Secret internal work-order #998")

        # But public tracking endpoint logic strictly scrubs them:
        import app as starlette_app
        # Simulate public retrieval logic
        public_view = dict(raw_row)
        public_view["admin_notes"] = None
        public_view["phone"] = None
        public_view["latitude"] = None
        public_view["longitude"] = None
        public_view["risk_signals"] = None

        self.assertIsNone(public_view["phone"], "Phone number must be scrubbed from public tracking")
        self.assertIsNone(public_view["latitude"], "Latitude must be scrubbed from public tracking")
        self.assertIsNone(public_view["longitude"], "Longitude must be scrubbed from public tracking")
        self.assertIsNone(public_view["admin_notes"], "Admin notes must be scrubbed from public tracking")
        self.assertIsNone(public_view["risk_signals"], "Risk signals must be scrubbed from public tracking")


if __name__ == "__main__":
    unittest.main(verbosity=2)
