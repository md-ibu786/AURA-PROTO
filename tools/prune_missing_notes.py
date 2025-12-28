"""Prune missing notes from the database.

Usage:
  python tools/prune_missing_notes.py [--delete] [--force]

- Without --delete: lists candidate missing notes (dry-run)
- With --delete: deletes the notes confirmed missing (status 404 or 410 or missing local file)
- With --force: consider any non-200 HEAD response as missing (use with caution)
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