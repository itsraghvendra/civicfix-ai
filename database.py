"""
CivicFix AI - SQLite Database Layer (Lucknow Edition)
Persistent storage, parameterized SQL queries, schema migrations, and Lucknow seed data.
"""

import sqlite3
import random
import json
from datetime import datetime, timedelta
import pandas as pd
from config import DB_PATH, ALLOWED_CATEGORIES, ALLOWED_PRIORITIES, ALLOWED_STATUSES, MUNICIPAL_DEPARTMENTS


def get_connection():
    """Returns a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes and migrates the SQLite schema for complaints."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tracking_id TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        locality TEXT NOT NULL,
        landmark TEXT,
        category TEXT NOT NULL,
        priority TEXT NOT NULL,
        priority_reason TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Submitted',
        assigned_department TEXT,
        assigned_officer TEXT,
        image_path TEXT,
        admin_notes TEXT,
        status_history TEXT,
        is_duplicate INTEGER DEFAULT 0,
        duplicate_of TEXT,
        similarity_score REAL DEFAULT 0.0,
        classification_source TEXT DEFAULT 'rules_fallback',
        phone TEXT,
        latitude REAL,
        longitude REAL,
        location_shared INTEGER DEFAULT 0,
        image_caption TEXT,
        captcha_verified INTEGER DEFAULT 0,
        otp_verified INTEGER DEFAULT 0,
        risk_signals TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # Rate limiting table for persistent multi-instance or single-instance abuse prevention
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rate_limits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT NOT NULL,
        timestamp REAL NOT NULL
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rate_limits_key_time ON rate_limits(key, timestamp);")

    # Passwordless mobile OTP store (stores ONLY salted one-way hashes, never plaintext OTPs)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS otp_verifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone_hash TEXT NOT NULL,
        hashed_otp TEXT NOT NULL,
        salt TEXT NOT NULL,
        attempts_left INTEGER DEFAULT 3,
        expires_at REAL NOT NULL,
        verified INTEGER DEFAULT 0,
        verification_token TEXT,
        created_at REAL NOT NULL
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_otp_phone_hash ON otp_verifications(phone_hash);")

    # Check and run non-destructive schema migrations
    cursor.execute("PRAGMA table_info(complaints)")
    existing_cols = [row[1] for row in cursor.fetchall()]

    new_cols = {
        "landmark": "TEXT",
        "image_path": "TEXT",
        "admin_notes": "TEXT",
        "status_history": "TEXT",
        "phone": "TEXT",
        "latitude": "REAL",
        "longitude": "REAL",
        "location_shared": "INTEGER DEFAULT 0",
        "image_caption": "TEXT",
        "captcha_verified": "INTEGER DEFAULT 0",
        "otp_verified": "INTEGER DEFAULT 0",
        "risk_signals": "TEXT",
    }
    for col, col_type in new_cols.items():
        if col not in existing_cols:
            cursor.execute(f"ALTER TABLE complaints ADD COLUMN {col} {col_type};")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracking_id ON complaints(tracking_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON complaints(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON complaints(category);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_locality ON complaints(locality);")

    conn.commit()
    conn.close()

    # Seed demo data if database is empty
    seed_demo_data()


def generate_tracking_id():
    """Generates a human-friendly unique tracking ID like CF-2026-1042."""
    conn = get_connection()
    cursor = conn.cursor()
    while True:
        num = random.randint(1001, 9999)
        tracking_id = f"CF-2026-{num}"
        cursor.execute("SELECT 1 FROM complaints WHERE tracking_id = ?", (tracking_id,))
        if not cursor.fetchone():
            conn.close()
            return tracking_id


def create_complaint(
    title: str,
    description: str,
    locality: str,
    category: str,
    priority: str,
    priority_reason: str,
    landmark: str = None,
    image_path: str = None,
    status: str = "Submitted",
    assigned_department: str = None,
    assigned_officer: str = None,
    admin_notes: str = None,
    is_duplicate: int = 0,
    duplicate_of: str = None,
    similarity_score: float = 0.0,
    classification_source: str = "rules_fallback",
    phone: str = None,
    latitude: float = None,
    longitude: float = None,
    location_shared: int = 0,
    image_caption: str = None,
    captcha_verified: int = 0,
    otp_verified: int = 0,
    risk_signals: str = None,
) -> str:
    """Inserts a new complaint into SQLite and returns the assigned tracking ID."""
    tracking_id = generate_tracking_id()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Initial history record
    initial_history = [
        {
            "status": status,
            "timestamp": now_str,
            "notes": "Citizen report logged into CIVICFIX AI prototype.",
        }
    ]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO complaints (
            tracking_id, title, description, locality, landmark, category, priority,
            priority_reason, status, assigned_department, assigned_officer, image_path,
            admin_notes, status_history, is_duplicate, duplicate_of, similarity_score,
            classification_source, phone, latitude, longitude, location_shared,
            image_caption, captcha_verified, otp_verified, risk_signals,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tracking_id,
            title.strip(),
            description.strip(),
            locality.strip(),
            landmark.strip() if landmark else None,
            category,
            priority,
            priority_reason.strip(),
            status,
            assigned_department,
            assigned_officer,
            image_path,
            admin_notes,
            json.dumps(initial_history),
            is_duplicate,
            duplicate_of,
            similarity_score,
            classification_source,
            phone.strip() if phone else None,
            latitude,
            longitude,
            1 if location_shared else 0,
            image_caption.strip() if image_caption else None,
            1 if captcha_verified else 0,
            1 if otp_verified else 0,
            risk_signals,
            now_str,
            now_str,
        ),
    )
    conn.commit()
    conn.close()
    return tracking_id


def get_complaint_by_tracking_id(tracking_id: str):
    """Retrieves a single complaint as a dictionary by tracking ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM complaints WHERE tracking_id = ?", (tracking_id.strip().upper(),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_all_complaints_list(locality=None, category=None, priority=None, status=None, search=None) -> list:
    """Fetches complaints as a list of dictionaries for clean JSON API responses."""
    conn = get_connection()
    query = "SELECT * FROM complaints WHERE 1=1"
    params = []

    if locality and locality != "All":
        query += " AND locality = ?"
        params.append(locality)

    if category and category != "All":
        query += " AND category = ?"
        params.append(category)

    if priority and priority != "All":
        query += " AND priority = ?"
        params.append(priority)

    if status and status != "All":
        if status == "In Review":
            query += " AND status IN ('In Review', 'Under Review')"
        else:
            query += " AND status = ?"
            params.append(status)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query += " AND (tracking_id LIKE ? OR title LIKE ? OR description LIKE ? OR locality LIKE ? OR landmark LIKE ?)"
        params.extend([term, term, term, term, term])

    query += " ORDER BY id DESC"

    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    result = [dict(r) for r in rows]
    conn.close()
    return result


