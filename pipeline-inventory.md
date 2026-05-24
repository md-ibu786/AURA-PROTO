# AURA-NOTES-MANAGER Pipeline Inventory

> Scope: major user/system pipelines across frontend, backend, and services.

## 1) Auth / Login & User Sync
- **Frontend entry:**
  - `frontend/src/pages/LoginPage.tsx` (login form + redirect)
  - `frontend/src/stores/useAuthStore.ts` (Firebase sign-in, token sync, /auth/me)
  - `frontend/src/components/ProtectedRoute.tsx` (route guard)
  - `frontend/src/api/firebaseClient.ts` (Firebase SDK init)
  - `frontend/src/api/client.ts` (auth headers + 401 retry)
- **Backend entry:**
  - `api/auth.py` (token verification + RBAC dependencies)
  - `api/auth_sync.py` (`POST /api/auth/sync` initial user sync)
  - `api/users.py` (`GET /api/auth/me` profile)
  - `api/main.py` (router registration)
- **Flow outline:**
  1. LoginPage → `useAuthStore.login()`
  2. Firebase Auth sign-in → ID token
  3. `POST /api/auth/sync` (create Firestore user if missing)
  4. `GET /api/auth/me` → role/department → store hydration
  5. `ProtectedRoute` gates access by role/department

## 2) Admin User Management (RBAC)
- **Frontend entry:**
  - `frontend/src/pages/AdminDashboard.tsx`
  - `frontend/src/api/userApi.ts`
- **Backend entry:**
  - `api/users.py` (CRUD `/api/users`, admin-only)
  - `api/auth_sync.py` (admin create/update/delete in Firebase)
- **Flow outline:**
  1. AdminDashboard requests `/api/users` with auth token
  2. Create/update/delete users → Firestore + Firebase custom claims
  3. Admin UI refreshes list with filters

## 3) Explorer Tree / Hierarchy Read (Navigation)
- **Frontend entry:**
  - `frontend/src/pages/ExplorerPage.tsx`
  - `frontend/src/api/explorerApi.ts` (`getExplorerTree`, `getNodeChildren`)
  - `frontend/src/components/explorer/SidebarTree.tsx`, `GridView.tsx`, `ListView.tsx`
- **Backend entry:**
  - `api/explorer.py` (`GET /api/explorer/tree`, `/children/...`)
  - `api/hierarchy.py` (read helpers used by legacy endpoints)
- **Flow outline:**
  1. ExplorerPage → `getExplorerTree(depth)`
  2. `/api/explorer/tree` builds async tree from Firestore subcollections
  3. UI renders tree + child nodes; lazy load via `/children/{type}/{id}`

## 4) Hierarchy CRUD + Note Management
- **Frontend entry:**
  - `frontend/src/api/explorerApi.ts` (create/update/delete departments/semesters/subjects/modules/notes)
  - `frontend/src/components/explorer/ContextMenu.tsx` + `ExplorerPage.tsx` delete handler
- **Backend entry:**
  - `api/hierarchy_crud.py` (CRUD + cascade delete + duplicate naming)
  - `api/notes.py` (note creation helper)
  - `api/graph_manager.py` (KG cleanup on cascade delete)
- **Flow outline:**
  1. UI create/rename/delete actions → `/api/{departments|semesters|subjects|modules|notes}`
  2. Firestore updates + cascade deletion of subcollections and PDFs
  3. Optional `/api/notes/{id}/cascade` clears KG + PDF + Firestore

## 5) Audio-to-Notes Pipeline (AI Note Generator)
- **Frontend entry:**
  - `frontend/src/components/explorer/UploadDialog.tsx`
  - `frontend/src/api/audioApi.ts` (`startPipeline`, `getPipelineStatus`)
- **Backend entry:**
  - `api/audio_processing.py` (`POST /api/audio/process-pipeline`, `GET /api/audio/pipeline-status/{job_id}`)
