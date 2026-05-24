# Explorer & Hierarchy Fix Plan

**Source:** `reviews/explorer-review.md`  
**Date:** 2026-05-24  
**Scope:** Backend CRUD + API security, frontend explorer UI

---

## Overview

| Item | Detail |
|------|--------|
| **Total findings** | 6 Critical, 7 High, 14 Medium, 8 Low |
| **Plan scope** | All Critical + High + selected Medium (M-4, M-5, M-8, M-9) |
| **Effort estimate** | ~3–4 focused sessions |
| **Affected files** | `api/explorer.py`, `api/hierarchy_crud.py`, `api/hierarchy/router.py`, `api/notes.py`, `frontend/src/pages/ExplorerPage.tsx`, `frontend/src/components/explorer/GridView.tsx`, `frontend/src/components/explorer/SidebarTree.tsx`, `frontend/src/components/explorer/SelectionActionBar.tsx` |

---

## Prerequisites

1. Backend running on port 8000 (`python -m uvicorn main:app --reload --port 8000`)
2. Frontend dev server on port 5174 (`npm run dev` from `frontend/`)
3. `pytest` passing before changes (baseline)
4. `npm run lint` + `npm run build` passing before changes (baseline)

---

## Fix Group 1: Security — Unauthenticated Endpoints (Critical)

**Rationale:** Multiple endpoints expose the full academic hierarchy and allow destructive operations without any authentication. This is the highest-priority fix.

### 1a. C-3 — `list_subjects` missing auth

**File:** `api/hierarchy_crud.py:459`  
**Confirmed:** Line 96 of the router shows `list_subjects` has no `Depends(require_*)`.

**Before:**
```python
@router.get("/subjects")
def list_subjects(semester_id: str):
    """List all subjects for a specific semester."""
```

**After:**
```python
@router.get("/subjects")
def list_subjects(
    semester_id: str,
    user: FirestoreUser = Depends(require_staff_or_admin),
):
    """List all subjects for a specific semester."""
```

**Validation:** `pytest api/test_hierarchy_crud.py` or manual curl without token → 401.

---

### 1b. C-4 — `move_node` missing auth

**File:** `api/explorer.py:370–371`  
**Confirmed:** No auth dependency on the endpoint.

**Before:**
```python
@router.post("/move", response_model=MoveResponse)
def move_node(request: MoveRequest):
```

**After:**
```python
@router.post("/move", response_model=MoveResponse)
def move_node(
    request: MoveRequest,
    user: FirestoreUser = Depends(require_admin),
):
```

Add import at top of file:
```python
try:
    from auth import require_admin, FirestoreUser
except (ImportError, ModuleNotFoundError):
    from api.auth import require_admin, FirestoreUser
```

**Validation:** curl POST `/api/explorer/move` without token → 401.

---

### 1c. C-5 — Hierarchy navigation endpoints missing auth

**File:** `api/hierarchy/router.py:67–182`  
**Confirmed:** All four endpoints (`get_departments`, `get_semesters`, `get_subjects`, `get_modules`) have no auth.

**Before:**
```python
@router.get("/departments", response_model=DepartmentListResponse)
def get_departments() -> DepartmentListResponse:
```

**After:**
```python
from fastapi import Depends
try:
    from auth import require_staff_or_admin, FirestoreUser
except (ImportError, ModuleNotFoundError):
    from api.auth import require_staff_or_admin, FirestoreUser

@router.get("/departments", response_model=DepartmentListResponse)
def get_departments(
    user: FirestoreUser = Depends(require_staff_or_admin),
) -> DepartmentListResponse:
```

Apply the same `Depends(require_staff_or_admin)` to `get_semesters`, `get_subjects`, and `get_modules`.

**Validation:** curl each endpoint without token → 401.

---

## Fix Group 2: Data Integrity — Move Operation (Critical)

**Rationale:** `move_node` generates new Firestore document IDs but doesn't update the `id` field inside the document data, breaking all FK lookups via `find_doc_by_id`.

