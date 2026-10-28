"""
CivicFix AI - Configuration & Constants (Lucknow Edition)
Brand system, Lucknow localities, demo teams, categories, priorities, and environment setup.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Groq API Configuration (backend-only, never exposed to client)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
GROQ_TIMEOUT_SECONDS = 6.0

# Database & File Storage Paths
DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).parent)))
DB_PATH = Path(os.getenv("DB_PATH", str(DATA_DIR / "civicfix.db")))
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", str(DATA_DIR / "uploads")))
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Upload Configuration
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

# Brand Messages
BRAND_NAME = "CIVICFIX AI"
LOCATION_NAME = "Lucknow, Uttar Pradesh, India"
TAGLINE = "Together, Let's Make Lucknow Better."
SUPPORTING_MESSAGE = "Every small action can help create a cleaner, safer, and more beautiful city."

# Civic Complaint Categories
ALLOWED_CATEGORIES = [
    "Roads & potholes",
    "Garbage & sanitation",
    "Streetlights",
    "Water supply & leakage",
    "Drainage & sewage",
    "Public safety / hazard",
    "Parks & public spaces",
    "Other / needs review",
]

# Complaint Statuses (Civilian Progression: Submitted -> In Review -> In Progress -> Resolved)
ALLOWED_STATUSES = ["Submitted", "In Review", "In Progress", "Resolved"]
ALLOWED_PRIORITIES = ["High", "Medium", "Low"]

# Standard Lucknow Localities (Mandatory Dropdown List)
LUCKNOW_LOCALITIES = [
    "Gomti Nagar",
    "Hazratganj",
    "Aliganj",
    "Indira Nagar",
    "Chowk",
    "Alambagh",
    "Jankipuram",
    "Mahanagar",
    "Rajajipuram",
    "Aminabad",
    "Ashiyana",
    "Vikas Nagar",
    "Other / Enter manually",
]

# Municipal Demo Teams for Administrative Assignment
MUNICIPAL_DEPARTMENTS = [
    "Roads Maintenance Cell",
    "Solid Waste & Sanitation Division",
    "Water Supply Department (Jal Sansthan)",
    "Drainage & Sewerage Network",
    "Electrical & Street Lighting Maintenance",
    "Parks & Public Spaces Division",
    "Public Safety & Hazard Response Unit",
]

# Brand Color Palette Tokens
BRAND_COLORS = {
    "soft_white": "#E8E9DF",      # Page canvas background
    "sage_green": "#A9B887",      # Selected nav, secondary highlights, accents
    "deep_olive": "#2E3D28",      # Sidebar, brand logo, headings, primary buttons
    "white": "#FFFFFF",           # Form and card surfaces
    "text_main": "#1E251B",       # High contrast body text
    "text_muted": "#576352",      # Secondary caption text
    "border_subtle": "#D5D7C9",   # 1px border dividers
    "priority_high": "#B91C1C",   # Red
    "priority_med": "#B45309",    # Amber
    "priority_low": "#4B5563",    # Neutral grey
}

# --- Abuse Prevention, CAPTCHA & Security Configuration ---

# Server Secret Key for salting OTP hashes and signing verification tokens
SECRET_KEY = os.getenv("SECRET_KEY", "civicfix-secret-salt-lucknow-2026-prototype")

# Cloudflare Turnstile CAPTCHA (Optional / Configurable)
TURNSTILE_SITE_KEY = os.getenv("TURNSTILE_SITE_KEY", "").strip()
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "").strip()
CAPTCHA_REQUIRED_ALWAYS = os.getenv("CAPTCHA_REQUIRED_ALWAYS", "false").lower() == "true"
TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

# Rate Limiting Configuration (Configurable Thresholds and Windows)
RATE_LIMIT_SUBMISSION_MAX = int(os.getenv("RATE_LIMIT_SUBMISSION_MAX", "5"))         # max 5 submissions
RATE_LIMIT_SUBMISSION_WINDOW = int(os.getenv("RATE_LIMIT_SUBMISSION_WINDOW", "600")) # in 10 minutes
RATE_LIMIT_OTP_REQUEST_MAX = int(os.getenv("RATE_LIMIT_OTP_REQUEST_MAX", "3"))        # max 3 OTP requests
RATE_LIMIT_OTP_REQUEST_WINDOW = int(os.getenv("RATE_LIMIT_OTP_REQUEST_WINDOW", "600"))# in 10 minutes
RATE_LIMIT_OTP_VERIFY_MAX = int(os.getenv("RATE_LIMIT_OTP_VERIFY_MAX", "5"))          # max 5 verify attempts
OTP_RESEND_COOLDOWN_SECONDS = int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60"))    # 60s cooldown

# Passwordless Mobile OTP Configuration
OTP_REQUIRED = os.getenv("OTP_REQUIRED", "false").lower() == "true"                  # Optional by default
OTP_EXPIRY_SECONDS = int(os.getenv("OTP_EXPIRY_SECONDS", "300"))                      # 5 minutes
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "3"))                           # Invalidate after 3 fails
SMS_PROVIDER = os.getenv("SMS_PROVIDER", "demo").lower().strip()                     # "demo", "twilio", "fast2sms", "none"

# SMS Gateway Credentials (Adapter Pattern)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "").strip()
FAST2SMS_API_KEY = os.getenv("FAST2SMS_API_KEY", "").strip()

# Suspicious Activity Detection Thresholds
SUSPICIOUS_FAIL_ATTEMPTS = int(os.getenv("SUSPICIOUS_FAIL_ATTEMPTS", "3"))
SUSPICIOUS_SIMILARITY_THRESHOLD = float(os.getenv("SUSPICIOUS_SIMILARITY_THRESHOLD", "0.72"))
SUSPICIOUS_BURST_WINDOW = int(os.getenv("SUSPICIOUS_BURST_WINDOW", "120")) # 2 minutes burst window
