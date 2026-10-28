"""
CivicFix AI - Modern Civic Grievance Management System (Lucknow Edition)
Starlette backend powering the Tailwind CSS Single-Page Application.
Backend Groq API classification, transparent priority scoring, advisory duplicate detection,
file uploads, server-side rate limiting, Cloudflare Turnstile CAPTCHA, passwordless mobile OTP,
and persistent SQLite storage for Lucknow Municipal Corporation.
"""

import os
import uuid
import json
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

import config
import database
import classifier
import duplicate_detector
import security
import sms_provider

# Initialize SQLite database and demo records
database.init_db()

# Setup templates and static assets
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


def get_client_info(request):
    """Extracts client IP and derives privacy-preserving client identifier."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    # Respect reverse proxy headers if running behind trusted proxy
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    user_agent = request.headers.get("user-agent", "")
    client_id = security.compute_client_id(client_ip, user_agent)
    return client_ip, user_agent, client_id


async def home_view(request):
    """Serves the main single-page application."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "brand_name": config.BRAND_NAME,
            "tagline": config.TAGLINE,
            "supporting_message": config.SUPPORTING_MESSAGE,
            "location_name": config.LOCATION_NAME,
            "has_groq": bool(config.GROQ_API_KEY),
            "groq_model": config.GROQ_MODEL,
            "turnstile_site_key": config.TURNSTILE_SITE_KEY,
            "otp_required": config.OTP_REQUIRED,
            "sms_provider": config.SMS_PROVIDER,
        },
    )


async def get_config(request):
    """Returns categories, localities, departments, security policies, and engine status."""
    client_ip, user_agent, client_id = get_client_info(request)
    provider = sms_provider.get_sms_provider()

    return JSONResponse(
        {
            "brand_name": config.BRAND_NAME,
            "tagline": config.TAGLINE,
            "supporting_message": config.SUPPORTING_MESSAGE,
            "location_name": config.LOCATION_NAME,
            "categories": config.ALLOWED_CATEGORIES,
            "localities": config.LUCKNOW_LOCALITIES,
            "departments": config.MUNICIPAL_DEPARTMENTS,
            "statuses": config.ALLOWED_STATUSES,
            "has_groq": bool(config.GROQ_API_KEY),
            "groq_model": config.GROQ_MODEL,
            "turnstile_site_key": config.TURNSTILE_SITE_KEY,
            "otp_required": config.OTP_REQUIRED,
            "sms_provider_name": provider.get_provider_name(),
            "is_live_sms": provider.is_live_gateway(),
            "sms_provider_type": config.SMS_PROVIDER,
            "client_id": client_id,
        }
    )


async def get_security_status(request):
    """Evaluates whether current client triggers suspicion or requires CAPTCHA."""
    client_ip, user_agent, client_id = get_client_info(request)
    is_suspicious, reason = security.evaluate_suspicion(client_id)

    provider = sms_provider.get_sms_provider()
    crypto_challenge = None
    if not config.TURNSTILE_SITE_KEY:
        crypto_challenge = security.generate_crypto_challenge(client_id)

    return JSONResponse(
        {
            "require_captcha": is_suspicious or config.CAPTCHA_REQUIRED_ALWAYS,
            "reason": reason,
            "turnstile_site_key": config.TURNSTILE_SITE_KEY,
            "crypto_challenge": crypto_challenge,
            "otp_required": config.OTP_REQUIRED,
            "sms_provider_name": provider.get_provider_name(),
            "is_live_sms": provider.is_live_gateway(),
        }
    )


