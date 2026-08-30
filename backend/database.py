import os
import queue
import threading
from dotenv import load_dotenv
import pg8000.dbapi
from google.cloud.sql.connector import Connector

load_dotenv()

# ---------------------------------------------------------------------------
# Cloud SQL Python Connector — connection pool
# ---------------------------------------------------------------------------
# Required environment variables:
#   INSTANCE_CONNECTION_NAME  e.g. my-project:us-central1:my-instance
#   DB_NAME                   e.g. community
#   DB_USER                   e.g. community_user
#   DB_PASSWORD               the database user's password
#
# Authentication uses Application Default Credentials (ADC):
#   - Locally:  run  gcloud auth application-default login
#   - Cloud Run / GCE: the attached service account is used automatically.
#
# The connector opens an encrypted mTLS tunnel to Cloud SQL, so no public
# IP address, host, port, or DATABASE_URL is needed here.
# ---------------------------------------------------------------------------

_INSTANCE_CONNECTION_NAME = os.environ.get("INSTANCE_CONNECTION_NAME")
_DB_NAME     = os.environ.get("DB_NAME")
_DB_USER     = os.environ.get("DB_USER")
_DB_PASSWORD = os.environ.get("DB_PASSWORD")

for _var, _val in [
    ("INSTANCE_CONNECTION_NAME", _INSTANCE_CONNECTION_NAME),
    ("DB_NAME",                  _DB_NAME),
    ("DB_USER",                  _DB_USER),
    ("DB_PASSWORD",              _DB_PASSWORD),
]:
    if not _val:
        raise RuntimeError(
            f"Required environment variable '{_var}' is not set. "
            "Check your .env file or deployment configuration."
        )

# Module-level Connector instance — reused for the lifetime of the process.
_connector = Connector()


def _get_pg_connection():
    """
    Factory used by the queue pool below.
    Opens a pg8000 connection via the Cloud SQL Connector mTLS tunnel.
    pg8000 is a supported driver for the Cloud SQL Python Connector;
    psycopg2 is not.
    """
    return _connector.connect(
        _INSTANCE_CONNECTION_NAME,
        "pg8000",
        user=_DB_USER,
        password=_DB_PASSWORD,
        db=_DB_NAME,
    )


# ---------------------------------------------------------------------------
# Thread-safe connection pool backed by queue.Queue.
#
# psycopg2.pool.ThreadedConnectionPool treats `connection_factory` as a
# psycopg2 *connection subclass* and always passes a DSN string as the first
# positional argument when constructing connections.  That breaks the Cloud SQL
# Connector factory, which takes zero arguments.  A queue.Queue pool calls the
# factory correctly and is equally thread-safe.
# ---------------------------------------------------------------------------

_POOL_MAXCONN = 10
_pool_queue: queue.Queue = queue.Queue(maxsize=_POOL_MAXCONN)
_pool_lock = threading.Lock()
_pool_size = 0  # tracks how many connections have been created


def _get_pool_conn():
    """
    Returns a connection from the pool.  Creates a new one (up to MAXCONN)
    if the queue is empty; otherwise blocks until one is returned.
    """
    global _pool_size
    try:
        # Non-blocking: reuse an idle connection immediately.
        return _pool_queue.get_nowait()
    except queue.Empty:
        pass

    with _pool_lock:
        if _pool_size < _POOL_MAXCONN:
            conn = _get_pg_connection()
            _pool_size += 1
            return conn

    # Pool is full — wait for an idle connection (up to 30 s).
    return _pool_queue.get(timeout=30)


def _return_pool_conn(conn):
    """Returns a connection to the pool, closing it if it is no longer usable."""
    global _pool_size
    try:
        # pg8000 has no .closed attribute; probe with rollback instead.
        conn.rollback()          # discard any uncommitted state
        _pool_queue.put_nowait(conn)
    except Exception:
        # Connection is broken; discard it and allow a fresh one to be made.
        with _pool_lock:
            _pool_size = max(0, _pool_size - 1)
        try:
            conn.close()
        except Exception:
            pass


