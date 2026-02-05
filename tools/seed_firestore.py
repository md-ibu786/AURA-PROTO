"""
============================================================================
FILE: seed_firestore.py
LOCATION: tools/seed_firestore.py
============================================================================

PURPOSE:
    Migrate data from mock_db.json to Firestore with idempotency support

ROLE IN PROJECT:
    One-time migration script for initial data seeding
    Can be re-run safely (idempotent) to update existing documents

DEPENDENCIES:
    - firebase-admin
    - google-cloud-firestore
    - serviceAccountKey.json (Firebase credentials)
    - mock_db.json (source data)

USAGE:
    python tools/seed_firestore.py
    python tools/seed_firestore.py --dry-run
    python tools/seed_firestore.py --collection users
    python tools/seed_firestore.py --collection departments/{id}/semesters
    python tools/seed_firestore.py --reset
    python tools/seed_firestore.py --credentials serviceAccountKey-auth.json
============================================================================
"""
from __future__ import annotations

import argparse
import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import firebase_admin
from firebase_admin import credentials, firestore
from google.api_core import exceptions

from migration_config import (
    COLLECTIONS_WITH_ID_FIELD,
    FIELD_MAPPINGS,
    MIGRATION_SETTINGS,
    TransformContext,
    get_collection_priority,
    get_collection_type,
    get_default_values,
    get_path_id,
    get_required_fields,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MOCK_DB_PATH = PROJECT_ROOT / "mock_db.json"
DEFAULT_CREDENTIALS_PATH = PROJECT_ROOT / "serviceAccountKey.json"


@dataclass(frozen=True)
class CollectionEntry:
    """Represents a collection path and its documents from mock_db.json."""
    collection_path: str
    collection_type: str
    documents: Dict[str, Any]


class FirestoreMigrator:
    """Handles migration from mock_db.json to Firestore."""

    def __init__(
        self,
        dry_run: bool = False,
        credentials_path: Optional[Path] = None,
    ) -> None:
        self.dry_run = dry_run
        self.db: Optional[firestore.Client] = None
        self.credentials_path = credentials_path or DEFAULT_CREDENTIALS_PATH
        self.stats = {
            "created": 0,
            "updated": 0,
            "errors": 0,
            "skipped": 0,
        }
        self._pending_writes: Dict[str, str] = {}
        self._stats_lock = threading.Lock()

    def initialize_firebase(self) -> None:
        """Initialize Firebase Admin SDK."""
        if not self.credentials_path.exists():
            raise FileNotFoundError(
                "Service account key not found: "
                f"{self.credentials_path}"
            )

        if not firebase_admin._apps:
            cred = credentials.Certificate(str(self.credentials_path))
            firebase_admin.initialize_app(cred)

        self.db = firestore.client()
        logger.info("Firebase initialized successfully")

    def load_mock_data(self) -> Dict[str, Any]:
        """Load data from mock_db.json."""
        if not MOCK_DB_PATH.exists():
            raise FileNotFoundError(f"mock_db.json not found: {MOCK_DB_PATH}")

        with MOCK_DB_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        logger.info("Loaded mock data with %s top-level keys", len(data))
        return data

    def record_migration_start(self) -> str:
        """Record migration start in Firestore."""
        if self.dry_run:
            return "dry-run"

        assert self.db is not None
        migration_ref = self.db.collection("_migrations").document()
        migration_data = {
            "started_at": datetime.utcnow().isoformat(),
            "schema_version": MIGRATION_SETTINGS["schema_version"],
            "source": "mock_db.json",
            "status": "in_progress",
            "dry_run": self.dry_run,
        }
        migration_ref.set(migration_data)
        return migration_ref.id

    def record_migration_complete(self, migration_id: str) -> None:
        """Record migration completion."""
        if self.dry_run:
            return

        assert self.db is not None
        self.db.collection("_migrations").document(migration_id).update(
            {
                "completed_at": datetime.utcnow().isoformat(),
                "status": "completed",
                "stats": self.stats,
            }
        )

    def record_migration_error(self, migration_id: str, error: str) -> None:
        """Record migration error."""
        if self.dry_run:
            return

        assert self.db is not None
        self.db.collection("_migrations").document(migration_id).update(
            {
                "failed_at": datetime.utcnow().isoformat(),
                "status": "failed",
                "error": error,
                "stats": self.stats,
            }
        )

    def get_last_successful_migration(self) -> Optional[str]:
        """Return timestamp of last successful migration, if any."""
        assert self.db is not None
        try:
            docs = (
                self.db.collection("_migrations")
                .where("status", "==", "completed")
                .order_by(
                    "completed_at",
                    direction=firestore.Query.DESCENDING,
                )
                .limit(1)
                .stream()
            )
            for doc in docs:
                data = doc.to_dict()
                return data.get("completed_at")
        except exceptions.FailedPrecondition as exc:
            logger.warning(
                "Skipping migration lookup due to missing index: %s",
                exc,
            )
        return None

    def transform_document(
        self,
        collection_type: str,
        collection_path: str,
        doc_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Transform document to match Firestore schema."""
        context = TransformContext(
            collection_type=collection_type,
            collection_path=collection_path,
            doc_id=doc_id,
            path_segments=collection_path.split("/"),
        )

        mapping = FIELD_MAPPINGS.get(collection_type, {})
        drop_fields = set(mapping.get("drop", []))
        rename_fields = mapping.get("rename", {})

        transformed: Dict[str, Any] = {}
        for source_field, value in data.items():
            if source_field in drop_fields:
                continue
            dest_field = rename_fields.get(source_field, source_field)
            transformed[dest_field] = value

        additions = mapping.get("add", {})
        for field, value_or_func in additions.items():
            if callable(value_or_func):
                transformed[field] = value_or_func(data, context)
            else:
                transformed[field] = value_or_func

        if collection_type in COLLECTIONS_WITH_ID_FIELD:
            transformed["id"] = doc_id

        if collection_type == "users":
            transformed["uid"] = doc_id
            if transformed.get("departmentId") == "":
                transformed["departmentId"] = None
            subject_ids = transformed.get("subjectIds")
            if subject_ids is None:
                transformed["subjectIds"] = []
            elif isinstance(subject_ids, tuple):
                transformed["subjectIds"] = list(subject_ids)

        self._apply_path_derivations(collection_type, context, transformed)
        self._apply_defaults(collection_type, transformed)
        self._validate_required_fields(collection_type, doc_id, transformed)
        return transformed

    def _apply_defaults(
        self,
        collection_type: str,
        document: Dict[str, Any],
    ) -> None:
        defaults = get_default_values(collection_type)
        for field, value in defaults.items():
            if field not in document or document[field] in (None, ""):
                document[field] = value

    def _apply_path_derivations(
        self,
        collection_type: str,
        context: TransformContext,
        document: Dict[str, Any],
    ) -> None:
        if collection_type == "semesters" and "department_id" not in document:
            department_id = get_path_id(context.path_segments, "departments")
            if department_id:
                document["department_id"] = department_id

        if collection_type == "subjects" and "semester_id" not in document:
            semester_id = get_path_id(context.path_segments, "semesters")
            if semester_id:
                document["semester_id"] = semester_id

        if collection_type == "modules" and "subject_id" not in document:
            subject_id = get_path_id(context.path_segments, "subjects")
            if subject_id:
                document["subject_id"] = subject_id

        if collection_type == "notes":
            if "module_id" not in document:
                module_id = get_path_id(context.path_segments, "modules")
                if module_id:
                    document["module_id"] = module_id

            if "subjectId" not in document:
                subject_id = get_path_id(context.path_segments, "subjects")
                if subject_id:
                    document["subjectId"] = subject_id

            if "departmentId" not in document:
                department_id = get_path_id(
                    context.path_segments,
                    "departments",
                )
                if department_id:
                    document["departmentId"] = department_id

    def _validate_required_fields(
        self,
        collection_type: str,
        doc_id: str,
        document: Dict[str, Any],
    ) -> None:
        for field in get_required_fields(collection_type):
            if field not in document:
                raise ValueError(
                    f"Required field '{field}' missing in "
                    f"{collection_type}/{doc_id}"
                )

    def check_existing_document(
        self,
        collection_path: str,
        doc_id: str,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if document exists and return its data."""
        assert self.db is not None
        doc_ref = self.db.collection(collection_path).document(doc_id)
        doc = doc_ref.get()
        if doc.exists:
            return True, doc.to_dict()
        return False, None

    def should_update(
        self,
        existing_data: Dict[str, Any],
    ) -> bool:
        """Check if existing document should be updated."""
        existing_version = existing_data.get("_v", 0)
        current_version = MIGRATION_SETTINGS["schema_version"]

        if existing_version < current_version:
            return True

        if existing_data.get("_migrated_at"):
            return False

        return True

    def _queue_pending_write(self, doc_path: str, stat_key: str) -> None:
        """Track a pending write so stats can update on completion."""
        with self._stats_lock:
            self._pending_writes[doc_path] = stat_key

    def _increment_stat(self, stat_key: str) -> None:
        """Increment a stat counter in a thread-safe way."""
        with self._stats_lock:
            self.stats[stat_key] += 1

    def _record_write_success(self, doc_path: str) -> bool:
        """Update stats for a successful write."""
        with self._stats_lock:
            stat_key = self._pending_writes.pop(doc_path, None)
            if not stat_key:
                return False
            self.stats[stat_key] += 1
            return True

    def _record_write_failure(self, doc_path: Optional[str]) -> None:
        """Update stats for a failed write."""
        with self._stats_lock:
            if doc_path:
                self._pending_writes.pop(doc_path, None)
            self.stats["errors"] += 1

    def migrate_collection(
        self,
        collection_path: str,
        collection_type: str,
        documents: Dict[str, Any],
        bulk_writer: Any,
    ) -> None:
        """Migrate all documents in a collection path."""
        logger.info(
            "Migrating %s documents to %s",
            len(documents),
            collection_path,
        )

        for index, (doc_id, data) in enumerate(documents.items(), start=1):
            try:
                transformed = self.transform_document(
                    collection_type=collection_type,
                    collection_path=collection_path,
                    doc_id=doc_id,
                    data=data,
                )

                exists, existing = self.check_existing_document(
                    collection_path,
                    doc_id,
                )

                if exists and existing and not self.should_update(existing):
                    self._increment_stat("skipped")
                    continue

                transformed["_v"] = MIGRATION_SETTINGS["schema_version"]
                transformed["_migrated_at"] = datetime.utcnow().isoformat()
                transformed["_migration_source"] = "mock_db.json"

                stat_key = "updated" if exists else "created"
                if self.dry_run:
                    action = "update" if exists else "create"
                    logger.info(
                        "[DRY RUN] Would %s %s/%s",
                        action,
                        collection_path,
                        doc_id,
                    )
                    self._increment_stat(stat_key)
                else:
                    assert self.db is not None
                    doc_ref = self.db.collection(collection_path).document(
                        doc_id
                    )
                    bulk_writer.set(doc_ref, transformed, merge=True)
                    self._queue_pending_write(doc_ref.path, stat_key)

                if index % 100 == 0:
                    logger.info(
                        "Progress: %s/%s in %s",
                        index,
                        len(documents),
                        collection_path,
                    )

            except Exception as exc:  # pylint: disable=broad-except
                logger.error(
                    "Error processing %s/%s: %s",
                    collection_path,
                    doc_id,
                    exc,
                )
                self._increment_stat("errors")

    def _collection_entries(
        self,
        mock_data: Dict[str, Any],
        target_collection: Optional[str],
    ) -> List[CollectionEntry]:
        entries: List[CollectionEntry] = []
        for key, value in mock_data.items():
            if not isinstance(value, dict):
                logger.warning("Skipping non-dict key: %s", key)
                continue

            collection_type = get_collection_type(key)
            if not collection_type:
                logger.warning("Unknown collection key: %s", key)
                continue

            if target_collection:
                if "/" in target_collection and key != target_collection:
                    continue
                if "/" not in target_collection and \
                        collection_type != target_collection:
                    continue

            entries.append(
                CollectionEntry(
                    collection_path=key,
                    collection_type=collection_type,
                    documents=value,
                )
            )

        entries.sort(
            key=lambda entry: (
                get_collection_priority(entry.collection_type),
                entry.collection_path,
            )
        )
        return entries

    def _delete_document_recursive(self, doc_ref: Any) -> None:
        for subcollection in doc_ref.collections():
            self._delete_collection_recursive(subcollection, batch_size=50)
        doc_ref.delete()

    def _delete_collection_recursive(
        self,
        collection_ref: Any,
        batch_size: int = 50,
    ) -> None:
        docs = list(collection_ref.limit(batch_size).stream())
        for doc in docs:
            self._delete_document_recursive(doc.reference)
        if len(docs) >= batch_size:
            self._delete_collection_recursive(collection_ref, batch_size)

    def reset_data(self, target_collection: Optional[str]) -> None:
        """Delete existing data before migration (DANGEROUS)."""
        if self.dry_run:
            logger.info("Dry run mode - reset skipped")
            return

        assert self.db is not None
        confirm = input(
            "WARNING: This will DELETE data in Firestore. "
            "Type 'yes' to confirm: "
        )
        if confirm.lower() != "yes":
            logger.info("Reset cancelled")
            return

        if target_collection:
            logger.info("Resetting collection: %s", target_collection)
            if "/" in target_collection:
                collection_ref = self.db.collection(target_collection)
                self._delete_collection_recursive(collection_ref)
                return

            if target_collection == "users":
                self._delete_collection_recursive(
                    self.db.collection("users")
                )
                return

            if target_collection == "departments":
                self._delete_collection_recursive(
                    self.db.collection("departments")
                )
                return

            logger.warning("Reset skipped: unknown collection")
            return

        logger.info("Resetting users and departments")
        self._delete_collection_recursive(self.db.collection("users"))
        self._delete_collection_recursive(self.db.collection("departments"))

    def run(
        self,
        target_collection: Optional[str] = None,
        reset: bool = False,
    ) -> None:
        """Run the migration."""
        logger.info("Starting Firestore migration")
        if self.dry_run:
            logger.info("DRY RUN MODE - no changes will be made")

        self.initialize_firebase()

        last_migration = self.get_last_successful_migration()
        if last_migration:
            logger.info(
                "Last successful migration completed at: %s",
                last_migration,
            )

        migration_id = self.record_migration_start()

        try:
            if reset:
                self.reset_data(target_collection)

            mock_data = self.load_mock_data()
            entries = self._collection_entries(mock_data, target_collection)

            if not entries:
                logger.warning("No collections matched for migration")
                self.record_migration_error(
                    migration_id,
                    "No collections matched for migration",
                )
                return

            assert self.db is not None
            bulk_writer = self.db.bulk_writer()

            if hasattr(bulk_writer, "_max_batch_size"):
                bulk_writer._max_batch_size = MIGRATION_SETTINGS["batch_size"]

            def on_write_result(
                reference: Any,
                _result: Any,
                _bulk_writer_ref: Any,
            ) -> None:
                doc_path = getattr(reference, "path", None)
                if not doc_path:
                    logger.warning(
                        "Write success missing document path: %s",
                        reference,
                    )
                    return
                if not self._record_write_success(doc_path):
                    logger.warning(
                        "Write success for untracked document: %s",
                        doc_path,
                    )

            def on_write_error(
                error: Any,
                _bulk_writer_ref: Any,
            ) -> bool:
                logger.error("Write failed: %s", error)
                failed_attempts = getattr(error, "failed_attempts", None)
                if failed_attempts is None:
                    failed_attempts = getattr(error, "attempts", 0)
                should_retry = (
                    failed_attempts < MIGRATION_SETTINGS["max_retries"]
                )
                if not should_retry:
                    doc_path = None
                    operation = getattr(error, "operation", None)
                    if operation is not None:
                        reference = getattr(operation, "reference", None)
                        if reference is not None:
                            doc_path = getattr(reference, "path", None)
                    self._record_write_failure(doc_path)
                return should_retry

            bulk_writer.on_write_result(on_write_result)
            bulk_writer.on_write_error(on_write_error)

            for entry in entries:
                self.migrate_collection(
                    collection_path=entry.collection_path,
                    collection_type=entry.collection_type,
                    documents=entry.documents,
                    bulk_writer=bulk_writer,
                )

            if not self.dry_run:
                logger.info("Flushing writes to Firestore...")
                bulk_writer.close()

            logger.info("=" * 50)
            logger.info("Migration complete")
            logger.info("  Created: %s", self.stats["created"])
            logger.info("  Updated: %s", self.stats["updated"])
            logger.info("  Skipped: %s", self.stats["skipped"])
            logger.info("  Errors:  %s", self.stats["errors"])
            logger.info("=" * 50)

            self.record_migration_complete(migration_id)

        except Exception as exc:
            self.record_migration_error(migration_id, str(exc))
            raise


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Migrate mock_db.json data to Firestore",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--collection",
        help=(
            "Migrate only a specific collection type (users, departments, "
            "semesters, subjects, modules, notes) or a collection path"
        ),
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing data before migration (DANGEROUS)",
    )
    parser.add_argument(
        "--credentials",
        help="Path to service account key JSON",
    )
    return parser


def main() -> None:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    credentials_path = (
        Path(args.credentials) if args.credentials else None
    )
    migrator = FirestoreMigrator(
        dry_run=args.dry_run,
        credentials_path=credentials_path,
    )
    migrator.run(
        target_collection=args.collection,
        reset=args.reset,
    )


if __name__ == "__main__":
    main()
