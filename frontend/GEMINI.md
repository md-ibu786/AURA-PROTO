# GEMINI.md (AURA-NOTES-MANAGER/frontend)

**For Google Gemini CLI**

**Generated:** 2026-01-19

## OVERVIEW

React 18 frontend for staff hierarchy management with Gemini-powered audio-to-notes pipeline.

## GEMINI-SPECIFIC NOTES

### AI Services
- **Summarization**: Gemini in `services/summarizer.py`
- **Content refinement**: Gemini in `services/coc.py`
- **STT**: Deepgram Nova-3 (NOT Gemini)

### API Integration
- **Typed fetch**: `fetchApi<T>()`, `fetchFormData<T>()`
- **Error handling**: Custom `DuplicateError` for 409 conflicts
- **Proxy**: Vite proxies `/api` → `127.0.0.1:8001`

### State Management
- **Zustand**: UI state only (`useExplorerStore`)
- **React Query**: Server state (separate)
- **Clear separation**: Don't mix Zustand + React Query

## KEY FILES

| Component | Path |
|-----------|------|
| API client | `api/client.ts` (typed wrappers, DuplicateError) |
| Explorer API | `api/explorerApi.ts` (CRUD operations) |
| State store | `stores/useExplorerStore.ts` |
| Main page | `pages/ExplorerPage.tsx` |
| Integration | `integration/` (tests + service layer) |

## DEVELOPMENT

```bash
cd AURA-NOTES-MANAGER/frontend
npm run dev      # Frontend at localhost:5173
# API: http://127.0.0.1:8001 (not localhost)
```

## AUDIO PIPELINE

1. **Upload**: Audio file → FastAPI `/audio/upload`
2. **Transcription**: Deepgram Nova-3 (`services/stt.py`)
3. **Refinement**: Gemini (`services/coc.py`)
4. **Summary**: Gemini (`services/summarizer.py`)
5. **PDF**: Generate from transcript (`services/pdf_generator.py`)

## TESTING

- **Unit**: Vitest with `@testing-library/react`
- **E2E**: Playwright, SEQUENTIAL (DB consistency)
- **Integration**: `integration/` folder contains test helpers

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

**Example (TypeScript - Store):**
```typescript
// useExplorerStore.ts
// Zustand store for UI state (not server state)

// Manages sidebar collapse, selected hierarchy node, and search filters.
// Server state is handled separately via React Query. Clear separation
// enforced to prevent state management confusion.

// @see: integration/ - Tests and service connections
// @note: UI state only - server state uses React Query
```

**Enforcement:**
- File headers are REQUIRED for: `.ts`, `.tsx`, `.js`, `.jsx`
- Existing files without headers: Add when modifying (>30% changes)
- New files: ALWAYS add header before first write
- Vite config, Vitest config: Optional but recommended