def get_db_connection():
    """
    Borrows a connection from the pool and attaches a ._return reference so
    callers can return it via conn._return(conn).
    The existing _close() helper calls conn.pool.putconn(conn); a thin shim on
    the returned connection preserves that interface.
    """
    conn = _get_pool_conn()
    # Provide a .pool shim with a putconn() method so _close() works unchanged.
    class _PoolShim:
        @staticmethod
        def putconn(c):
            _return_pool_conn(c)
    conn.pool = _PoolShim()
    return conn


class _DictCursor:
    """
    Wraps a pg8000 cursor so that fetched rows behave like dicts, preserving
    the existing ``row["column_name"]`` access pattern throughout the codebase.
    pg8000 returns plain tuples; this wrapper zips column names from
    cursor.description onto each row after every execute/executemany call.
    """

    def __init__(self, raw_cursor):
        self._cur = raw_cursor

    # ---- passthrough attributes the rest of the code uses ----
    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description

    # ---- execution methods ----
    def execute(self, query, params=()):
        """
        Delegates to the pg8000 cursor.  pg8000.execute() tests len(args),
        so we must never pass None — use an empty tuple for no-parameter queries.
        """
        if params is None:
            params = ()
        self._cur.execute(query, params)

    def executemany(self, query, seq):
        self._cur.executemany(query, seq)

    # ---- fetch methods — return dicts ----
    def _row_to_dict(self, row):
        if row is None:
            return None
        cols = [d[0] for d in self._cur.description]
        return dict(zip(cols, row))

    def fetchone(self):
        return self._row_to_dict(self._cur.fetchone())

    def fetchall(self):
        if self._cur.description is None:
            return []
        cols = [d[0] for d in self._cur.description]
        return [dict(zip(cols, row)) for row in self._cur.fetchall()]


def _cursor(conn):
    """Returns a dict-row cursor for the given pg8000 connection."""
    return _DictCursor(conn.cursor())


