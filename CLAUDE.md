# CivicFix AI — Developer & Assistant Guidance (CLAUDE.md)

## Tech Stack
- **Language**: Python 3.10+
- **Frontend / Styling**: Tailwind CSS (Utility-first CSS, Inter typography, Lucide Icons)
- **Backend / ASGI**: Starlette + Uvicorn
- **Persistence**: SQLite (embedded, parameterized queries)
- **Machine Learning**: scikit-learn (`TfidfVectorizer`, `cosine_similarity`) for advisory duplicate detection
- **LLM Integration**: Groq Python SDK (`groq` package) calling Llama-3.3-70b-versatile
- **Data Handling**: pandas

---

## Standard Run Commands

### Installation
```bash
pip install -r requirements.txt
```

### Run Application (Local)
```bash
python app.py
```
*(Starts Starlette ASGI web server on http://localhost:8501)*

### Run Application (Production / Render)
```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

### Test Security & Abuse Prevention Suite (Unit Tests)
```bash
python tests/test_security_and_abuse.py
```

### Full Acceptance & Screenshot Suite
```bash
python verify_and_capture.py
```

---

## Design System Rules (Tailwind CSS)
1. **Brand Colors**:
   - Soft White `#E8E9DF`: Canvas / page background (`bg-[#E8E9DF]`).
   - Sage Green `#A9B887`: Secondary actions, selected nav states, subtle highlights (`bg-[#A9B887]`).
   - Deep Olive `#2E3D28`: Sidebar, brand identity, headings, primary buttons (`bg-[#2E3D28]`, `text-[#2E3D28]`).
   - White `#FFFFFF`: Cards and form surfaces (`bg-white`).
2. **Typography**:
   - Inter / system sans-serif. Swiss Style left-alignment, generous whitespace, legible hierarchy.
3. **Buttons**:
   - Must not look AI-generated: No gradients, no neon glows, no sparkles, no oversized pills.
   - Primary: Solid Deep Olive, soft-white text, 8px radius (`rounded-lg`), 40–44px height, medium weight label.
   - Secondary: Sage Green tint or olive outline.
   - Human labels: "Submit complaint", "Track status", "Assign officer", "Save changes".
4. **Hero Image**:
   - Lucknow Rumi Darwaza / Bara Imambara with dark-olive overlay for readable text.
   - Rounded corners (`rounded-lg`) and "Serving Lucknow" caption. Alt text included.
5. **Priority Tags**:
   - Red for High (`bg-red-50 text-red-700 border-red-200`)
   - Amber for Medium (`bg-amber-50 text-amber-700 border-amber-200`)
   - Neutral Grey for Low (`bg-gray-100 text-gray-700 border-gray-300`)

---

## "Do Not Break" Principles
1. **SQLite Persistence**:
   - All complaint submissions, rate limits, and admin updates must persist in `civicfix.db`. Parameterized queries only.
2. **Strict Category & Priority Validation**:
   - The 8 allowed categories and 3 priorities (High, Medium, Low) must be strictly enforced.
3. **Deterministic Rule-Based Fallback**:
   - If Groq API is missing, times out (6s), or fails, the application MUST automatically fall back to rule-based classification and priority determination. The app must never crash, hang, or display a broken screen.
4. **Advisory Duplicate Detection**:
   - Check complaints via TF-IDF cosine similarity. Flag potential duplicates advisory-only; NEVER automatically delete or merge citizen reports. Allow civilian confirmation via modal (`force_duplicate: true`).
5. **Compulsory Live Photo Evidence**:
   - Require camera evidence (`image_path`). Reject submissions with HTTP 400 if photo is omitted.
6. **Unique Tracking IDs & Public Privacy Scrub**:
   - Generated as `CF-2026-XXXX`. Public tracking screen must look up complaints cleanly and MUST strictly scrub civilian phone numbers, GPS coordinates, internal admin notes, and risk audit signals.
7. **Admin Department & Officer Updates**:
   - Admin updates must persist to SQLite and immediately reflect in the database and tracking views.
8. **Live Database Metrics**:
   - Dashboard summary cards must compute counts directly from SQLite records (never hardcoded numbers).

---

## Security, Abuse Prevention & Secret Management
- **Never hardcode API keys or secrets**.
- Always read `GROQ_API_KEY`, `TURNSTILE_SECRET_KEY`, and `SECRET_KEY` from `.env` via `config.py`.
- Call Groq and Turnstile verification **strictly from the backend**.
- **No Plaintext OTPs**: Store only salted one-way SHA-256 hashes in `otp_verifications`. Plaintext OTPs must never be persisted or logged to production files.
- **Persistent Rate Limiting**: Check client submission limits via SQLite store (`rate_limits`). Reject bursts with HTTP 429 and retry-after header.
- **Adaptive CAPTCHA**: Evaluate suspicious signals (bursts, duplicate spam, repeated failed OTPs). Never trust client-side validation; require server verification via Turnstile or signed cryptographic challenge.
- **Prototype Reality Disclaimers**:
  - Never claim complaints are submitted to real municipal authorities or emergency services.
  - Never claim camera photos, CAPTCHA, phone OTP, or browser location prove legal identity or physical incident occurrence at the captured location.
- Ensure `.env` and `*.db` are strictly ignored by `.gitignore` and never committed to version control.
