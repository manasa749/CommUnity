import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

# Database file location configuration
DB_PATH = os.environ.get("DATABASE_PATH", "community.db")

def get_db_connection():
    """Establishes connection to the SQLite database with dictionary-like row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes the database schema if tables do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            flat_number TEXT NOT NULL,
            hashed_password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # Community contacts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            designation TEXT NOT NULL,
            category TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            availability TEXT,
            is_seed INTEGER NOT NULL DEFAULT 0
        )
    """)

    # Recommendations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            contact_info TEXT,
            created_by_user_id INTEGER NOT NULL,
            created_by_name TEXT NOT NULL,
            created_date TEXT NOT NULL,
            vote_count INTEGER NOT NULL DEFAULT 0,
            is_seed INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (created_by_user_id) REFERENCES users(id)
        )
    """)

    # Recommendation votes table (one vote per user per recommendation)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendation_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recommendation_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            voted_date TEXT NOT NULL,
            UNIQUE(recommendation_id, user_id),
            FOREIGN KEY (recommendation_id) REFERENCES recommendations(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()

    _seed_contacts()
    _seed_recommendations()


def _seed_contacts():
    """Insert seed community contacts if the table is empty."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM contacts WHERE is_seed = 1")
    row = cursor.fetchone()
    if row and row["cnt"] > 0:
        conn.close()
        return

    seed_contacts = [
        ("Suresh Nair",        "Community President",        "Management",  "+91 98400 11001", "president@community.in",   "Mon–Fri, 10am–6pm", 1),
        ("Meera Krishnamurthy","Community Secretary",         "Management",  "+91 98400 11002", "secretary@community.in",   "Mon–Sat, 9am–5pm",  1),
        ("Ramesh Pillai",      "Treasurer",                  "Management",  "+91 98400 11003", "treasurer@community.in",   "Mon–Fri, 10am–4pm", 1),
        ("Anand Kumar",        "Maintenance Manager",         "Maintenance", "+91 98400 22001", "maintenance@community.in", "Mon–Sat, 8am–7pm",  1),
        ("Vijay Mohan",        "Plumbing & Electrical Lead", "Maintenance", "+91 98400 22002", None,                       "Mon–Sat, 9am–6pm",  1),
        ("Lakshmi Sundaram",   "Housekeeping Supervisor",    "Maintenance", "+91 98400 22003", None,                       "Mon–Sat, 7am–5pm",  1),
        ("Security Office",    "Main Gate Security Desk",    "Security",    "+91 98400 33001", None,                       "24 × 7",            1),
        ("Babu Thomas",        "Head of Security",           "Security",    "+91 98400 33002", "security@community.in",    "Mon–Sat, 9am–6pm",  1),
        ("KSEB Complaint Cell","Electricity Board Helpline", "Emergency",   "1800-425-0022",   None,                       "24 × 7",            1),
        ("KWA Helpline",       "Water Authority Helpline",   "Emergency",   "1916",            None,                       "24 × 7",            1),
        ("Ambulance / Police", "Emergency Services",         "Emergency",   "112",             None,                       "24 × 7",            1),
        ("Dr. Nisha Prasad",   "Nearest General Physician",  "Other",       "+91 98400 55001", None,                       "Mon–Sat, 9am–1pm",  1),
        ("Community Cab Pool", "Shared Transport Coordinator","Other",      "+91 98400 55002", "cabpool@community.in",     "7am–10pm",          1),
    ]

    cursor.executemany(
        "INSERT INTO contacts (name, designation, category, phone, email, availability, is_seed) VALUES (?,?,?,?,?,?,?)",
        seed_contacts
    )
    conn.commit()
    conn.close()


