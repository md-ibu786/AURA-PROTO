"""
============================================================================
FILE: explorer.py
LOCATION: api/explorer.py
============================================================================

PURPOSE:
    Provides async API endpoints for the React file explorer interface.
    Delivers the full hierarchy tree structure and supports lazy-loading
    of children for efficient rendering of large hierarchies.

ROLE IN PROJECT:
    This is the primary API consumed by the React frontend's SidebarTree
    and main content area. It transforms Firestore's nested subcollections
    into the ExplorerNode tree structure expected by the frontend.

    Key features:
    - Async operations using asyncio.gather for parallel fetching
    - Lazy loading support via /children endpoint
    - Move operations with copy-delete (required by Firestore)

KEY COMPONENTS:
    Models:
    - HierarchyType: Enum for node types (department, semester, subject, module, note)
    - ExplorerNode: Main tree node structure with type, label, children, metadata
    - ExplorerNodeMeta: Additional metadata (noteCount, hasChildren, pdfFilename, etc.)
    - MoveRequest/MoveResponse: For node move operations

    Async Helpers (parallel fetching):
    - _build_single_department_async: Build one department with children
    - _build_semesters_async: Build all semesters for a department
    - _build_subjects_async: Build all subjects for a semester
    - _build_modules_async: Build all modules for a subject
    - _build_notes_async: Build all notes for a module

    Endpoints:
    - GET /api/explorer/tree: Full hierarchy tree (async, parallel)
    - GET /api/explorer/children/{type}/{id}: Lazy load children
    - POST /api/explorer/move: Move node to new parent

DEPENDENCIES:
    - External: fastapi, pydantic, asyncio, google-cloud-firestore
    - Internal: config.py (db, async_db clients)

USAGE:
    # Frontend fetch
    const response = await fetch('/api/explorer/tree?depth=5');
    const nodes = await response.json();
============================================================================
"""

import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum
from google.cloud import firestore

try:
    from config import db, async_db
except (ImportError, ModuleNotFoundError):
    try:
        from .config import db, async_db
    except (ImportError, ModuleNotFoundError):
        from api.config import db, async_db

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


# ========== ASYNC HELPER FUNCTIONS ==========


async def _get_note_count_async(module_path: str) -> int:
    """Count notes in a module asynchronously."""
    notes_ref = async_db.collection(f"{module_path}/notes")
    docs = [d async for d in notes_ref.stream()]
    return len(docs)


async def _has_children_async(parent_path: str, child_collection: str) -> bool:
    """Check if parent has any children in specified collection."""
    coll_ref = async_db.collection(f"{parent_path}/{child_collection}")
    docs = [d async for d in coll_ref.limit(1).stream()]
    return len(docs) > 0


async def _build_notes_async(module_path: str, module_id: str) -> List[ExplorerNode]:
    """Build note nodes for a module asynchronously."""
    notes_ref = async_db.collection(f"{module_path}/notes").order_by(
        "created_at", direction=firestore.Query.DESCENDING
    )
    result = []
    async for note in notes_ref.stream():
        data = note.to_dict()
        pdf_url = data.get("pdf_url")
        pdf_filename = pdf_url.split("/")[-1] if pdf_url else None

        result.append(
            ExplorerNode(
                id=note.id,
                type=HierarchyType.note,
                label=data.get("title", f"Note {note.id}"),
                parentId=module_id,
                meta=ExplorerNodeMeta(
                    hasChildren=False,
                    pdfFilename=pdf_filename,
                    createdAt=str(data.get("created_at"))
                    if data.get("created_at")
                    else None,
                    processing=False,
                ),
            )
        )
    return result


async def _build_single_module_async(
    mod_doc, subject_id: str, subject_path: str, include_children: bool
) -> ExplorerNode:
    """Build a single module node."""
    data = mod_doc.to_dict()
    node_id = mod_doc.id
    module_path = f"{subject_path}/modules/{node_id}"

    note_count = await _get_note_count_async(module_path)
    children = None
    if include_children and note_count > 0:
        children = await _build_notes_async(module_path, node_id)

    return ExplorerNode(
        id=node_id,
        type=HierarchyType.module,
        label=data.get("name"),
        parentId=subject_id,
        children=children,
        meta=ExplorerNodeMeta(
            hasChildren=note_count > 0,
            noteCount=note_count,
            ordering=data.get("module_number"),
        ),
    )


