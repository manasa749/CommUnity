#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_sqlite_to_postgres.py
One-time migration: copies every row from the local SQLite database
(backend/community.db) into the PostgreSQL database configured through
DATABASE_URL.

Safety guarantees
-----------------
* The SQLite source is opened READ-ONLY and is never modified.
* All PostgreSQL writes happen inside a single transaction.  If anything
  fails the entire transaction is rolled back; the target database is left
  unchanged.
* The script refuses to run if any of the six application tables already
  contain rows in the target database, preventing accidental duplication.
  Pass --force-overwrite to truncate and re-migrate (use with caution).
* Passwords / hashed_password values are never printed.

Usage
-----
    # From the CommUnity/backend directory:
    python migrate_sqlite_to_postgres.py

    # Or with an explicit paths override:
    python migrate_sqlite_to_postgres.py \\
        --sqlite  path/to/community.db \\
        --pg-url  postgresql://user:pass@host:5432/dbname

    # Re-run from scratch (truncates all target tables first):
    python migrate_sqlite_to_postgres.py --force-overwrite
"""

import argparse
import os
import sqlite3
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# third-party
# ---------------------------------------------------------------------------
try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.errors
except ImportError:
    sys.exit(
        "ERROR: psycopg2-binary is not installed.\n"
        "Run:  pip install psycopg2-binary"
    )

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; DATABASE_URL can be set in the shell env

# ---------------------------------------------------------------------------
# Schema DDL
# Mirrors database.py exactly.  FK constraints are added AFTER data load so
# that insertion order does not matter.
# ---------------------------------------------------------------------------

_DDL_TABLES = """
CREATE TABLE IF NOT EXISTS users (
    id               INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name             TEXT NOT NULL,
    email            TEXT UNIQUE NOT NULL,
    flat_number      TEXT NOT NULL,
    hashed_password  TEXT NOT NULL,
    role             TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contacts (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name         TEXT NOT NULL,
    designation  TEXT NOT NULL,
    category     TEXT NOT NULL,
    phone        TEXT,
    email        TEXT,
    availability TEXT,
    is_seed      INTEGER NOT NULL DEFAULT 0
);

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
    is_seed             INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS recommendation_votes (
    id                 INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    recommendation_id  INTEGER NOT NULL,
    user_id            INTEGER NOT NULL,
    voted_date         TEXT NOT NULL,
    UNIQUE(recommendation_id, user_id)
);

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
    admin_note          TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS announcements (
    id                    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title                 TEXT NOT NULL,
    content               TEXT NOT NULL,
    category              TEXT NOT NULL DEFAULT 'General',
    published_by_user_id  INTEGER NOT NULL,
    published_by_name     TEXT NOT NULL,
    published_date        TEXT NOT NULL,
    status                TEXT NOT NULL DEFAULT 'published'
);
"""

# FK constraints added after data load so insertion order does not matter.
# NOT VALID means PostgreSQL marks them without scanning existing rows;
# they are still enforced for future inserts.
_DDL_FK_STATEMENTS = [
    ("fk_rec_user",
     "ALTER TABLE recommendations "
     "ADD CONSTRAINT fk_rec_user "
     "FOREIGN KEY (created_by_user_id) REFERENCES users(id) NOT VALID"),
    ("fk_rv_rec",
     "ALTER TABLE recommendation_votes "
     "ADD CONSTRAINT fk_rv_rec "
     "FOREIGN KEY (recommendation_id) REFERENCES recommendations(id) NOT VALID"),
    ("fk_rv_user",
     "ALTER TABLE recommendation_votes "
     "ADD CONSTRAINT fk_rv_user "
     "FOREIGN KEY (user_id) REFERENCES users(id) NOT VALID"),
    ("fk_issue_user",
     "ALTER TABLE issues "
     "ADD CONSTRAINT fk_issue_user "
     "FOREIGN KEY (created_by_user_id) REFERENCES users(id) NOT VALID"),
    ("fk_ann_user",
     "ALTER TABLE announcements "
     "ADD CONSTRAINT fk_ann_user "
     "FOREIGN KEY (published_by_user_id) REFERENCES users(id) NOT VALID"),
]

# ---------------------------------------------------------------------------
# Table migration specifications
# Each entry: (table_name, ordered_column_list, identity_col_to_reset)
# ---------------------------------------------------------------------------

TABLES = [
    (
        "users",
        ["id", "name", "email", "flat_number", "hashed_password", "role"],
        "id",
    ),
    (
        "contacts",
        ["id", "name", "designation", "category", "phone", "email", "availability", "is_seed"],
        "id",
    ),
    (
        "recommendations",
        [
            "id", "service_name", "category", "description", "contact_info",
            "created_by_user_id", "created_by_name", "created_date",
            "vote_count", "is_seed",
        ],
        "id",
    ),
    (
        "recommendation_votes",
        ["id", "recommendation_id", "user_id", "voted_date"],
        "id",
    ),
    (
        "issues",
        [
            "id", "title", "description", "category", "location",
            "created_date", "updated_date", "status",
            "created_by_user_id", "created_by_name",
            "assigned_to", "attachment_ref", "admin_note",
        ],
        "id",
    ),
    (
        "announcements",
        [
            "id", "title", "content", "category",
            "published_by_user_id", "published_by_name",
            "published_date", "status",
        ],
        "id",
    ),
]

# Columns whose values must never appear in log/print output
_SENSITIVE_COLUMNS = {"hashed_password"}


# ---------------------------------------------------------------------------
# Output helpers (pure ASCII - safe on Windows cp1252 terminals)
# ---------------------------------------------------------------------------

def _banner(msg):
    sep = "-" * 60
    print("\n" + sep)
    print("  " + msg)
    print(sep)


def _ok(msg):
    print("  [OK]   " + msg)


def _warn(msg):
    print("  [WARN] " + msg, file=sys.stderr)


def _fail(msg):
    print("\n  [FAIL] ERROR: " + msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _sqlite_row_count(sqlite_conn, table):
    cur = sqlite_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM " + table)
    return cur.fetchone()[0]


def _pg_row_count(pg_cur, table):
    pg_cur.execute("SELECT COUNT(*) AS n FROM " + table)
    return pg_cur.fetchone()["n"]


def _reset_sequence(pg_cur, table, col):
    """
    After inserting rows with explicit IDs into a GENERATED ALWAYS AS IDENTITY
    column (using OVERRIDING SYSTEM VALUE), the internal sequence is NOT updated
    automatically.  This call resets the sequence to max(col)+1 so the next
    application INSERT gets a non-conflicting value.
    """
    pg_cur.execute(
        "SELECT setval("
        "  pg_get_serial_sequence(%(table)s, %(col)s),"
        "  COALESCE((SELECT MAX(" + col + ") FROM " + table + "), 0) + 1,"
        "  false"
        ")",
        {"table": table, "col": col},
    )


# ---------------------------------------------------------------------------
# Idempotency guard
# ---------------------------------------------------------------------------

def _check_target_empty(pg_cur, force):
    """
    Returns True if all target tables are empty (safe to proceed).
    If any table has rows and force=False, prints an error and returns False.
    If force=True, truncates all tables and returns True.
    """
    non_empty = []
    for table, _, _ in TABLES:
        try:
            n = _pg_row_count(pg_cur, table)
            if n > 0:
                non_empty.append((table, n))
        except Exception:
            # Table may not exist yet; DDL will create it
            pass

    if not non_empty:
        return True

    if force:
        _warn("--force-overwrite active: truncating all target tables ...")
        for table, _, _ in reversed(TABLES):
            pg_cur.execute("TRUNCATE TABLE " + table + " CASCADE")
        _warn("All target tables truncated.")
        return True

    _fail(
        "Target PostgreSQL database already contains rows.\n"
        "       Tables with existing data:"
    )
    for table, n in non_empty:
        print("         * " + table + ": " + str(n) + " row(s)", file=sys.stderr)
    print(
        "\n"
        "       To re-migrate from scratch, re-run with --force-overwrite.\n"
        "       To migrate into a fresh database, create a new empty PostgreSQL\n"
        "       database first and point DATABASE_URL at it.\n",
        file=sys.stderr,
    )
    return False


# ---------------------------------------------------------------------------
# Core migration
# ---------------------------------------------------------------------------

def migrate(sqlite_path, pg_url, force=False):
    """
    Performs the full migration.  Returns True on success, False on failure.
    """
    # 1. Open SQLite (read-only)
    if not Path(sqlite_path).exists():
        _fail("SQLite source not found: " + sqlite_path)
        return False

    try:
        uri = "file:" + str(Path(sqlite_path).as_posix()) + "?mode=ro"
        sqlite_conn = sqlite3.connect(uri, uri=True)
        sqlite_conn.row_factory = sqlite3.Row
    except sqlite3.OperationalError as exc:
        _fail("Cannot open SQLite source: " + str(exc))
        return False

    # 2. Open PostgreSQL
    try:
        pg_conn = psycopg2.connect(pg_url)
        pg_conn.autocommit = False
    except psycopg2.OperationalError as exc:
        _fail("Cannot connect to PostgreSQL: " + str(exc))
        sqlite_conn.close()
        return False

    pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # 3. Create schema
        _banner("Step 1 of 4 - Ensuring PostgreSQL schema exists")
        for stmt in _DDL_TABLES.split(";"):
            stmt = stmt.strip()
            if stmt:
                pg_cur.execute(stmt)
        _ok("Schema DDL applied (CREATE TABLE IF NOT EXISTS).")

        # 4. Idempotency guard
        _banner("Step 2 of 4 - Checking target is empty")
        if not _check_target_empty(pg_cur, force):
            pg_conn.rollback()
            return False
        _ok("Target tables are empty - safe to proceed.")

        # 5. Migrate rows table by table
        _banner("Step 3 of 4 - Migrating data")
        results = []

        for table, columns, seq_col in TABLES:
            src_count = _sqlite_row_count(sqlite_conn, table)
            print("\n  [" + table + "]  source rows: " + str(src_count))

            if src_count == 0:
                _ok("No rows to migrate.")
                results.append((table, 0, 0))
                continue

            # Fetch all rows from SQLite
            sq_cur = sqlite_conn.cursor()
            col_list = ", ".join(columns)
            sq_cur.execute("SELECT " + col_list + " FROM " + table)
            rows = sq_cur.fetchall()

            # Build INSERT with explicit ID override
            placeholders = ", ".join(["%s"] * len(columns))
            insert_sql = (
                "INSERT INTO " + table + " (" + col_list + ") "
                "OVERRIDING SYSTEM VALUE "
                "VALUES (" + placeholders + ")"
            )

            # Convert sqlite3.Row -> plain tuple (preserving None for NULLs)
            data = [tuple(row[c] for c in columns) for row in rows]

            pg_cur.executemany(insert_sql, data)

            # Reset the IDENTITY sequence so future app inserts don't conflict
            _reset_sequence(pg_cur, table, seq_col)

            dst_count = _pg_row_count(pg_cur, table)
            status = "OK" if dst_count == src_count else "MISMATCH"
            print("       target rows after insert: " + str(dst_count) + "  " + status)
            results.append((table, src_count, dst_count))

        # 6. FK constraints
        _banner("Step 4 of 4 - Adding foreign-key constraints")
        for constraint_name, stmt in _DDL_FK_STATEMENTS:
            try:
                pg_cur.execute(stmt)
                _ok(constraint_name + " added.")
            except psycopg2.errors.DuplicateObject:
                conn = pg_cur.connection
                conn.rollback()
                # Recreate cursor after rollback
                pg_cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                _warn(constraint_name + " already exists - skipped.")

        # 7. Commit
        pg_conn.commit()
        _banner("Migration complete - COMMITTED")

        # 8. Print summary
        all_ok = True
        header = "  {:<28}  {:>8}  {:>8}  {}".format(
            "Table", "Source", "Target", "Status"
        )
        sep = "  " + "-" * 28 + "  " + "-" * 8 + "  " + "-" * 8 + "  " + "-" * 10
        print("\n" + header)
        print(sep)
        for table, src, dst in results:
            ok = src == dst
            all_ok = all_ok and ok
            flag = "OK" if ok else "MISMATCH"
            print("  {:<28}  {:>8}  {:>8}  {}".format(table, src, dst, flag))
        print()

        if all_ok:
            print("  [OK] All row counts match. Migration successful.\n")
        else:
            _fail("Row count mismatch detected. Review output above.\n")

        return all_ok

    except Exception as exc:
        _fail(
            "Unexpected error - rolling back PostgreSQL transaction.\n"
            "       " + str(exc)
        )
        try:
            pg_conn.rollback()
            print(
                "       PostgreSQL transaction rolled back."
                "  Source database unchanged.",
                file=sys.stderr,
            )
        except Exception:
            pass
        return False

    finally:
        try:
            pg_cur.close()
            pg_conn.close()
        except Exception:
            pass
        try:
            sqlite_conn.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser():
    parser = argparse.ArgumentParser(
        description="Migrate CommUnity SQLite database to PostgreSQL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python migrate_sqlite_to_postgres.py\n"
            "  python migrate_sqlite_to_postgres.py --sqlite path/to/community.db"
            " --pg-url postgresql://user:pass@host:5432/dbname\n"
            "  python migrate_sqlite_to_postgres.py --force-overwrite\n"
        ),
    )
    parser.add_argument(
        "--sqlite",
        default=str(Path(__file__).parent / "community.db"),
        metavar="PATH",
        help=(
            "Path to the SQLite source database "
            "(default: community.db next to this script)."
        ),
    )
    parser.add_argument(
        "--pg-url",
        default=None,
        metavar="DSN",
        help=(
            "PostgreSQL connection string. "
            "Defaults to the DATABASE_URL environment variable."
        ),
    )
    parser.add_argument(
        "--force-overwrite",
        action="store_true",
        help=(
            "DANGER: truncate all target tables and re-migrate from scratch. "
            "Use only when you are certain the target data can be discarded."
        ),
    )
    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()

    pg_url = args.pg_url or os.environ.get("DATABASE_URL")
    if not pg_url:
        parser.error(
            "PostgreSQL connection string is required. "
            "Set DATABASE_URL or pass --pg-url."
        )

    sqlite_path = args.sqlite

    # Mask the URL for display (hide password)
    try:
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(pg_url)
        netloc = (parsed.username or "") + ":***@" + (parsed.hostname or "")
        if parsed.port:
            netloc += ":" + str(parsed.port)
        display_url = urlunparse(parsed._replace(netloc=netloc))
    except Exception:
        display_url = "<connection string>"

    _banner("CommUnity - SQLite to PostgreSQL Migration")
    print("  Source (SQLite) : " + str(sqlite_path))
    print("  Target (PG)     : " + display_url)
    if args.force_overwrite:
        print("  Mode            : FORCE OVERWRITE (existing data will be deleted)")
    else:
        print("  Mode            : Safe (aborts if target tables are non-empty)")
    print()

    success = migrate(sqlite_path, pg_url, force=args.force_overwrite)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