### 2a. C-1 — Move creates new IDs without updating stored `id` field

**File:** `api/explorer.py:410–424`  
**Confirmed:** `new_ref = target_parent_ref.collection(source_coll_name).document()` generates a new ID. `data` retains the old `id` field.

**Before (line 411–424):**
```python
new_ref = target_parent_ref.collection(source_coll_name).document()
data = source_ref.get().to_dict()
if data is None:
    raise ValueError(f"Source document not found: {source_ref.id}")
fk_map = { ... }
if request.nodeType in fk_map:
    data[fk_map[request.nodeType]] = request.targetParentId
new_ref.set(data)
```

**After:**
```python
new_ref = target_parent_ref.collection(source_coll_name).document()
data = source_ref.get().to_dict()
if data is None:
    raise ValueError(f"Source document not found: {source_ref.id}")
fk_map = { ... }
if request.nodeType in fk_map:
    data[fk_map[request.nodeType]] = request.targetParentId
data["id"] = new_ref.id  # Update stored ID to match new document ID
new_ref.set(data)
```

### 2b. H-6 — `copy_children` doesn't update `id` field for children

**File:** `api/explorer.py:426–438`  
**Confirmed:** `new_child_ref = dest.collection(coll.id).document()` generates new IDs but `child_data` retains old `id`.

**Before:**
```python
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
```

**After:**
```python
def copy_children(src, dest, ancestor_fks=None):
    if ancestor_fks is None:
        ancestor_fks = {}
    for coll in src.collections():
        for doc in coll.stream():
            new_child_ref = dest.collection(coll.id).document()
            child_data = doc.to_dict()
            # Update FK to immediate parent
            if coll.id == "subjects":
                child_data["semester_id"] = dest.id
            elif coll.id == "modules":
                child_data["subject_id"] = dest.id
            elif coll.id == "notes":
                child_data["module_id"] = dest.id
            # Update stored ID to match new document ID
            child_data["id"] = new_child_ref.id
            new_child_ref.set(child_data)
            copy_children(doc.reference, new_child_ref, ancestor_fks)
```

**Validation:** Move a node, then query `find_doc_by_id` for the moved node and its children — all should resolve correctly.

---

## Fix Group 3: Silent Error Swallowing (Critical)

### 3. C-6 — `delete_document_recursive` silently swallows file deletion errors

**File:** `api/hierarchy_crud.py:166–185`  
**Confirmed:** `except Exception: pass` at line 183–184.

**Before:**
```python
if pdf_url:
    try:
        clean_path = pdf_url.lstrip("/")
        file_path = os.path.join(base_dir, clean_path)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass
```

**After:**
```python
if pdf_url:
    try:
        clean_path = pdf_url.lstrip("/")
        file_path = os.path.join(base_dir, clean_path)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logger.warning(f"Failed to delete PDF {pdf_url}: {e}")
```

Ensure `logger` is imported at top of file (already is — `import logging` present).

**Validation:** Temporarily lock a PDF file, delete its parent node, check logs for warning.

---

## Fix Group 4: Transactional Integrity (Critical + High)

### 4. C-2 / H-1 — Sibling reads outside transaction scope

**File:** `api/hierarchy_crud.py:381–410`  
**Confirmed:** `coll.stream()` at line 390 is outside the transaction.

**Before:**
```python
@fs.transactional
def create_in_transaction(transaction):
    parent_doc = parent_ref.get(transaction=transaction)
    if not parent_doc.exists:
        raise HTTPException(status_code=404, detail="Department not found")
    coll = parent_ref.collection("semesters")
    docs = [d.to_dict() for d in coll.stream()]  # NOT transactional
```

