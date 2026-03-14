# Coding Conventions

**Analysis Date:** 2026-03-13

## File Headers (MANDATORY)

All source files MUST include a standardized file header. This is enforced and mandatory.

**TypeScript/JavaScript files (`.ts`, `.tsx`):**
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

**Python files (`.py`):**
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

## Naming Patterns

**Files:**
- `camelCase.ts` for utility files (`client.ts`, `explorerApi.ts`)
- `PascalCase.tsx` for React components (`ExplorerPage.tsx`, `WarningDialog.tsx`)
- Co-located tests: `filename.test.ts` or `filename.test.tsx` next to source

**Functions:**
- `lowerCamelCase` for functions and methods
- `fetchApi`, `getAllDepartments`, `handleSubmit`
- Async functions prefixed with verb indicating action: `fetch*`, `get*`, `create*`, `update*`, `delete*`

**Variables:**
- `const` by default, `let` when reassignment needed
- **NEVER use `var`**
- `lowerCamelCase` for variables
- `ALL_CAPS_WITH_UNDERSCORES` for constants: `API_BASE`, `MAX_RETRIES`

**Types:**
- `PascalCase` for interfaces, types, enums
- Examples: `FileSystemNode`, `HierarchyType`, `ViewMode`
- Use `T[]` for simple arrays, `Array<T>` for complex unions

**Classes:**
- `PascalCase` for class names
- Use TypeScript's `private`/`protected` modifiers (not `#private` fields)
- **NEVER use `public` modifier** (it's the default)
- Mark readonly properties with `readonly`

## Code Style

**Formatting (Google TypeScript Style Guide):**
- Single quotes (`'`) for strings
- Template literals (`` ` ``) for interpolation and multi-line strings
- Explicit semicolons (no ASI reliance)
- Line length: ~100 characters (soft limit)

**Linting:**
- ESLint 9.x with `typescript-eslint`
- Config: `frontend/eslint.config.js`
- Plugins: `@eslint/js`, `typescript-eslint`, `react-hooks`, `react-refresh`
- React Refresh rule: `only-export-components` with `allowConstantExport: true`

**Strict TypeScript Settings:**
```json
{
  "strict": true,
  "noUnusedLocals": true,
  "noUnusedParameters": true,
  "noFallthroughCasesInSwitch": true,
  "noUncheckedSideEffectImports": true
}
```

## Import Organization

**Order (observed in codebase):**
1. React/Node built-ins
2. External libraries (zustand, @tanstack/react-query)
3. Internal absolute imports (`@/components`, `@/stores`)
4. Internal relative imports (`../types`, `./client`)
5. Type-only imports last

**Path Aliases:**
- `@/` maps to `frontend/src/`
- Configured in `tsconfig.app.json` and `vite.config.ts`

## Error Handling

**Patterns (NEVER leave empty catch blocks):**
```typescript
try {
    await riskyOperation();
} catch (error) {
    if (error instanceof DuplicateError) {
        // Handle specific error type
        showWarningDialog(error.message);
    } else {
        console.error('Operation failed:', error);
        throw error; // Re-throw if can't handle
    }
}
```

**Custom Error Classes:**
- `DuplicateError` in `frontend/src/api/client.ts` for 409 conflicts
- Always extends Error with additional properties

### Logging

**Framework:** `console` (browser native)

**Patterns:**
- `console.error` for actual errors
- `console.warn` for non-critical warnings
- Include context in messages: `'Failed to get auth token', e`

### Function Design

**Size:** Small, focused functions (typically <50 lines)

**Parameters:**
- Use options object pattern for >3 parameters
- Destructure when appropriate

**Return Values:**
- Always type return values in function signatures
- Use explicit return types for public APIs

### Module Design

**Exports:**
- Use **named exports** exclusively
- **DO NOT use default exports**
- Example: `export { fetchApi, DuplicateError }`

**Barrel Files:**
- Present in stores (`src/stores/index.ts`)
- Re-export from feature folders

## Python Conventions

### Naming Patterns

**Files:**
- `snake_case.py` for modules (`hierarchy_crud.py`, `audio_processing.py`)

**Functions/Methods:**
- `snake_case` for functions
- Examples: `get_all_departments`, `create_note_endpoint`

**Variables:**
- `snake_case` for variables
- `_internal` single leading underscore for internal members

**Classes:**
- `PascalCase` for classes
- Examples: `FakeDocSnapshot`, `FirestoreUser`, `ApiHelper`

**Constants:**
- `ALL_CAPS_WITH_UNDERSCORES`
- Examples: `API_BASE`, `MAX_RETRIES`

### Code Style (Google Python Style Guide)

**Formatting:**
- **Line length: 80 characters maximum**
- **Indentation: 4 spaces** (never tabs)
- Two blank lines between top-level definitions
- One blank line between method definitions

**Imports:**
- Use `import x` for packages/modules
- Use `from x import y` only when `y` is a submodule
- Group imports: standard library, third-party, application
- Each import on separate line

**Docstrings:**
- Use `"""triple double quotes"""`
- Every public module, function, class, method must have docstring
- Include `Args:`, `Returns:`, and `Raises:` sections
- Example:
```python
def _make_user(
    uid: str,
    role: models.UserRole,
    status: models.UserStatus = 'active',
) -> models.FirestoreUser:
    """Build a FirestoreUser for tests.

    Args:
        uid: Firebase uid.
        role: User role.
        status: Account status.

    Returns:
        FirestoreUser: User model.
    """
```

### Error Handling

**Patterns:**
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

**Specific exception types:** Always use specific exceptions, never bare `except:`

### Type Annotations

- Type annotations strongly encouraged for public APIs
- Use `typing` module for complex types: `Optional[str]`, `list[str]`, `dict[str, Any]`

## Testing Conventions

**Test File Naming:**
- TypeScript: `filename.test.ts` (co-located with source)
- Python: `test_*.py` (in `tests/` or co-located)

**Test Organization:**
- Use `describe` blocks for grouping in Vitest
- Use class-based grouping in Python pytest
- Descriptive test names: `should_throw_DuplicateError_on_409`

**Mocking:**
- Use `vi.mock()` in Vitest for module mocking
- Use `monkeypatch` and `unittest.mock` in Python

---

*Convention analysis: 2026-03-13*