def _close(conn):
    """Returns the connection to the pool."""
    try:
        conn.pool.putconn(conn)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def init_db():
    """Initialises the database schema if tables do not exist."""
    conn = get_db_connection()
    cursor = _cursor(conn)

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id               INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name             TEXT NOT NULL,
            email            TEXT UNIQUE NOT NULL,
            flat_number      TEXT NOT NULL,
            hashed_password  TEXT NOT NULL,
            role             TEXT NOT NULL
        )
    """)

    # Community contacts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name         TEXT NOT NULL,
            designation  TEXT NOT NULL,
            category     TEXT NOT NULL,
            phone        TEXT,
            email        TEXT,
            availability TEXT,
            is_seed      INTEGER NOT NULL DEFAULT 0
        )
    """)

    # Recommendations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            service_name        TEXT NOT NULL,
            category            TEXT NOT NULL,
            description         TEXT NOT NULL,
            contact_info        TEXT,
            created_by_user_id  INTEGER NOT NULL,
            created_by_name     TEXT NOT NULL,
            created_date        TEXT NOT NULL,
            vote_count          INTEGER NOT NULL DEFAULT 0,
            is_seed             INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (created_by_user_id) REFERENCES users(id)
        )
    """)

    # Recommendation votes table (one vote per user per recommendation)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendation_votes (
            id                 INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            recommendation_id  INTEGER NOT NULL,
            user_id            INTEGER NOT NULL,
            voted_date         TEXT NOT NULL,
            UNIQUE(recommendation_id, user_id),
            FOREIGN KEY (recommendation_id) REFERENCES recommendations(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Issues table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            title               TEXT NOT NULL,
            description         TEXT NOT NULL,
            category            TEXT NOT NULL,
            location            TEXT NOT NULL,
            created_date        TEXT NOT NULL,
            updated_date        TEXT NOT NULL,
            status              TEXT NOT NULL DEFAULT 'Open',
            created_by_user_id  INTEGER NOT NULL,
            created_by_name     TEXT NOT NULL,
            assigned_to         TEXT DEFAULT NULL,
            attachment_ref      TEXT DEFAULT NULL,
            admin_note          TEXT DEFAULT NULL,
            FOREIGN KEY (created_by_user_id) REFERENCES users(id)
        )
    """)

    # Add admin_note column to any pre-existing issues table that lacks it.
    # PostgreSQL raises sqlstate 42701 (duplicate_column) when it already exists.
    try:
        cursor.execute("ALTER TABLE issues ADD COLUMN admin_note TEXT DEFAULT NULL")
        conn.commit()
    except pg8000.dbapi.DatabaseError as exc:
        # pg8000 surfaces the sqlstate in exc.args as a dict with key 'C'.
        sqlstate = (exc.args[0] or {}).get("C", "") if exc.args else ""
        if sqlstate == "42701":   # duplicate_column — column already exists, safe to ignore
            conn.rollback()       # clear the error state before continuing
        else:
            conn.rollback()
            raise

    # Announcements table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id                    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            title                 TEXT NOT NULL,
            content               TEXT NOT NULL,
            category              TEXT NOT NULL DEFAULT 'General',
            published_by_user_id  INTEGER NOT NULL,
            published_by_name     TEXT NOT NULL,
            published_date        TEXT NOT NULL,
            status                TEXT NOT NULL DEFAULT 'published',
            FOREIGN KEY (published_by_user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    _close(conn)

    _seed_contacts()
    _seed_recommendations()


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

def _seed_contacts():
    """Insert seed community contacts if the table is empty."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    # Delete existing seed contacts to allow changes to update immediately
    cursor.execute("DELETE FROM contacts WHERE is_seed = 1")

    seed_contacts = [
        ("Suresh Nair",         "Community President",          "Management",  "+91 98400 11001", "president@community.in",   "Mon\u2013Fri, 10am\u20136pm", 1),
        ("Meera Krishnamurthy", "Community Secretary",          "Management",  "+91 98400 11002", "secretary@community.in",   "Mon\u2013Sat, 9am\u20135pm",  1),
        ("Anand Kumar",         "Maintenance Manager",          "Maintenance", "+91 98400 22001", "maintenance@community.in", "Mon\u2013Sat, 8am\u20137pm",  1),
        ("Lakshmi Sundaram",    "Housekeeping Supervisor",      "Maintenance", "+91 98400 22003", None,                       "Mon\u2013Sat, 7am\u20135pm",  1),
        ("Vijay Mohan",         "Plumbing & Electrical Lead",   "Maintenance", "+91 98400 22002", None,                       "Mon\u2013Sat, 9am\u20136pm",  1),
        ("Babu Thomas",         "Head of Security",             "Security",    "+91 98400 33002", "security@community.in",    "Mon\u2013Sat, 9am\u20136pm",  1),
        ("Security Office",     "Main Gate Security Desk",      "Security",    "+91 98400 33001", None,                       "24 \u00d7 7",                 1),
        ("Ambulance / Police",  "Emergency Services Helpline",  "Emergency",   "112",             None,                       "24 \u00d7 7",                 1),
        ("KSEB Complaint Cell", "Electricity Board Helpline",   "Emergency",   "1800-425-0022",   None,                       "24 \u00d7 7",                 1),
        ("KWA Helpline",        "Water Authority Helpline",     "Emergency",   "1916",            None,                       "24 \u00d7 7",                 1),
        ("Community Cab Pool",  "Shared Transport Coordinator", "Other",       "+91 98400 55002", "cabpool@community.in",     "7am\u201310pm",               1),
        ("Ravi Shankar",        "General Facilities Coordinator","Other",      "+91 98400 55003", "facilities@community.in",  "Mon\u2013Sat, 9am\u20136pm",  1),
    ]

    cursor.executemany(
        "INSERT INTO contacts (name, designation, category, phone, email, availability, is_seed) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        seed_contacts
    )
    conn.commit()
    _close(conn)


def _seed_recommendations():
    """Insert seed recommendations if the table is empty. Uses a placeholder user id = 0."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    cursor.execute("SELECT COUNT(*) AS cnt FROM recommendations WHERE is_seed = 1")
    row = cursor.fetchone()
    if row and row["cnt"] > 0:
        _close(conn)
        return

    seed_recs = [
        # (service_name, category, description, contact_info, created_by_name, created_date, vote_count)
        ("Hathway Broadband",    "Broadband",        "Reliable 200 Mbps fibre. Good customer support. Minimal downtime in the last year.", "+91 98400 41001", "Community Admin", "2024-01-10", 14),
        ("ACT Fibernet",         "Broadband",        "Fast unlimited plan. Speeds are consistent even during peak hours.", "+91 98400 41002", "Arjun Menon",     "2024-02-05", 10),
        ("Rajan Plumbing",       "Plumber",          "Very reliable. Fixed our overhead tank leak quickly. Reasonable pricing.", "+91 98400 42001", "Priya Nair",      "2024-01-20",  8),
        ("Sunil Plumbers",       "Plumber",          "Available on weekends. Handles all kinds of pipe work and fittings.", "+91 98400 42002", "Sanjay Varma",    "2024-03-15",  5),
        ("Bright Electricals",   "Electrician",      "Handled full wiring for our flat renovation. Professional and clean work.", "+91 98400 43001", "Deepa Krishnan",  "2024-02-14",  9),
        ("Anoop Electric Works", "Electrician",      "Quick response for urgent calls. Good for inverter and switchboard repairs.", "+91 98400 43002", "Rohan Nambiar",   "2024-04-01",  6),
        ("Chill Zone AC Service","AC Service",       "Best in the area. They service and gas-fill efficiently. Annual contract available.", "+91 98400 44001", "Meena Suresh",    "2024-01-25", 12),
        ("Cool Air Services",    "AC Service",       "Serviced three units in one day. Very punctual and honest about spare part costs.", "+91 98400 44002", "Vikram Iyer",     "2024-03-20",  7),
        ("FixIt Appliance Care", "Appliance Repair", "One-stop shop for washing machines, refrigerators, and microwaves.", "+91 98400 45001", "Ananya Thomas",   "2024-02-28",  8),
        ("HomeServe Repairs",    "Appliance Repair", "Good for Samsung and LG appliances. Original spares used.", "+91 98400 45002", "Kabir Singh",     "2024-04-10",  4),
        ("CleanPro Services",    "Cleaning",         "Monthly deep-clean package for apartments. Bring their own equipment.", "+91 98400 46001", "Lakshmi Pillai",  "2024-01-18",  7),
        ("Shine Home Cleaning",  "Cleaning",         "Available on short notice. Very thorough sofa and carpet cleaning.", "+91 98400 46002", "Farhan Akhtar",   "2024-03-30",  5),
        ("Asha Maths Tuition",   "Tutor",            "Excellent for classes 6\u201310 maths. Kids in the community show strong improvement.", "+91 98400 47001", "Priti Sharma",    "2024-02-07",  9),
        ("Sunrise Physics Tutor","Tutor",            "IIT background. Takes +1 and +2 physics batches. Highly recommended.", "+91 98400 47002", "Raj Gopal",       "2024-04-15",  6),
        ("Dr. Home Healthcare",  "Healthcare",       "Home nursing and post-surgery care available. Certified staff.", "+91 98400 48001", "Sunita Rajan",    "2024-03-05",  8),
        ("QuickWash Laundry",    "Laundry",          "Pick-up and delivery within 48 hours. Good for bulk clothes and curtains.", "+91 98400 49001", "Aditya Menon",    "2024-01-30",  6),
        ("Fresh Wash Express",   "Laundry",          "Same-day service available. Dry-clean option for formal wear.", "+91 98400 49002", "Divya Kumar",     "2024-04-20",  3),
        ("PestShield Services",  "Other",            "Effective termite and cockroach treatment. Safe chemical formulations.", "+91 98400 50001", "Girish Nair",     "2024-02-20",  7),
        ("SecureKidz Day Care",  "Other",            "Day care for kids aged 2\u20136. Trusted by several families in the community.", "+91 98400 50002", "Rekha Pillai",    "2024-03-25",  5),
    ]

    cursor.executemany(
        """INSERT INTO recommendations
           (service_name, category, description, contact_info, created_by_user_id,
            created_by_name, created_date, vote_count, is_seed)
           VALUES (%s,%s,%s,%s,0,%s,%s,%s,1)""",
        seed_recs
    )
    conn.commit()
    _close(conn)


# \u2500\u2500\u2500 User queries \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def get_user_by_email(email: str):
    """Retrieves a user record by email address. Returns dict or None."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    cursor.execute("SELECT * FROM users WHERE email = %s", (email.lower().strip(),))
    row = cursor.fetchone()
    _close(conn)
    return dict(row) if row else None


def get_user_by_id(user_id: int):
    """Retrieves a user record by id. Returns dict or None."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    _close(conn)
    return dict(row) if row else None


def create_user(name: str, email: str, flat_number: str, hashed_password: str, role: str = "Resident"):
    """Inserts a new user record into the database."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    try:
        cursor.execute(
            """INSERT INTO users (name, email, flat_number, hashed_password, role)
               VALUES (%s, %s, %s, %s, %s)
               RETURNING id""",
            (name.strip(), email.lower().strip(), flat_number.strip(), hashed_password, role)
        )
        user_id = cursor.fetchone()["id"]
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except pg8000.dbapi.DatabaseError as exc:
        sqlstate = (exc.args[0] or {}).get("C", "") if exc.args else ""
        if sqlstate != "23505":   # 23505 = unique_violation
            raise
        conn.rollback()
        return None
    finally:
        _close(conn)


# \u2500\u2500\u2500 Contact queries \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def get_all_contacts(category: str = None, search: str = None):
    """Returns all contacts, optionally filtered by category and/or search string."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    query = "SELECT * FROM contacts WHERE 1=1"
    params = []

    if category and category != "All":
        query += " AND category = %s"
        params.append(category)

    if search:
        query += " AND (name ILIKE %s OR designation ILIKE %s)"
        like = f"%{search}%"
        params.extend([like, like])

    query += " ORDER BY category, name"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    _close(conn)
    return [dict(r) for r in rows]


def get_contact_by_id(contact_id: int):
    """Returns a single contact record by id."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    cursor.execute("SELECT * FROM contacts WHERE id = %s", (contact_id,))
    row = cursor.fetchone()
    _close(conn)
    return dict(row) if row else None


# \u2500\u2500\u2500 Recommendation queries \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def get_all_recommendations(category: str = None, search: str = None):
    """Returns all recommendations, optionally filtered by category and/or search."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    query = "SELECT * FROM recommendations WHERE 1=1"
    params = []

    if category and category != "All":
        query += " AND category = %s"
        params.append(category)

    if search:
        query += " AND (service_name ILIKE %s OR description ILIKE %s)"
        like = f"%{search}%"
        params.extend([like, like])

    query += " ORDER BY vote_count DESC, created_date DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    _close(conn)
    return [dict(r) for r in rows]


def get_recommendation_by_id(rec_id: int):
    """Returns a single recommendation by id."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    cursor.execute("SELECT * FROM recommendations WHERE id = %s", (rec_id,))
    row = cursor.fetchone()
    _close(conn)
    return dict(row) if row else None


def create_recommendation(service_name: str, category: str, description: str,
                          contact_info: str, user_id: int, user_name: str, created_date: str):
    """Inserts a new resident-created recommendation."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    cursor.execute(
        """INSERT INTO recommendations
           (service_name, category, description, contact_info, created_by_user_id,
            created_by_name, created_date, vote_count, is_seed)
           VALUES (%s,%s,%s,%s,%s,%s,%s,0,0)
           RETURNING id""",
        (service_name.strip(), category.strip(), description.strip(),
         contact_info.strip() if contact_info else None, user_id, user_name, created_date)
    )
    rec_id = cursor.fetchone()["id"]
    conn.commit()
    cursor.execute("SELECT * FROM recommendations WHERE id = %s", (rec_id,))
    row = cursor.fetchone()
    _close(conn)
    return dict(row) if row else None


