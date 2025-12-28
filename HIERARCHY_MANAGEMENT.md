# Hierarchy Management & Endpoint Generation Explained

## 📋 Overview

Your system now has complete CRUD (Create, Read, Update, Delete) operations for all hierarchy tables with automatic cascading deletes.

---

## 🔄 How Cascading Deletes Work

The database schema has `ON DELETE CASCADE` foreign keys, meaning:

```
departments (id=1)
  └── semesters (dept_id=1)
      └── subjects (sem_id=1)
          └── modules (subj_id=1)
              └── notes (module_id=1)
```

**When you delete:**
- **Department** → All its semesters, subjects, modules, and notes are deleted
- **Semester** → All its subjects, modules, and notes are deleted  
- **Subject** → All its modules and notes are deleted
- **Module** → All its notes are deleted
- **Note** → Only the database entry is removed (PDF file remains on disk)

---

## 🎯 Available Operations

| Entity      | Create | Rename | Delete |
|-------------|--------|--------|--------|
| Department  | ✅     | ✅     | ✅     |
| Semester    | ✅     | ✅     | ✅     |
| Subject     | ✅     | ✅     | ✅     |
| Module      | ✅     | ✅     | ✅     |
| Note        | ❌*    | ✅     | ✅     |

*Notes are created automatically during PDF generation in the main app

---

## 📡 API Endpoints Created

### Departments
- `POST /api/departments` - Create new department
- `PUT /api/departments/{id}` - Rename department
- `DELETE /api/departments/{id}` - Delete department (cascades)

### Semesters
- `POST /api/semesters` - Create new semester
- `PUT /api/semesters/{id}` - Rename semester
- `DELETE /api/semesters/{id}` - Delete semester (cascades)

### Subjects
- `POST /api/subjects` - Create new subject
- `PUT /api/subjects/{id}` - Rename subject
- `DELETE /api/subjects/{id}` - Delete subject (cascades)

### Modules
- `POST /api/modules` - Create new module
- `PUT /api/modules/{id}` - Rename module
- `DELETE /api/modules/{id}` - Delete module (cascades)

### Notes
- `PUT /api/notes/{id}` - Rename note (title only)
- `DELETE /api/notes/{id}` - Delete note (database only, PDF remains)

---

## 🖥️ User Interfaces

### 1. **Main App** (port 8501)
- Upload audio → transcribe → summarize → generate PDF
- Select hierarchy from dropdowns
- Auto-saves note to database when module is selected

### 2. **Notes Explorer** (port 8502)
- Browse notes by hierarchy
- View PDF availability status
- Staff tools: cleanup PDFs, prune missing notes

### 3. **Hierarchy Management** (port 8503) **← NEW!**
- Create new departments, semesters, subjects, modules
- Rename existing items
- Delete items with cascade warnings

---

## 🔍 How Endpoint Generation Works

### Question: "How does the endpoint generated does it generate in upload itself while selecting them in the dropdown menu?"

**Answer:** The endpoints are **already generated** when you seed the database. Here's the flow:

### 1. **Database Seeding** (Run once)
```bash
cd api
python seed_db.py
```

This creates the hierarchy structure:
```
Department: Computer Science (id=1, code=CS)
  └── Semester: 1 - First Year Fall (id=1)
      └── Subject: CS101 - Introduction to Computing (id=1)
          └── Module: Module 1 - Basics of Computing (id=1)
```

### 2. **Dropdown Selection** (In UI/main.py)

When you select items in the sidebar:

```python
# Step 1: User opens the app
departments = fetch_departments()  # GET /departments
# Returns: [{"id": 1, "label": "Computer Science", "type": "department"}]

# Step 2: User selects "Computer Science"
# App stores: st.session_state['hierarchy']['department'] = {"id": 1, "label": "...", ...}
# Then fetches:
semesters = fetch_semesters(dept_id=1)  # GET /departments/1/semesters
# Returns: [{"id": 1, "label": "1 - First Year Fall", "type": "semester"}]

# Step 3: User selects semester
# Stores semester in session_state
subjects = fetch_subjects(sem_id=1)  # GET /semesters/1/subjects
# Returns: [{"id": 1, "label": "CS101 - Introduction to Computing", ...}]

# Step 4: User selects subject
modules = fetch_modules(subj_id=1)  # GET /subjects/1/modules
# Returns: [{"id": 1, "label": "Module 1 - Basics of Computing", ...}]

# Step 5: User selects module
# Now st.session_state['hierarchy'] has all IDs:
# {
#   'department': {'id': 1, ...},
#   'semester': {'id': 1, ...},
#   'subject': {'id': 1, ...},
#   'module': {'id': 1, ...}
# }
```

### 3. **PDF Generation & Note Creation**

