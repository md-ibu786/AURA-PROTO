"""
============================================================================
FILE: verify_migration_and_crud.py
LOCATION: tools/verify_migration_and_crud.py
============================================================================

PURPOSE:
    Verification script to validate that the Firestore migration was
    successful and that CRUD operations are working correctly. Performs
    a series of health checks on the database and API functionality.

ROLE IN PROJECT:
    Post-migration validation tool. Run after migrate_db.py to confirm:
    - Data was successfully migrated to Firestore
    - Nested collections are properly structured
    - Explorer tree builder works with new data
    - Write operations (create/read/delete) function correctly

VERIFICATION STEPS:
    1. Check Data Existence: Query departments and nested semesters
    2. Verify Explorer Tree Builder: Call get_explorer_tree()
    3. Test CRUD Write: Create a test department, verify, then delete

OUTPUT MARKERS:
    ✅ PASS: Test succeeded
    ❌ FAIL: Test failed (with error details)
    ⚠️ WARNING: Non-critical issue detected

DEPENDENCIES:
    - External: firebase_admin
    - Internal: api/config.py (db), api/explorer.py, api/hierarchy_crud.py

USAGE:
    python tools/verify_migration_and_crud.py

NOTES:
    - Creates and deletes a test department (self-cleaning)
    - Safe to run multiple times
    - Should be run with the backend stopped to avoid conflicts
============================================================================
"""
import sys
import os
import time

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from api.config import db
    from api.explorer import get_explorer_tree
    from api.hierarchy_crud import create_department, DepartmentCreate
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def verify():
    print("=== STARTING VERIFICATION ===")
    
    # 1. Check Data Existence
    print("\n1. Checking existing data (Migration Result)...")
    try:
        depts = list(db.collection('departments').limit(5).stream())
        print(f"Found {len(depts)} departments (limit 5).")
        if not depts:
            print("❌ FAIL: No departments found. Migration might have failed or DB is empty.")
        else:
            print(f"✅ PASS: Found data. Sample: {depts[0].to_dict().get('name')}")
            
            # Check for subcollections (Semesters)
            sem_ref = depts[0].reference.collection('semesters').limit(1).stream()
            sems = list(sem_ref)
            if sems:
                 print(f"✅ PASS: Found nested semesters. Sample: {sems[0].to_dict().get('name')}")
            else:
                 print("⚠️ WARNING: No semesters found for first department (might be empty dept).")

    except Exception as e:
        print(f"❌ FAIL: Firestore connection/query failed: {e}")
        return

    # 2. Check Tree Builder
    print("\n2. Verifying Explorer Tree Builder...")
    try:
        tree = get_explorer_tree(depth=2)
        print(f"Tree root items: {len(tree)}")
        if len(tree) > 0:
            print(f"✅ PASS: Tree build successful. Root: {tree[0].label}")
        else:
            print("⚠️ WARNING: Tree is empty.")
    except Exception as e:
        print(f"❌ FAIL: get_explorer_tree failed: {e}")
        import traceback
        traceback.print_exc()

    # 3. Test CRUD Write
    print("\n3. Testing Write Operation (Create Department)...")
    try:
        test_name = f"Test Verify {int(time.time())}"
        new_dept = create_department(DepartmentCreate(name=test_name, code="TV"))
        print(f"Created: {new_dept}")
        dept_id = new_dept['department']['id']
        
        # Verify read
        doc = db.collection('departments').document(dept_id).get()
        if doc.exists and doc.to_dict()['name'] == test_name:
            print("✅ PASS: Write verified.")
        else:
            print("❌ FAIL: Written document not found.")
            
        # Cleanup
        db.collection('departments').document(dept_id).delete()
        print("✅ PASS: Cleanup successful.")
        
    except Exception as e:
        print(f"❌ FAIL: CRUD operation failed: {e}")

    print("\n=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    verify()
