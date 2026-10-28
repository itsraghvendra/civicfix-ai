# CivicFix AI — Lucknow Civic Grievance Management System

> **"Together, Let's Make Lucknow Better."**

CivicFix AI is an enterprise-grade civic complaint management platform built with **Tailwind CSS** and a high-performance **Python / Starlette** backend for the **Lucknow Municipal Corporation (LMC)** and the residents of Lucknow. It empowers citizens to submit civic grievances (potholes, sanitation issues, leaking water lines, dark streetlights) **without requiring mandatory account creation**, provides transparent AI classification and priority recommendations, flags possible duplicate reports, and provides real-time public status tracking alongside a municipal officer workspace.

This edition introduces an end-to-end **Abuse Prevention, Security & Privacy Architecture**:
1. **Adaptive CAPTCHA & Suspicious-Activity Detection** (Cloudflare Turnstile + Cryptographic Fallback)
2. **Server-Side Persistent Rate Limiting** (Configurable SQLite token bucket / sliding window)
3. **Advisory Duplicate Complaint Checks** (Similarity detection with civilian confirmation modal)
4. **Configurable Passwordless Mobile OTP** (Pluggable SMS Provider Adapters, salted one-way hashing)
5. **Compulsory Live Photo Evidence** (In-browser camera stream with live image captioning)
6. **Optional Location Sharing & Public Privacy Redaction** (Strict zero-leakage public tracking)

---

## 🌿 Earthy Nature-Inspired Civic Design System (Tailwind CSS)

CivicFix AI features a bespoke, accessible design system styled entirely with **Tailwind CSS**:
- **Soft White (`#E8E9DF`)**: Natural, low-strain canvas background (`bg-[#E8E9DF]`).
- **Sage Green (`#A9B887`)**: Subtle highlights, selected navigation states, secondary action accents (`bg-[#A9B887]`, `border-[#A9B887]`).
- **Deep Olive (`#2E3D28`)**: Institutional authority, sidebar base, key headings, primary buttons (`bg-[#2E3D28]`, `text-[#2E3D28]`).
- **Pure White (`#FFFFFF`)**: High-legibility card and form surfaces (`bg-white`).
- **Human Buttons**: Solid 8px radius (`rounded-lg`), 42px height (`h-[42px]`), clear focus rings, and direct labels (*"Submit complaint"*, *"Track status"*, *"Assign officer"*). No neon glows, sparkles, or oversized pills.
- **Lucknow Heritage Hero**: Historic Rumi Darwaza hero image with a dark-olive overlay, rounded corners, and a *"📍 Serving Lucknow"* badge.
- **Semantically Distinct Priorities**: High (Red `bg-red-50 text-red-700`), Medium (Amber `bg-amber-50 text-amber-700`), Low (Neutral Grey `bg-gray-100 text-gray-700`) ensuring instant cognitive recognition.

---

## 🛡️ Abuse Prevention & Security Architecture

### 1. Adaptive CAPTCHA & Suspicious-Activity Detection
- **Frictionless Normal Flow**: Genuine civilians who submit normal reports, capture live photos, and do not trigger burst patterns are never bothered with CAPTCHAs.
- **Suspicion Engine**: The backend evaluates incoming submissions for suspicious signals:
  - Rapid bursts from the same client identifier (>= 4 requests in 60 seconds).
  - High similarity with existing complaints.
  - Repeated failed OTP verification attempts (>= 3 failures).
  - Flagged or abusive IP addresses.
- **Cloudflare Turnstile Integration**: Validates Turnstile tokens via Cloudflare's server-side `siteverify` endpoint using `TURNSTILE_SECRET_KEY`. Client-side tokens are never trusted blindly.
- **Zero-Dependency Cryptographic Fallback**: When Turnstile keys are unconfigured (e.g. offline testing or local hackathon demo), the system automatically issues a signed cryptographic arithmetic challenge (`CRYPTO:timestamp:hash`). This ensures abuse protection is never disabled even without external cloud services.

### 2. Server-Side Rate Limiting
- **Persistent SQLite Rate Limit Store**: Stored in `rate_limits` table with automatic index cleanup.
- **Privacy-Conscious Client Identifiers**: Keys are generated using a salted SHA-256 hash of client IP, User-Agent, and server `SECRET_KEY` (`compute_client_id`), preventing storage of raw identifying metadata.
- **Configurable Thresholds**:
  - `RATE_LIMIT_SUBMISSION_MAX=5` per 10 minutes (`RATE_LIMIT_SUBMISSION_WINDOW=600`).
  - `RATE_LIMIT_OTP_REQUEST_MAX=3` per 15 minutes (`RATE_LIMIT_OTP_WINDOW=900`).
  - `RATE_LIMIT_OTP_VERIFY_MAX=5` per 15 minutes.
