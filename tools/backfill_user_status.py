"""
============================================================================
FILE: backfill_user_status.py
LOCATION: tools/backfill_user_status.py
============================================================================

PURPOSE:
    One-time migration script to backfill missing user status fields in
    Firestore.

ROLE IN PROJECT:
    Ensures legacy user documents include a status value so auth checks
    do not block valid users after the auth refactor.

KEY COMPONENTS:
    - main: CLI entry point with dry-run/apply modes
    - _collect_missing_status: Detects user docs missing status
    - _apply_updates: Writes status updates in batches

DEPENDENCIES:
    - External: firebase_admin (via api.config)
    - Internal: api.config

USAGE:
    Dry run (default):
        python tools/backfill_user_status.py

    Apply changes (requires USE_REAL_FIREBASE=true):
        python tools/backfill_user_status.py --apply
============================================================================
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Tuple


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

try:
    from api.config import get_db
except ImportError as exc:
    raise SystemExit(
        "Failed to import api.config. "
        "Run this script from the project root."
    ) from exc


UserUpdate = Tuple[str, dict]


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Backfill missing status field in Firestore users."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply updates (default is dry-run).",
    )
    parser.add_argument(
        "--default-status",
        default="active",
        help="Status value to set when missing.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=400,
        help="Firestore batch size (max 500).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of documents scanned (0 = no limit).",
    )
    parser.add_argument(
        "--show-ids",
        type=int,
        default=20,
        help="Show up to N document IDs in the report.",
    )
    return parser.parse_args()


def _iter_users(limit: int) -> Iterator:
    """Yield user documents from Firestore.

    Args:
        limit: Max number of docs to scan (0 = no limit).

    Returns:
        Iterator: Firestore document snapshots.
    """
    db = get_db()
    query = db.collection("users")
    if limit and limit > 0:
        query = query.limit(limit)
    return query.stream()


def _collect_missing_status(
    limit: int,
    default_status: str,
) -> Tuple[List[UserUpdate], List[str]]:
    """Collect updates for users missing status.

    Args:
        limit: Max number of docs to scan.
        default_status: Status value to set when missing.

    Returns:
        Tuple[List[UserUpdate], List[str]]: Updates and invalid status IDs.
    """
    updates: List[UserUpdate] = []
    invalid_status: List[str] = []
    timestamp = datetime.utcnow().isoformat()

    for doc in _iter_users(limit):
        data = doc.to_dict() or {}
        status = data.get("status")
        if status in (None, ""):
            updates.append(
                (
                    doc.id,
                    {"status": default_status, "updatedAt": timestamp},
                )
            )
        elif status not in ("active", "disabled"):
            invalid_status.append(doc.id)

    return updates, invalid_status


def _apply_updates(updates: Iterable[UserUpdate], batch_size: int) -> int:
    """Apply updates in Firestore batches.

    Args:
        updates: Iterable of (doc_id, updates) tuples.
        batch_size: Number of writes per batch.

    Returns:
        int: Number of documents updated.
    """
    db = get_db()
    batch = db.batch()
    count = 0
    pending = 0

    for doc_id, payload in updates:
        doc_ref = db.collection("users").document(doc_id)
        batch.update(doc_ref, payload)
        pending += 1

        if pending >= batch_size:
            batch.commit()
            batch = db.batch()
            count += pending
            pending = 0

    if pending:
        batch.commit()
        count += pending

    return count


def main() -> int:
    """Run the backfill script.

    Returns:
        int: Process exit code.
    """
    args = _parse_args()
    use_real_firebase = (
        os.getenv("USE_REAL_FIREBASE", "false").lower() == "true"
    )

    if args.apply and not use_real_firebase:
        print(
            "Refusing to apply updates because USE_REAL_FIREBASE is not true."
        )
        print("Set USE_REAL_FIREBASE=true and try again.")
        return 2

    if args.batch_size <= 0 or args.batch_size > 500:
        print("Invalid --batch-size. Must be between 1 and 500.")
        return 2

    updates, invalid_status = _collect_missing_status(
        args.limit,
        args.default_status,
    )

    print("Backfill user status report")
    print(f"  USE_REAL_FIREBASE: {use_real_firebase}")
    print(f"  Dry run: {not args.apply}")
    print(f"  Missing status docs: {len(updates)}")
    print(f"  Invalid status docs: {len(invalid_status)}")

    if args.show_ids and updates:
        sample = [doc_id for doc_id, _ in updates[: args.show_ids]]
        print(f"  Sample missing IDs: {', '.join(sample)}")

    if invalid_status and args.show_ids:
        sample = invalid_status[: args.show_ids]
        print(f"  Sample invalid IDs: {', '.join(sample)}")

    if not args.apply:
        print("Dry run complete. No changes applied.")
        return 0

    updated_count = _apply_updates(updates, args.batch_size)
    print(f"Applied updates to {updated_count} documents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
