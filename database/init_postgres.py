"""
Initialize PostgreSQL database with schema.
Run this once to create tables in your Neon database.
"""
import os
import dotenv

dotenv.load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL or not DATABASE_URL.startswith("postgres"):
    print("ERROR: DATABASE_URL not set or invalid")
    exit(1)

import psycopg

# Read the PostgreSQL schema
schema_path = os.path.join(os.path.dirname(__file__), "schema_postgres.sql")
with open(schema_path, 'r', encoding='utf-8') as f:
    schema = f.read()

print(f"Connecting to database...")
conn = psycopg.connect(DATABASE_URL)

print("Creating tables...")
conn.execute(schema)
conn.commit()
conn.close()

print("✓ Database initialized successfully!")
print("Tables created: departments, semesters, subjects, modules, notes")
