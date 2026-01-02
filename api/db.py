"""
Database helper - PostgreSQL only.
Requires DATABASE_URL environment variable to be set.
"""
import os
from contextlib import contextmanager
import dotenv

dotenv.load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL or not DATABASE_URL.startswith("postgres"):
    raise RuntimeError("DATABASE_URL environment variable must be set to a valid PostgreSQL connection string")

import psycopg
from psycopg.rows import dict_row

# SQL Placeholder for PostgreSQL
PLACEHOLDER = "%s"

@contextmanager
def get_db_connection():
    """Get a fresh database connection for each request."""
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def execute_query(query, params=None):
    """Execute a query. For SELECT returns rows as list of dicts. For DELETE/UPDATE returns empty list."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params or ())
        if cur.description is not None:
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        return []

def execute_one(query, params=None):
    """Execute a query and return a single row as dict, or None."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params or ())
        if cur.description is None:
            return None
        row = cur.fetchone()
        if not row:
            return None
        return dict(row)

def execute_write(query, params=None):
    """Execute a write query. Use RETURNING id to get inserted ID."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params or ())
        try:
            row = cur.fetchone()
            if row and 'id' in row:
                return row['id']
        except Exception:
            pass
        return None