def has_user_voted(rec_id: int, user_id: int) -> bool:
    """Returns True if the given user has already voted for this recommendation."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    cursor.execute(
        "SELECT id FROM recommendation_votes WHERE recommendation_id = %s AND user_id = %s",
        (rec_id, user_id)
    )
    row = cursor.fetchone()
    _close(conn)
    return row is not None


def toggle_vote_recommendation(rec_id: int, user_id: int, voted_date: str):
    """
    Toggles a vote: adds the vote if the user has not voted yet, or removes it
    if the user has already voted. Returns the updated recommendation dict.
    Always returns the updated recommendation (never None on a valid rec_id).
    """
    already_voted = has_user_voted(rec_id, user_id)
    conn = get_db_connection()
    cursor = _cursor(conn)
    try:
        if already_voted:
            # Remove the vote
            cursor.execute(
                "DELETE FROM recommendation_votes WHERE recommendation_id = %s AND user_id = %s",
                (rec_id, user_id)
            )
            # Decrement, but never go below 0
            cursor.execute(
                "UPDATE recommendations SET vote_count = GREATEST(0, vote_count - 1) WHERE id = %s",
                (rec_id,)
            )
        else:
            # Add the vote
            cursor.execute(
                "INSERT INTO recommendation_votes (recommendation_id, user_id, voted_date) VALUES (%s,%s,%s)",
                (rec_id, user_id, voted_date)
            )
            cursor.execute(
                "UPDATE recommendations SET vote_count = vote_count + 1 WHERE id = %s",
                (rec_id,)
            )
        conn.commit()
    except pg8000.dbapi.DatabaseError as exc:
        sqlstate = (exc.args[0] or {}).get("C", "") if exc.args else ""
        if sqlstate != "23505":   # 23505 = unique_violation
            raise
        conn.rollback()
        _close(conn)
        return get_recommendation_by_id(rec_id)
    _close(conn)
    return get_recommendation_by_id(rec_id)


def upvote_recommendation(rec_id: int, user_id: int, voted_date: str):
    """
    Casts one vote from user_id for rec_id.
    Returns the updated recommendation, or None if the user already voted.
    """
    if has_user_voted(rec_id, user_id):
        return None

    conn = get_db_connection()
    cursor = _cursor(conn)
    try:
        cursor.execute(
            "INSERT INTO recommendation_votes (recommendation_id, user_id, voted_date) VALUES (%s,%s,%s)",
            (rec_id, user_id, voted_date)
        )
        cursor.execute(
            "UPDATE recommendations SET vote_count = vote_count + 1 WHERE id = %s",
            (rec_id,)
        )
        conn.commit()
    except pg8000.dbapi.DatabaseError as exc:
        sqlstate = (exc.args[0] or {}).get("C", "") if exc.args else ""
        if sqlstate != "23505":   # 23505 = unique_violation
            raise
        conn.rollback()
        _close(conn)
        return None
    _close(conn)
    return get_recommendation_by_id(rec_id)


def get_user_votes(user_id: int) -> list:
    """Returns list of recommendation IDs that the user has already voted for."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    cursor.execute(
        "SELECT recommendation_id FROM recommendation_votes WHERE user_id = %s",
        (user_id,)
    )
    rows = cursor.fetchall()
    _close(conn)
    return [r["recommendation_id"] for r in rows]


