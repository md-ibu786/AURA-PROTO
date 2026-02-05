"""
============================================================================
FILE: revert_firestore.py
LOCATION: tools/revert_firestore.py
============================================================================

PURPOSE:
    Remove migrated Firestore data from a target project safely

ROLE IN PROJECT:
    Emergency rollback helper to undo accidental migrations

KEY COMPONENTS:
    - initialize_firebase: Loads credentials and returns a Firestore client
    - delete_collection_recursive: Removes collections and subcollections

DEPENDENCIES:
    - External: firebase-admin, google-cloud-firestore
    - Internal: None

USAGE:
    python tools/revert_firestore.py --credentials serviceAccountKey.json \
        --confirm
============================================================================
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Iterable, List

import firebase_admin
from firebase_admin import credentials, firestore


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CREDENTIALS_PATH = PROJECT_ROOT / "serviceAccountKey.json"
DEFAULT_COLLECTIONS = ["users", "departments", "_migrations"]


def initialize_firebase(credentials_path: Path) -> firestore.Client:
    """Initialize Firebase Admin SDK and return Firestore client."""
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Service account key not found: {credentials_path}"
        )

    if not firebase_admin._apps:
        cred = credentials.Certificate(str(credentials_path))
        firebase_admin.initialize_app(cred)

    return firestore.client()


def delete_collection_recursive(
    collection_ref: firestore.CollectionReference,
    batch_size: int = 50,
) -> int:
    """Delete all documents in a collection, including subcollections."""
    docs = list(collection_ref.limit(batch_size).stream())
    deleted = 0

    for doc in docs:
        for subcollection in doc.reference.collections():
            deleted += delete_collection_recursive(subcollection, batch_size)
        doc.reference.delete()
        deleted += 1

    if len(docs) >= batch_size:
        deleted += delete_collection_recursive(collection_ref, batch_size)

    return deleted


def delete_collections(
    db: firestore.Client,
    collections: Iterable[str],
) -> None:
    """Delete a list of collections from Firestore."""
    for collection_name in collections:
        logger.info("Deleting collection: %s", collection_name)
        deleted = delete_collection_recursive(db.collection(collection_name))
        logger.info(
            "Deleted %s documents from %s",
            deleted,
            collection_name,
        )


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Revert migrated Firestore data",
    )
    parser.add_argument(
        "--credentials",
        default=str(DEFAULT_CREDENTIALS_PATH),
        help="Path to service account key JSON",
    )
    parser.add_argument(
        "--collections",
        default=",".join(DEFAULT_COLLECTIONS),
        help="Comma-separated collection names to delete",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually delete data (required)",
    )
    return parser


def main() -> None:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    if not args.confirm:
        logger.error("Refusing to run without --confirm flag.")
        raise SystemExit(1)

    credentials_path = Path(args.credentials)
    collections = [
        name.strip()
        for name in args.collections.split(",")
        if name.strip()
    ]

    db = initialize_firebase(credentials_path)
    delete_collections(db, collections)


if __name__ == "__main__":
    main()
