# GEMINI.md (AURA-NOTES-MANAGER)

**For Google Gemini CLI**

**Generated:** 2026-03-06

## OVERVIEW

Full-stack hierarchy and note management system with React 18 + Vite frontend, FastAPI backend, Firebase Firestore, Neo4j knowledge graph, and AI-powered audio processing with Gemini integration.

## PROJECT STRUCTURE

```
AURA-NOTES-MANAGER/
├── api/                    # FastAPI backend
│   ├── main.py            # Server entry point
│   ├── hierarchy_crud.py  # CRUD operations
│   ├── explorer.py        # Explorer endpoints
│   ├── audio_processing.py # Audio pipeline
│   ├── kg_processor.py    # Knowledge graph processing
│   ├── users.py           # User management
│   └── config.py          # Configuration
├── frontend/              # React frontend
│   ├── src/
│   │   ├── api/          # API client layer
│   │   ├── components/   # React components
│   │   ├── features/kg/  # Knowledge Graph feature module
│   │   ├── pages/        # Page components
│   │   ├── stores/       # Zustand state management
│   │   └── types/        # TypeScript types
│   ├── AGENTS.md         # Frontend-specific agent guide
│   ├── CLAUDE.md         # Claude Code guide
│   └── GEMINI.md         # Gemini CLI guide
├── services/              # AI/ML services (STT, summarization, PDF)
├── e2e/                   # Playwright E2E tests
├── tools/                 # Utility scripts
└── requirements.txt       # Python dependencies
```

## GEMINI-SPECIFIC NOTES

### AI Services Integration
- **Summarization**: Gemini in `services/summarizer.py`
- **Content refinement**: Gemini in `services/coc.py`
- **STT**: Deepgram Nova-3 (NOT Gemini) in `services/stt.py`
- **Knowledge Graph**: Neo4j integration with KG processing pipeline

### Backend Architecture
- **Framework**: FastAPI (Python 3.10+)
- **Port**: 8001 (not 8000)
- **Database**: Firebase Firestore (not SQLite)
- **Auth**: Firebase Authentication
- **Cache**: Redis for Celery task queue

### Frontend Architecture
- **Framework**: React 18 + Vite + TypeScript 5.6
- **Port**: 5174 (not 5173)
- **State**: Zustand (UI/auth) + TanStack Query (server state)
- **Styling**: Tailwind CSS
- **Auth**: Firebase Authentication

### API Integration
- **Typed fetch**: `fetchApi<T>()`, `fetchFormData<T>()`
- **Error handling**: Custom `DuplicateError` for 409 conflicts
- **Proxy**: Vite proxies `/api` → `127.0.0.1:8001`
- **Base URL**: Always use `127.0.0.1`, never `localhost`

### Knowledge Graph Feature
- **Location**: `frontend/src/features/kg/`
- **Components**: KGStatusBadge, ProcessDialog, ProcessingQueue, FileSelectionBar
- **Hook**: useKGProcessing for managing KG operations
- **Types**: kg.types.ts defines KG interfaces
- **Backend**: `api/kg_processor.py` for KG processing

## KEY FILES

| Component | Path |
|-----------|------|
| API client | `frontend/src/api/client.ts` (typed wrappers, DuplicateError, auth) |
| Explorer API | `frontend/src/api/explorerApi.ts` (CRUD operations) |
| User API | `frontend/src/api/userApi.ts` |
| Firebase | `frontend/src/api/firebaseClient.ts` |
| UI State | `frontend/src/stores/useExplorerStore.ts` |
| Auth State | `frontend/src/stores/useAuthStore.ts` |
| Explorer Page | `frontend/src/pages/ExplorerPage.tsx` |
| Login Page | `frontend/src/pages/LoginPage.tsx` |
| Admin Dashboard | `frontend/src/pages/AdminDashboard.tsx` |
| KG Processing | `frontend/src/features/kg/hooks/useKGProcessing.ts` |
| Backend Main | `api/main.py` |
| KG Processor | `api/kg_processor.py` |
| Hierarchy CRUD | `api/hierarchy_crud.py` |

## DEVELOPMENT

### Backend
```bash
cd api
python -m uvicorn main:app --reload --port 8001
```

### Frontend
```bash
cd frontend
npm run dev              # Frontend at localhost:5174
npm run build            # Type check + production build
npm run lint             # ESLint check
npm test                 # Run Vitest unit tests
npm run test:e2e         # Run Playwright E2E tests
npm run test:rules       # Firestore rules tests with emulator
```

**Backend API**: http://127.0.0.1:8001 (proxied via Vite)

## AUDIO PIPELINE

