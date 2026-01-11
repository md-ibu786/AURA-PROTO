"""
============================================================================
FILE: hierarchy_crud.py
LOCATION: api/hierarchy_crud.py
============================================================================

PURPOSE:
    Provides Create, Update, Delete (CRUD) REST API endpoints for all
    hierarchy entities: departments, semesters, subjects, modules, and notes.
    Implements transactional operations with duplicate name handling and
    cascading deletes for nested Firestore subcollections.

ROLE IN PROJECT:
    This is the write layer for hierarchy management. The React frontend's
    context menu operations (New Folder, Rename, Delete) call these endpoints.
    
    Key features:
    - Automatic unique name generation for duplicates (e.g., "Name (2)")
    - Transactional parent validation before creating children
    - Recursive deletion of subcollections and associated PDF files
    - Collection group queries to find nested documents by ID

KEY COMPONENTS:
    Utility Functions:
    - get_next_available_number(): Sequential numbering for semesters/modules
    - get_next_available_code(): Generate codes like SUBJ001, SUBJ002
    - get_unique_name(): Add (N) suffix for duplicate names
    - delete_document_recursive(): Cascade delete with PDF cleanup
    - find_doc_by_id(): Collection group query to locate nested docs
    
    Pydantic Models:
    - DepartmentCreate/Update, SemesterCreate/Update
    - SubjectCreate/Update, ModuleCreate/Update, NoteUpdate
    
    Endpoints:
    - POST/PUT/DELETE /api/departments/{id}
    - POST/PUT/DELETE /api/semesters/{id}
    - POST/PUT/DELETE /api/subjects/{id}
    - POST/PUT/DELETE /api/modules/{id}
    - PUT/DELETE /api/notes/{id} (notes created via audio_processing)

DEPENDENCIES:
    - External: fastapi, pydantic, google-cloud-firestore
    - Internal: config.py (db client)

USAGE:
    # Create a new subject under a semester
    POST /api/subjects
    {"semester_id": "abc123", "name": "Data Structures", "code": "CS201"}
    
    # Delete a module (cascades to notes, deletes PDFs)
    DELETE /api/modules/xyz789
============================================================================
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from google.cloud import firestore
try:
    from config import db
except (ImportError, ModuleNotFoundError):
    try:
        from .config import db
    except (ImportError, ModuleNotFoundError):
        from api.config import db

router = APIRouter(prefix="/api", tags=["hierarchy-crud"])

# ========== UTILITY FUNCTIONS ==========

def get_next_available_number(numbers: list[int]) -> int:
    """Find the next available sequential number (max + 1)."""
    if not numbers:
        return 1
    return max(numbers) + 1

def get_next_available_code(codes: list[str], prefix: str = "SUBJ") -> str:
    """Generate the next available code like SUBJ001."""
    if not codes:
        return f"{prefix}001"
    
    # Simple extract and max logic
    nums = []
    for c in codes:
        if c.startswith(prefix):
            try:
                nums.append(int(c[len(prefix):]))
            except ValueError:
                pass
    
    next_num = get_next_available_number(nums)
    return f"{prefix}{next_num:03d}"

def get_unique_name(names: list[str], base_name: str) -> str:
    """Generate unique name with (N) suffix."""
    if base_name not in names:
        return base_name
    
    import re
    suffix_numbers = [1]
    pattern = re.compile(rf'^{re.escape(base_name)} \((\d+)\)$')
    for n in names:
        match = pattern.match(n)
        if match:
            suffix_numbers.append(int(match.group(1)))
    
    next_suffix = get_next_available_number(suffix_numbers)
    if next_suffix == 1: next_suffix = 2
    return f"{base_name} ({next_suffix})"

# Helper to delete collection recursively
def delete_collection(coll_ref, batch_size=50):
    docs = list(coll_ref.limit(batch_size).stream())
    deleted = 0
    for doc in docs:
        delete_document_recursive(doc.reference)
        deleted += 1

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)

def delete_document_recursive(doc_ref):
    """Delete a document and all its subcollections, including associated PDF files."""
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    for coll in doc_ref.collections():
        # Check if this is a notes collection - clean up PDF files first
        if coll.id == 'notes':
            for note_doc in coll.stream():
                data = note_doc.to_dict()
                pdf_url = data.get('pdf_url')
                if pdf_url:
                    try:
                        clean_path = pdf_url.lstrip('/')
                        file_path = os.path.join(base_dir, clean_path)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except Exception:
                        pass  # Continue even if file cleanup fails
        delete_collection(coll)
    doc_ref.delete()

# Helper to find parent semester from just ID (expensive scan or requires known department)
# For this prototype, we will assume requests provide context or we scan deeply if needed.
# But `modules` table doesn't have parent semester explicitly in Firestore ID? 
# Wait, existing API designs: 
# `delete_module(mod_id)` -> In Firestore, we need path!
# If frontend sends just `mod_id` (auto-generated string), we cannot easily find it without a Collection Group Query.
# Solution: Use Collection Group Query to find the doc reference.

def find_doc_by_id(collection_name: str, doc_id: str):
    """Find a document reference by ID using collection group query.
    
    Uses the 'id' field stored in each document for lookup, since
    Firestore's FieldPath.document_id() requires the full path.
    """
    # collection_name e.g. 'modules'
    # Note: 'departments' is root, easy. Others are nested.
    if collection_name == 'departments':
        doc = db.collection('departments').document(doc_id).get()
        return doc.reference if doc.exists else None
    
    # For nested collections, query by the 'id' field stored in documents
    # This is the recommended approach for collection group queries
    docs = list(db.collection_group(collection_name).where('id', '==', doc_id).stream())
    if docs:
        return docs[0].reference
    return None


# ========== MODELS (Updated IDs to str) ==========

class DepartmentCreate(BaseModel):
    name: str
    code: str

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None

class SemesterCreate(BaseModel):
    department_id: str
    semester_number: int  # Logic might calculate this, but model keeps int
    name: str

class SemesterUpdate(BaseModel):
    semester_number: Optional[int] = None
    name: Optional[str] = None

class SubjectCreate(BaseModel):
    semester_id: str
    name: str
    code: str

class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None

class ModuleCreate(BaseModel):
    subject_id: str
    module_number: int
    name: str

class ModuleUpdate(BaseModel):
    module_number: Optional[int] = None
    name: Optional[str] = None

class NoteUpdate(BaseModel):
    title: str

# ========== DEPARTMENTS ==========

@router.post("/departments", responses={409: {"description": "Conflict: Department with this name already exists"}})
def create_department(dept: DepartmentCreate):
    # Check for duplicates
    existing = list(db.collection('departments').where('name', '==', dept.name).limit(1).stream())
    if existing:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "DUPLICATE_NAME",
                "message": f"Department with name '{dept.name}' already exists."
            }
        )

    try:
        new_ref = db.collection('departments').document()
        data = dept.dict()
        data['id'] = new_ref.id
        new_ref.set(data)
        return {"message": "Department created", "department": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/departments/{dept_id}")
def update_department(dept_id: str, dept: DepartmentUpdate):
    doc_ref = db.collection('departments').document(dept_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Department not found")
    
    updates = {k: v for k, v in dept.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No updates")
    
    if 'name' in updates:
        # Check for duplicates
        siblings_names = [d.to_dict().get('name') for d in db.collection('departments').stream() if d.id != dept_id]
        updates['name'] = get_unique_name(siblings_names, updates['name'])

    doc_ref.update(updates)
    return {"message": "Department updated", "department": {**doc_ref.get().to_dict(), 'id': dept_id}}

@router.delete("/departments/{dept_id}")
def delete_department(dept_id: str):
    doc_ref = db.collection('departments').document(dept_id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Department not found")
    
    # Manual cascade TODO: Files cleanup (omitted for brevity, requires iterating notes)
    # We will just do DB cleanup here. File cleanup requires note path lookup.
    
    delete_document_recursive(doc_ref)
    return {"message": "Department deleted"}

# ========== SEMESTERS ==========

@router.post("/semesters")
def create_semester(sem: SemesterCreate):
    """Create a semester with transactional parent validation."""
    from google.cloud import firestore as fs
    
    parent_ref = db.collection('departments').document(sem.department_id)
    
    @fs.transactional
    def create_in_transaction(transaction):
        # Transactional read of parent
        parent_doc = parent_ref.get(transaction=transaction)
        if not parent_doc.exists:
            raise HTTPException(status_code=404, detail="Department not found")
        
        # Read existing semesters (outside transaction scope but acceptable for prototype)
        coll = parent_ref.collection('semesters')
        docs = [d.to_dict() for d in coll.stream()]
        
        nums = [d.get('semester_number', 0) for d in docs]
        names = [d.get('name', '') for d in docs]
        
        next_num = get_next_available_number(nums)
        unique_name = get_unique_name(names, sem.name)
        
        new_ref = coll.document()
        data = {
            'name': unique_name,
            'semester_number': next_num,
            'department_id': sem.department_id,
            'id': new_ref.id
        }
        # Transactional write
        transaction.set(new_ref, data)
        return data
    
    transaction = db.transaction()
    data = create_in_transaction(transaction)
    return {"message": "Semester created", "semester": data}

@router.put("/semesters/{sem_id}")
def update_semester(sem_id: str, sem: SemesterUpdate):
    doc_ref = find_doc_by_id('semesters', sem_id)
    if not doc_ref:
        raise HTTPException(status_code=404, detail="Semester not found")
    
    updates = {k: v for k, v in sem.dict().items() if v is not None}
    if not updates: raise HTTPException(status_code=400, detail="No updates")
    
    if 'name' in updates:
        siblings_names = [d.to_dict().get('name') for d in doc_ref.parent.stream() if d.id != sem_id]
        updates['name'] = get_unique_name(siblings_names, updates['name'])

    doc_ref.update(updates)
    return {"message": "Semester updated", "semester": {**doc_ref.get().to_dict(), 'id': sem_id}}

@router.delete("/semesters/{sem_id}")
def delete_semester(sem_id: str):
    doc_ref = find_doc_by_id('semesters', sem_id)
    if not doc_ref:
        raise HTTPException(status_code=404, detail="Semester not found")
    
    delete_document_recursive(doc_ref)
    return {"message": "Semester deleted"}

# ========== SUBJECTS ==========

@router.post("/subjects")
def create_subject(subj: SubjectCreate):
    """Create a subject with transactional semester validation."""
    from google.cloud import firestore as fs
    
    parent_ref = find_doc_by_id('semesters', subj.semester_id)
    if not parent_ref:
        raise HTTPException(status_code=404, detail="Semester not found")
    
    @fs.transactional
    def create_in_transaction(transaction):
        coll = parent_ref.collection('subjects')
        docs = [d.to_dict() for d in coll.stream()]
        
        codes = [d.get('code', '') for d in docs]
        names = [d.get('name', '') for d in docs]
        
        code_to_use = subj.code
        if code_to_use in codes:
            code_to_use = get_next_available_code(codes, subj.code)
        unique_name = get_unique_name(names, subj.name)
        
        new_ref = coll.document()
        data = {
            'name': unique_name,
            'code': code_to_use,
            'semester_id': subj.semester_id,
            'id': new_ref.id
        }
        transaction.set(new_ref, data)
        return data
    
    transaction = db.transaction()
    data = create_in_transaction(transaction)
    return {"message": "Subject created", "subject": data}

@router.put("/subjects/{subj_id}")
def update_subject(subj_id: str, subj: SubjectUpdate):
    doc_ref = find_doc_by_id('subjects', subj_id)
    if not doc_ref: raise HTTPException(status_code=404, detail="Not found")
    
    updates = {k: v for k, v in subj.dict().items() if v is not None}
    if not updates: raise HTTPException(status_code=400, detail="No updates")

    if 'name' in updates:
        siblings_names = [d.to_dict().get('name') for d in doc_ref.parent.stream() if d.id != subj_id]
        updates['name'] = get_unique_name(siblings_names, updates['name'])

    doc_ref.update(updates)
    return {"message": "Updated", "subject": {**doc_ref.get().to_dict(), 'id': subj_id}}

@router.delete("/subjects/{subj_id}")
def delete_subject(subj_id: str):
    doc_ref = find_doc_by_id('subjects', subj_id)
    if not doc_ref: raise HTTPException(status_code=404, detail="Not found")
    delete_document_recursive(doc_ref)
    return {"message": "Deleted"}

# ========== MODULES ==========

@router.post("/modules")
def create_module(mod: ModuleCreate):
    """Create a module with transactional subject validation."""
    from google.cloud import firestore as fs
    
    parent_ref = find_doc_by_id('subjects', mod.subject_id)
    if not parent_ref:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    @fs.transactional
    def create_in_transaction(transaction):
        coll = parent_ref.collection('modules')
        docs = [d.to_dict() for d in coll.stream()]
        
        nums = [d.get('module_number', 0) for d in docs]
        names = [d.get('name', '') for d in docs]
        
        next_num = get_next_available_number(nums)
        unique_name = get_unique_name(names, mod.name)
        
        new_ref = coll.document()
        data = {
            'name': unique_name,
            'module_number': next_num,
            'subject_id': mod.subject_id,
            'id': new_ref.id
        }
        transaction.set(new_ref, data)
        return data
    
    transaction = db.transaction()
    data = create_in_transaction(transaction)
    return {"message": "Module created", "module": data}

@router.put("/modules/{mod_id}")
def update_module(mod_id: str, mod: ModuleUpdate):
    doc_ref = find_doc_by_id('modules', mod_id)
    if not doc_ref: raise HTTPException(status_code=404, detail="Not found")
    updates = {k: v for k, v in mod.dict().items() if v is not None}
    if not updates: raise HTTPException(status_code=400, detail="No updates")

    if 'name' in updates:
        siblings_names = [d.to_dict().get('name') for d in doc_ref.parent.stream() if d.id != mod_id]
        updates['name'] = get_unique_name(siblings_names, updates['name'])

    doc_ref.update(updates)
    return {"message": "Updated", "module": {**doc_ref.get().to_dict(), 'id': mod_id}}

@router.delete("/modules/{mod_id}")
def delete_module(mod_id: str):
    doc_ref = find_doc_by_id('modules', mod_id)
    if not doc_ref: raise HTTPException(status_code=404, detail="Not found")
    delete_document_recursive(doc_ref)
    return {"message": "Deleted"}

# ========== NOTES ==========

@router.put("/notes/{note_id}")
def update_note(note_id: str, note: NoteUpdate):
    doc_ref = find_doc_by_id('notes', note_id)
    if not doc_ref: raise HTTPException(status_code=404, detail="Not found")
    
    new_title = note.title
    siblings_titles = [d.to_dict().get('title') for d in doc_ref.parent.stream() if d.id != note_id]
    new_title = get_unique_name(siblings_titles, new_title)

    doc_ref.update({'title': new_title})
    return {"message": "Note renamed", "note": {**doc_ref.get().to_dict(), 'id': note_id}}

@router.delete("/notes/{note_id}")
def delete_note(note_id: str):
    doc_ref = find_doc_by_id('notes', note_id)
    if not doc_ref: raise HTTPException(status_code=404, detail="Not found")
    
    # Try delete file
    import os
    data = doc_ref.get().to_dict()
    pdf_url = data.get('pdf_url')
    if pdf_url:
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            clean_path = pdf_url.lstrip('/')
            file_path = os.path.join(base_dir, clean_path)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
            
    doc_ref.delete()
    return {"message": "Note deleted"}
