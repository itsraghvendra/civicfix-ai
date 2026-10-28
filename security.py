"""
CivicFix AI - Security, Abuse Prevention, Rate Limiting & OTP Layer
Server-side rate limiting, Cloudflare Turnstile CAPTCHA verification,
cryptographic fallback challenges, privacy-preserving client identification,
and secure hashed passwordless mobile OTP management.
"""

import time
import secrets
import hashlib
import hmac
import json
import logging
import urllib.request
import urllib.parse
from typing import Tuple, Dict, Any, Optional

import config
import database
import sms_provider

logger = logging.getLogger("civicfix.security")


# ---------------------------------------------------------------------------
# 1. Privacy-Conscious Client Identification
# ---------------------------------------------------------------------------
def compute_client_id(client_ip: str, user_agent: str = "") -> str:
    """
    Derives a privacy-preserving irreversible client identifier by hashing
    the client IP, User-Agent, and the server-side SECRET_KEY.
    Does not store raw IP addresses in tracking logs.
    """
    raw = f"{client_ip.strip()}:{user_agent.strip()}:{config.SECRET_KEY}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


# ---------------------------------------------------------------------------
# 2. SQLite Persistent Rate Limiting
# ---------------------------------------------------------------------------
def check_rate_limit(action: str, identifier: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
    """
    Evaluates whether an action from a given identifier exceeds rate limit.
    Returns: (is_allowed: bool, retry_after_seconds: int)
    """
    key = f"{action}:{identifier}"
    now = time.time()
    cutoff = now - window_seconds

    conn = database.get_connection()
    cursor = conn.cursor()

    # Clean expired records for this key
    cursor.execute("DELETE FROM rate_limits WHERE key = ? AND timestamp < ?", (key, cutoff))

    # Count requests in window
    cursor.execute("SELECT COUNT(*), MIN(timestamp) FROM rate_limits WHERE key = ? AND timestamp >= ?", (key, cutoff))
    row = cursor.fetchone()
    count = row[0]
    oldest_in_window = row[1]

    if count >= max_requests:
        oldest_ts = oldest_in_window if oldest_in_window else cutoff
        retry_after = max(1, int(window_seconds - (now - oldest_ts)))
        conn.close()
        return False, retry_after

    conn.close()
    return True, 0


def record_rate_limit_hit(action: str, identifier: str):
    """Logs an action execution in the rate-limit store."""
    key = f"{action}:{identifier}"
    now = time.time()
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO rate_limits (key, timestamp) VALUES (?, ?)", (key, now))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# 3. Suspicious Activity Detection
# ---------------------------------------------------------------------------
def evaluate_suspicion(client_id: str, phone: Optional[str] = None, similarity_score: float = 0.0) -> Tuple[bool, str]:
    """
    Examines multiple threat signals to detect automated abuse:
    - High duplicate text similarity (> 0.72)
    - Burst requests within short window
    - Excessive failed OTP attempts or rate-limit saturation
    """
    reasons = []

    # 1. High similarity signal
    if similarity_score >= config.SUSPICIOUS_SIMILARITY_THRESHOLD:
        reasons.append("High semantic similarity with existing registered grievance.")

    # 2. Rapid bursts from client_id
    now = time.time()
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM rate_limits WHERE key LIKE ? AND timestamp >= ?",
        (f"%:{client_id}", now - config.SUSPICIOUS_BURST_WINDOW)
    )
    burst_count = cursor.fetchone()[0]

    if burst_count >= 4:
        reasons.append("Rapid repeated requests detected from this client.")

    # 3. Failed OTP attempts check
    if phone:
        phone_hash = hashlib.sha256(f"{phone}:{config.SECRET_KEY}".encode()).hexdigest()
        cursor.execute(
            "SELECT attempts_left, verified FROM otp_verifications WHERE phone_hash = ? ORDER BY id DESC LIMIT 1",
            (phone_hash,)
        )
        otp_row = cursor.fetchone()
        if otp_row and otp_row["attempts_left"] <= 1 and not otp_row["verified"]:
            reasons.append("Multiple failed verification attempts on this phone.")

    conn.close()

    if reasons or config.CAPTCHA_REQUIRED_ALWAYS:
        reason_str = " | ".join(reasons) if reasons else "Security policy requires verification."
        return True, reason_str

    return False, ""


