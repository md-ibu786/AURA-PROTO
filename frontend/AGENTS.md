# AURA-NOTES-MANAGER/frontend

**Generated:** 2026-01-19

## OVERVIEW

React 18 + Vite + TypeScript 5.6 frontend for staff hierarchy/note management with Zustand state, typed API layer, and custom DuplicateError handling.

## STRUCTURE

```
frontend/
├── src/
│   ├── api/              # Typed fetch wrappers (client.ts, explorerApi.ts, audioApi.ts)
│   ├── components/       # UI components (Explorer, Sidebar, Layout)
│   ├── integration/      # Service connection layer + test files
│   ├── pages/            # Page components (ExplorerPage.tsx)
│   ├── stores/           # Zustand state (useExplorerStore.ts)
│   ├── types/            # TypeScript interfaces
│   └── styles/           # CSS files
├── vite.config.ts        # Proxy to 127.0.0.1:8001
└── vitest.config.ts      # Unit test configuration
```

## WHERE TO LOOK

| Task | Location |
|------|----------|
| API integration | `src/api/client.ts` (fetch wrappers), `src/api/explorerApi.ts` (CRUD) |
| State management | `src/stores/useExplorerStore.ts` (Zustand, UI state only) |
| Page structure | `src/pages/ExplorerPage.tsx` |
| Service connections | `src/integration/` (test files + integration layer) |
| Custom errors | `src/api/client.ts` (DuplicateError class) |
| Unit tests | `src/**/*.test.ts(x)` (Vitest) |

## CONVENTIONS

- **API layer**: Typed fetch wrappers in `src/api/` with `DuplicateError` for 409 conflicts
- **State separation**: Zustand (`useExplorerStore`) for UI state only; server state via React Query
- **Integration layer**: `src/integration/` contains service connection logic + test files
- **Vite proxy**: Proxies `/api` to `127.0.0.1:8001` (not `localhost`)
- **Vitest**: Unit testing with `@testing-library/react` and `@tanstack/react-query`
- **No `any`**: Google TypeScript Style Guide enforced

## Python Environment (for backend testing)

- **ALWAYS use the root venv** (from project root) for all Python tasks
- **NEVER install dependencies globally** or create local venvs
- Run Python tests from project root:
  ```bash
  # Correct - use root venv
  cd ../.. && .venv/Scripts/python -m pytest AURA-NOTES-MANAGER/api/tests/
  cd ../.. && .venv/Scripts/python -m pip install <package>

  # Wrong - do NOT use global Python
  python -m pytest
  pip install <package>
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
