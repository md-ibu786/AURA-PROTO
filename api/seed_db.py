"""
Seed the local SQLite database with minimal hierarchy data for development.
This script is safe to run multiple times - it checks for existing entries.
"""
from api.db import execute_query, execute_one, execute_write

# Check if departments exist
existing = execute_query("SELECT id FROM departments LIMIT 1")
if existing:
    print("DB already seeded")
else:
    # Insert a sample department -> semester -> subject -> module chain
    dept_id = execute_write("INSERT INTO departments (name, code) VALUES (?, ?)", ("Computer Science", "CSE"))
    sem_id = execute_write("INSERT INTO semesters (department_id, semester_number, name) VALUES (?, ?, ?)", (dept_id, 5, "Semester 5"))
    subj_id = execute_write("INSERT INTO subjects (semester_id, name, code) VALUES (?, ?, ?)", (sem_id, "Operating Systems", "OS"))
    mod_id = execute_write("INSERT INTO modules (subject_id, module_number, name) VALUES (?, ?, ?)", (subj_id, 1, "Process Scheduling"))
    print(f"Inserted sample hierarchy: dept={dept_id}, sem={sem_id}, subj={subj_id}, mod={mod_id}")