- **Clear User Messaging**: On HTTP 429, the system returns a polite, transparent notification detailing the maximum limit and exact seconds remaining before a retry is permitted.

### 3. Advisory Duplicate Complaint Checks
- **Pre-Submission Vector Match**: Evaluates title, description, category, locality, and image signals using TF-IDF and cosine similarity against recent active records.
- **Non-Destructive Civilian Modal**: Rather than automatically rejecting, deleting, or merging citizen grievances, the app displays an advisory modal with matching incident details, status, and tracking ID.
- **Informed Choice**: Civilians can choose to track the existing incident or click *"Submit as Separate Incident"* (`force_duplicate: true`), which requires step-up security verification.

### 4. Configurable Passwordless Mobile OTP
- **Account-Free Verification**: Civilians can verify their phone number via a 6-digit one-time code without creating a permanent account or password.
- **Configurable Requirement**: Governed by `OTP_REQUIRED` in `.env` (set to `false` for prototype evaluation, `true` for strict verification).
- **Pluggable SMS Provider Adapter Hierarchy**:
  - `DemoSMSProvider`: Local development and evaluation mode. Logs masked phone numbers and codes to the backend terminal; never simulates fake SMS success.
  - `TwilioSMSProvider`: Production-ready SMS delivery via Twilio API.
  - `Fast2SMSSMSProvider`: Production-ready SMS delivery via Fast2SMS (Indian carrier route).
  - `DisabledSMSProvider`: Explicitly disables SMS delivery when credentials are absent.
- **Cryptographic Security**:
  - Cryptographically secure 6-digit OTPs via Python `secrets`.
  - Stored strictly as **salted SHA-256 one-way hashes**; plaintext OTPs are never saved or logged in the database.
  - 300-second expiry (`OTP_EXPIRY_SECONDS=300`).
  - 3-attempt lockout invalidating the code.
  - Signed HMAC-SHA256 verification token issued upon success (`verification_token`), valid for 30 minutes.

### 5. Compulsory Live Photo Capture & Image Captioning
- **Live Camera Stream**: Interactive HTML5 viewfinder using `navigator.mediaDevices.getUserMedia` with fallback to rear camera (`capture="environment"`).
- **Compulsory Validation**: Forms submitted without a captured photo are rejected (HTTP 400).
- **Automatic Live Image Captioning**: Photo metadata and visual parameters are analyzed upon upload to generate an explanatory evidence caption.

### 6. Location Sharing & Zero-Leakage Privacy
- **Optional GPS Sharing**: Civilians may opt-in to attach their browser coordinates (`navigator.geolocation`).
- **Strict Public Privacy Redaction**: Public tracking endpoints (`GET /api/complaints/{id}`) strictly redact:
  - Phone numbers (`phone`)
  - Exact GPS coordinates (`latitude`, `longitude`)
  - Internal administrative notes (`admin_notes`)
  - Internal risk signals and audit flags (`risk_signals`)
- **Authorized Municipal Dispatch**: Coordinates and verified phone numbers are visible exclusively to authorized municipal officers in the Admin Portal for field dispatch.

---

## 🚀 Key Features

### 1. Citizen Homepage (Default View)
- Opens to the civilian homepage by default for Lucknow residents.
- Hero section with Lucknow's Rumi Darwaza, Soft White typography, and *"📍 Serving Lucknow"* badge.
- Tagline: *"Together, Let's Make Lucknow Better."*
- Motivation section: *"Small Reports. Better Streets. Stronger Communities."* with 3 feature cards (*Notice It*, *Report It*, *Track It*).
- **Lucknow Visual Gallery**: 4 balanced cards featuring authentic photography of **Rumi Darwaza**, **Bara Imambara**, **Gomti Riverfront**, and **Janeshwar Mishra Park**.
- 8 supported civic grievance categories with descriptions.
- 4-step *"How It Works"* progression.
- Transparent prototype disclaimer and civic privacy guarantee.

### 2. Complaint Submission Form
- **Immediate Danger Banner**: Advises citizens to dial 112 for urgent life-safety perils.
- **Dual Locality Input**: Dropdown of 13 primary Lucknow neighborhoods plus write-in landmark or manual locality entry.
- **Compulsory Live Photo Capture**: In-browser camera viewfinder, photo capture, preview, and image caption generator.
- **Optional Passwordless Mobile OTP**: Input field, 60-second cooldown timer, 300-second code expiry, and verification badge.
- **Optional Geolocation**: One-click coordinate attachment with privacy disclosure.
- **Advisory Duplicate Warning**: Modal interface allowing users to view existing reports or proceed with duplicate submission.
- **Backend Classification**: Powered by Groq API (Llama-3.3-70b-versatile) with automatic fallback to deterministic civic rules.
- **Transparent Priority Explanation**: Displays a plain-language reason for why a priority was assigned.
- Unique Tracking ID generation (e.g. `CF-2026-1048`).