def get_all_complaints(category=None, priority=None, status=None, search=None) -> pd.DataFrame:
    """Fetches complaints as DataFrame."""
    complaints = get_all_complaints_list(category=category, priority=priority, status=status, search=search)
    return pd.DataFrame(complaints)


def update_complaint_status(
    tracking_id: str,
    status: str,
    assigned_department: str = None,
    assigned_officer: str = None,
    admin_notes: str = None,
) -> bool:
    """Updates complaint status, department, officer assignments, and appends to status history."""
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Fetch existing status history
    cursor.execute("SELECT status_history FROM complaints WHERE tracking_id = ?", (tracking_id,))
    row = cursor.fetchone()
    history = []
    if row and row["status_history"]:
        try:
            history = json.loads(row["status_history"])
        except Exception:
            history = []

    # Append new event
    history.append({
        "status": status,
        "department": assigned_department,
        "officer": assigned_officer,
        "notes": admin_notes,
        "timestamp": now_str,
    })

    cursor.execute(
        """
        UPDATE complaints
        SET status = ?, assigned_department = ?, assigned_officer = ?, admin_notes = ?,
            status_history = ?, updated_at = ?
        WHERE tracking_id = ?
        """,
        (status, assigned_department, assigned_officer, admin_notes, json.dumps(history), now_str, tracking_id),
    )
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected


