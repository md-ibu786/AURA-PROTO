"""
Database helper with SQLite fallback for local development.
If DATABASE_URL (Postgres) is provided, and psycopg is available, it will use that.
Otherwise it uses a local SQLite database at database/database.db and initializes schema from database/schema.sql
"""
import os
import sqlite3
from contextlib import contextmanager
import dotenv

dotenv.load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE_DB_PATH = os.path.join(BASE_DIR, "database", "database.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")

# Try to use Postgres if DATABASE_URL provided and psycopg available
USE_POSTGRES = False
try:
    if DATABASE_URL and DATABASE_URL.startswith("postgres"):
        import psycopg
        from psycopg.rows import dict_row
        USE_POSTGRES = True
except Exception:
    USE_POSTGRES = False

if not USE_POSTGRES:
    # Ensure database folder exists
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)

    def init_sqlite_db():
        conn = sqlite3.connect(SQLITE_DB_PATH)
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            schema = f.read()
        conn.executescript(schema)
        conn.commit()
        conn.close()

    if not os.path.exists(SQLITE_DB_PATH):
        init_sqlite_db()

@contextmanager
def get_db_connection():
    if USE_POSTGRES:
        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

def execute_query(query, params=None):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params or ())
        rows = cur.fetchall()
        # Convert sqlite3.Row objects to dicts
        result = []
        for r in rows:
            if isinstance(r, sqlite3.Row):
                result.append({k: r[k] for k in r.keys()})
            else:
                result.append(dict(r))
        return result

def execute_one(query, params=None):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params or ())
        row = cur.fetchone()
        if not row:
            return None
        if isinstance(row, sqlite3.Row):
            return {k: row[k] for k in row.keys()}
        return dict(row)

def execute_write(query, params=None):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params or ())
        try:
            return cur.lastrowid
        except Exception:
            return None