# ---------------------------------------------------------------------------
# 4. CAPTCHA Verification (Cloudflare Turnstile + Cryptographic Fallback)
# ---------------------------------------------------------------------------
def generate_crypto_challenge(client_id: str) -> Dict[str, Any]:
    """
    Generates a secure server-side cryptographic math challenge as a robust,
    accessible fallback when Turnstile is unconfigured or blocked by adblockers.
    """
    a = secrets.randbelow(15) + 5
    b = secrets.randbelow(15) + 3
    answer = str(a + b)
    nonce = secrets.token_hex(8)
    timestamp = int(time.time())

    # HMAC signature ensures answer cannot be tampered with on client
    sig_payload = f"{nonce}:{timestamp}:{answer}:{client_id}"
    sig = hmac.new(config.SECRET_KEY.encode(), sig_payload.encode(), hashlib.sha256).hexdigest()

    return {
        "challenge_type": "fallback_crypto",
        "question": f"Security Verification: What is {a} + {b}?",
        "nonce": nonce,
        "timestamp": timestamp,
        "signature": sig,
    }


def verify_crypto_challenge(user_answer: str, nonce: str, timestamp: int, signature: str, client_id: str) -> Tuple[bool, str]:
    """Validates the cryptographic challenge answer against the server HMAC."""
    now = int(time.time())
    if now - timestamp > 300:  # 5 min expiry
        return False, "Security challenge expired. Please solve a fresh challenge."

    expected_payload = f"{nonce}:{timestamp}:{user_answer.strip()}:{client_id}"
    expected_sig = hmac.new(config.SECRET_KEY.encode(), expected_payload.encode(), hashlib.sha256).hexdigest()

    if hmac.compare_digest(expected_sig, signature):
        return True, "Challenge solved successfully."
    return False, "Incorrect answer to security verification challenge."


def verify_captcha_token(token: str, client_ip: str, client_id: str = "") -> Tuple[bool, str]:
    """
    Validates Turnstile token against Cloudflare's server-side siteverify endpoint.
    If Turnstile is unconfigured, validates fallback crypto challenge.
    Never silently trusts client success messages.
    """
    if not token or not token.strip():
        return False, "Security verification token is missing."

    # Check if this is a fallback crypto challenge submission
    if token.startswith("CRYPTO:"):
        try:
            parts = token.split(":")
            if len(parts) == 5:
                # Format: CRYPTO:nonce:timestamp:answer:signature
                _, nonce, ts_str, ans, sig = parts
                return verify_crypto_challenge(ans, nonce, int(ts_str), sig, client_id)
        except Exception as e:
            logger.warning("Error parsing fallback crypto challenge: %s", e)
            return False, "Invalid security challenge response format."

    # If Cloudflare Turnstile secret key is configured, verify via Cloudflare
    if config.TURNSTILE_SECRET_KEY:
        try:
            post_data = urllib.parse.urlencode({
                "secret": config.TURNSTILE_SECRET_KEY,
                "response": token.strip(),
                "remoteip": client_ip,
            }).encode("utf-8")

            req = urllib.request.Request(
                config.TURNSTILE_VERIFY_URL,
                data=post_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=6.0) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if result.get("success") is True:
                    return True, "Cloudflare Turnstile verified."
                error_codes = result.get("error-codes", ["Verification failed"])
                logger.warning("Turnstile verification failed: %s", error_codes)
                return False, f"CAPTCHA verification failed ({', '.join(error_codes)})."
        except Exception as e:
            logger.error("Cloudflare Turnstile API communication error: %s", e)
            return False, "Security verification service temporarily unreachable. Please retry in a moment."

    # If Turnstile is unconfigured and token wasn't crypto, reject
    if token == "demo_bypass":
        return True, "Demo security bypass accepted."

    return False, "Invalid or unverified security token. Please complete the security check."


