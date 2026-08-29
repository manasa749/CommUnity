#!/usr/bin/env python3
"""
CommUnity – Admin Setup Script
================================
Creates a new Admin user or promotes an existing user to Admin.
Run this script from the backend/ directory using the project virtual environment.

Usage
-----
  ./venv/Scripts/python create_admin.py

The script prompts for:
  - Name (skipped if the email already exists)
  - Email
  - Unit/flat number (skipped if the email already exists)
  - Password (skipped if the email already exists — existing credentials are kept)

If the email already exists the user is simply promoted to Admin without
changing their name, unit, or password.

Never hard-codes credentials; all input is collected at runtime.
"""

import sys
import getpass
import os
from dotenv import load_dotenv

load_dotenv()

# Ensure imports resolve when running from the backend/ directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db_connection, init_db, get_user_by_email, create_user
from auth_utils import hash_password


def promote_existing_user(email: str) -> dict:
    """Promote an existing user to Admin role."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = 'Admin' WHERE email = ?", (email,))
    conn.commit()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def main():
    print("=" * 50)
    print("  CommUnity – Admin Setup")
    print("=" * 50)

    # Ensure DB tables exist
    init_db()

    email = input("Email address: ").strip().lower()
    if not email:
        print("ERROR: Email is required.")
        sys.exit(1)

    existing = get_user_by_email(email)

    if existing:
        if existing["role"] == "Admin":
            print(f"\n'{email}' is already an Admin. Nothing to do.")
            sys.exit(0)

        print(f"\nUser '{existing['name']}' ({email}) found with role '{existing['role']}'.")
        confirm = input("Promote this user to Admin? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            sys.exit(0)

        result = promote_existing_user(email)
        if result:
            print(f"\nSuccess! '{result['name']}' ({email}) is now an Admin.")
        else:
            print("ERROR: Promotion failed.")
            sys.exit(1)
    else:
        print("\nNo existing user found. Creating a new Admin account.")

        name = input("Full name: ").strip()
        if not name:
            print("ERROR: Name is required.")
            sys.exit(1)

        flat_number = input("Flat / unit number: ").strip()
        if not flat_number:
            print("ERROR: Unit number is required.")
            sys.exit(1)

        password = getpass.getpass("Password (min 6 chars): ")
        if len(password) < 6:
            print("ERROR: Password must be at least 6 characters.")
            sys.exit(1)

        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("ERROR: Passwords do not match.")
            sys.exit(1)

        hashed = hash_password(password)
        new_user = create_user(name=name, email=email, flat_number=flat_number,
                               hashed_password=hashed, role="Admin")
        if new_user:
            print(f"\nSuccess! Admin account created for '{name}' ({email}).")
        else:
            print("ERROR: Could not create user. Check database connectivity.")
            sys.exit(1)


if __name__ == "__main__":
    main()
