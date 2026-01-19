"""
============================================================================
FILE: prune_missing_notes.py
LOCATION: tools/prune_missing_notes.py
============================================================================

PURPOSE:
    Database cleanup utility to find and optionally delete notes whose
    PDF/document files no longer exist. Helps maintain data integrity
    by removing orphaned database records.

ROLE IN PROJECT:
    Maintenance tool for data hygiene. Useful when:
    - PDF files are manually deleted from the filesystem
    - External storage URLs become inaccessible
    - After failed uploads that created DB records without files

KEY OPERATIONS:
    1. Query all notes from SQLite database
    2. Check each pdf_url via HEAD request (for URLs) or filesystem check
    3. Report notes with 404/410 responses or missing local files
    4. Optionally delete orphaned records (--delete flag)

COMMAND LINE OPTIONS:
    --delete: Actually delete orphaned notes (default: dry-run)
    --force: Treat any non-200 response as missing (use with caution)

DEPENDENCIES:
    - External: requests, sqlite3 (Python standard library)
    - Internal: Uses API_BASE_URL env var for URL validation

USAGE:
    # Dry run - see what would be deleted
    python tools/prune_missing_notes.py
    
    # Delete orphaned records
    python tools/prune_missing_notes.py --delete

NOTES:
    - Targets legacy SQLite database at database/database.db
    - For Firestore, use API endpoints or write a similar script
============================================================================
"""
import os
import sqlite3
import requests
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / 'database' / 'database.db'
API_BASE = os.getenv('API_BASE_URL', 'http://localhost:8000')

parser = argparse.ArgumentParser()
parser.add_argument('--delete', action='store_true', help='Delete missing notes')
parser.add_argument('--force', action='store_true', help='Treat any non-200 response as missing')
args = parser.parse_args()

if not DB_PATH.exists():
    print('Database not found at', DB_PATH)
    raise SystemExit(1)

conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()
cur.execute('SELECT id, title, pdf_url FROM notes')
rows = cur.fetchall()

candidates = []
for id_, title, url in rows:
    if not url:
        continue
    # Normalize to full URL if relative
    if url.startswith('http'):
        full = url
    else:
        full = f"{API_BASE.rstrip('/')}/{url.lstrip('/')}"

    # If it's a local file path (file:// or exists on disk), check filesystem
    if full.startswith('file:'):
        path = full[5:]
        exists = os.path.exists(path)
        if not exists:
            candidates.append((id_, title, url, 'file-missing'))
        continue

    # HEAD request
    try:
        r = requests.head(full, timeout=3, allow_redirects=True)
        status = r.status_code
    except requests.exceptions.RequestException as e:
        status = None

    if status == 200:
        continue
    if status in (404, 410) or (args.force and status and status != 200):
        candidates.append((id_, title, url, status))
    else:
        # unknown or transient error - skip unless force
        if args.force and (status is None or status != 200):
            candidates.append((id_, title, url, status))

# Report
if not candidates:
    print('No missing notes detected.')
    conn.close()
    raise SystemExit(0)

print('Missing note candidates:')
for id_, title, url, status in candidates:
    print(f" - id={id_} title={title!r} url={url!r} status={status}")

if args.delete:
    print('\nDeleting candidates...')
    for id_, title, url, status in candidates:
        cur.execute('DELETE FROM notes WHERE id = ?', (id_,))
        print(f"Deleted note id={id_} title={title!r}")
    conn.commit()
    print('Deletion complete.')
else:
    print('\nDRY RUN: no deletions performed. Re-run with --delete to remove these notes.')

conn.close()