**After (option A — document as known limitation with comment):**
```python
@fs.transactional
def create_in_transaction(transaction):
    parent_doc = parent_ref.get(transaction=transaction)
    if not parent_doc.exists:
        raise HTTPException(status_code=404, detail="Department not found")
    # NOTE: Sibling reads are outside the transaction scope.
    # Firestore transactions only track reads via transaction.get().
    # This means duplicate detection is best-effort under concurrent creates.
    # For production, consider a mutex or unique index on (parent_id, name).
    coll = parent_ref.collection("semesters")
    docs = [d.to_dict() for d in coll.stream()]
```

Apply the same comment to `create_subject` (line ~484) and `create_module` (line ~565).

**Validation:** Accept as documented limitation. For full fix, add an application-level lock or Firestore `@google.cloud.firestore` unique document constraint.

---

## Fix Group 5: Pydantic Validation (High)

### 5. H-3 — No input validation on create models

**File:** `api/hierarchy_crud.py:221–263`  
**Confirmed:** All create models have bare `str` / `int` fields with no constraints.

**Before:**
```python
class DepartmentCreate(BaseModel):
    name: str
    code: str

class SemesterCreate(BaseModel):
    department_id: str
    semester_number: int
    name: str

class SubjectCreate(BaseModel):
    semester_id: str
    name: str
    code: str

class ModuleCreate(BaseModel):
    subject_id: str
    module_number: int
    name: str
```

**After:**
```python
from pydantic import Field

class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=1, max_length=50)

class SemesterCreate(BaseModel):
    department_id: str
    semester_number: int = Field(..., ge=1, le=12)
    name: str = Field(..., min_length=1, max_length=200)

class SubjectCreate(BaseModel):
    semester_id: str
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=1, max_length=50)

class ModuleCreate(BaseModel):
    subject_id: str
    module_number: int = Field(..., ge=1, le=100)
    name: str = Field(..., min_length=1, max_length=200)
```

**Validation:** Send empty name → 422 validation error. Send negative semester_number → 422.

---

## Fix Group 6: Async/Sync Mixing (High)

### 6. H-4 — `delete_note_cascade` fragile asyncio pattern

**File:** `api/hierarchy_crud.py:710–777`  
**Confirmed:** Sync endpoint uses `asyncio.run_coroutine_threadsafe` / `loop.run_until_complete` / `asyncio.run` cascade.

**Before:**
```python
@router.delete("/notes/{note_id}/cascade")
def delete_note_cascade(note_id: str, ...):
    ...
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(graph_manager.delete_document(note_id), loop)
            success, _ = future.result(timeout=30)
        else:
            success, _ = loop.run_until_complete(graph_manager.delete_document(note_id))
    except RuntimeError:
        success, _ = asyncio.run(graph_manager.delete_document(note_id))
```

**After:**
```python
@router.delete("/notes/{note_id}/cascade")
async def delete_note_cascade(note_id: str, ...):
    ...
    graph_manager = GraphManager(neo4j_driver)
    success, _ = await graph_manager.delete_document(note_id)
```

This is the cleanest fix since FastAPI natively supports async handlers. The sync Firestore reads (`find_doc_by_id`, `doc_ref.get()`) also work in async context (they block the thread but are fast).

**Validation:** Test cascade delete on a note with `kg_status='ready'` — should complete without hanging.

---

## Fix Group 7: DRY Violation (High)

### 7. H-2 — `get_unique_name` / `get_next_available_number` duplicated

**Files:** `api/hierarchy_crud.py:126–151`, `api/notes.py:68–86`  
**Confirmed:** Identical implementations in both files.

**Action:** Create `api/utils.py` with both functions, then import from both files.

**`api/utils.py` (new file):**
```python
"""Shared utility functions for hierarchy and notes modules."""

import re


def get_next_available_number(numbers: list[int]) -> int:
    """Find the next available sequential number (max + 1)."""
    if not numbers:
        return 1
    return max(numbers) + 1


def get_unique_name(names: list[str], base_name: str) -> str:
    """Generate unique name with (N) suffix for duplicates."""
    if base_name not in names:
        return base_name

    suffix_numbers = [1]
    pattern = re.compile(rf"^{re.escape(base_name)} \((\d+)\)$")
    for n in names:
        match = pattern.match(n)
        if match:
            suffix_numbers.append(int(match.group(1)))

    next_suffix = get_next_available_number(suffix_numbers)
    if next_suffix == 1:
        next_suffix = 2
    return f"{base_name} ({next_suffix})"
```