- **Services:**
  - `services/stt.py` (Deepgram transcription)
  - `services/coc.py` (transcript refinement)
  - `services/summarizer.py` (note generation)
  - `services/pdf_generator.py` (PDF creation)
  - `api/notes.py` (create note record)
- **Flow outline:**
  1. UploadDialog uploads audio → `/api/audio/process-pipeline`
  2. Background pipeline: transcribe → refine → summarize → generate PDF
  3. Create note record + store `pdf_url`
  4. UI polls `/pipeline-status/{job_id}` until complete

## 6) Direct Document Upload (Non-Audio)
- **Frontend entry:** `frontend/src/components/explorer/UploadDialog.tsx` (document mode)
- **Backend entry:** `api/audio_processing.py` (`POST /api/audio/upload-document`)
- **Flow outline:**
  1. Upload doc (PDF/DOCX/TXT/MD)
  2. Server writes to `/pdfs` and creates note record via `notes.py`
  3. Explorer tree refresh shows new note

## 7) PDF Delivery + Bulk ZIP
- **Frontend entry:**
  - `frontend/src/api/explorerApi.ts` (`downloadNotesZip`)
  - Explorer nodes carry `pdfFilename` for file access
- **Backend entry:**
  - `api/main.py` (`GET /api/pdfs/{filename}`, `POST /api/pdfs/zip`, `/pdfs` static mount)
- **Flow outline:**
  1. UI requests `/api/pdfs/{filename}` (auth) or `/api/pdfs/zip`
  2. Backend resolves safe path → `FileResponse` or `StreamingResponse` zip

## 8) Knowledge Graph (KG) Processing
- **Frontend entry:**
  - `frontend/src/features/kg/components/ProcessDialog.tsx`
  - `frontend/src/features/kg/components/ProcessingQueue.tsx`
  - `frontend/src/features/kg/hooks/useKGProcessing.ts`
  - `frontend/src/api/explorerApi.ts` (`/v1/kg/*` calls)
- **Backend entry:**
  - `api/kg/router.py` (`/api/v1/kg/process-batch`, `/processing-queue`, `/documents/{id}/status`)
  - `api/tasks/document_processing_tasks.py` (Celery queue + progress)
  - `api/kg_processor.py` (KnowledgeGraphProcessor)
- **Services:**
  - `services/embeddings.py`, `services/llm_entity_extractor.py`, `services/entity_aware_chunker.py`,
    `services/entity_deduplicator.py`, `services/document_parsers/*`
- **Flow outline:**
  1. User selects notes → `POST /api/v1/kg/process-batch`
  2. Celery task processes documents → chunking/embeddings/entity extraction → Neo4j
  3. Firestore `kg_status` updated; UI polls queue + status

## 9) Module Publishing (M2KG)
- **Backend entry:**
  - `api/modules/router.py` (CRUD + publish/unpublish)
  - `api/modules/service.py` (Firestore `m2kg_modules` collection)
  - `api/modules/publishing.py` (published_modules + audit log)
- **Flow outline:**
  1. Create/update module → Firestore
  2. Publish/unpublish updates status + published_modules collection + audit log

## 10) Admin Settings + Analytics (Usage/Trends/Summaries)
- **Frontend entry:**
  - `frontend/src/pages/SettingsPage.tsx` (settings + health)
  - `frontend/src/pages/UsagePage.tsx` (usage dashboard)
- **Backend entry:**
  - `api/routers/settings.py` (`/api/v1/settings/*` provider config + key mgmt)
  - `api/routers/usage.py` (`/api/v1/usage/*` cost/usage analytics)
  - `api/routers/summaries.py` (`/v1/summaries/*` doc/module summaries)
  - `api/routers/trends.py` (`/v1/trends/*` trend analytics)
- **Services:**
  - `services/summary_service.py` (LLM summaries + caching)
  - `services/trend_analyzer.py` (concept trends + Neo4j)
- **Flow outline:**
  1. Admin UI requests analytics/settings endpoints
  2. Backend uses Redis + model_router + Neo4j services to respond