def _seed_recommendations():
    """Insert seed recommendations if the table is empty. Uses a placeholder user id = 0."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM recommendations WHERE is_seed = 1")
    row = cursor.fetchone()
    if row and row["cnt"] > 0:
        conn.close()
        return

    seed_recs = [
        # (service_name, category, description, contact_info, created_by_name, created_date, vote_count)
        ("Hathway Broadband",    "Broadband",       "Reliable 200 Mbps fibre. Good customer support. Minimal downtime in the last year.", "+91 98400 41001", "Community Admin", "2024-01-10", 14),
        ("ACT Fibernet",         "Broadband",       "Fast unlimited plan. Speeds are consistent even during peak hours.", "+91 98400 41002", "Arjun Menon",     "2024-02-05", 10),
        ("Rajan Plumbing",       "Plumber",         "Very reliable. Fixed our overhead tank leak quickly. Reasonable pricing.", "+91 98400 42001", "Priya Nair",      "2024-01-20",  8),
        ("Sunil Plumbers",       "Plumber",         "Available on weekends. Handles all kinds of pipe work and fittings.", "+91 98400 42002", "Sanjay Varma",    "2024-03-15",  5),
        ("Bright Electricals",   "Electrician",     "Handled full wiring for our flat renovation. Professional and clean work.", "+91 98400 43001", "Deepa Krishnan",  "2024-02-14",  9),
        ("Anoop Electric Works", "Electrician",     "Quick response for urgent calls. Good for inverter and switchboard repairs.", "+91 98400 43002", "Rohan Nambiar",   "2024-04-01",  6),
        ("Chill Zone AC Service","AC Service",      "Best in the area. They service and gas-fill efficiently. Annual contract available.", "+91 98400 44001", "Meena Suresh",    "2024-01-25", 12),
        ("Cool Air Services",    "AC Service",      "Serviced three units in one day. Very punctual and honest about spare part costs.", "+91 98400 44002", "Vikram Iyer",     "2024-03-20",  7),
        ("FixIt Appliance Care", "Appliance Repair","One-stop shop for washing machines, refrigerators, and microwaves.", "+91 98400 45001", "Ananya Thomas",   "2024-02-28",  8),
        ("HomeServe Repairs",    "Appliance Repair","Good for Samsung and LG appliances. Original spares used.", "+91 98400 45002", "Kabir Singh",     "2024-04-10",  4),
        ("CleanPro Services",    "Cleaning",        "Monthly deep-clean package for apartments. Bring their own equipment.", "+91 98400 46001", "Lakshmi Pillai",  "2024-01-18",  7),
        ("Shine Home Cleaning",  "Cleaning",        "Available on short notice. Very thorough sofa and carpet cleaning.", "+91 98400 46002", "Farhan Akhtar",   "2024-03-30",  5),
        ("Asha Maths Tuition",   "Tutor",           "Excellent for classes 6–10 maths. Kids in the community show strong improvement.", "+91 98400 47001", "Priti Sharma",    "2024-02-07",  9),
        ("Sunrise Physics Tutor","Tutor",           "IIT background. Takes +1 and +2 physics batches. Highly recommended.", "+91 98400 47002", "Raj Gopal",       "2024-04-15",  6),
        ("Dr. Home Healthcare",  "Healthcare",      "Home nursing and post-surgery care available. Certified staff.", "+91 98400 48001", "Sunita Rajan",    "2024-03-05",  8),
        ("QuickWash Laundry",    "Laundry",         "Pick-up and delivery within 48 hours. Good for bulk clothes and curtains.", "+91 98400 49001", "Aditya Menon",    "2024-01-30",  6),
        ("Fresh Wash Express",   "Laundry",         "Same-day service available. Dry-clean option for formal wear.", "+91 98400 49002", "Divya Kumar",     "2024-04-20",  3),
        ("PestShield Services",  "Other",           "Effective termite and cockroach treatment. Safe chemical formulations.", "+91 98400 50001", "Girish Nair",     "2024-02-20",  7),
        ("SecureKidz Day Care",  "Other",           "Day care for kids aged 2–6. Trusted by several families in the community.", "+91 98400 50002", "Rekha Pillai",    "2024-03-25",  5),
    ]

    cursor.executemany(
        """INSERT INTO recommendations
           (service_name, category, description, contact_info, created_by_user_id,
            created_by_name, created_date, vote_count, is_seed)
           VALUES (?,?,?,?,0,?,?,?,1)""",
        seed_recs
    )
    conn.commit()
    conn.close()


# ─── User queries ─────────────────────────────────────────────────────────────

def get_user_by_email(email: str):
    """Retrieves a user record by email address. Returns dict or None."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int):
    """Retrieves a user record by id. Returns dict or None."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def create_user(name: str, email: str, flat_number: str, hashed_password: str, role: str = "Resident"):
    """Inserts a new user record into the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, email, flat_number, hashed_password, role) VALUES (?, ?, ?, ?, ?)",
            (name.strip(), email.lower().strip(), flat_number.strip(), hashed_password, role)
        )
        conn.commit()
        user_id = cursor.lastrowid
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


# ─── Contact queries ───────────────────────────────────────────────────────────

def get_all_contacts(category: str = None, search: str = None):
    """Returns all contacts, optionally filtered by category and/or search string."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM contacts WHERE 1=1"
    params = []

    if category and category != "All":
        query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND (name LIKE ? OR designation LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like])

    query += " ORDER BY category, name"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_contact_by_id(contact_id: int):
    """Returns a single contact record by id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ─── Recommendation queries ────────────────────────────────────────────────────

def get_all_recommendations(category: str = None, search: str = None):
    """Returns all recommendations, optionally filtered by category and/or search."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM recommendations WHERE 1=1"
    params = []

    if category and category != "All":
        query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND (service_name LIKE ? OR description LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like])

    query += " ORDER BY vote_count DESC, created_date DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recommendation_by_id(rec_id: int):
    """Returns a single recommendation by id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recommendations WHERE id = ?", (rec_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def create_recommendation(service_name: str, category: str, description: str,
                          contact_info: str, user_id: int, user_name: str, created_date: str):
    """Inserts a new resident-created recommendation."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO recommendations
           (service_name, category, description, contact_info, created_by_user_id,
            created_by_name, created_date, vote_count, is_seed)
           VALUES (?,?,?,?,?,?,?,0,0)""",
        (service_name.strip(), category.strip(), description.strip(),
         contact_info.strip() if contact_info else None, user_id, user_name, created_date)
    )
    conn.commit()
    rec_id = cursor.lastrowid
    cursor.execute("SELECT * FROM recommendations WHERE id = ?", (rec_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def has_user_voted(rec_id: int, user_id: int) -> bool:
    """Returns True if the given user has already voted for this recommendation."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM recommendation_votes WHERE recommendation_id = ? AND user_id = ?",
        (rec_id, user_id)
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None


def upvote_recommendation(rec_id: int, user_id: int, voted_date: str):
    """
    Casts one vote from user_id for rec_id.
    Returns the updated recommendation, or None if the user already voted.
    """
    if has_user_voted(rec_id, user_id):
        return None

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO recommendation_votes (recommendation_id, user_id, voted_date) VALUES (?,?,?)",
            (rec_id, user_id, voted_date)
        )
        cursor.execute(
            "UPDATE recommendations SET vote_count = vote_count + 1 WHERE id = ?",
            (rec_id,)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return None
    conn.close()
    return get_recommendation_by_id(rec_id)


def get_user_votes(user_id: int) -> list:
    """Returns list of recommendation IDs that the user has already voted for."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT recommendation_id FROM recommendation_votes WHERE user_id = ?",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [r["recommendation_id"] for r in rows]


# Proactively initialize database tables on import
init_db()
