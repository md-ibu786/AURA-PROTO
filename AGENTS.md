# AURA-NOTES-MANAGER

**Generated:** 2026-02-03

## PROJECT OVERVIEW

Full-stack hierarchy and note management system with React 18 + Vite frontend, FastAPI backend, Firebase Firestore, Neo4j knowledge graph, and AI-powered audio processing.

**Tech Stack:**
- **Frontend:** React 18, TypeScript 5.6, Vite, Zustand, TanStack Query, Tailwind CSS
- **Backend:** FastAPI (Python 3.10+), Uvicorn
- **Database:** Firebase Firestore, Neo4j, Redis (caching)
- **AI/ML:** Google Gemini, Deepgram (STT), Vertex AI
- **Testing:** Vitest (unit), Playwright (E2E), Pytest (backend)

## BUILD, LINT, AND TEST COMMANDS

### Frontend (from `frontend/`)
```bash
npm run dev              # Start dev server (port 5173)
npm run build            # Type check + production build
npm run lint             # ESLint check
npm test                 # Run Vitest unit tests
npm run test:e2e         # Run Playwright E2E tests
npm run test:e2e:ui      # Run E2E tests with UI
npm run test:e2e:headed  # Run E2E tests with visible browser
```

**Run a single unit test:**
```bash
npm test -- src/components/MyComponent.test.tsx
npm test -- --grep "test name pattern"
```

**Run a single E2E test:**
```bash
npx playwright test tests/explorer.spec.ts
npx playwright test --grep "test name pattern"
npx playwright test --debug  # Debug mode
```

### Backend (from project root)
```bash
cd api
python -m uvicorn main:app --reload --port 8000  # Start backend server
```

**Run all backend tests (from project root):**
```bash
pytest                           # All tests
pytest -v                        # Verbose output
pytest --cov=api --cov-report=html  # With coverage
```

**Run a single test file:**
```bash
pytest api/test_kg_processor.py
pytest test_women_empowerment.py
```

**Run a specific test function:**
```bash
pytest api/test_kg_processor.py::test_function_name
pytest -k "test_name_pattern"  # Run tests matching pattern
```

### E2E Tests (from `e2e/`)
```bash
npm test              # Run all E2E tests
npm run test:api      # API endpoint tests only
npm run test:ui       # UI interaction tests only
npm run test:audio    # Audio processing tests only
npm run show-report   # View HTML test report
```

### Python Environment
- **ALWAYS use the root virtual environment** for all Python tasks
- **NEVER install dependencies globally** or create local venvs
```bash
# Activate venv (Windows)
.venv\Scripts\activate

# Install packages (from project root with venv activated)
pip install <package>
pip install -r requirements.txt
```

## CODE STYLE GUIDELINES

### TypeScript/JavaScript (Google TypeScript Style Guide)

**Variables & Declarations:**
- Use `const` by default, `let` when reassignment needed
- **NEVER use `var`** (forbidden)
- Use ES6 modules (`import`/`export`), no `namespace`

**Exports:**
- Use **named exports** (e.g., `export { MyClass }`)
- **DO NOT use default exports**

**Types:**
- **Avoid `any` type** — use `unknown` or specific types
- **Avoid type assertions** (`as SomeType`) unless justified
- **DO NOT use `{}` type** — use `unknown`, `Record<string, unknown>`, or `object`
- Prefer `T[]` for simple types, `Array<T>` for complex unions
- Use optional parameters (`?`) instead of `| undefined`