async def _build_modules_async(
    subject_path: str, subject_id: str, include_children: bool = True
) -> List[ExplorerNode]:
    """Build all module nodes for a subject asynchronously with parallel fetching."""
    modules_ref = async_db.collection(f"{subject_path}/modules").order_by(
        "module_number"
    )
    mod_docs = [d async for d in modules_ref.stream()]

    # Parallel build of each module
    tasks = [
        _build_single_module_async(doc, subject_id, subject_path, include_children)
        for doc in mod_docs
    ]
    return await asyncio.gather(*tasks)


async def _build_single_subject_async(
    subj_doc, semester_id: str, semester_path: str, include_children: bool
) -> ExplorerNode:
    """Build a single subject node."""
    data = subj_doc.to_dict()
    node_id = subj_doc.id
    subject_path = f"{semester_path}/subjects/{node_id}"

    has_kids = await _has_children_async(subject_path, "modules")
    children = None
    if include_children and has_kids:
        children = await _build_modules_async(
            subject_path, node_id, include_children=include_children
        )

    return ExplorerNode(
        id=node_id,
        type=HierarchyType.subject,
        label=data.get("name"),
        parentId=semester_id,
        children=children,
        meta=ExplorerNodeMeta(hasChildren=has_kids, code=data.get("code")),
    )


async def _build_subjects_async(
    semester_path: str, semester_id: str, include_children: bool = True
) -> List[ExplorerNode]:
    """Build all subject nodes for a semester asynchronously with parallel fetching."""
    subjects_ref = async_db.collection(f"{semester_path}/subjects").order_by("name")
    subj_docs = [d async for d in subjects_ref.stream()]

    tasks = [
        _build_single_subject_async(doc, semester_id, semester_path, include_children)
        for doc in subj_docs
    ]
    return await asyncio.gather(*tasks)


async def _build_single_semester_async(
    sem_doc, dept_id: str, dept_path: str, include_children: bool
) -> ExplorerNode:
    """Build a single semester node."""
    data = sem_doc.to_dict()
    node_id = sem_doc.id
    semester_path = f"{dept_path}/semesters/{node_id}"

    has_kids = await _has_children_async(semester_path, "subjects")
    children = None
    if include_children and has_kids:
        children = await _build_subjects_async(
            semester_path, node_id, include_children=include_children
        )

    return ExplorerNode(
        id=node_id,
        type=HierarchyType.semester,
        label=data.get("name"),
        parentId=dept_id,
        children=children,
        meta=ExplorerNodeMeta(
            hasChildren=has_kids, ordering=data.get("semester_number")
        ),
    )


async def _build_semesters_async(
    dept_path: str, dept_id: str, include_children: bool = True
) -> List[ExplorerNode]:
    """Build all semester nodes for a department asynchronously with parallel fetching."""
    semesters_ref = async_db.collection(f"{dept_path}/semesters").order_by(
        "semester_number"
    )
    sem_docs = [d async for d in semesters_ref.stream()]

    tasks = [
        _build_single_semester_async(doc, dept_id, dept_path, include_children)
        for doc in sem_docs
    ]
    return await asyncio.gather(*tasks)


async def _build_single_department_async(dept_doc, depth: int) -> ExplorerNode:
    """Build a single department node."""
    data = dept_doc.to_dict()
    node_id = dept_doc.id
    dept_path = f"departments/{node_id}"

    has_kids = await _has_children_async(dept_path, "semesters")
    children = None
    if depth > 1 and has_kids:
        children = await _build_semesters_async(
            dept_path, node_id, include_children=(depth > 2)
        )

    return ExplorerNode(
        id=node_id,
        type=HierarchyType.department,
        label=data.get("name"),
        parentId=None,
        children=children,
        meta=ExplorerNodeMeta(hasChildren=has_kids, code=data.get("code")),
    )


# Sync helper for find_doc_ref (unchanged, uses sync db for simplicity in move/delete)
def find_doc_ref_sync(collection_name: str, doc_id: str):
    """Find a document reference by ID using collection group query (sync)."""
    if collection_name == "departments":
        doc = db.collection("departments").document(doc_id).get()
        return doc.reference if doc.exists else None

    docs = list(db.collection_group(collection_name).where("id", "==", doc_id).stream())
    return docs[0].reference if docs else None


# ========== ASYNC ENDPOINTS ==========


