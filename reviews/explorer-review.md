# Explorer & Hierarchy Management Pipeline Review

**Reviewer:** Review Subagent  
**Date:** 2026-05-24  
**Scope:** Full-stack explorer pipeline (backend CRUD, frontend UI, state management)

---

## Summary

The explorer and hierarchy pipeline is a well-structured dual-layer system with clear separation between CRUD (`hierarchy_crud.py`), read-only navigation (`hierarchy.py`, `hierarchy/router.py`), and frontend explorer UI. The architecture follows reasonable patterns with parallel async fetching, transactional creates, and role-based access control.

However, there are several issues ranging from race conditions in duplicate detection to missing authentication on read endpoints and inconsistent validation models. The most critical concern is that the `move_node` operation generates new document IDs for all moved nodes, silently breaking external references.

**Total findings: 6 Critical, 7 High, 14 Medium, 8 Low**

---

## Findings

### CRITICAL

---

#### C-1: Move Operation Breaks All Node IDs (Data Integrity)

**Files:** `api/explorer.py`, lines 275-330  
**Severity:** Critical

The `move_node` endpoint implements Firestore's required copy-delete pattern, but creates **new document IDs** for the moved node and every descendant:

```python
new_ref = target_parent_ref.collection(source_coll_name).document()  # NEW ID
data = source_ref.get().to_dict()
new_ref.set(data)

def copy_children(src, dest):
    for coll in src.collections():
        for doc in coll.stream():
            new_child_ref = dest.collection(coll.id).document()  # NEW ID
```

The FK fields (e.g., `semester_id`, `subject_id`, `module_id`) are updated to the parent's ID, but the **moved node's own `id` field** in the document data still contains the **old ID**. This means:

- The `id` field stored in the document no longer matches the Firestore document ID.
- `find_doc_by_id()` uses `FieldFilter("id", "==", doc_id)` which queries by the stored `id` field, not the document path. After a move, the stored `id` points to the old (deleted) document.
- External references (AURA-CHAT's `published_modules`, Neo4j KG nodes, note `subjectId`/`departmentId` fields) all become stale.
- All children get new document IDs but retain old `id` fields — creating a permanent inconsistency.

**Fix:** After `new_ref.set(data)`, update the `id` field to match `new_ref.id`:
```python
data["id"] = new_ref.id
new_ref.set(data)
```
Do the same for all recursively copied children. Also update all FK references in external systems.

---

#### C-2: Race Condition in Transactional Creates (Concurrency)

**Files:** `api/hierarchy_crud.py`, lines 374-417 (`create_semester`), 484-527 (`create_subject`), 565-604 (`create_module`)  
**Severity:** Critical

All create functions use `@fs.transactional` but read siblings **inside** the transaction while reading them via `.stream()` which is **not** a transactional read in Firestore:

```python
@fs.transactional
def create_in_transaction(transaction):
    parent_ref.get(transaction=transaction)  # ✅ Transactional read
    coll = parent_ref.collection("semesters")
    docs = [d.to_dict() for d in coll.stream()]  # ❌ NOT transactional read
    # ...
    transaction.set(new_ref, data)  # ✅ Transactional write
```

Firestore transactions only track reads performed through the `transaction` parameter. The `.stream()` call is a regular read outside the transaction, so the duplicate name/number check is **not protected by the transaction**. Two concurrent creates could:

1. Both read siblings list (empty or same state)
2. Both calculate the same next number / same unique name
3. Both succeed, creating duplicates

**Fix:** Either:
- (a) Use a subcollection query with `transaction.get()` instead of `.stream()`, or
- (b) Use a separate mutex/lock at the application level, or
- (c) Accept this as a known prototype limitation and add a comment

---

#### C-3: Missing Authentication on `list_subjects` Endpoint (Security)

**File:** `api/hierarchy_crud.py`, lines 459-476  
**Severity:** Critical

```python
@router.get("/subjects")
def list_subjects(semester_id: str):
    """List all subjects for a specific semester."""
    # No auth dependency!
```

Unlike all other endpoints in this router, `list_subjects` has **no** `Depends(require_*)` parameter. Any unauthenticated user can enumerate all subjects for any semester ID. This exposes the full academic structure to the public.

**Fix:** Add appropriate auth dependency:
```python
@router.get("/subjects")
def list_subjects(
    semester_id: str,
    user: FirestoreUser = Depends(require_staff_or_admin),
):
```

---

#### C-4: Missing Authentication on `move_node` Endpoint (Security)

**File:** `api/explorer.py`, lines 272-330  
**Severity:** Critical

```python
@router.post("/move", response_model=MoveResponse)
def move_node(request: MoveRequest):
    """Move a node to a new parent."""
    # No auth dependency!
```

The entire move operation — which can restructure the entire hierarchy and delete source nodes — is completely unauthenticated. Any user (including students and anonymous users) can move departments, semesters, subjects, modules, and notes.

**Fix:** Add authentication:
```python
from auth import require_admin

@router.post("/move", response_model=MoveResponse)
def move_node(
    request: MoveRequest,
    user: FirestoreUser = Depends(require_admin),
):
```

---

#### C-5: Missing Authentication on Hierarchy Navigation Endpoints (Security)

**File:** `api/hierarchy/router.py`, lines 68-181  
**Severity:** Critical

All hierarchy navigation endpoints are completely unauthenticated:

```python
@router.get("/departments", response_model=DepartmentListResponse)
def get_departments() -> DepartmentListResponse:
    # No auth

@router.get("/semesters", response_model=SemesterListResponse)
def get_semesters(department_id: str = Query(...)) -> SemesterListResponse:
    # No auth
```

These endpoints expose the full academic structure (departments, semesters, subjects, modules) to any caller. For a staff-facing system, this should require authentication.

**Fix:** Add auth dependencies to all endpoints, or create a dependency that allows any authenticated user.

---

#### C-6: `delete_document_recursive` Silently Swallows File Deletion Errors (Data Consistency)

**File:** `api/hierarchy_crud.py`, lines 225-240  
**Severity:** Critical (reclassified from High — affects cascade reliability)

```python
def delete_document_recursive(doc_ref):
    for coll in doc_ref.collections():
        if coll.id == "notes":
            for note_doc in coll.stream():
                note_data = note_doc.to_dict()
                pdf_url = note_data.get("pdf_url")
                if pdf_url:
                    try:
                        # ...
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except Exception:
                        pass  # ❌ Silent failure
        delete_collection(coll)
    doc_ref.delete()
```

If file deletion fails (locked file, permissions, etc.), the PDF remains on disk as an orphan. The Firestore document is deleted regardless, so there's no way to retry or even know the file wasn't cleaned up. Over time, this accumulates orphaned files.

**Fix:** Log the error at minimum. For the `delete_document_recursive` used by cascade operations, collect errors and surface them:
```python
except Exception as e:
    logger.warning(f"Failed to delete PDF {file_path}: {e}")
```

---

### HIGH

---

#### H-1: Incomplete Transactional Pattern — Sibling Reads Outside Transaction Scope

**Files:** `api/hierarchy_crud.py`, lines 383-416  
**Severity:** High

Extends C-2. The `create_semester` transaction reads siblings for both number generation and name deduplication, but these reads are outside the transaction:

```python
@fs.transactional
def create_in_transaction(transaction):
    parent_doc = parent_ref.get(transaction=transaction)
    coll = parent_ref.collection("semesters")
    docs = [d.to_dict() for d in coll.stream()]  # Outside transaction
```

This also means the "next number" calculation can produce gaps or duplicates under concurrent load.

**Fix:** Same as C-2.

---

#### H-2: `get_unique_name` Duplicated Across Two Files (DRY Violation)

**Files:** `api/hierarchy_crud.py`, lines 136-151; `api/notes.py`, lines 62-77  
**Severity:** High

Both files define identical `get_unique_name` and `get_next_available_number` functions. Changes to one won't propagate to the other, leading to subtle behavioral drift.

**Fix:** Extract into a shared `utils.py` module and import from there.

---

#### H-3: No Input Validation on Pydantic Create Models (Security)

**File:** `api/hierarchy_crud.py`, lines 234-263  
**Severity:** High

The create/update models have no field constraints:

```python
class DepartmentCreate(BaseModel):
    name: str          # No min_length, max_length, or pattern
    code: str          # No validation

class SemesterCreate(BaseModel):
    department_id: str
    semester_number: int  # No ge/le constraints
    name: str
```

This allows:
- Empty strings for names and codes
- Extremely long names (potential UI overflow, storage issues)
- Negative semester numbers
- Whitespace-only names that appear empty

Compare with the well-validated `ModuleCreate` in `api/modules/models.py` which has `min_length=1, max_length=200`, `ge=2000, le=2100` etc.

**Fix:** Add Pydantic Field constraints:
```python
class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=1, max_length=50)

class SemesterCreate(BaseModel):
    department_id: str
    semester_number: int = Field(..., ge=1, le=12)
    name: str = Field(..., min_length=1, max_length=200)
```

---

#### H-4: Async/Sync Mixing in `delete_note_cascade` (Reliability)

**File:** `api/hierarchy_crud.py`, lines 644-745  
**Severity:** High

The cascade delete endpoint is a sync FastAPI handler that needs to call an async `GraphManager.delete_document()`. The code attempts multiple workarounds:

```python
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

This pattern is fragile:
- `asyncio.run_coroutine_threadsafe` with a running loop may not work correctly if the loop belongs to uvicorn.
- `asyncio.get_event_loop()` is deprecated in Python 3.12+.
- `future.result(timeout=30)` will block the sync thread for up to 30 seconds, potentially stalling the server.

**Fix:** Make the endpoint `async` and `await` directly, or use `run_in_executor` for the sync parts:
```python
@router.delete("/notes/{note_id}/cascade")
async def delete_note_cascade(note_id: str, ...):
    # ...
    graph_manager = GraphManager(neo4j_driver)
    success, _ = await graph_manager.delete_document(note_id)
```

---

#### H-5: No Confirmation for Cascade Deletion Scope (UX)

**File:** `frontend/src/pages/ExplorerPage.tsx`, lines 94-120  
**Severity:** High

The delete confirmation dialog says:

```
"Are you sure you want to delete "{nodeToDelete.label}"? This action cannot be undone."
```

But for a **department** deletion, this cascades to all semesters, subjects, modules, notes, PDFs, and potentially KG data. The user has no warning about the scope of the deletion.

**Fix:** Show the count of affected items in the confirmation:
```typescript
const deleteScopeMessage = (type: HierarchyType) => {
    if (type === 'department') return 'This will permanently delete all semesters, subjects, modules, notes, and PDFs under this department.';
    if (type === 'semester') return 'This will permanently delete all subjects, modules, notes, and PDFs under this semester.';
    // etc.
};
```

---

#### H-6: `copy_children` Overwrites FK Only for Hardcoded Collections (Data Integrity)

**File:** `api/explorer.py`, lines 310-323  
**Severity:** High

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

The FK update uses `dest.id` which is the **new** document ID of the parent. But this only updates the FK to the immediate parent. Deeper descendants (e.g., notes under a moved module) don't get their `subjectId` or `departmentId` fields updated. The note's `subjectId` will still point to the old parent path's subject.

**Fix:** Propagate all ancestor FKs through the recursive copy, not just the immediate parent's.

---

#### H-7: Bulk Delete in `SelectionActionBar` Lacks Per-Item Confirmation (UX)

**File:** `frontend/src/components/explorer/SelectionActionBar.tsx`, lines 133-164  
**Severity:** High

The `handleDelete` function deletes selected notes without any confirmation dialog. The user clicks the trash icon and immediately starts the cascade delete for all selected notes:

```typescript
const handleDelete = async () => {
    const noteIds = nodes.filter(n => n.type === 'note').map(n => n.id);
    if (noteIds.length === 0) return;
    setIsDeleting(true);
    // Deletes immediately - no confirmation
    for (let i = 0; i < noteIds.length; i++) {
        await deleteNoteCascade(noteIds[i]);
    }
```

**Fix:** Add a confirmation dialog before initiating the delete loop, especially for multi-select operations.

---

### MEDIUM

---

#### M-1: Full Tree Fetch Without Pagination (Performance)

**File:** `api/explorer.py`, lines 260-266  
**Severity:** Medium

```python
@router.get("/tree", response_model=List[ExplorerNode])
async def get_explorer_tree(depth: int = 5):
    depts_ref = async_db.collection("departments").order_by("name")
    dept_docs = [d async for d in depts_ref.stream()]
    tasks = [_build_single_department_async(doc, depth) for doc in dept_docs]
    return await asyncio.gather(*tasks)
```

For a production deployment with many departments, semesters, subjects, modules, and notes, this fetches the **entire hierarchy** in one request. With `depth=5` (default), it traverses all the way to notes, potentially returning thousands of nodes.

**Fix:** Implement cursor-based pagination at the top level, or limit default depth to 2-3 and rely on the lazy-loading endpoint for deeper traversal.

---

#### M-2: `list` in `ModuleService` Fetches All Docs Then Paginates In-Memory (Performance)

**File:** `api/modules/service.py`, lines 112-143  
**Severity:** Medium

```python
def list(self, ...):
    all_docs = list(query.stream())  # Fetches ALL matching docs
    total = len(all_docs)
    offset = (page - 1) * page_size
    paginated_docs = all_docs[offset : offset + page_size]
```

This loads the entire result set into memory and slices it. For large collections, this is wasteful. Firestore supports `.offset()` and `.limit()` for server-side pagination (though offset has its own limitations).

**Fix:** Use `.limit(page_size)` with cursor-based pagination (start_after) for better performance. At minimum, use `.offset()`:
```python
query = query.offset(offset).limit(page_size)
paginated_docs = list(query.stream())
```

---

#### M-3: Redundant Double Auth Check on Department Endpoints (Code Smell)

**File:** `api/hierarchy_crud.py`, lines 279-293, 312-326, 349-365  
**Severity:** Medium

```python
def create_department(
    dept: DepartmentCreate,
    user: FirestoreUser = Depends(require_staff_or_admin),  # Allows staff + admin
):
    if user.role not in ("admin",):  # ❌ Overrides to admin-only
        raise HTTPException(...)
```

The endpoint first accepts staff via `require_staff_or_admin`, then rejects them with a manual role check. This is confusing — just use `require_admin` directly:

```python
def create_department(
    dept: DepartmentCreate,
    user: FirestoreUser = Depends(require_admin),  # Clean admin-only
):
```

---

#### M-4: Explorer Page Uses `alert()` for Error Handling (UX)

**Files:** `frontend/src/pages/ExplorerPage.tsx`, line 119; `frontend/src/components/explorer/GridView.tsx`, lines 122, 155; `frontend/src/components/explorer/SidebarTree.tsx`, lines 89, 138  
**Severity:** Medium

Multiple places use `alert()` for error messages:
```typescript
alert(`Failed to delete: ${(error as Error).message}`);
alert("Rename failed");
alert(`Failed to create: ${(error as Error).message}`);
```

`alert()` blocks the UI thread, is not accessible (no screen reader support), and looks unprofessional.

**Fix:** Use the existing `openWarningDialog` pattern or a toast notification (the project already uses `sonner` in `UploadDialog.tsx`).

---

#### M-5: `ExplorerPage` Uses `useEffect` to Redirect Admins (Anti-Pattern)

**File:** `frontend/src/pages/ExplorerPage.tsx`, lines 73-76  
**Severity:** Medium

```typescript
useEffect(() => {
    if (isAdmin()) {
        navigate('/admin', { replace: true });
    }
}, [isAdmin, navigate]);
```

This causes a flash of the explorer page before redirecting. The redirect should be handled at the routing level (e.g., in `ProtectedRoute` or a route guard), not inside the page component.

**Fix:** Handle the redirect in the router configuration or a layout-level guard.

---

#### M-6: `tree.find()` Searches Entire Unfiltered Tree for Student Auto-Navigation (Logic)

**File:** `frontend/src/pages/ExplorerPage.tsx`, lines 89-96  
**Severity:** Medium

```typescript
if (user?.role === 'student' && user?.departmentId) {
    const userDept = tree.find(dept => dept.id === user.departmentId);
    if (userDept) {
        navigateTo(userDept, []);
    }
}
```

`tree` is the unfiltered full tree. For students, this could navigate to a department that `getFilteredTree()` would later filter out (if `departmentId` doesn't match). The search should use `filteredTree` instead.

**Fix:** Use `getFilteredTree()` result or ensure the navigation logic uses the filtered tree.

---

#### M-7: Semester Number Calculation Uses Name Regex (Fragile)

**File:** `frontend/src/components/explorer/GridView.tsx`, lines 142-152  
**Severity:** Medium

```typescript
case 'semester': {
    const existingSemesters = items.filter(i => i.type === 'semester');
    let semNum = 1;
    if (existingSemesters.length > 0) {
        const numbers = existingSemesters.map(s => {
            const match = s.label.match(/\d+/);
            return match ? parseInt(match[0]) : 0;
        });
        semNum = Math.max(...numbers, existingSemesters.length) + 1;
    }
    await api.createSemester(creatingParentId!, semNum, name);
```

This extracts semester numbers from **labels** using regex. If a user renames a semester to "Fall 2026", the regex would extract `2026` as the semester number. This is unreliable.

**Fix:** Use `meta.ordering` or `meta.semester_number` from the backend data instead of parsing labels.

---

#### M-8: `SidebarTree` Hardcodes `semester_number=1` for New Semesters (Logic Bug)

**File:** `frontend/src/components/explorer/SidebarTree.tsx`, lines 67  
**Severity:** Medium

```typescript
case 'semester':
    await api.createSemester(parentId!, 1, name);  // Always 1!
```

When creating a semester from the sidebar tree, the semester number is always hardcoded to `1`. The GridView correctly calculates the next number. The sidebar creation bypasses this logic.

**Fix:** Pass the current siblings count or use the same calculation as GridView.

---

#### M-9: `SidebarTree` Also Hardcodes `module_number=1` (Logic Bug)

**File:** `frontend/src/components/explorer/SidebarTree.tsx`, line 71  
**Severity:** Medium

Same issue as M-8 but for modules. Always sends `module_number: 1`.

**Fix:** Same as M-8.

---

#### M-10: Drag-Drop Selection Box Uses `document.querySelectorAll` (Fragile)

**File:** `frontend/src/components/explorer/SelectionOverlay.tsx`, lines 85-95  
**Severity:** Medium

```typescript
const selectableElements = document.querySelectorAll('.selectable-item');
selectableElements.forEach((el) => {
    const rect = el.getBoundingClientRect();
    const id = el.getAttribute('data-id');
```

This queries the entire DOM for `.selectable-item` elements. If multiple explorer instances exist (unlikely but possible during transitions), or if other components use the same class, incorrect items could be selected.

**Fix:** Scope the query to the container ref:
```typescript
const selectableElements = containerRef.current?.querySelectorAll('.selectable-item');
```

---

#### M-11: `ContextMenu` No Focus Trap (Accessibility)

**File:** `frontend/src/components/explorer/ContextMenu.tsx`, lines 133-177  
**Severity:** Medium

The context menu renders as a positioned div but lacks:
- Focus trapping (Tab key moves focus outside the menu)
- Escape key handling to close the menu
- `role="menu"` and `role="menuitem"` attributes
- `aria-label` on the container
- Automatic focus on first item when opened

**Fix:** Add `role="menu"`, `role="menuitem"`, trap focus, handle Escape, and use `aria-` attributes.

---

#### M-12: No File Size Validation on Upload (Security / Reliability)

**File:** `frontend/src/components/explorer/UploadDialog.tsx`, lines 213-250  
**Severity:** Medium

The upload dialog accepts files without any size validation:
```typescript
const handleDrop = useCallback((e: React.DragEvent) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        setSelectedFile(files[0]);  // No size check
    }
}, []);
```

Large files (100MB+) could cause:
- Upload timeouts
- Server-side memory issues
- Poor UX with no progress indication during upload

**Fix:** Add client-side size validation and show an error for files exceeding the limit (e.g., 50MB):
```typescript
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
if (files[0].size > MAX_FILE_SIZE) {
    setError('File size exceeds 50MB limit');
    return;
}
```

---

#### M-13: `SelectionActionBar` Query Cache Lookup Pattern (Robustness)

**File:** `frontend/src/components/explorer/SelectionActionBar.tsx`, lines 75-85  
**Severity:** Medium

```typescript
const tree = queryClient.getQueryData<FileSystemNode[]>(['explorer', 'tree']) || [];
const selectedNodes = findNodesByIds(tree, selectedIds);
```

This reads the query cache directly rather than through a hook. If the tree data becomes stale (e.g., another user modifies the hierarchy), the selection actions operate on stale data. The `handleDelete` and `handleDownload` functions repeat this pattern inside the handler, reading cache at call time.

**Fix:** This is acceptable for the current prototype but consider using `useQuery` with `select` for derived data to ensure reactivity.

---

#### M-14: Duplicate Code Between GridView and ListView Selection Logic

**Files:** `frontend/src/components/explorer/GridView.tsx`, lines 192-220; `frontend/src/components/explorer/ListView.tsx`, lines 109-137  
**Severity:** Medium

Both components have identical selection handling logic:
```typescript
const isKGReady = item.type === 'note' && item.meta?.kg_status === 'ready';
const isDisabledInSelection = selectionMode && (deleteMode ? !isKGReady : isKGReady);
```

The click handlers, selection mode logic, and KG-status checks are duplicated word-for-word.

**Fix:** Extract into a shared custom hook:
```typescript
function useExplorerItemClick(items: FileSystemNode[]) {
    // Shared click logic with selection mode handling
}
```

---

### LOW

---

#### L-1: `_ensure_explorer_node_model` Never Called (Dead Code)

**File:** `api/explorer.py`, line 337  
**Severity:** Low

```python
def _ensure_explorer_node_model() -> None:
    """Lazily rebuild ExplorerNode model for Pydantic v2 recursive references."""
    ExplorerNode.model_rebuild()
```

This function is defined but never called. Pydantic v2 may auto-rebuild, or this may be needed but was forgotten during refactoring.

**Fix:** Either call it at module load time or remove the dead code.

---

#### L-2: `get_next_available_code` Prefix Matching Is Greedy (Edge Case)

**File:** `api/hierarchy_crud.py`, lines 126-133  
**Severity:** Low

```python
def get_next_available_code(codes: list[str], prefix: str = "SUBJ") -> str:
    for c in codes:
        if c.startswith(prefix):
            try:
                nums.append(int(c[len(prefix):]))
```

If prefix is "CS" and codes include ["CS101", "CSAI200"], it would try to parse "AI200" as an int and fail silently. The function handles this with a bare `except ValueError: pass`, so it's safe but could produce confusing results with certain code patterns.

**Fix:** Use a more precise regex pattern: `re.match(rf'^{re.escape(prefix)}(\d+)$', c)`

---

#### L-3: `created_at` Stored as ISO String vs Firestore Timestamp (Inconsistency)

**Files:** `api/notes.py`, line 97; `api/modules/service.py`, line 84  
**Severity:** Low

Notes store `created_at` as `datetime.datetime.now().isoformat()` (a string), while ModuleService stores `created_at` as `datetime.utcnow()` (a Firestore Timestamp). The explorer `_build_notes_async` function must handle both:

```python
createdAt=str(data.get("created_at")) if data.get("created_at") else None,
```

This inconsistency makes date handling fragile across the codebase.

**Fix:** Standardize on one format. Prefer Firestore Timestamp for querying/indexing, ISO string for display.

---

#### L-4: `importlib.util` Loading of `hierarchy.py` (Fragile Import)

**File:** `api/hierarchy/router.py`, lines 30-42  
**Severity:** Low

```python
hierarchy_file_path = os.path.join(os.path.dirname(__file__), "..", "hierarchy.py")
hierarchy_file = importlib.util.spec_from_file_location("hierarchy_functions", hierarchy_file_path)
hierarchy_module = importlib.util.module_from_spec(hierarchy_file)
hierarchy_file.loader.exec_module(hierarchy_module)
```

This manually loads `hierarchy.py` to avoid circular imports between `api/hierarchy/` package and `api/hierarchy.py` module. It works but is fragile — any import error in `hierarchy.py` will fail silently at module load time with a cryptic error.

**Fix:** Rename `api/hierarchy.py` to `api/hierarchy_data.py` (or similar) and use normal imports. This eliminates the naming conflict with the `api/hierarchy/` package.

---

#### L-5: `handleCreateSubmit` Sets Code from Name Heuristic (Weak Logic)

**File:** `frontend/src/components/explorer/GridView.tsx`, lines 128-132  
**Severity:** Low

```typescript
case 'department': {
    const code = name.substring(0, 4).toUpperCase().replace(/\s/g, '');
    await api.createDepartment(name, code);
    break;
}
case 'subject': {
    const code = name.substring(0, 6).toUpperCase().replace(/\s/g, '');
```

Department codes are derived from the first 4 characters of the name. A department named "AI" gets code "AI", "Mathematics" gets "MATH". This produces inconsistent codes. The backend also does this in `SubjectCreate` but is more robust with `get_next_available_code`.

**Fix:** Either show a code input field in the UI or use the backend's code generation logic consistently.

---

#### L-6: Missing `key` Prop Warning Risk in `SelectionOverlay`

**File:** `frontend/src/components/explorer/SelectionOverlay.tsx`  
**Severity:** Low

The `SelectionOverlay` component uses `document.querySelectorAll` to find items, bypassing React's virtual DOM. This means React's reconciliation doesn't track these elements, and there's a subtle risk if items are added/removed during selection.

Not a bug currently, but a code smell for a React application.

---

#### L-7: Explorer Tree Query Uses `staleTime: Infinity` Implied by Manual Refetch Pattern

**File:** `frontend/src/pages/ExplorerPage.tsx`, lines 78-80  
**Severity:** Low

```typescript
const { data: tree = [], isLoading, error } = useQuery({
    queryKey: ['explorer', 'tree'],
    queryFn: () => getExplorerTree(5),
});
```

No `staleTime`, `cacheTime`, or `refetchInterval` configured. The default `staleTime` is 0, meaning the tree is considered stale immediately and will refetch on every mount/remount. Every mutation also does `refetchQueries` or `invalidateQueries`. This causes frequent full-tree reloads.

**Fix:** Set a reasonable `staleTime` (e.g., 30 seconds) to reduce unnecessary refetches:
```typescript
const { data: tree = [] } = useQuery({
    queryKey: ['explorer', 'tree'],
    queryFn: () => getExplorerTree(5),
    staleTime: 30_000,
});
```

---

#### L-8: `canCreateChild` in ContextMenu Doesn't Allow Staff to Create Notes Under Modules

**File:** `frontend/src/components/explorer/ContextMenu.tsx`, lines 84-95  
**Severity:** Low

```typescript
const canCreateChild = () => {
    if (isAdmin && ['department', 'semester', 'subject'].includes(node.type)) {
        return true;
    }
    if (isStaff && node.type === 'subject') {  // Only subject → module
        return true;
    }
    return false;
};
```

Staff can create modules under subjects, but cannot create notes under modules via the context menu. The `handleCreate` function has a special case that shows an alert instead:

```typescript
if (childType.type === 'note') {
    alert('Use the Audio Upload feature to create notes...');
```

This is intentional (notes require the upload dialog), but the context menu still shows the "New Note" option which immediately fails with an alert. This is confusing.

**Fix:** Either hide the "New Note" option from the context menu when the upload dialog would be required, or open the UploadDialog directly.

---

## Architecture Observations

### 1. Dual Module Systems (Noted, Not Flagged)

The codebase has two parallel module systems:
- **Hierarchy modules** (`/api/modules` in `hierarchy_crud.py`): Subcollections under subjects in the hierarchy tree.
- **M2KG modules** (`/api/v1/modules` in `modules/router.py`): Top-level `m2kg_modules` collection with publishing workflow.

These are clearly different concepts (hierarchy organization vs. KG publishing), but the naming overlap is confusing. The `modules/router.py` service uses `COLLECTION = "m2kg_modules"` which avoids data collision, but the API paths could collide depending on routing order.

### 2. Sync vs. Async Split

The explorer tree endpoint (`/api/explorer/tree`) is async with parallel fetching via `asyncio.gather`, while all CRUD endpoints in `hierarchy_crud.py` are sync. This is reasonable — reads benefit from parallelism, writes benefit from simplicity. However, it means the write-heavy CRUD layer doesn't leverage FastAPI's async capabilities for Firestore operations.

### 3. `find_doc_by_id` Pattern

Both `explorer.py` and `hierarchy_crud.py` implement the same `find_doc_by_id` / `find_doc_ref_sync` function using collection group queries. This should be shared.

---

## Recommendations (Prioritized)

1. **Immediate:** Fix C-3 and C-5 (add authentication to unprotected endpoints)
2. **Immediate:** Fix C-1 (move operation ID corruption) before using the move feature
3. **Short-term:** Add Pydantic validation to hierarchy_crud models (H-3)
4. **Short-term:** Fix sidebar tree hardcoded semester/module numbers (M-8, M-9)
5. **Medium-term:** Extract shared utilities (`get_unique_name`, `find_doc_by_id`) to reduce duplication (H-2)
6. **Medium-term:** Add confirmation dialog for bulk delete (H-7) and cascade scope warning (H-5)
7. **Long-term:** Add pagination support for tree endpoint (M-1)