### 3. Public Complaint Tracking
- Search complaints by unique Tracking ID format `CF-2026-XXXX`.
- Demo ID quick-chips for 1-click testing (`CF-2026-1001`, `CF-2026-1003`, etc.).
- **Visual Progress Timeline**: Step indicator showing progression (*Submitted → In Review → In Progress → Resolved*).
- Attached photo viewer for resident-submitted evidence.
- Assigned municipal department and designated field officer visibility.
- **Strict Privacy Standard**: Citizen contact details, GPS coordinates, and administrative notes are strictly stripped.

### 4. Municipal Officer Workspace (Admin Portal)
- Distinct administrative experience secured by a demo access gate (`admin123`).
- **Bento Grid Summary Cards**: Live SQLite-backed metrics for Total Reports, Submitted, In Review, In Progress, and Resolved.
- Multi-dimensional filtering by Locality, Category, Priority, and Status, plus full-text registry search.
- **Grievance Action Inspector**: Comprehensive complaint breakdown, attached photo inspection with full-size preview link, verified contact information, and dispatch coordinates.
- **Department Dispatch & Officer Assignment**: Assign issues to 7 Lucknow municipal departments and record assigned engineers.
- **Internal Administrative Notes & Audit Trail**: Save internal notes and view complete chronological status change history.

---

## 🛠 Tech Stack

- **Frontend Styling**: Tailwind CSS (with bespoke brand palette extension)
- **Icons**: Lucide Icons
- **Backend Server**: Starlette + Uvicorn (Fast ASGI)
- **Database**: SQLite3 (persistent with parameterized queries)
- **Natural Language Processing**: Groq Cloud Python SDK (`groq`)
- **Machine Learning**: `scikit-learn` (`TfidfVectorizer`, `cosine_similarity`)
- **Data Manipulation**: `pandas`
- **Configuration & Security**: `python-dotenv`, `hashlib`, `hmac`, `secrets`
- **Image Processing**: `pillow`

---

## ⚡ Groq API Integration & Deterministic Fallback

CivicFix AI uses Groq's high-speed inference engine with **Llama-3.3-70b-versatile** to classify complaint categories and provide transparent priority rationale.

### Resilient Fallback Architecture:
- The Groq API key is read solely on the backend from `GROQ_API_KEY` in `.env`. It is never hardcoded or exposed to client code.
- A **strict 6.0-second timeout** prevents any UI freeze or infinite wait.
- Strict response validation ensures the category matches one of the 8 allowed categories and priority is one of `High`, `Medium`, or `Low`.
- **Zero-Failure Guarantee**: If `GROQ_API_KEY` is missing, the API times out, or the LLM returns invalid output, the system seamlessly engages the **deterministic rule-based classification engine**. The complaint is saved cleanly to SQLite with full priority justification, ensuring **no crashes, no broken screens, and 100% operational continuity**.

---

## 📦 Setup & Installation

### 1. Clone or Open Workspace
```bash
cd c:\Users\yadav\Desktop\hackfest
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Key configuration settings in `.env`:
```env
# AI Classification
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Cloudflare Turnstile CAPTCHA (Optional - falls back to Cryptographic challenge)
TURNSTILE_SITE_KEY=
TURNSTILE_SECRET_KEY=
CAPTCHA_REQUIRED_ALWAYS=false

# Rate Limiting
RATE_LIMIT_SUBMISSION_MAX=5
RATE_LIMIT_SUBMISSION_WINDOW=600

# Mobile OTP Verification (Optional for prototype)
OTP_REQUIRED=false
OTP_EXPIRY_SECONDS=300
OTP_MAX_ATTEMPTS=3
SMS_PROVIDER=demo

# Server Secret Key
SECRET_KEY=civicfix_secret_key_change_in_production
```

---

## 🏃‍♂️ How to Run

Launch the application locally:
```bash
python app.py
```
Open your browser at `http://localhost:8501`.

---

## ☁️ Deploying on Render (render.com)

CivicFix AI is production-ready for **Render** using either **Render Blueprints** or manual Web Service creation.

