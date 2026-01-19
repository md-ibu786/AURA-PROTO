"""
============================================================================
FILE: cleanup_pdfs.py
LOCATION: tools/cleanup_pdfs.py
============================================================================

PURPOSE:
    Maintenance script to consolidate PDF files and normalize database entries.
    Moves stray PDFs from the legacy UI/pdfs directory to the canonical pdfs/
    directory and updates database references to use consistent paths.

ROLE IN PROJECT:
    One-time migration utility created during the Streamlit-to-React migration.
    Ensures all PDF paths are normalized to the new /pdfs/{filename} format.
    Can be run multiple times safely (idempotent).

KEY OPERATIONS:
    1. Move files from UI/pdfs/ to pdfs/ (handling name conflicts)
    2. Remove empty UI/pdfs/ directory
    3. Update SQLite database entries with normalized paths

DEPENDENCIES:
    - External: shutil, sqlite3 (Python standard library)
    - Internal: None

USAGE:
    python tools/cleanup_pdfs.py

NOTES:
    - This script targets the legacy SQLite database
    - For Firestore, PDF path updates should be done via the API
============================================================================
"""
import os
import shutil
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_PDFS = ROOT / 'UI' / 'pdfs'
ROOT_PDFS = ROOT / 'pdfs'
DB_PATH = ROOT / 'database' / 'database.db'

os.makedirs(ROOT_PDFS, exist_ok=True)

moved = []
if UI_PDFS.exists():
    for p in UI_PDFS.iterdir():
        if p.is_file():
            dest = ROOT_PDFS / p.name
            i = 1
            base = p.stem
            ext = p.suffix
            while dest.exists():
                dest = ROOT_PDFS / f"{base}-{i}{ext}"
                i += 1
            shutil.move(str(p), str(dest))
            moved.append((str(p), str(dest)))
    try:
        UI_PDFS.rmdir()
    except Exception:
        pass

# Normalize DB entries
updated = []
if DB_PATH.exists():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("SELECT id, pdf_url FROM notes")
    rows = cur.fetchall()
    for id, url in rows:
        if not url:
            continue
        # If url references UI/pdfs or has absolute filesystem path to UI/pdfs, normalize
        if 'UI/pdfs' in url or 'UI\\pdfs' in url or url.startswith('file:'):
            basename = os.path.basename(url)
            new = f"pdfs/{basename}"
            cur.execute('UPDATE notes SET pdf_url = ? WHERE id = ?', (new, id))
            updated.append((id, url, new))
    conn.commit()
    conn.close()

# Output summary
print('Moved files:')
for s, d in moved:
    print(f' - {s} -> {d}')
print('DB updates:')
for u in updated:
    print(f' - id {u[0]}: {u[1]} -> {u[2]}')
print('Done.')