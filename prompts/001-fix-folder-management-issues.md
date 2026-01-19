<objective>
Fix critical folder management issues in the AURA Proto project. The user reports:
1. Can only create department folders (nested folder creation fails)
2. Cannot rename folders
3. Cannot create folders inside created department folders
4. Delete functionality doesn't work

Root cause identified: ID format mismatch between frontend and backend. Frontend expects "type-id" format (e.g., "department-123") but backend returns Firestore auto-generated string IDs (e.g., "ABC123XYZ"). Frontend code uses `id.split('-')[1]` which fails with raw Firestore IDs.

This fix will restore full CRUD functionality for all folder operations across the hierarchy.
</objective>

<context>
Project: AURA Proto - A hierarchical file/folder management system with departments, semesters, subjects, etc.
Tech Stack: React frontend, Python/FastAPI backend, Firestore database
Previous Migration: Recently migrated from PostgreSQL (integer IDs) to Firestore (string IDs)

Relevant files identified by exploration:
- Frontend components: `frontend/src/components/explorer/ContextMenu.tsx`, `GridView.tsx`, `ListView.tsx`
- Frontend layout: `frontend/src/components/layout/Sidebar.tsx`
- Frontend store: `frontend/src/stores/useExplorerStore.ts`
- Frontend API: `frontend/src/api/explorerApi.ts`
- Backend API: `api/hierarchy_crud.py`, `explorer.py`, `main.py`

The issue affects all CRUD operations: create (nested), rename, delete.
</context>

<requirements>
1. **Thoroughly analyze** all frontend files that parse node IDs
2. **Remove all `id.split('-')[1]` parsing logic** - this is the root cause
3. **Use raw string IDs directly** from Firestore responses
4. **Update all API calls** to pass string IDs correctly
5. **Fix parent ID handling** in nested folder creation
6. **Verify all CRUD operations work**: create, rename, delete (including nested)
7. **Test the complete flow** from frontend to backend to Firestore

Specific files to modify:
- `frontend/src/components/explorer/ContextMenu.tsx` - rename, delete operations
- `frontend/src/components/explorer/GridView.tsx` - click handlers, nested creation
- `frontend/src/components/explorer/ListView.tsx` - click handlers
- `frontend/src/components/layout/Sidebar.tsx` - ID parsing
- `frontend/src/stores/useExplorerStore.ts` - state management
- `frontend/src/api/explorerApi.ts` - API function signatures if needed

Check for:
- Line 83, 115 in ContextMenu.tsx
- Lines 85, 136, 141, 146 in GridView.tsx
- Line 65 in ListView.tsx
- Lines 31, 54 in Sidebar.tsx
</requirements>

<implementation>
**Step 1: Identify all ID parsing issues**
Search for patterns:
- `id.split('-')[1]`
- `parseInt(node.id.split('-')[1])`
- Any code that assumes "type-id" format

**Step 2: Fix ContextMenu.tsx**
- Rename operation: Use `node.id` directly instead of parsing
- Delete operation: Use `node.id` directly instead of parsing
- Create nested: Use `node.id` directly as `parentId`

**Step 3: Fix GridView.tsx**
- Click handlers: Use `node.id` directly
- Nested creation: Pass `node.id` as `parentId` without parsing
- All ID references: Use raw string IDs

**Step 4: Fix ListView.tsx**
- Click handlers: Use `node.id` directly
- All ID references: Use raw string IDs

**Step 5: Fix Sidebar.tsx**
- ID parsing: Remove split logic, use raw IDs

**Step 6: Fix useExplorerStore.ts**
- Check state management for any ID format assumptions
- Update any ID transformation logic

**Step 7: Verify explorerApi.ts**
- Ensure API functions accept string IDs
- Check function signatures match backend expectations

**Step 8: Backend verification**
- Review `api/hierarchy_crud.py` to confirm it expects string IDs
- Verify `api/explorer.py` tree building uses correct ID formats
- Check routes in `api/main.py`

**Why this matters**: The ID format mismatch breaks the entire CRUD workflow. Departments work because they're root-level (no parent ID needed), but all nested operations fail because the frontend can't extract valid IDs from Firestore's string format.
</implementation>

<output>
Modify these files with fixes:
- `./frontend/src/components/explorer/ContextMenu.tsx`
- `./frontend/src/components/explorer/GridView.tsx`
- `./frontend/src/components/explorer/ListView.tsx`
- `./frontend/src/components/layout/Sidebar.tsx`
- `./frontend/src/stores/useExplorerStore.ts` (if needed)
- `./frontend/src/api/explorerApi.ts` (if needed)

For each file:
1. Read the current content
2. Identify all ID parsing issues
3. Replace `id.split('-')[1]` patterns with direct ID usage
4. Update API calls to pass string IDs correctly
5. Ensure parent ID handling works for nested operations
6. Write the fixed version

After modifications, create a summary file:
- `./fix-summary.md` - Document what was changed and why
</output>

<verification>
Before declaring complete, verify your work:

1. **Search for remaining issues**: Run a search for `split('-')` across all frontend files to ensure no parsing logic remains

2. **Check all CRUD operations**:
   - Create department (root level) - should work
   - Create semester inside department - should now work
   - Create subject inside semester - should now work
   - Rename any folder - should now work
   - Delete any folder (including nested) - should now work

3. **Verify ID flow**:
   - Backend returns Firestore ID: "ABC123XYZ"
   - Frontend stores it: node.id = "ABC123XYZ"
   - Frontend passes to API: id = "ABC123XYZ"
   - Backend receives and processes correctly

4. **Review error handling**: Ensure invalid IDs are caught and reported clearly

5. **Test edge cases**:
   - Empty folder names
   - Duplicate names
   - Deep nesting
   - Deleting folders with children
</verification>

<success_criteria>
✅ All ID parsing with `split('-')[1]` removed from frontend
✅ All CRUD operations work: create (nested), rename, delete
✅ Parent IDs correctly passed for nested folder creation
✅ String IDs used consistently throughout the flow
✅ No TypeScript errors or runtime errors
✅ Folder hierarchy displays correctly with proper IDs
✅ Fix summary documented
</success_criteria>
