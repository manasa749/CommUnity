import sqlite3
import os

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
    conn.commit()
    conn.close()

def get_user_by_email(email: str):
    """Retrieves a user record by email address. Returns dict or None."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

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
        # IntegrityError is raised on unique constraint violation (duplicate email)
        return None
    finally:
        conn.close()

# Proactively initialize database tables on import
init_db()