**Classes:**
- Use TypeScript's `private`/`protected` modifiers, not `#private` fields
- **NEVER use `public` modifier** (it's the default)
- Mark readonly properties with `readonly`

**Strings & Operators:**
- Use single quotes (`'`) for strings
- Use template literals (`` ` ``) for interpolation and multi-line strings
- Always use `===` and `!==` (never `==` or `!=`)
- Explicitly end statements with semicolons (no ASI reliance)

**Naming Conventions:**
- `UpperCamelCase`: Classes, interfaces, types, enums, decorators
- `lowerCamelCase`: Variables, parameters, functions, methods, properties
- `CONSTANT_CASE`: Global constants, enum values
- **DO NOT use `_` prefix/suffix** for identifiers

**Comments:**
- Use `/** JSDoc */` for documentation, `//` for implementation comments
- **DO NOT declare types in JSDoc** (redundant in TypeScript)
- Comments must add information, not restate code

**File Headers (MANDATORY for all .ts/.tsx files):**
```typescript
/**
 * ============================================================================
 * FILE: client.ts
 * LOCATION: frontend/src/api/client.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Brief 1-line description of what this file does
 *
 * ROLE IN PROJECT:
 *    How this file fits into the larger system (2-3 lines)
 *
 * KEY COMPONENTS:
 *    - Component1: What it does
 *    - Component2: What it does
 *
 * DEPENDENCIES:
 *    - External: List external libraries
 *    - Internal: List internal modules
 *
 * USAGE:
 *    Example code snippet
 * ============================================================================
 */
```

### Python (Google Python Style Guide)

**Imports:**
- Use `import x` for packages/modules
- Use `from x import y` only when `y` is a submodule
- Group imports: standard library, third-party, application
- Each import on separate line

**Formatting:**
- **Line length: 80 characters maximum**
- **Indentation: 4 spaces** (never tabs)
- Two blank lines between top-level definitions
- One blank line between method definitions

**Naming Conventions:**
- `snake_case`: Modules, functions, methods, variables
- `PascalCase`: Classes
- `ALL_CAPS_WITH_UNDERSCORES`: Constants
- `_internal`: Single leading underscore for internal members

**Docstrings:**
- Use `"""triple double quotes"""`
- Every public module, function, class, and method must have a docstring
- Start with one-line summary
- Include `Args:`, `Returns:`, and `Raises:` sections

**Best Practices:**
- Run `pylint` on code before committing
- Use built-in exception classes
- Avoid mutable default arguments (no `[]` or `{}` as defaults)
- Use implicit false checks: `if not my_list:`
- Use `if foo is None:` to check for None
- Type annotations strongly encouraged for public APIs

**File Headers (MANDATORY for all .py files):**
```python
"""
============================================================================
FILE: main.py
LOCATION: api/main.py
============================================================================

PURPOSE:
    Brief description of what this file does

ROLE IN PROJECT:
    How this file fits into the larger system
    - Key responsibility 1
    - Key responsibility 2

KEY COMPONENTS:
    - Component1: What it does
    - Component2: What it does

DEPENDENCIES:
    - External: fastapi, uvicorn
    - Internal: config.py, hierarchy.py

USAGE:
    Run with: python -m uvicorn main:app --reload
============================================================================
"""
```

### Error Handling

**TypeScript:**
- **NEVER leave empty catch blocks** `catch(e) {}`
- Always handle or log errors
- Use custom error classes for specific cases (e.g., `DuplicateError`)
```typescript
try {
    await riskyOperation();
} catch (error) {
    if (error instanceof DuplicateError) {
        // Handle duplicate specifically
    } else {
        console.error('Operation failed:', error);
        throw error;
    }
}
```

**Python:**
- Use specific exception types
- Never use bare `except:` clauses
```python
try:
    risky_operation()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    raise
except Exception as e:
    logger.exception("Unexpected error")
    raise
```

## PROJECT STRUCTURE

```
AURA-NOTES-MANAGER/
├── api/                    # FastAPI backend
│   ├── main.py            # Server entry point
│   ├── hierarchy_crud.py  # CRUD operations
│   ├── explorer.py        # Explorer endpoints
│   ├── audio_processing.py # Audio pipeline
│   ├── kg_processor.py    # Knowledge graph processing
│   └── config.py          # Configuration
├── frontend/              # React frontend
│   ├── src/
│   │   ├── api/          # API client layer
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── stores/       # Zustand state management
│   │   └── types/        # TypeScript types
│   └── AGENTS.md         # Frontend-specific agent guide
├── e2e/                   # Playwright E2E tests
├── tools/                 # Utility scripts
├── documentations/        # Project documentation
│   └── code_styleguides/  # Style guide references
├── requirements.txt       # Python dependencies
└── conftest.py           # Pytest configuration
```

## AGENT BEST PRACTICES

### Before Starting
- **Read relevant code first** — understand before modifying
- **Use Task tool for exploration** — conserve context for complex searches
- **Check existing patterns** — maintain consistency with codebase

### During Implementation
- **Write tests BEFORE or WITH code** — TDD when appropriate
- **Type safety first** — never suppress type errors
- **Minimal changes** — fix bugs without refactoring unrelated code
- **File headers required** — add to all new/significantly modified files

### Before Completing
- **Run build/lint** — ensure no compilation errors
- **Run relevant tests** — verify functionality, not just compilation
- **Check for regressions** — ensure no new errors introduced
- **Verify all requirements** — task complete only when 100% confident

### Never
- ❌ Skip verification (build, lint, tests)
- ❌ Guess library behavior — search documentation first
- ❌ Partial-ship — complete all requirements or ask for clarification
- ❌ Assume knowledge — read the code before changing
- ❌ Leave empty catch blocks or suppress type errors
- ❌ Use `any` type or type assertions without justification
- ❌ Skip file headers on new/modified files

## QUICK REFERENCE

**Common Tasks:**
- API changes → Test with backend running on port 8000
- Frontend changes → Test with dev server on port 5173
- Full E2E flow → Both servers + `npm test` in e2e/
- Type errors → Run `npm run build` in frontend/
- Python tests → Run `pytest` from project root with venv activated

**Key Files:**
- Frontend API client: `frontend/src/api/client.ts`
- Backend entry: `api/main.py`
- Frontend state: `frontend/src/stores/useExplorerStore.ts`
- Type definitions: `frontend/src/types/`
- Python config: `api/config.py`

For frontend-specific details, see `frontend/AGENTS.md`.