**In `api/hierarchy_crud.py`:** Remove the local definitions, add:
```python
try:
    from utils import get_next_available_number, get_unique_name
except (ImportError, ModuleNotFoundError):
    from api.utils import get_next_available_number, get_unique_name
```

**In `api/notes.py`:** Same import replacement.

**Validation:** `pytest` — all existing tests should pass unchanged.

---

## Fix Group 8: Cascade Delete UX (High)

### 8a. H-5 — No scope warning for cascade deletion

**File:** `frontend/src/pages/ExplorerPage.tsx:121–150`  
**Confirmed:** Delete confirmation uses a generic message.

**Before (line 121–125):**
```typescript
const handleDeleteConfirm = async () => {
    if (!nodeToDelete) return;
    const { id, type } = nodeToDelete;
    closeDeleteDialog();
```

**After:** Add scope warning in the confirmation dialog (the dialog component should be updated to show the message, or add a pre-confirm step):
```typescript
const getCascadeWarning = (type: string): string => {
    switch (type) {
        case 'department':
            return 'This will permanently delete all semesters, subjects, modules, notes, and PDFs under this department.';
        case 'semester':
            return 'This will permanently delete all subjects, modules, notes, and PDFs under this semester.';
        case 'subject':
            return 'This will permanently delete all modules, notes, and PDFs under this subject.';
        case 'module':
            return 'This will permanently delete all notes and PDFs under this module.';
        default:
            return 'This action cannot be undone.';
    }
};
```

Integrate this message into the existing `ConfirmDialog` or `openWarningDialog` pattern.

---

### 8b. H-7 — Bulk delete lacks confirmation

**File:** `frontend/src/components/explorer/SelectionActionBar.tsx:222–265`  
**Confirmed:** `handleDelete` starts deleting immediately without any confirmation dialog.

**Before (line 222–229):**
```typescript
const handleDelete = async () => {
    const tree = queryClient.getQueryData<FileSystemNode[]>(['explorer', 'tree']) || [];
    const nodes = findNodesByIds(tree, selectedIds);
    const noteIds = nodes.filter(n => n.type === 'note').map(n => n.id);
    if (noteIds.length === 0) return;
    setIsDeleting(true);
```

**After:**
```typescript
const handleDelete = async () => {
    const tree = queryClient.getQueryData<FileSystemNode[]>(['explorer', 'tree']) || [];
    const nodes = findNodesByIds(tree, selectedIds);
    const noteIds = nodes.filter(n => n.type === 'note').map(n => n.id);
    if (noteIds.length === 0) return;

    const confirmed = window.confirm(
        `Are you sure you want to delete ${noteIds.length} note(s)? This will also remove their PDF files and knowledge graph data. This action cannot be undone.`
    );
    if (!confirmed) return;

    setIsDeleting(true);
```

Replace `window.confirm` with the project's `ConfirmDialog` component if available.

**Validation:** Select multiple notes, click delete — confirmation should appear before deletion starts.

---

## Fix Group 9: Sidebar Hardcoded Numbers (Medium)

### 9a. M-8 — `SidebarTree` hardcodes `semester_number=1`

**File:** `frontend/src/components/explorer/SidebarTree.tsx:105`  
**Confirmed:** `await api.createSemester(parentId!, 1, name);`

**Before:**
```typescript
case 'semester':
    await api.createSemester(parentId!, 1, name);
    break;
```