@router.get("/tree", response_model=List[ExplorerNode])
async def get_explorer_tree(depth: int = 5):
    """Get the full hierarchy tree asynchronously with parallel fetching."""
    depts_ref = async_db.collection("departments").order_by("name")
    dept_docs = [d async for d in depts_ref.stream()]

    # Build all departments in parallel
    tasks = [_build_single_department_async(doc, depth) for doc in dept_docs]
    return await asyncio.gather(*tasks)


@router.get("/children/{node_type}/{node_id}", response_model=List[ExplorerNode])
async def get_node_children(node_type: HierarchyType, node_id: str):
    """Get immediate children of a node (lazy loading) asynchronously."""
    # Use sync find for simplicity, then async build
    coll_map = {
        HierarchyType.department: "departments",
        HierarchyType.semester: "semesters",
        HierarchyType.subject: "subjects",
        HierarchyType.module: "modules",
    }

    if node_type not in coll_map:
        return []

    parent_ref = find_doc_ref_sync(coll_map[node_type], node_id)
    if not parent_ref:
        raise HTTPException(status_code=404, detail="Node not found")

    parent_path = parent_ref.path

    if node_type == HierarchyType.department:
        return await _build_semesters_async(
            parent_path, node_id, include_children=False
        )
    elif node_type == HierarchyType.semester:
        return await _build_subjects_async(parent_path, node_id, include_children=False)
    elif node_type == HierarchyType.subject:
        return await _build_modules_async(parent_path, node_id, include_children=False)
    elif node_type == HierarchyType.module:
        return await _build_notes_async(parent_path, node_id)
    return []


# ========== SYNC ENDPOINTS (Move, Status) - Unchanged logic ==========


@router.post("/move", response_model=MoveResponse)
def move_node(request: MoveRequest):
    """
    Move a node to a new parent.
    NOTE: Firestore requires copy-delete for moving between subcollections.
    This implementation handles it recursively.
    """
    target_coll_type_map = {
        HierarchyType.semester: "departments",
        HierarchyType.subject: "semesters",
        HierarchyType.module: "subjects",
        HierarchyType.note: "modules",
    }

    if request.nodeType not in target_coll_type_map:
        raise HTTPException(status_code=400, detail="Invalid node type for move")

    target_type = request.targetParentType
    manual_map = {
        HierarchyType.semester: HierarchyType.department,
        HierarchyType.subject: HierarchyType.semester,
        HierarchyType.module: HierarchyType.subject,
        HierarchyType.note: HierarchyType.module,
    }

    if manual_map[request.nodeType] != target_type:
        raise HTTPException(status_code=400, detail="Invalid target parent type")

    source_coll_name = f"{request.nodeType.value}s"
    source_ref = find_doc_ref_sync(source_coll_name, request.nodeId)
    if not source_ref:
        raise HTTPException(status_code=404, detail="Source node not found")

    target_parent_coll_name = f"{target_type.value}s"
    target_parent_ref = find_doc_ref_sync(
        target_parent_coll_name, request.targetParentId
    )
    if not target_parent_ref:
        raise HTTPException(status_code=404, detail="Target parent not found")

    try:
        new_ref = target_parent_ref.collection(source_coll_name).document()
        data = source_ref.get().to_dict()
        fk_map = {
            HierarchyType.semester: "department_id",
            HierarchyType.subject: "semester_id",
            HierarchyType.module: "subject_id",
            HierarchyType.note: "module_id",
        }
        if request.nodeType in fk_map:
            data[fk_map[request.nodeType]] = request.targetParentId

        new_ref.set(data)

        def copy_children(src, dest):
            for coll in src.collections():
                for doc in coll.stream():
                    new_child_ref = dest.collection(coll.id).document()
                    child_data = doc.to_dict()
                    if coll.id == "subjects":
                        child_data["semester_id"] = dest.id
                    elif coll.id == "modules":
                        child_data["subject_id"] = dest.id
                    elif coll.id == "notes":
                        child_data["module_id"] = dest.id
                    new_child_ref.set(child_data)
                    copy_children(doc.reference, new_child_ref)

        copy_children(source_ref, new_ref)

        def delete_recursive(doc):
            for coll in doc.collections():
                for d in coll.stream():
                    delete_recursive(d.reference)
            doc.delete()

        delete_recursive(source_ref)

        return MoveResponse(success=True, message="Node moved via copy-delete")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Move failed: {str(e)}")


# Rebuild model for Pydantic v2 recursive references
ExplorerNode.model_rebuild()