1. **Upload**: Audio file → FastAPI `/audio/upload`
2. **Transcription**: Deepgram Nova-3 (`services/stt.py`)
3. **Refinement**: Gemini (`services/coc.py`)
4. **Summary**: Gemini (`services/summarizer.py`)
5. **PDF**: Generate from transcript (`services/pdf_generator.py`)
6. **Knowledge Graph**: Optional Neo4j processing

## TESTING

- **Unit (Frontend)**: Vitest with `@testing-library/react` (13 test files)
- **Unit (Backend)**: pytest with `api/tests/`
- **E2E**: Playwright in `e2e/`, SEQUENTIAL for DB consistency (`fullyParallel: false`)
- **Firestore Rules**: Jest for security rules testing

## PYTHON ENVIRONMENT

- **ALWAYS use the root venv** (`../.venv` or `../../.venv`) for all Python tasks
- **NEVER install dependencies globally** or in subdirectory venvs
```bash
# Correct - use root venv
../.venv/Scripts/python -m pytest api/tests/
../.venv/Scripts/python -m pip install <package>
```

## AGENT BEHAVIOUR

### Research-First Principle
- **ALWAYS web-search before implementing** unfamiliar libraries, APIs, or patterns
- **NEVER assume** library behavior — verify with official documentation
- **Search first** when encountering: new npm packages, Python libraries, framework features, or external APIs
- Use `librarian` agent for documentation lookup, `explore` agent for codebase patterns

### SWE Best Practices
- **Write tests BEFORE or WITH code**, not after — TDD when appropriate
- **Verify with diagnostics**: Run `lsp_diagnostics` before marking tasks complete
- **Build & test**: Always run build/test commands after implementation
- **Type safety first**: Never suppress type errors with `as any`, `@ts-ignore`
- **Error handling**: Never leave empty catch blocks `catch(e) {}`
- **Minimal changes**: Fix bugs without refactoring unrelated code

### Never Be Lazy
- **Don't skip verification** — always run diagnostics, build, and tests
- **Don't guess** — search for patterns, ask clarification questions when ambiguous
- **Don't partial-ship** — task is complete ONLY when all criteria met
- **Don't assume knowledge** — read the relevant code before modifying
- **Don't skip tests** — verify functionality, not just compilation

### Certainty Before Conclusion
- **NEVER declare complete** without 100% confidence
- **Verify every requirement** from the original request is addressed
- **Check for regressions**: Run relevant tests before claiming fix
- **Run diagnostics**: Ensure no new errors introduced
- **If uncertain, ask**: Better to clarify than ship broken code

### Productivity & Intelligence
- **Parallel execution**: Use background agents for independent tasks (explore, librarian, document-writer)
- **Delegate visual work**: Always use `frontend-ui-ux-engineer` agent for styling/layout changes
- **Consult Oracle** for: architecture decisions, 2+ failed fix attempts, complex debugging
- **Use todo tracking**: Mark in_progress → completed in real-time
- **Batch small tasks**: Group related edits, run diagnostics once
- **Think before code**: Understand the problem, then implement
- **Learn from failures**: Document what failed, consult Oracle after 3 attempts

### Delegation Guidelines
| Domain | Delegate To | When |
|--------|-------------|------|
| Visual/UI changes | `frontend-ui-ux-engineer` | Styling, layout, animations |
| External docs | `librarian` | Library API, official docs |
| Codebase patterns | `explore` | Finding existing implementations |
| Architecture review | `oracle` | Multi-system tradeoffs, design |
| Documentation | `document-writer` | READMEs, guides, AGENTS.md |
| Hard debugging | `oracle` | After 2+ failed fix attempts |

### Evidence Requirements
Task is NOT complete without:
- [ ] `lsp_diagnostics` clean on changed files
- [ ] Build passes (if applicable)
- [ ] Tests pass (or explicit note of pre-existing failures)
- [ ] User's original request fully addressed

### File Header Requirements
**MANDATORY for every code file created or updated:**

```typescript
// {FILE_NAME}
// {Brief 1-line description of what this file does}

// Longer description (2-4 lines):
// - What problem does this file solve?
// - What are the key functions/classes?
// - Any important context for future maintainers

// @see: {Related files}
// @note: {Important caveats or gotchas}
```

**Example (TypeScript - API Client):**
```typescript
// client.ts
// Typed fetch wrapper with DuplicateError handling for 409 conflicts

// Provides fetchApi<T>() and fetchFormData<T>() with consistent error
// handling. DuplicateError is thrown on 409 conflicts for graceful
// handling of duplicate hierarchy entries.

// @see: explorerApi.ts - CRUD operations using this client
// @note: Proxy /api to 127.0.0.1:8001 (not localhost)
```

**Enforcement:**
- File headers are REQUIRED for: `.ts`, `.tsx`, `.js`, `.jsx`, `.py`
- Existing files without headers: Add when modifying (>30% changes)
- New files: ALWAYS add header before first write
