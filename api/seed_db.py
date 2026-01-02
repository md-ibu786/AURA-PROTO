"""
Seed the PostgreSQL database with minimal hierarchy data for development.
This script is safe to run multiple times - it checks for existing entries.
"""
try:
    from db import execute_query, execute_one, PLACEHOLDER
except ImportError:
    from api.db import execute_query, execute_one, PLACEHOLDER

# Check if departments exist
existing = execute_query("SELECT id FROM departments LIMIT 1")
if existing:
    print("DB already seeded")
else:
    # Insert a sample department -> semester -> subject -> module chain using RETURNING
    dept = execute_one(f"INSERT INTO departments (name, code) VALUES ({PLACEHOLDER}, {PLACEHOLDER}) RETURNING id", ("Computer Science", "CSE"))
    dept_id = dept['id']
    
    sem = execute_one(f"INSERT INTO semesters (department_id, semester_number, name) VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}) RETURNING id", (dept_id, 5, "Semester 5"))
    sem_id = sem['id']
    
    subj = execute_one(f"INSERT INTO subjects (semester_id, name, code) VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}) RETURNING id", (sem_id, "Operating Systems", "OS"))
    subj_id = subj['id']
    
    mod = execute_one(f"INSERT INTO modules (subject_id, module_number, name) VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}) RETURNING id", (subj_id, 1, "Process Scheduling"))
    mod_id = mod['id']
    
    print(f"Inserted sample hierarchy: dept={dept_id}, sem={sem_id}, subj={subj_id}, mod={mod_id}")