### Option A: 1-Click Blueprint Deploy (Recommended)
Because a [`render.yaml`](file:///c:/Users/yadav/Desktop/hackfest/render.yaml) is included in the root directory:
1. Push your project to a GitHub repository.
2. In the [Render Dashboard](https://dashboard.render.com), click **New +** -> **Blueprint**.
3. Connect your repository.
4. Render automatically parses `render.yaml`, configures the Python runtime, build command, start command, and prompts for `GROQ_API_KEY`.
5. Click **Apply**.

### Option B: Manual Web Service Setup
1. Push your project code to GitHub or GitLab.
2. In the [Render Dashboard](https://dashboard.render.com), click **New +** -> **Web Service**.
3. Select your repository.
4. Configure the settings:
   - **Environment**: `Python 3`
   - **Region**: Choose the closest region (e.g. *Singapore* or *Frankfurt*)
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free
5. In **Advanced -> Environment Variables**, add:
   - `PYTHON_VERSION`: `3.11.9`
   - `GROQ_API_KEY`: *Your Groq API key* (optional; automatic fallback engages if empty)
   - `GROQ_MODEL`: `llama-3.3-70b-versatile`
   - `SECRET_KEY`: *Any random string for token signing*
   - `OTP_REQUIRED`: `false`
   - `SMS_PROVIDER`: `demo`
6. Click **Create Web Service**. Once built, your app will be live at `https://<your-service-name>.onrender.com`.

> [!NOTE]
> - **Port Handling**: Render dynamically assigns a port via `$PORT`. Both `uvicorn app:app --host 0.0.0.0 --port $PORT` and `python app.py` automatically bind to this port.
> - **Client IP behind Proxy**: [`get_client_info`](file:///c:/Users/yadav/Desktop/hackfest/app.py) in `app.py` automatically parses `X-Forwarded-For` so rate-limiting and security checks accurately track real client IPs behind Render's proxy.
> - **Storage**: On Render's Free tier, the filesystem is ephemeral. `database.init_db()` automatically recreates the SQLite database and seed records whenever the service boots or redeploys. For persistent file uploads and DB records across rebuilds, attach a Render Persistent Disk mounted to `/uploads` and the project directory.

---

## 🧪 Testing & Verification

### Run Security & Abuse Prevention Unit Tests (10 Tests)
```bash
python tests/test_security_and_abuse.py
```
*Validates rate limiting, CAPTCHA token verification, cryptographic challenge math, OTP hashing and expiry, attempt lockouts, duplicate detection advisories, SMS provider hierarchy, and public privacy scrub.*

### Run End-to-End Acceptance Suite & Screenshot Capture (10 Tests)
```bash
python verify_and_capture.py
```
*Executes full civilian journey, live camera upload, normal complaint submission, advisory duplicate handling, public privacy verification, and captures 8 fresh desktop and mobile screenshots.*

---

## 📁 Project Structure

```
hackfest/
├── app.py                      # Starlette ASGI server with REST API routes
├── config.py                   # Configuration, brand tokens, security parameters
├── database.py                 # SQLite database, parameterized queries, rate limits, OTP store
├── security.py                 # Client ID hashing, rate limiting, suspicion detection, OTP engine
├── sms_provider.py             # Abstract SMS adapter: Demo, Twilio, Fast2SMS, Disabled
├── classifier.py               # Groq API classification + deterministic rule-based fallback
├── duplicate_detector.py       # TF-IDF + Cosine similarity advisory duplicate detection
├── verify_and_capture.py       # End-to-end acceptance suite & screenshot runner
├── tests/
│   └── test_security_and_abuse.py # 10 unit & security test cases
├── templates/
│   └── index.html              # Tailwind CSS Single-Page Application
├── static/
│   ├── css/
│   │   └── styles.css          # Custom button rules, badges, and offline fallback CSS
│   └── js/
│       └── app.js              # State management, camera stream, OTP timers, CAPTCHA
├── screenshots/                # Generated desktop and mobile UI screenshots
├── assets/
│   └── lucknow_hero.jpg        # Lucknow Rumi Darwaza hero image asset
├── .env.example                # Sample environment file
├── .env                        # Local environment configuration (git ignored)
├── .gitignore                  # Git ignore rules for .env and *.db
├── README.md                   # Full project documentation
├── CLAUDE.md                   # Guidance and 'do not break' architecture rules
├── DESIGN.md                   # Complete design system tokens and typography specification
└── requirements.txt            # Python dependencies
```

---

## ⚠️ Prototype & Security Disclaimers

> [!IMPORTANT]
> **CIVICFIX AI IS A PROTOTYPE / HACKATHON DEMONSTRATOR**:
> - **No Real Municipal Dispatch**: Submissions recorded on this prototype are stored in a local demonstration database for evaluation purposes and are **NOT** dispatched to real emergency services, the Lucknow Municipal Corporation, or police authorities. In real emergencies, residents must call **112**.
> - **Evidence & Verification Limitations**: Compulsory live camera capture, Cloudflare Turnstile, mobile phone OTP, and browser location sharing significantly deter bulk automated spam and provide basic evidence. However, they **do not prove legal identity**, do not guarantee that an incident occurred at the stated time or place, and are not tamper-proof against sophisticated actors. All civic actions must be physically surveyed and confirmed by certified municipal officers.
> - **Privacy by Design**: Sensitive civilian contact details (phone numbers) and precise geolocation coordinates are strictly redacted from public tracking views and made accessible solely to authorized municipal dispatchers.