# \u2500\u2500\u2500 Issue queries \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def get_all_issues(category: str = None, status: str = None, search: str = None, user_id: int = None):
    """Returns issues, optionally filtered by category, status, search string, or created_by_user_id."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    query = "SELECT * FROM issues WHERE 1=1"
    params = []

    if category and category != "All":
        query += " AND category = %s"
        params.append(category)

    if status and status != "All":
        query += " AND status = %s"
        params.append(status)

    if user_id:
        query += " AND created_by_user_id = %s"
        params.append(user_id)

    if search:
        query += " AND (title ILIKE %s OR description ILIKE %s OR location ILIKE %s)"
        like = f"%{search}%"
        params.extend([like, like, like])

    query += " ORDER BY created_date DESC, id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    _close(conn)
    return [dict(r) for r in rows]


def get_issue_by_id(issue_id: int):
    """Returns a single issue record by ID."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    cursor.execute("SELECT * FROM issues WHERE id = %s", (issue_id,))
    row = cursor.fetchone()
    _close(conn)
    return dict(row) if row else None


def create_issue(title: str, description: str, category: str, location: str,
                 user_id: int, user_name: str, created_date: str, attachment_ref: str = None):
    """Inserts a new issue record into the database."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    cursor.execute(
        """INSERT INTO issues
           (title, description, category, location, created_date, updated_date,
            status, created_by_user_id, created_by_name, assigned_to, attachment_ref)
           VALUES (%s, %s, %s, %s, %s, %s, 'Open', %s, %s, NULL, %s)
           RETURNING id""",
        (title.strip(), description.strip(), category.strip(), location.strip(),
         created_date, created_date, user_id, user_name, attachment_ref.strip() if attachment_ref else None)
    )
    issue_id = cursor.fetchone()["id"]
    conn.commit()
    cursor.execute("SELECT * FROM issues WHERE id = %s", (issue_id,))
    row = cursor.fetchone()
    _close(conn)
    return dict(row) if row else None


def update_issue_status_and_assignee(issue_id: int, status_val: str, assigned_to: str,
                                      updated_date: str, admin_note: str = ""):
    """Updates status, assignment, admin note, and updated_date of an issue."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    cursor.execute(
        """UPDATE issues
           SET status = %s, assigned_to = %s, updated_date = %s, admin_note = %s
           WHERE id = %s""",
        (status_val.strip(),
         assigned_to.strip() if assigned_to else None,
         updated_date,
         admin_note.strip() if admin_note else None,
         issue_id)
    )
    conn.commit()
    _close(conn)
    return get_issue_by_id(issue_id)


