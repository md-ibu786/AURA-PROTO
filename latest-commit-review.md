# Latest Commit Review (AURA-NOTES-MANAGER)

## Summary
- Risk level: Medium-High (data-loss risk in KG deletion cleanup)
- Scope reviewed: Neo4j delete flow, KG delete endpoint, frontend delete-mode UX

## Issues
1) High — Global orphan cleanup can delete unrelated entities and runs once per document
   - Location: `api/graph_manager.py:573`
   - What: `delete_document` runs a global orphan cleanup that deletes any entity not connected to any Document/Chunk, and this is executed for every document in the batch.
   - Impact: Potential data loss for unrelated modules or in-progress processing; repeated full-graph cleanup per doc can be expensive.

2) Medium — Neo4j deletion can succeed while Firestore update fails (state inconsistency)
   - Location: `api/kg/router.py:398`
   - What: Firestore status reset happens after Neo4j deletion. If `note.reference.update` fails, the KG is deleted but the note remains `kg_status=ready`.
   - Impact: Inconsistent state between Neo4j and Firestore; UI may keep disabling reprocessing.

3) Low — Delete-mode selection restrictions implemented in GridView only
   - Location: `frontend/src/components/explorer/ListView.tsx:134`
   - What: ListView selection logic does not check `selectionMode` / `deleteMode` or KG-ready status, unlike GridView.
   - Impact: Users in ListView can select non-KG-ready items and trigger delete-batch, causing avoidable failures and inconsistent UX.

## Notes
- Consider scoping orphan cleanup by module or running it once per batch after deletions.
- Add compensation/retry logic when Firestore updates fail after Neo4j deletions.
- Align ListView behavior with GridView for process/delete mode constraints.