When you click "Summarize" and generate a PDF:

```python
# If module is selected, auto-save:
if st.session_state['hierarchy'].get('module'):
    payload = {
        "department_id": 1,  # from session_state
        "semester_id": 1,
        "subject_id": 1,
        "module_id": 1,
        "title": "Artificial Intelligence",
        "pdf_url": "pdfs/Artificial_Intelligence_1766835694.pdf"
    }
    
    # POST /notes creates the note entry
    response = requests.post(f"{API_URL}/notes", json=payload)
    # Returns: {"id": 7, "module_id": 1, "title": "...", "pdf_url": "...", ...}
```

### 4. **The "Endpoint" is the API URL**

The endpoint is the FastAPI route: `POST /notes`

This endpoint is handled by [api/main.py](d:\Users\Mo_sh\FINAL YEAR PROJECT\AURA-PROTO\api\main.py):

```python
@app.post("/notes", status_code=201)
def create_note(note_req: CreateNoteRequest):
    # Validates hierarchy, creates note in database
    return {"id": note_id, "module_id": ..., "title": ..., ...}
```

---

## 🎨 Flow Diagram

```
[User Action]           [API Endpoint]              [Database]
    |                        |                           |
Select Dept  ---------> GET /departments  --------> SELECT * FROM departments
    |                        |                           |
Select Sem   ---------> GET /depts/{id}/sems ------> SELECT * FROM semesters WHERE dept_id=?
    |                        |                           |
Select Subj  ---------> GET /sems/{id}/subjs -------> SELECT * FROM subjects WHERE sem_id=?
    |                        |                           |
Select Module --------> GET /subjs/{id}/mods -------> SELECT * FROM modules WHERE subj_id=?
    |                        |                           |
Generate PDF             (local operation)           (no DB yet)
    |                        |                           |
Auto-save    ---------> POST /notes -----------------> INSERT INTO notes (module_id, title, pdf_url)
```

---

## 🚀 Getting Started

### Start the API Server
```bash
cd api
uvicorn main:app --reload
# API runs on http://localhost:8000
```

### Start the Main App
```bash
streamlit run UI/main.py
# Runs on http://localhost:8501
```

### Start the Explorer
```bash
streamlit run UI/explorer.py
# Runs on http://localhost:8502
```

### Start the Management UI
```bash
streamlit run UI/manage.py --server.port 8503
# Runs on http://localhost:8503
```

---

## 🔐 Key Points

1. **Endpoints are pre-defined** in the FastAPI app, not generated dynamically
2. **Dropdown selections** fetch data from those endpoints using the IDs
3. **Session state** stores the selected hierarchy IDs
4. **PDF generation** uses those IDs to create the note entry
5. **Cascading deletes** automatically clean up child records

---

## 🛠️ Example: Adding a New University's Hierarchy

### Option 1: Use Management UI (Recommended)
1. Open http://localhost:8503
2. Go to "Create" tab
3. Create Department → Semester → Subject → Module

### Option 2: Use API Directly
```bash
# Create department
curl -X POST "http://localhost:8000/api/departments" \
  -H "Content-Type: application/json" \
  -d '{"name": "Engineering", "code": "ENG"}'

# Create semester
curl -X POST "http://localhost:8000/api/semesters" \
  -H "Content-Type: application/json" \
  -d '{"department_id": 2, "semester_number": 1, "name": "Fall 2024"}'

# Create subject
curl -X POST "http://localhost:8000/api/subjects" \
  -H "Content-Type: application/json" \
  -d '{"semester_id": 2, "name": "Physics", "code": "PHY101"}'

# Create module
curl -X POST "http://localhost:8000/api/modules" \
  -H "Content-Type: application/json" \
  -d '{"subject_id": 2, "module_number": 1, "name": "Mechanics"}'
```

### Option 3: Direct SQL (Advanced)
```sql
-- Insert into database/database.db
INSERT INTO departments (name, code) VALUES ('Engineering', 'ENG');
-- Get the department ID, then insert semester, etc.
```

---

## ⚠️ Important Notes

- **PDF files are NOT deleted** when you delete notes from the database
- **Use the prune script** to clean up orphaned PDFs: `python tools/prune_missing_notes.py`
- **Cascading deletes cannot be undone** - always double-check before deleting
- **Cache is cleared** after create/delete operations (600s TTL otherwise)

---

## 📝 Summary

✅ **CRUD operations** for all hierarchy tables
✅ **Automatic cascading deletes**  
✅ **Management UI** for easy administration
✅ **API endpoints** already exist (not dynamically generated)
✅ **Dropdown selections** just fetch from those endpoints
✅ **Session state** tracks the selected hierarchy
✅ **PDF auto-save** uses those IDs to create notes
