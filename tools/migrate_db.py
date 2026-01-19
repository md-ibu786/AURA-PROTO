"""
============================================================================
FILE: migrate_db.py
LOCATION: tools/migrate_db.py
============================================================================

PURPOSE:
    One-time migration script to transfer data from PostgreSQL (Render/Neon)
    to Firestore. Copies all hierarchy entities (Departments, Semesters,
    Subjects, Modules, Notes) while maintaining parent-child relationships.

ROLE IN PROJECT:
    Historical utility from the database migration phase. The project
    originally used PostgreSQL on Render, then migrated to Firestore for
    better integration with Firebase ecosystem and reduced server costs.

KEY OPERATIONS:
    1. Connect to PostgreSQL using DATABASE_URL environment variable
    2. Read all tables (departments, semesters, subjects, modules, notes)
    3. Create corresponding documents in Firestore nested subcollections
    4. Track ID mappings to preserve parent-child relationships
    5. Use batched writes (400 ops max) for efficiency

DATA MAPPING:
    PostgreSQL (Flat Tables) → Firestore (Nested Collections)
    - departments → departments/{id}
    - semesters → departments/{dept}/semesters/{id}
    - subjects → .../semesters/{sem}/subjects/{id}
    - modules → .../subjects/{subj}/modules/{id}
    - notes → .../modules/{mod}/notes/{id}

DEPENDENCIES:
    - External: psycopg, firebase_admin, python-dotenv
    - Internal: api/db.py (or falls back to direct Firebase init)

ENVIRONMENT VARIABLES:
    - DATABASE_URL: PostgreSQL connection string
    - FIREBASE_CREDENTIALS or serviceAccountKey.json path

USAGE:
    python tools/migrate_db.py

WARNING:
    This is a ONE-WAY migration. Run on a test database first.
    Does not delete PostgreSQL data after migration.
============================================================================
"""
import os
import sys
import psycopg
from psycopg.rows import dict_row
import firebase_admin
from firebase_admin import credentials, firestore
import dotenv

# Load environment variables
dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Setup Paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Initialize Firebase
# Note: We duplicate logic here slightly to be standalone or import config if possible
# safely importing config from here might be tricky due to relative imports if not careful
# but sys.path append helps.
try:
    from api.db import db # using the exported db client from our new setup
except ImportError:
    # Fallback if run directly and pythonpath issues
    cred_path = os.path.join(os.path.dirname(__file__), '..', 'serviceAccountKey.json')
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    db = firestore.client()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not set in .env")
    sys.exit(1)

def get_pg_connection():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def batch_commit(batch):
    """Commits a batch and returns a new one."""
    batch.commit()
    return db.batch()

