# CLAUDE.md (AURA-NOTES-MANAGER/frontend)

**For Claude Code**

**Generated:** 2026-01-19

## OVERVIEW

React 18 + Vite + TypeScript 5.6 frontend for staff hierarchy/note management with typed API layer and custom error handling.

## ARCHITECTURE

### Page-Based Structure
```
src/
├── api/              # Typed fetch wrappers (client.ts, DuplicateError)
├── components/       # UI, Explorer, Sidebar, Layout
├── integration/      # Service connections + tests
├── pages/            # ExplorerPage.tsx (main)
├── stores/           # useExplorerStore.ts (Zustand, UI state only)
├── types/            # TypeScript interfaces
└── styles/           # CSS files
```

### State Management
- **Zustand**: UI state only (`useExplorerStore`)
- **React Query**: Server state (separate from Zustand)
- **No mixing**: Clear separation enforced

### API Layer
- **Typed fetch wrappers**: `fetchApi<T>()`, `fetchFormData<T>()`
- **Custom error**: `DuplicateError` for 409 conflicts
- **Base URL**: `/api` (Vite proxy to `127.0.0.1:8001`)

## CLAUDE CODE RULES

### Frontend Changes
- **Visual/UI**: Delegate to `frontend-ui-ux-engineer` agent
- **Logic/API**: Handle directly (use typed wrappers)
- **Never use**: `any` type, default exports

### API Patterns
- **DuplicateError**: Handle 409 conflicts gracefully
- **Typed responses**: Always use `<T>` generics
- **FormData**: Use `fetchFormData<T>()` wrapper

### Testing
- **Unit**: Vitest with `@testing-library/react`
- **E2E**: Playwright in `e2e/`, SEQUENTIAL (fullyParallel: false)
- **DB consistency**: Tests run one-at-a-time

## KEY FILES

| Purpose | File |
|---------|------|
| API client | `api/client.ts` (DuplicateError, typed fetch) |
| Explorer CRUD | `api/explorerApi.ts` |
| State | `stores/useExplorerStore.ts` |
| Page | `pages/ExplorerPage.tsx` |
| Integration | `integration/` (tests + service layer) |

## TESTING

- **Unit**: Vitest configured
- **E2E**: Sequential for DB consistency
- **Run**: `npm run test:e2e` from project root

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
