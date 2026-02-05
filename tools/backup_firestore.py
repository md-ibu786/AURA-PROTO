"""
============================================================================
FILE: backup_firestore.py
LOCATION: tools/backup_firestore.py
============================================================================

PURPOSE:
    Create a managed export backup of Firestore data

ROLE IN PROJECT:
    Safety backup before running migrations
    Allows point-in-time recovery using gcloud firestore import

DEPENDENCIES:
    - Google Cloud SDK (gcloud)
    - Appropriate IAM permissions
    - A Cloud Storage bucket for exports

USAGE:
    python tools/backup_firestore.py
    python tools/backup_firestore.py --bucket gs://my-backup-bucket
============================================================================
"""
from __future__ import annotations

import argparse
import logging
import subprocess
from datetime import datetime
from typing import Optional


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_COLLECTION_IDS = (
    "users,departments,semesters,subjects,modules,notes"
)


def create_backup(bucket_name: Optional[str]) -> str:
    """Create a Firestore backup using managed export."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    if not bucket_name:
        bucket_name = input(
            "Enter Cloud Storage bucket for backup "
            "(e.g., gs://my-project-backups): "
        )

    if not bucket_name.startswith("gs://"):
        bucket_name = f"gs://{bucket_name}"

    export_path = f"{bucket_name}/firestore-backup-{timestamp}"

    logger.info("Starting Firestore export to %s", export_path)

    try:
        result = subprocess.run(
            [
                "gcloud",
                "firestore",
                "export",
                export_path,
                f"--collection-ids={DEFAULT_COLLECTION_IDS}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        logger.info("Backup completed successfully")
        logger.info("Backup location: %s", export_path)
        if result.stdout:
            logger.info(result.stdout.strip())

        return export_path

    except subprocess.CalledProcessError as exc:
        logger.error("Backup failed: %s", exc)
        if exc.stderr:
            logger.error(exc.stderr.strip())
        raise
    except FileNotFoundError as exc:
        logger.error("gcloud command not found. Install Google Cloud SDK.")
        raise exc


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(description="Backup Firestore data")
    parser.add_argument(
        "--bucket",
        help="Cloud Storage bucket (gs://bucket-name)",
    )
    return parser


def main() -> None:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    try:
        backup_path = create_backup(args.bucket)
        print(f"\nBackup created: {backup_path}")
        print("\nTo restore from this backup:")
        print(f"gcloud firestore import {backup_path}")
    except Exception:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