def migrate():
    print("Starting migration...")
    
    # Maps to store old_id -> new_info (id or full info)
    # dept_map: old_id -> new_doc_id
    dept_map = {}
    # sem_map: old_id -> {'id': new_doc_id, 'dept_id': new_parent_doc_id}
    sem_map = {}
    # subj_map: old_id -> {'id': new_id, 'sem_id': new_sem_id, 'dept_id': new_dept_id}
    subj_map = {}
    # mod_map: old_id -> {'id': new_id, ...}
    mod_map = {}

    batch = db.batch()
    op_count = 0
    BATCH_LIMIT = 400 # Buffer below 500

    with get_pg_connection() as conn:
        # 1. Departments
        print("Migrating Departments...")
        cur = conn.execute("SELECT * FROM departments")
        for row in cur:
            new_ref = db.collection('departments').document()
            
            # Prepare data
            data = {
                'name': row['name'],
                'code': row.get('code'), # might be null
                'original_id': row['id']
            }
            batch.set(new_ref, data)
            dept_map[row['id']] = new_ref.id
            
            op_count += 1
            if op_count >= BATCH_LIMIT:
                batch = batch_commit(batch)
                op_count = 0
        
        batch = batch_commit(batch) # Commit remaining departments
        op_count = 0
        print(f"Migrated {len(dept_map)} departments.")

        # 2. Semesters
        print("Migrating Semesters...")
        cur = conn.execute("SELECT * FROM semesters")
        for row in cur:
            old_dept_id = row['department_id']
            if old_dept_id not in dept_map:
                print(f"Skipping semester {row['id']} - parent dept {old_dept_id} not found")
                continue
            
            dept_uid = dept_map[old_dept_id]
            new_ref = db.collection('departments').document(dept_uid).collection('semesters').document()
            
            data = {
                'name': row['name'],
                'semester_number': row['semester_number'],
                'original_id': row['id']
            }
            batch.set(new_ref, data)
            sem_map[row['id']] = {'id': new_ref.id, 'dept_id': dept_uid}

            op_count += 1
            if op_count >= BATCH_LIMIT:
                batch = batch_commit(batch)
                op_count = 0
        
        batch = batch_commit(batch)
        op_count = 0
        print(f"Migrated {len(sem_map)} semesters.")

        # 3. Subjects
        print("Migrating Subjects...")
        cur = conn.execute("SELECT * FROM subjects")
        for row in cur:
            old_sem_id = row['semester_id']
            if old_sem_id not in sem_map:
                continue
            
            sem_info = sem_map[old_sem_id]
            dept_uid = sem_info['dept_id']
            sem_uid = sem_info['id']

            new_ref = db.collection('departments').document(dept_uid)\
                        .collection('semesters').document(sem_uid)\
                        .collection('subjects').document()
            
            data = {
                'name': row['name'],
                'code': row.get('code'),
                'original_id': row['id']
            }
            batch.set(new_ref, data)
            subj_map[row['id']] = {'id': new_ref.id, 'sem_id': sem_uid, 'dept_id': dept_uid}

            op_count += 1
            if op_count >= BATCH_LIMIT:
                batch = batch_commit(batch)
                op_count = 0
        
        batch = batch_commit(batch)
        op_count = 0
        print(f"Migrated {len(subj_map)} subjects.")

        # 4. Modules
        print("Migrating Modules...")
        cur = conn.execute("SELECT * FROM modules")
        for row in cur:
            old_subj_id = row['subject_id']
            if old_subj_id not in subj_map:
                continue
            
            subj_info = subj_map[old_subj_id]
            dept_uid = subj_info['dept_id']
            sem_uid = subj_info['sem_id']
            subj_uid = subj_info['id']

            new_ref = db.collection('departments').document(dept_uid)\
                        .collection('semesters').document(sem_uid)\
                        .collection('subjects').document(subj_uid)\
                        .collection('modules').document()
            
            data = {
                'name': row['name'],
                'module_number': row.get('module_number'),
                'original_id': row['id']
            }
            batch.set(new_ref, data)
            mod_map[row['id']] = {'id': new_ref.id, 'subj_id': subj_uid, 'sem_id': sem_uid, 'dept_id': dept_uid}

            op_count += 1
            if op_count >= BATCH_LIMIT:
                batch = batch_commit(batch)
                op_count = 0

        batch = batch_commit(batch)
        op_count = 0
        print(f"Migrated {len(mod_map)} modules.")

        # 5. Notes (Assuming table exists, if not catching error)
        try:
            print("Migrating Notes...")
            # Check column names for notes first or just try SELECT *
            # Expected: id, module_id, name, content, (maybe file_path or created_at?)
            cur = conn.execute("SELECT * FROM notes")
            count_notes = 0
            for row in cur:
                old_mod_id = row['module_id']
                if old_mod_id not in mod_map:
                    continue
                
                mod_info = mod_map[old_mod_id]
                dept_uid = mod_info['dept_id']
                sem_uid = mod_info['sem_id']
                subj_uid = mod_info['subj_id']
                mod_uid = mod_info['id']

                new_ref = db.collection('departments').document(dept_uid)\
                            .collection('semesters').document(sem_uid)\
                            .collection('subjects').document(subj_uid)\
                            .collection('modules').document(mod_uid)\
                            .collection('notes').document()
                
                # Copy all fields except id
                data = dict(row)
                data['original_id'] = data.pop('id')
                # Remove module_id as it's implied by hierarchy
                if 'module_id' in data:
                    del data['module_id']
                
                batch.set(new_ref, data)
                count_notes += 1
                
                op_count += 1
                if op_count >= BATCH_LIMIT:
                    batch = batch_commit(batch)
                    op_count = 0
            
            batch = batch_commit(batch)
            print(f"Migrated {count_notes} notes.")

        except psycopg.errors.UndefinedTable:
            print("Notes table not found, skipping.")
        except Exception as e:
            print(f"Error migrating notes: {e}")

    print("Migration complete!")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
