"""
Explorer API endpoints for React frontend.
Provides tree view of hierarchy and move/rename operations.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Literal
from enum import Enum

try:
    from db import execute_query, execute_one, PLACEHOLDER
except ImportError:
    import sys
    import os
    # Add project root to path if needed for direct execution
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from api.db import execute_query, execute_one, PLACEHOLDER

router = APIRouter(prefix="/api/explorer", tags=["explorer"])


# ========== MODELS ==========

class HierarchyType(str, Enum):
    department = "department"
    semester = "semester"
    subject = "subject"
    module = "module"
    note = "note"


class ExplorerNodeMeta(BaseModel):
    noteCount: Optional[int] = None
    hasChildren: bool = False
    ordering: Optional[int] = None
    pdfFilename: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    processing: bool = False
    code: Optional[str] = None


class ExplorerNode(BaseModel):
    id: str
    type: HierarchyType
    label: str
    parentId: Optional[str] = None
    children: Optional[List["ExplorerNode"]] = None
    meta: Optional[ExplorerNodeMeta] = None


class MoveRequest(BaseModel):
    nodeId: str
    nodeType: HierarchyType
    targetParentId: str
    targetParentType: HierarchyType


class MoveResponse(BaseModel):
    success: bool
    message: str
    node: Optional[ExplorerNode] = None


# ========== HELPER FUNCTIONS ==========

def _get_note_count_for_module(module_id: int) -> int:
    """Get count of notes for a module."""
    """Get count of notes for a module."""
    result = execute_one(f"SELECT COUNT(*) as cnt FROM notes WHERE module_id = {PLACEHOLDER}", (module_id,))
    return result['cnt'] if result else 0


def _get_child_count(entity_type: str, parent_id: int) -> int:
    """Get count of children for an entity."""
    """Get count of children for an entity."""
    queries = {
        'department': f"SELECT COUNT(*) as cnt FROM semesters WHERE department_id = {PLACEHOLDER}",
        'semester': f"SELECT COUNT(*) as cnt FROM subjects WHERE semester_id = {PLACEHOLDER}",
        'subject': f"SELECT COUNT(*) as cnt FROM modules WHERE subject_id = {PLACEHOLDER}",
        'module': f"SELECT COUNT(*) as cnt FROM notes WHERE module_id = {PLACEHOLDER}",
    }
    if entity_type not in queries:
        return 0
    result = execute_one(queries[entity_type], (parent_id,))
    return result['cnt'] if result else 0


def _build_notes_for_module(module_id: int, module_str_id: str) -> List[ExplorerNode]:
    """Build note nodes for a module."""
    notes = execute_query(
        f"SELECT id, title, pdf_url, created_at FROM notes WHERE module_id = {PLACEHOLDER} ORDER BY created_at DESC",
        (module_id,)
    ) or []
    
    result = []
    for note in notes:
        pdf_filename = None
        if note.get('pdf_url'):
            pdf_filename = note['pdf_url'].split('/')[-1] if '/' in note['pdf_url'] else note['pdf_url']
        
        result.append(ExplorerNode(
            id=f"note-{note['id']}",
            type=HierarchyType.note,
            label=note['title'] or f"Note {note['id']}",
            parentId=module_str_id,
            children=None,
            meta=ExplorerNodeMeta(
                hasChildren=False,
                pdfFilename=pdf_filename,
                createdAt=str(note['created_at']) if note.get('created_at') else None,
                processing=False
            )
        ))
    return result


def _build_modules_for_subject(subject_id: int, subject_str_id: str, include_notes: bool = True) -> List[ExplorerNode]:
    """Build module nodes for a subject."""
    modules = execute_query(
        f"SELECT id, module_number, name FROM modules WHERE subject_id = {PLACEHOLDER} ORDER BY module_number",
        (subject_id,)
    ) or []
    
    result = []
    for mod in modules:
        mod_str_id = f"module-{mod['id']}"
        note_count = _get_note_count_for_module(mod['id'])
        
        children = None
        if include_notes and note_count > 0:
            children = _build_notes_for_module(mod['id'], mod_str_id)
        
        result.append(ExplorerNode(
            id=mod_str_id,
            type=HierarchyType.module,
            label=mod['name'],
            parentId=subject_str_id,
            children=children,
            meta=ExplorerNodeMeta(
                hasChildren=note_count > 0,
                noteCount=note_count,
                ordering=mod['module_number']
            )
        ))
    return result


def _build_subjects_for_semester(semester_id: int, semester_str_id: str, include_children: bool = True) -> List[ExplorerNode]:
    """Build subject nodes for a semester."""
    subjects = execute_query(
        f"SELECT id, code, name FROM subjects WHERE semester_id = {PLACEHOLDER} ORDER BY name",
        (semester_id,)
    ) or []
    
    result = []
    for subj in subjects:
        subj_str_id = f"subject-{subj['id']}"
        child_count = _get_child_count('subject', subj['id'])
        
        children = None
        if include_children and child_count > 0:
            children = _build_modules_for_subject(subj['id'], subj_str_id)
        
        result.append(ExplorerNode(
            id=subj_str_id,
            type=HierarchyType.subject,
            label=subj['name'],
            parentId=semester_str_id,
            children=children,
            meta=ExplorerNodeMeta(
                hasChildren=child_count > 0,
                code=subj['code']
            )
        ))
    return result


def _build_semesters_for_department(dept_id: int, dept_str_id: str, include_children: bool = True) -> List[ExplorerNode]:
    """Build semester nodes for a department."""
    semesters = execute_query(
        f"SELECT id, semester_number, name FROM semesters WHERE department_id = {PLACEHOLDER} ORDER BY semester_number",
        (dept_id,)
    ) or []
    
    result = []
    for sem in semesters:
        sem_str_id = f"semester-{sem['id']}"
        child_count = _get_child_count('semester', sem['id'])
        
        children = None
        if include_children and child_count > 0:
            children = _build_subjects_for_semester(sem['id'], sem_str_id)
        
        result.append(ExplorerNode(
            id=sem_str_id,
            type=HierarchyType.semester,
            label=sem['name'],
            parentId=dept_str_id,
            children=children,
            meta=ExplorerNodeMeta(
                hasChildren=child_count > 0,
                ordering=sem['semester_number']
            )
        ))
    return result


# ========== ENDPOINTS ==========

@router.get("/tree", response_model=List[ExplorerNode])
def get_explorer_tree(depth: int = 5):
    """
    Get the full hierarchy tree for the explorer.
    
    Args:
        depth: How many levels deep to fetch (1=departments only, 5=full tree including notes)
    
    Returns:
        List of department nodes with nested children
    """
    departments = execute_query("SELECT id, name, code FROM departments ORDER BY name") or []
    
    result = []
    for dept in departments:
        dept_str_id = f"department-{dept['id']}"
        child_count = _get_child_count('department', dept['id'])
        
        children = None
        if depth > 1 and child_count > 0:
            children = _build_semesters_for_department(
                dept['id'], 
                dept_str_id, 
                include_children=(depth > 2)
            )
        
        result.append(ExplorerNode(
            id=dept_str_id,
            type=HierarchyType.department,
            label=dept['name'],
            parentId=None,
            children=children,
            meta=ExplorerNodeMeta(
                hasChildren=child_count > 0,
                code=dept['code']
            )
        ))
    
    return result


@router.get("/children/{node_type}/{node_id}", response_model=List[ExplorerNode])
def get_node_children(node_type: HierarchyType, node_id: int):
    """
    Get immediate children of a node (for lazy loading).
    """
    parent_str_id = f"{node_type.value}-{node_id}"
    
    if node_type == HierarchyType.department:
        return _build_semesters_for_department(node_id, parent_str_id, include_children=False)
    elif node_type == HierarchyType.semester:
        return _build_subjects_for_semester(node_id, parent_str_id, include_children=False)
    elif node_type == HierarchyType.subject:
        return _build_modules_for_subject(node_id, parent_str_id, include_notes=False)
    elif node_type == HierarchyType.module:
        return _build_notes_for_module(node_id, parent_str_id)
    else:
        return []


@router.post("/move", response_model=MoveResponse)
def move_node(request: MoveRequest):
    """
    Move a node to a new parent.
    Validates that the move is allowed based on hierarchy rules.
    """
    # Parse IDs
    try:
        node_id = int(request.nodeId.split('-')[-1])
        target_id = int(request.targetParentId.split('-')[-1])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid node or target ID format")
    
    # Validate move rules
    allowed_moves = {
        HierarchyType.semester: HierarchyType.department,
        HierarchyType.subject: HierarchyType.semester,
        HierarchyType.module: HierarchyType.subject,
        HierarchyType.note: HierarchyType.module,
    }
    
    if request.nodeType not in allowed_moves:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot move {request.nodeType.value} nodes"
        )
    
    if allowed_moves[request.nodeType] != request.targetParentType:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot move {request.nodeType.value} to {request.targetParentType.value}. "
                   f"Expected parent type: {allowed_moves[request.nodeType].value}"
        )
    
    # Verify target parent exists
    parent_tables = {
        HierarchyType.department: "departments",
        HierarchyType.semester: "semesters",
        HierarchyType.subject: "subjects",
        HierarchyType.module: "modules",
    }
    
    parent_table = parent_tables[request.targetParentType]
    parent_exists = execute_one(f"SELECT id FROM {parent_table} WHERE id = {PLACEHOLDER}", (target_id,))
    if not parent_exists:
        raise HTTPException(status_code=404, detail=f"Target {request.targetParentType.value} not found")
    
    # Perform the move
    table_map = {
        HierarchyType.semester: ("semesters", "department_id"),
        HierarchyType.subject: ("subjects", "semester_id"),
        HierarchyType.module: ("modules", "subject_id"),
        HierarchyType.note: ("notes", "module_id"),
    }
    
    table, fk_column = table_map[request.nodeType]
    
    try:
        execute_query(
            f"UPDATE {table} SET {fk_column} = {PLACEHOLDER} WHERE id = {PLACEHOLDER}",
            (target_id, node_id)
        )
        
        return MoveResponse(
            success=True,
            message=f"Successfully moved {request.nodeType.value} to new {request.targetParentType.value}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Move failed: {str(e)}")


@router.get("/notes/{note_id}/status")
def get_note_status(note_id: int):
    """
    Get the processing status of a note.
    """
    note = execute_one(f"SELECT id, title, pdf_url, created_at FROM notes WHERE id = {PLACEHOLDER}", (note_id,))
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Determine status based on pdf_url presence
    has_pdf = bool(note.get('pdf_url'))
    
    return {
        "id": note_id,
        "title": note['title'],
        "status": "complete" if has_pdf else "processing",
        "pdfUrl": note.get('pdf_url'),
        "createdAt": note.get('created_at')
    }