# \u2500\u2500\u2500 Recommendation edit / delete \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def update_recommendation_details(rec_id: int, service_name: str, category: str,
                                  description: str, contact_info: str):
    """Updates mutable fields of a recommendation. Returns updated record."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    cursor.execute(
        """UPDATE recommendations
           SET service_name = %s, category = %s, description = %s, contact_info = %s
           WHERE id = %s""",
        (service_name.strip(), category.strip(), description.strip(),
         contact_info.strip() if contact_info else None, rec_id)
    )
    conn.commit()
    _close(conn)
    return get_recommendation_by_id(rec_id)


def delete_recommendation_by_id(rec_id: int) -> bool:
    """Deletes a recommendation and its associated votes. Returns True on success."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    cursor.execute("DELETE FROM recommendation_votes WHERE recommendation_id = %s", (rec_id,))
    cursor.execute("DELETE FROM recommendations WHERE id = %s", (rec_id,))
    conn.commit()
    rows_deleted = cursor.rowcount
    _close(conn)
    return rows_deleted > 0


# \u2500\u2500\u2500 Announcement queries \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def get_all_announcements(status_filter: str = None):
    """Returns announcements ordered by date descending. Optionally filtered by status."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    query = "SELECT * FROM announcements WHERE 1=1"
    params = []
    if status_filter:
        query += " AND status = %s"
        params.append(status_filter)
    query += " ORDER BY published_date DESC, id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    _close(conn)
    return [dict(r) for r in rows]


def get_announcement_by_id(ann_id: int):
    """Returns a single announcement by id."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    cursor.execute("SELECT * FROM announcements WHERE id = %s", (ann_id,))
    row = cursor.fetchone()
    _close(conn)
    return dict(row) if row else None


def create_announcement(title: str, content: str, category: str,
                        user_id: int, user_name: str,
                        published_date: str, status: str = "published"):
    """Inserts a new announcement created by an Admin."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    cursor.execute(
        """INSERT INTO announcements
           (title, content, category, published_by_user_id, published_by_name, published_date, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           RETURNING id""",
        (title.strip(), content.strip(), category.strip(),
         user_id, user_name, published_date, status)
    )
    ann_id = cursor.fetchone()["id"]
    conn.commit()
    _close(conn)
    return get_announcement_by_id(ann_id)


def update_announcement(ann_id: int, title: str, content: str,
                        category: str, status: str):
    """Updates an announcement's content and/or status."""
    conn = get_db_connection()
    cursor = _cursor(conn)
    cursor.execute(
        """UPDATE announcements
           SET title = %s, content = %s, category = %s, status = %s
           WHERE id = %s""",
        (title.strip(), content.strip(), category.strip(), status, ann_id)
    )
    conn.commit()
    _close(conn)
    return get_announcement_by_id(ann_id)


# Proactively initialize database tables on import
init_db()