**After:** Calculate the next number from siblings (same logic as GridView):
```typescript
case 'semester': {
    const siblings = nodes.filter(n => n.type === 'semester');
    let semNum = 1;
    if (siblings.length > 0) {
        const numbers = siblings.map(s => {
            const match = s.label.match(/\d+/);
            return match ? parseInt(match[0]) : 0;
        });
        semNum = Math.max(...numbers, siblings.length) + 1;
    }
    await api.createSemester(parentId!, semNum, name);
    break;
}
```

Note: `nodes` needs to be accessible in `CreationItem`. It's passed as a prop to `SidebarTree` but `CreationItem` doesn't receive it. Pass `nodes` as a prop to `CreationItem` or use the query cache.

### 9b. M-9 — `SidebarTree` hardcodes `module_number=1`

**File:** `frontend/src/components/explorer/SidebarTree.tsx:113`  
**Confirmed:** `await api.createModule(parentId!, 1, name);`

**Before:**
```typescript
case 'module':
    await api.createModule(parentId!, 1, name);
    break;
```

**After:**
```typescript
case 'module': {
    const siblings = nodes.filter(n => n.type === 'module');
    const modNum = siblings.length + 1;
    await api.createModule(parentId!, modNum, name);
    break;
}
```

**Validation:** Create a semester from the sidebar — number should increment correctly, not always be 1.

---

## Fix Group 10: Replace `alert()` with Toast (Medium)

### 10. M-4 — Multiple files use `alert()` for error handling

**Files:**
- `frontend/src/pages/ExplorerPage.tsx:148`
- `frontend/src/components/explorer/GridView.tsx:140, 208`
- `frontend/src/components/explorer/SidebarTree.tsx:123`
- `frontend/src/components/explorer/SelectionActionBar.tsx:104, 170, 185, 261, 263`

**Action:** Replace all `alert()` calls with `toast.error()` from `sonner` (already used in `UploadDialog.tsx`):
```typescript
import { toast } from 'sonner';

// Before
alert(`Failed to delete: ${(error as Error).message}`);

// After
toast.error(`Failed to delete: ${(error as Error).message}`);
```

For success messages, use `toast.success()`.

**Validation:** Trigger each error path — toast should appear instead of browser alert.

---

## Fix Group 11: Admin Redirect Anti-Pattern (Medium)

### 11. M-5 — `useEffect` redirect causes flash

**File:** `frontend/src/pages/ExplorerPage.tsx:84–88`  
**Confirmed:** `useEffect` with `navigate('/admin')` causes a render flash.

**Action:** Move the redirect to the router configuration. In the route definition for `/explorer`, add a guard:
```typescript
// In router config
{
    path: '/explorer',
    element: isAdmin() ? <Navigate to="/admin" replace /> : <ExplorerPage />,
}
```

Or use a `ProtectedRoute` wrapper that handles role-based redirects.

**Validation:** Log in as admin, navigate to `/explorer` — should redirect without flash.

---

## Fix Group 12: Redundant Auth Check (Medium)

### 12. M-3 — Double auth check on department endpoints

**File:** `api/hierarchy_crud.py:279–293, 312–326, 349–365`  
**Confirmed:** `require_staff_or_admin` dependency + manual `if user.role not in ("admin",):` check.

**Before:**
```python
def create_department(
    dept: DepartmentCreate,
    user: FirestoreUser = Depends(require_staff_or_admin),
):
    if user.role not in ("admin",):
        raise HTTPException(...)
```

**After:**
```python
def create_department(
    dept: DepartmentCreate,
    user: FirestoreUser = Depends(require_admin),
):
```

Apply to `update_department` and `delete_department` as well.

**Validation:** Staff user tries to create department → 403 from the dependency, not the manual check.

---

## Fix Group 13: Fragile Semester Number Calculation (Medium)

### 13. M-7 — GridView extracts semester number from label via regex

**File:** `frontend/src/components/explorer/GridView.tsx:174–186`  
**Confirmed:** `s.label.match(/\d+/)` to extract semester number.

