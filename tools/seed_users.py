"""
============================================================================
FILE: seed_users.py
LOCATION: tools/seed_users.py
============================================================================

PURPOSE:
    Seed script to populate test users in Firestore for development.

ROLE IN PROJECT:
    Provides a repeatable way to seed mock or real Firestore users
    for local authentication testing and development workflows.

KEY COMPONENTS:
    - get_seed_users: Returns the seed user payloads
    - seed_mock_db: Inserts seed users into the mock Firestore client
    - seed_firestore: Inserts seed users into real Firestore

DEPENDENCIES:
    - External: None
    - Internal: api.config, api.mock_firestore

USAGE:
    python tools/seed_users.py
============================================================================
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime


def get_seed_users():
    """Return list of seed users for development."""
    now = datetime.utcnow().isoformat() + "Z"

    return [
        {
            "id": "mock-admin-001",
            "email": "admin@test.com",
            "displayName": "Test Admin",
            "role": "admin",
            "departmentId": None,
            "subjectIds": None,
            "status": "active",
            "password": "Admin123!",
            "createdAt": now,
            "updatedAt": now,
        },
        {
            "id": "mock-staff-001",
            "email": "staff@test.com",
            "displayName": "Test Staff",
            "role": "staff",
            "departmentId": "dept-cs-001",
            "subjectIds": ["subject-001", "subject-002"],
            "status": "active",
            "password": "Staff123!",
            "createdAt": now,
            "updatedAt": now,
        },
        {
            "id": "mock-student-001",
            "email": "student@test.com",
            "displayName": "Test Student",
            "role": "student",
            "departmentId": "dept-cs-001",
            "subjectIds": None,
            "status": "active",
            "password": "Student123!",
            "createdAt": now,
            "updatedAt": now,
        },
    ]


def seed_mock_db():
    """Seed users into MockFirestoreClient."""
    from api.mock_firestore import MockFirestoreClient

    db = MockFirestoreClient()
    users = get_seed_users()

    print("Seeding users to mock database...")
    for user in users:
        user_data = user.copy()
        user_id = user_data.pop("id")
        db.collection("users").document(user_id).set(user_data)
        print(f"  Created: {user['email']} ({user['role']})")

    print(f"\nSeeded {len(users)} users successfully!")
    return users


def seed_firestore():
    """Seed users into real Firestore."""
    try:
        from api.config import db

        users = get_seed_users()

        print("Seeding users to Firestore...")
        for user in users:
            user_data = user.copy()
            user_id = user_data.pop("id")
            db.collection("users").document(user_id).set(user_data)
            print(f"  Created: {user['email']} ({user['role']})")

        print(f"\nSeeded {len(users)} users successfully!")
        return users

    except Exception as e:
        print(f"Error seeding Firestore: {e}")
        print("Falling back to mock database...")
        return seed_mock_db()


def main():
    """Main entry point."""
    use_real = os.environ.get("USE_REAL_FIREBASE", "false").lower() == "true"

    if use_real:
        seed_firestore()
    else:
        seed_mock_db()


if __name__ == "__main__":
    main()
