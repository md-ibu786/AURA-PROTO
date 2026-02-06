"""
============================================================================
FILE: verify_migration.py
LOCATION: tools/verify_migration.py
============================================================================

PURPOSE:
    Verify data integrity after Firestore migration

ROLE IN PROJECT:
    Automated checks to ensure migration was successful

DEPENDENCIES:
    - External: firebase-admin
    - Internal: mock_db.json (for comparison)
============================================================================
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import firebase_admin
from firebase_admin import credentials, firestore


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MOCK_DB_PATH = PROJECT_ROOT / "mock_db.json"
DEFAULT_CREDENTIALS_PATH = PROJECT_ROOT / "serviceAccountKey-auth.json"


def resolve_service_account_path() -> Path:
    """Return the service account key path."""
    if DEFAULT_CREDENTIALS_PATH.exists():
        return DEFAULT_CREDENTIALS_PATH
    raise FileNotFoundError(
        "Service account key not found: serviceAccountKey-auth.json"
    )


class MigrationVerifier:
    """Verify Firestore migration integrity against mock data."""

    def __init__(self) -> None:
        self.db: Optional[firestore.Client] = None
        self.issues: List[str] = []

    def initialize_firebase(self) -> None:
        """Initialize Firebase Admin SDK."""
        service_account_path = resolve_service_account_path()
        if not firebase_admin._apps:
            cred = credentials.Certificate(str(service_account_path))
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()

    def load_mock_data(self) -> Dict[str, Any]:
        """Load mock data from mock_db.json."""
        if not MOCK_DB_PATH.exists():
            raise FileNotFoundError(f"mock_db.json not found: {MOCK_DB_PATH}")
        with MOCK_DB_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def verify_collection_counts(self, mock_data: Dict[str, Any]) -> bool:
        """Verify document counts match between mock and Firestore."""
        logger.info("Verifying collection counts...")
        if self.db is None:
            raise RuntimeError("Firestore client not initialized")

        all_match = True
        for collection, docs in mock_data.items():
            if not isinstance(docs, dict):
                continue
            mock_count = len(docs)
            firestore_count = len(list(self.db.collection(collection).stream()))
            if mock_count != firestore_count:
                logger.error(
                    "%s: Count mismatch - mock: %s, firestore: %s",
                    collection,
                    mock_count,
                    firestore_count,
                )
                all_match = False
            else:
                logger.info(
                    "%s: %s documents OK",
                    collection,
                    firestore_count,
                )
        return all_match

    def verify_user_schema(self) -> bool:
        """Verify user documents have required schema."""
        logger.info("Verifying user schema...")
        if self.db is None:
            raise RuntimeError("Firestore client not initialized")

        users = self.db.collection("users").stream()
        required_fields = ["uid", "email", "role", "status", "_v"]
        allowed_roles = {"admin", "staff", "student"}
        allowed_statuses = {"active", "disabled"}
        all_valid = True

        for user in users:
            data = user.to_dict()
            missing = [field for field in required_fields if field not in data]
            if missing:
                logger.error("User %s missing fields: %s", user.id, missing)
                all_valid = False
            if data.get("role") not in allowed_roles:
                logger.error(
                    "User %s has invalid role: %s",
                    user.id,
                    data.get("role"),
                )
                all_valid = False
            if data.get("status") not in allowed_statuses:
                logger.error(
                    "User %s has invalid status: %s",
                    user.id,
                    data.get("status"),
                )
                all_valid = False

        if all_valid:
            logger.info("User schema: All valid")
        return all_valid

    def _completed_migrations(
        self,
    ) -> Iterable[firestore.DocumentSnapshot]:
        """Return completed migration docs without requiring indexes."""
        if self.db is None:
            raise RuntimeError("Firestore client not initialized")
        return [
            doc
            for doc in self.db.collection("_migrations").stream()
            if doc.to_dict().get("status") == "completed"
        ]

    def verify_migration_record(self) -> bool:
        """Verify migration was recorded as completed."""
        logger.info("Verifying migration record...")
        completed_docs = list(self._completed_migrations())
        if not completed_docs:
            logger.error("No completed migration record found")
            return False

        latest = max(
            completed_docs,
            key=lambda doc: doc.to_dict().get("completed_at", ""),
        )
        data = latest.to_dict()
        logger.info("Found migration record: %s", latest.id)
        logger.info("  Started: %s", data.get("started_at"))
        logger.info("  Completed: %s", data.get("completed_at"))
        logger.info("  Stats: %s", data.get("stats"))
        return True

    def run_all_checks(self) -> bool:
        """Run all verification checks."""
        logger.info("=" * 50)
        logger.info("Starting migration verification")
        logger.info("=" * 50)

        self.initialize_firebase()
        mock_data = self.load_mock_data()

        checks = [
            ("Collection counts", self.verify_collection_counts(mock_data)),
            ("User schema", self.verify_user_schema()),
            ("Migration record", self.verify_migration_record()),
        ]

        logger.info("=" * 50)
        logger.info("Verification Results:")

        all_passed = True
        for name, passed in checks:
            status = "PASS" if passed else "FAIL"
            logger.info("  %s: %s", name, status)
            if not passed:
                all_passed = False

        logger.info("=" * 50)
        return all_passed


def main() -> int:
    """CLI entrypoint."""
    verifier = MigrationVerifier()
    try:
        if verifier.run_all_checks():
            logger.info("\nAll verification checks passed.")
            return 0
        logger.error("\nSome verification checks failed")
        return 1
    except Exception as exc:
        logger.error("Verification failed with error: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