**Before:**
```typescript
const numbers = existingSemesters.map(s => {
    const match = s.label.match(/\d+/);
    return match ? parseInt(match[0]) : 0;
});
semNum = Math.max(...numbers, existingSemesters.length) + 1;
```

**After:** Use `meta.ordering` or `meta.semester_number` from the node data:
```typescript
const numbers = existingSemesters.map(s => s.meta?.semester_number ?? s.meta?.ordering ?? 0);
semNum = Math.max(...numbers, existingSemesters.length) + 1;
```

Check that `ExplorerNodeMeta` includes `semester_number` (it does — `explorer.py:266` sets `ordering=data.get("semester_number")`).

**Validation:** Rename a semester to "Fall 2026", create a new semester — number should not be 2027.

---

## Verification Checklist

- [ ] All endpoints return 401/403 without valid token
- [ ] `move_node` preserves document IDs (query by `id` field works after move)
- [ ] `copy_children` updates `id` field for all descendants
- [ ] `delete_document_recursive` logs file deletion failures
- [ ] Create functions have documented transaction limitation
- [ ] Pydantic models reject empty/negative/oversized inputs
- [ ] `delete_note_cascade` uses `async` + `await`
- [ ] `get_unique_name` exists only in `api/utils.py`
- [ ] Cascade delete confirmation shows scope warning
- [ ] Bulk delete shows confirmation before starting
- [ ] Sidebar create uses calculated numbers, not hardcoded `1`
- [ ] No `alert()` calls remain in explorer components
- [ ] Admin redirect happens at router level
- [ ] Department CRUD uses `require_admin` directly
- [ ] `pytest` passes (backend)
- [ ] `npm run lint` passes (frontend)
- [ ] `npm run build` passes (frontend)

---

## Risk Notes

1. **C-1/C-2 move fix** — Existing moved documents in production may already have mismatched IDs. A migration script may be needed to reconcile `id` fields with document IDs.
2. **C-5 hierarchy auth** — AURA-CHAT proxy may call these endpoints. Verify it sends auth tokens before deploying.
3. **H-4 async refactor** — Changing `delete_note_cascade` from sync to async may affect any middleware or dependency injection that assumes sync. Test thoroughly.
4. **H-7 bulk delete confirm** — Using `window.confirm` is a quick fix; replace with the project's dialog system for consistency.
5. **M-8/M-9 sidebar numbers** — Requires passing sibling data to `CreationItem`, which may need prop threading or query cache access.
6. **L-1 dead code** — `_ensure_explorer_node_model()` is never called. Safe to remove, but verify Pydantic v2 auto-rebuilds recursive models first.

---

## Deferred (Low Priority)

| ID | Finding | Reason |
|----|---------|--------|
| M-1 | Full tree fetch without pagination | Performance issue, not a bug. Defer to production optimization pass. |
| M-2 | In-memory pagination in ModuleService | Same — performance, not correctness. |
| M-10 | `document.querySelectorAll` in SelectionOverlay | Works correctly, just a code smell. |
| M-11 | ContextMenu accessibility | Important but not blocking. Defer to a11y audit. |
| M-12 | No file size validation on upload | Add in a follow-up security hardening pass. |
| M-13 | Stale cache in SelectionActionBar | Acceptable for prototype. |
| M-14 | Duplicated selection logic | Refactor in a shared hook pass. |
| L-1 | Dead `_ensure_explorer_node_model` | Remove opportunistically. |
| L-2 | Greedy prefix matching | Edge case, safe with current data. |
| L-3 | `created_at` format inconsistency | Standardize in a data model cleanup pass. |
| L-4 | `importlib.util` loading | Works, fragile but not broken. |
| L-5 | Code from name heuristic | Works for prototype. |
| L-6 | Missing key prop in SelectionOverlay | Not currently a bug. |
| L-7 | No staleTime on tree query | Optimization, not a bug. |
| L-8 | ContextMenu note creation UX | Minor UX issue. |