def get_dashboard_metrics() -> dict:
    """Computes live database-backed counts for Bento Grid cards."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM complaints")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Submitted'")
    submitted = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status IN ('In Review', 'Under Review')")
    in_review = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'In Progress'")
    in_progress = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Resolved'")
    resolved = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE priority = 'High' AND status != 'Resolved'")
    urgent_active = cursor.fetchone()[0]

    conn.close()

    return {
        "total": total,
        "submitted": submitted,
        "in_review": in_review,
        "pending": submitted + in_review,
        "in_progress": in_progress,
        "resolved": resolved,
        "urgent_active": urgent_active,
    }


def seed_demo_data():
    """Populates realistic demonstration complaints for Lucknow if database is empty."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM complaints")
    count = cursor.fetchone()[0]

    if count > 0:
        conn.close()
        return

    sample_reports = [
        {
            "tracking_id": "CF-2026-1001",
            "title": "Severe pothole cluster in main road near Hazratganj metro gate",
            "description": "Deep craters along the arterial road near Hazratganj metro station gate 2. Causes acute traffic gridlock during rush hours and poses severe risk of two-wheeler accidents.",
            "locality": "Hazratganj",
            "landmark": "Near Metro Gate 2 & Multi-level Parking",
            "category": "Roads & potholes",
            "priority": "High",
            "priority_reason": "High-traffic commercial arterial route with deep craters posing immediate risk of vehicular accidents and physical injury.",
            "status": "In Progress",
            "assigned_department": "Roads Maintenance Cell",
            "assigned_officer": "Er. Rajesh Verma (Zonal Assistant Engineer)",
            "days_ago": 3,
        },
        {
            "tracking_id": "CF-2026-1002",
            "title": "Uncollected community garbage dump accumulating near Patrakar Puram market",
            "description": "Overflowing secondary waste bin at Patrakar Puram intersection. Foul odor spreading to neighboring vegetable market and attracting stray animals.",
            "locality": "Gomti Nagar",
            "landmark": "Opposite Patrakar Puram Chauraha Market",
            "category": "Garbage & sanitation",
            "priority": "Medium",
            "priority_reason": "Sanitation hazard near commercial market and food stalls causing public hygiene concerns and traffic hindrance.",
            "status": "In Review",
            "assigned_department": "Solid Waste & Sanitation Division",
            "assigned_officer": "Shri D.K. Mishra (Sanitary Inspector)",
            "days_ago": 1,
        },
        {
            "tracking_id": "CF-2026-1003",
            "title": "Entire stretch of streetlights dark on Alambagh link road",
            "description": "Eight consecutive street lamps not working from Phoenix mall cut to Alambagh bus terminal. The road is pitch dark, creating serious safety hazards for pedestrians at night.",
            "locality": "Alambagh",
            "landmark": "Near Alambagh Inter-State Bus Terminal Cut",
            "category": "Streetlights",
            "priority": "High",
            "priority_reason": "Extended blackout corridor on high-transit pedestrian route posing severe crime and road safety vulnerability.",
            "status": "Submitted",
            "assigned_department": "Electrical & Street Lighting Maintenance",
            "assigned_officer": None,
            "days_ago": 0,
        },
        {
            "tracking_id": "CF-2026-1004",
            "title": "Main potable water supply pipe ruptured near Block B park",
            "description": "Underground drinking water feeder pipe burst early morning. Hundreds of gallons of clean water wasting onto street with zero pressure in residential taps.",
            "locality": "Indira Nagar",
            "landmark": "Near Sector 14 Water Tank",
            "category": "Water supply & leakage",
            "priority": "High",
            "priority_reason": "Major supply line rupture resulting in immediate loss of clean drinking water for residential community and road flooding.",
            "status": "In Progress",
            "assigned_department": "Water Supply Department (Jal Sansthan)",
            "assigned_officer": "Er. Amit Saxena (Jal Sansthan Inspector)",
            "days_ago": 2,
        },
        {
            "tracking_id": "CF-2026-1005",
            "title": "Open storm drain overflowing onto street during light rains",
            "description": "Drainage canal near Chowk heritage market is clogged with silt and plastic debris. Wastewater is backflowing into ground floor shops.",
            "locality": "Chowk",
            "landmark": "Near Gol Darwaza & Heritage Street",
            "category": "Drainage & sewage",
            "priority": "Medium",
            "priority_reason": "Blocked stormwater channel causing localized waterlogging and minor property inundation in dense market zone.",
            "status": "In Review",
            "assigned_department": "Drainage & Sewerage Network",
            "assigned_officer": "Shri S.N. Awasthi (Junior Engineer)",
            "days_ago": 4,
        },
        {
            "tracking_id": "CF-2026-1006",
            "title": "Broken swings and unmaintained walking track at Sector 4 public park",
            "description": "Metal chains on children swings are snapped with rusted edges exposed. Weeds have overgrown the senior citizen walking track.",
            "locality": "Jankipuram",
            "landmark": "Sector 4 Central Park",
            "category": "Parks & public spaces",
            "priority": "Low",
            "priority_reason": "Routine park infrastructure and landscaping upkeep without immediate life-safety peril.",
            "status": "Resolved",
            "assigned_department": "Parks & Public Spaces Division",
            "assigned_officer": "Shri P.K. Srivastava (Horticulture Officer)",
            "days_ago": 7,
        },
        {
            "tracking_id": "CF-2026-1007",
            "title": "Live electrical wire dangling from fallen branch near bus stop",
            "description": "High voltage wire loose and touching iron railing of the public bus shelter near Charbagh railway approach. Immediate hazard to commuters.",
            "locality": "Aminabad",
            "landmark": "Near Bus Stand & Railway Approach Road",
            "category": "Public safety / hazard",
            "priority": "High",
            "priority_reason": "Live high-voltage electrical cable in direct contact with public infrastructure presenting immediate electrocution danger.",
            "status": "Resolved",
            "assigned_department": "Public Safety & Hazard Response Unit",
            "assigned_officer": "Er. R.K. Tiwari (LESA Safety Officer)",
            "days_ago": 5,
        },
        {
            "tracking_id": "CF-2026-1008",
            "title": "Faded road lane markings and damaged cat-eyes on Vipin Khand curve",
            "description": "Reflective road paint has worn away and thermoplastic rumble markers are missing before the flyover ascent.",
            "locality": "Gomti Nagar",
            "landmark": "Near Vipin Khand Flyover Entry",
            "category": "Roads & potholes",
            "priority": "Low",
            "priority_reason": "Routine road furniture maintenance scheduled for standard zonal marking cycle.",
            "status": "Resolved",
            "assigned_department": "Roads Maintenance Cell",
            "assigned_officer": "Er. Rajesh Verma (Zonal Assistant Engineer)",
            "days_ago": 12,
        },
    ]

    for item in sample_reports:
        created_time = (datetime.now() - timedelta(days=item["days_ago"])).strftime("%Y-%m-%d %H:%M:%S")
        updated_time = (datetime.now() - timedelta(days=max(0, item["days_ago"] - 1))).strftime("%Y-%m-%d %H:%M:%S")
        history = [
            {"status": "Submitted", "timestamp": created_time, "notes": "Complaint logged by resident."},
            {"status": item["status"], "timestamp": updated_time, "department": item["assigned_department"], "officer": item["assigned_officer"]}
        ]

        cursor.execute(
            """
            INSERT INTO complaints (
                tracking_id, title, description, locality, landmark, category, priority,
                priority_reason, status, assigned_department, assigned_officer, image_path,
                admin_notes, status_history, is_duplicate, duplicate_of, similarity_score,
                classification_source, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 'Seeded demo record', ?, 0, NULL, 0.0, 'rules_fallback', ?, ?)
            """,
            (
                item["tracking_id"],
                item["title"],
                item["description"],
                item["locality"],
                item.get("landmark"),
                item["category"],
                item["priority"],
                item["priority_reason"],
                item["status"],
                item["assigned_department"],
                item["assigned_officer"],
                json.dumps(history),
                created_time,
                updated_time,
            ),
        )

    conn.commit()
    conn.close()