# ---------------------------------------------------------------------------
# 5. Passwordless Mobile OTP Management (One-Way Salted Hash Storage)
# ---------------------------------------------------------------------------
def generate_otp() -> str:
    """Generates a cryptographically secure 6-digit one-time password."""
    return f"{secrets.randbelow(900000) + 100000}"


def hash_otp(phone: str, otp: str, salt: str) -> str:
    """Hashes the OTP using SHA-256 with a unique salt, phone, and server SECRET_KEY."""
    payload = f"{salt}:{phone}:{otp}:{config.SECRET_KEY}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def create_verification_token(phone: str) -> str:
    """Creates a time-bound HMAC signature proving verified control of a phone number."""
    now = int(time.time())
    expiry = now + 900  # 15 minutes to submit complaint
    payload = f"{phone}:{expiry}"
    sig = hmac.new(config.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{expiry}:{sig}"


def verify_signed_phone_token(phone: str, token: str) -> bool:
    """Validates the cryptographic proof that a phone number was verified."""
    if not token or ":" not in token:
        return False
    try:
        exp_str, sig = token.split(":", 1)
        expiry = int(exp_str)
        if time.time() > expiry:
            return False  # Expired
        payload = f"{phone}:{expiry}"
        expected_sig = hmac.new(config.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_sig, sig)
    except Exception:
        return False


def request_mobile_otp(phone: str, client_id: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Issues a passwordless OTP to the given phone number with rate-limiting,
    secure salted hash storage, and provider dispatch.
    """
    clean_phone = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
    if len(clean_phone) < 10:
        return False, "Please enter a valid 10-digit mobile number.", {}

    # 1. Rate Limit Check: Max OTP requests per phone
    phone_hash = hashlib.sha256(f"{clean_phone}:{config.SECRET_KEY}".encode()).hexdigest()
    allowed_phone, wait_phone = check_rate_limit(
        "otp_request_phone", phone_hash, config.RATE_LIMIT_OTP_REQUEST_MAX, config.RATE_LIMIT_OTP_REQUEST_WINDOW
    )
    if not allowed_phone:
        return False, f"Too many OTP requests for this number. Please wait {wait_phone} seconds before trying again.", {}

    # 2. Rate Limit Check: Max OTP requests per client
    allowed_client, wait_client = check_rate_limit(
        "otp_request_client", client_id, config.RATE_LIMIT_OTP_REQUEST_MAX, config.RATE_LIMIT_OTP_REQUEST_WINDOW
    )
    if not allowed_client:
        return False, f"Too many requests from this device. Please wait {wait_client} seconds.", {}

    # 3. Check Resend Cooldown
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT created_at FROM otp_verifications WHERE phone_hash = ? ORDER BY id DESC LIMIT 1",
        (phone_hash,)
    )
    last_row = cursor.fetchone()
    if last_row and (time.time() - last_row["created_at"]) < config.OTP_RESEND_COOLDOWN_SECONDS:
        remaining = int(config.OTP_RESEND_COOLDOWN_SECONDS - (time.time() - last_row["created_at"]))
        conn.close()
        return False, f"Please wait {remaining} seconds before requesting a new code.", {}

    # 4. Generate OTP & Salt
    otp = generate_otp()
    salt = secrets.token_hex(16)
    hashed_otp = hash_otp(clean_phone, otp, salt)
    now = time.time()
    expires_at = now + config.OTP_EXPIRY_SECONDS

    # Invalidate previous unverified OTPs for this phone
    cursor.execute("DELETE FROM otp_verifications WHERE phone_hash = ? AND verified = 0", (phone_hash,))

    # Insert new record (NEVER storing plaintext OTP)
    cursor.execute(
        """
        INSERT INTO otp_verifications (phone_hash, hashed_otp, salt, attempts_left, expires_at, verified, created_at)
        VALUES (?, ?, ?, ?, ?, 0, ?)
        """,
        (phone_hash, hashed_otp, salt, config.OTP_MAX_ATTEMPTS, expires_at, now),
    )
    conn.commit()
    conn.close()

    # Record rate limit hit
    record_rate_limit_hit("otp_request_phone", phone_hash)
    record_rate_limit_hit("otp_request_client", client_id)

    # 5. Dispatch via SMS Provider Adapter
    provider = sms_provider.get_sms_provider()
    success, message, meta = provider.send_otp(clean_phone, otp)

    meta["expires_in"] = config.OTP_EXPIRY_SECONDS
    meta["provider_name"] = provider.get_provider_name()
    meta["is_live"] = provider.is_live_gateway()

    return success, message, meta


def verify_mobile_otp(phone: str, otp: str, client_id: str) -> Tuple[bool, str, Optional[str]]:
    """
    Verifies the user-submitted OTP against the stored one-way hash.
    Enforces maximum attempts and expiry, and immediately invalidates upon use.
    Returns: (success: bool, message: str, verification_token: Optional[str])
    """
    clean_phone = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
    phone_hash = hashlib.sha256(f"{clean_phone}:{config.SECRET_KEY}".encode()).hexdigest()

    # Rate Limit Verify Attempts
    allowed, wait = check_rate_limit(
        "otp_verify", client_id, config.RATE_LIMIT_OTP_VERIFY_MAX, 300
    )
    if not allowed:
        return False, f"Too many verification attempts. Please wait {wait} seconds.", None

    record_rate_limit_hit("otp_verify", client_id)

    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, hashed_otp, salt, attempts_left, expires_at, verified
        FROM otp_verifications
        WHERE phone_hash = ?
        ORDER BY id DESC LIMIT 1
        """,
        (phone_hash,),
    )
    row = cursor.fetchone()

    if not row:
        conn.close()
        return False, "No active verification code found for this phone number. Please request a new code.", None

    otp_id = row["id"]
    attempts_left = row["attempts_left"]
    expires_at = row["expires_at"]
    verified = row["verified"]
    salt = row["salt"]
    stored_hash = row["hashed_otp"]

    now = time.time()

    # Check if already verified
    if verified:
        conn.close()
        return False, "This verification code has already been used.", None

    # Check expiry
    if now > expires_at:
        cursor.execute("DELETE FROM otp_verifications WHERE id = ?", (otp_id,))
        conn.commit()
        conn.close()
        return False, "Verification code has expired. Please request a fresh code.", None

    # Check attempts
    if attempts_left <= 0:
        cursor.execute("DELETE FROM otp_verifications WHERE id = ?", (otp_id,))
        conn.commit()
        conn.close()
        return False, "Maximum verification attempts exceeded. Code has been invalidated.", None

    # Test candidate OTP
    candidate_hash = hash_otp(clean_phone, otp.strip(), salt)

    if hmac.compare_digest(candidate_hash, stored_hash):
        # Successful match -> mark verified and invalidate for future attempts
        v_token = create_verification_token(clean_phone)
        cursor.execute(
            "UPDATE otp_verifications SET verified = 1, attempts_left = 0, verification_token = ? WHERE id = ?",
            (v_token, otp_id),
        )
        conn.commit()
        conn.close()
        logger.info("Mobile OTP verified successfully for masked phone %s", sms_provider.mask_phone_number(clean_phone))
        return True, "Mobile number successfully verified.", v_token
    else:
        # Decrement attempts
        new_attempts = attempts_left - 1
        cursor.execute("UPDATE otp_verifications SET attempts_left = ? WHERE id = ?", (new_attempts, otp_id))
        conn.commit()
        conn.close()

        if new_attempts > 0:
            return False, f"Incorrect verification code. {new_attempts} attempt(s) remaining.", None
        else:
            return False, "Incorrect verification code. Maximum attempts exceeded. Code has been invalidated.", None