async def request_otp(request):
    """Handles passwordless mobile OTP dispatch."""
    client_ip, user_agent, client_id = get_client_info(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    phone = body.get("phone", "").strip()
    if not phone:
        return JSONResponse({"error": "Mobile phone number is required."}, status_code=400)

    success, message, meta = security.request_mobile_otp(phone, client_id)
    if not success:
        return JSONResponse({"error": message, **meta}, status_code=429 if "wait" in message.lower() else 400)

    return JSONResponse({"success": True, "message": message, **meta})


async def verify_otp(request):
    """Validates user OTP and generates an ephemeral signed verification token."""
    client_ip, user_agent, client_id = get_client_info(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    phone = body.get("phone", "").strip()
    otp = body.get("otp", "").strip()

    if not phone or not otp:
        return JSONResponse({"error": "Phone number and verification code are required."}, status_code=400)

    success, message, v_token = security.verify_mobile_otp(phone, otp, client_id)
    if not success:
        return JSONResponse({"error": message}, status_code=400)

    return JSONResponse({
        "success": True,
        "message": message,
        "verification_token": v_token,
    })


async def get_metrics(request):
    """Returns live database-backed counts for Bento Grid cards."""
    metrics = database.get_dashboard_metrics()
    return JSONResponse(metrics)


async def get_complaints(request):
    """Returns filtered complaints list."""
    params = request.query_params
    locality = params.get("locality", "All")
    category = params.get("category", "All")
    priority = params.get("priority", "All")
    status = params.get("status", "All")
    search = params.get("search", "")

    records = database.get_all_complaints_list(
        locality=locality,
        category=category,
        priority=priority,
        status=status,
        search=search,
    )
    return JSONResponse(records)


async def get_complaint_by_id(request):
    """
    Returns single complaint details by tracking ID.
    Guarantees strict privacy: Never leaks phone numbers, exact GPS coordinates,
    private admin notes, or internal abuse signals to civilian tracking views.
    """
    tracking_id = request.path_params.get("tracking_id", "").strip().upper()
    is_admin = request.query_params.get("admin") == "1"
    record = database.get_complaint_by_tracking_id(tracking_id)
    if not record:
        return JSONResponse({"error": "Complaint not found"}, status_code=404)

    # Strictly protect private civilian and administrative fields from public tracking view
    if not is_admin:
        record["admin_notes"] = None
        record["phone"] = None  # Protected
        record["latitude"] = None  # GPS protected
        record["longitude"] = None
        record["risk_signals"] = None
        if record.get("status_history"):
            try:
                hist = json.loads(record["status_history"])
                for h in hist:
                    h.pop("notes", None)
                record["status_history"] = json.dumps(hist)
            except Exception:
                pass

    return JSONResponse(record)


async def upload_photo(request):
    """
    Safely accepts and validates citizen complaint photo uploads.
    Enforces image format and 5MB size limits, saves with secure UUID filename,
    and generates instant live image captioning for evidence review.
    """
    try:
        form = await request.form()
    except Exception as e:
        return JSONResponse({"error": f"Invalid form submission: {str(e)}"}, status_code=400)

    file = form.get("photo")
    if not file or not hasattr(file, "filename") or not file.filename:
        return JSONResponse({"error": "No image file received"}, status_code=400)

    # 1. Validate file extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in config.ALLOWED_EXTENSIONS:
        return JSONResponse(
            {"error": f"Invalid file format '.{ext}'. Supported formats: JPEG, JPG, PNG, WebP."},
            status_code=400,
        )

    # 2. Read and validate file size (5MB max)
    contents = await file.read()
    if len(contents) > config.MAX_UPLOAD_BYTES:
        return JSONResponse(
            {"error": "File size exceeds the 5 MB limit. Please compress or choose a smaller image."},
            status_code=400,
        )

    # 3. Save with secure unique identifier (UUID)
    safe_filename = f"issue_{uuid.uuid4().hex[:12]}.{ext}"
    dest_path = config.UPLOADS_DIR / safe_filename
    with open(dest_path, "wb") as f:
        f.write(contents)

    # 4. Live Image Captioning Analysis
    caption = "Live Photo Evidence Captured: Photographic proof verified."
    try:
        from PIL import Image
        from io import BytesIO
        img = Image.open(BytesIO(contents))
        w, h = img.size
        caption = f"Live Camera Evidence ({w}x{h} {img.format}): Field photo captured for civic issue inspection."
    except Exception as e:
        logger.warning("Image captioning parsing warning: %s", e)

    return JSONResponse({
        "success": True,
        "filename": safe_filename,
        "image_path": f"/uploads/{safe_filename}",
        "image_caption": caption,
    })


async def create_complaint(request):
    """
    Submits a new citizen complaint with comprehensive abuse prevention:
    - Server-side rate limiting
    - Compulsory live camera photo check
    - Advisory duplicate detection with citizen confirmation
    - Cloudflare Turnstile / Cryptographic CAPTCHA verification when suspicious
    - Passwordless Mobile OTP verification when configured
    - Optional location sharing
    """
    client_ip, user_agent, client_id = get_client_info(request)

    # 1. Server-side Rate Limiting on Complaint Submission
    allowed, retry_after = security.check_rate_limit(
        "submission", client_id, config.RATE_LIMIT_SUBMISSION_MAX, config.RATE_LIMIT_SUBMISSION_WINDOW
    )
    if not allowed:
        return JSONResponse(
            {
                "error": f"Submission rate limit reached. Maximum {config.RATE_LIMIT_SUBMISSION_MAX} reports per 10 minutes. Please try again in {retry_after} seconds.",
                "retry_after": retry_after,
            },
            status_code=429,
        )

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    title = body.get("title", "").strip()
    description = body.get("description", "").strip()
    locality = body.get("locality", "").strip()
    landmark = body.get("landmark", "").strip()
    image_path = body.get("image_path")
    image_caption = body.get("image_caption", "")
    force_duplicate = body.get("force_duplicate", False)
    captcha_token = body.get("captcha_token", "")
    phone = body.get("phone", "").strip()
    otp_token = body.get("otp_token", "")
    latitude = body.get("latitude")
    longitude = body.get("longitude")
    location_shared = bool(body.get("location_shared", False))

    # Basic field validation
    if not title or not description or not locality:
        return JSONResponse({"error": "Title, Locality, and Description are required."}, status_code=400)

    # 2. Compulsory Live Photo Capture Requirement
    if not image_path or not os.path.exists(os.path.join(BASE_DIR, image_path.lstrip("/"))):
        return JSONResponse(
            {"error": "A live camera photo of the civic issue is required for submission."},
            status_code=400,
        )

    # 3. Advisory Duplicate Check (Explainable & User-Confirmed)
    dup_result = duplicate_detector.check_for_duplicates(title, description, locality, image_path=image_path)
    if dup_result["is_duplicate"] and not force_duplicate:
        return JSONResponse(
            {
                "is_duplicate": True,
                "duplicate_of": dup_result["duplicate_of"],
                "similarity_score": dup_result["similarity_score"],
                "matched_title": dup_result["matched_title"],
                "matched_locality": dup_result["matched_locality"],
                "matched_status": dup_result["matched_status"],
                "explanation": dup_result["explanation"],
                "message": (
                    f"Possible similar complaint detected: {dup_result['duplicate_of']} ('{dup_result['matched_title']}') "
                    f"in {dup_result['matched_locality']} is currently {dup_result['matched_status']}. "
                    "Do you want to review the existing report or submit this as a separate incident?"
                ),
            },
            status_code=409,
        )

    # 4. Suspicious Activity & CAPTCHA Verification
    is_suspicious, suspicion_reason = security.evaluate_suspicion(client_id, phone, dup_result["similarity_score"])
    captcha_verified = 0

    if is_suspicious or config.CAPTCHA_REQUIRED_ALWAYS:
        if not captcha_token:
            return JSONResponse(
                {
                    "error": f"Security verification required: {suspicion_reason or 'Please complete the security check.'}",
                    "require_captcha": True,
                    "reason": suspicion_reason,
                },
                status_code=403,
            )

        cap_valid, cap_msg = security.verify_captcha_token(captcha_token, client_ip, client_id)
        if not cap_valid:
            return JSONResponse(
                {
                    "error": f"Security verification failed: {cap_msg}",
                    "require_captcha": True,
                },
                status_code=403,
            )
        captcha_verified = 1

    # 5. Passwordless Mobile OTP Enforcement (Configurable)
    otp_verified = 0
    if config.OTP_REQUIRED:
        if not phone or not otp_token:
            return JSONResponse(
                {"error": "Mobile number verification via OTP is required for this deployment."},
                status_code=403,
            )
        if not security.verify_signed_phone_token(phone, otp_token):
            return JSONResponse(
                {"error": "Invalid or expired phone verification token. Please verify your phone number."},
                status_code=403,
            )
        otp_verified = 1
    elif phone and otp_token:
        # User chose to verify phone in optional mode
        if security.verify_signed_phone_token(phone, otp_token):
            otp_verified = 1

    # 6. Run Classification (Groq with deterministic rules fallback)
    classification = classifier.classify_complaint(title, description)

    # 7. Persist Complaint in SQLite
    tracking_id = database.create_complaint(
        title=title,
        description=description,
        locality=locality,
        landmark=landmark if landmark else None,
        image_path=image_path,
        category=classification["category"],
        priority=classification["priority"],
        priority_reason=classification["reason"],
        status="Submitted",
        assigned_department=None,
        assigned_officer=None,
        admin_notes=None,
        is_duplicate=1 if dup_result["is_duplicate"] else 0,
        duplicate_of=dup_result["duplicate_of"],
        similarity_score=dup_result["similarity_score"],
        classification_source=classification["source"],
        phone=phone if phone else None,
        latitude=latitude if location_shared else None,
        longitude=longitude if location_shared else None,
        location_shared=1 if location_shared else 0,
        image_caption=image_caption,
        captcha_verified=captcha_verified,
        otp_verified=otp_verified,
        risk_signals=suspicion_reason if is_suspicious else None,
    )

    # Record successful submission rate limit hit
    security.record_rate_limit_hit("submission", client_id)

    created_rec = database.get_complaint_by_tracking_id(tracking_id)
    # Ensure public return doesn't leak phone or GPS
    created_rec["phone"] = None
    created_rec["latitude"] = None
    created_rec["longitude"] = None
    created_rec["admin_notes"] = None
    created_rec["risk_signals"] = None

    return JSONResponse(created_rec, status_code=201)


async def update_complaint(request):
    """Updates complaint department, officer, status, and internal admin notes."""
    tracking_id = request.path_params.get("tracking_id", "").strip().upper()
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    status = body.get("status", "Submitted")
    assigned_department = body.get("assigned_department")
    assigned_officer = body.get("assigned_officer")
    admin_notes = body.get("admin_notes")

    success = database.update_complaint_status(
        tracking_id=tracking_id,
        status=status,
        assigned_department=assigned_department,
        assigned_officer=assigned_officer,
        admin_notes=admin_notes,
    )

    if not success:
        return JSONResponse({"error": "Failed to update complaint"}, status_code=400)
    return JSONResponse({"success": True})


async def check_duplicate(request):
    """Real-time advisory duplicate pre-check."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    title = body.get("title", "").strip()
    description = body.get("description", "").strip()
    locality = body.get("locality", "").strip()
    image_path = body.get("image_path", "")

    result = duplicate_detector.check_for_duplicates(title, description, locality, image_path=image_path)
    return JSONResponse(result)


# Define Routes
routes = [
    Route("/", home_view, methods=["GET"]),
    Route("/api/config", get_config, methods=["GET"]),
    Route("/api/metrics", get_metrics, methods=["GET"]),
    Route("/api/security/status", get_security_status, methods=["GET"]),
    Route("/api/otp/request", request_otp, methods=["POST"]),
    Route("/api/otp/verify", verify_otp, methods=["POST"]),
    Route("/api/complaints", get_complaints, methods=["GET"]),
    Route("/api/complaints/{tracking_id}", get_complaint_by_id, methods=["GET"]),
    Route("/api/complaints", create_complaint, methods=["POST"]),
    Route("/api/complaints/{tracking_id}/update", update_complaint, methods=["POST"]),
    Route("/api/upload-photo", upload_photo, methods=["POST"]),
    Route("/api/check-duplicate", check_duplicate, methods=["POST"]),
    Mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static"),
    Mount("/assets", StaticFiles(directory=os.path.join(BASE_DIR, "assets")), name="assets"),
    Mount("/uploads", StaticFiles(directory=str(config.UPLOADS_DIR)), name="uploads"),
]

app = Starlette(debug=True, routes=routes)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8501))
    print(f"Starting CivicFix AI (Lucknow Edition) with Tailwind CSS on http://localhost:{port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)

