---
phase: quick
plan: 2
type: execute
wave: 1
depends_on: []
files_modified: []
autonomous: true
requirements:
  - QUICK-02
must_haves:
  truths:
    - All test files are identified and catalogued
    - Test compatibility issues are documented
    - Failing tests are categorized by fix type
    - Test coverage gaps are identified
  artifacts:
    - path: ".planning/quick/2-check-if-the-current-test-files-are-comp/TEST_AUDIT_REPORT.md"
      provides: "Comprehensive test audit report"
  key_links:
    - from: "Test files"
      to: "Implementation files"
      via: "Import/require statements"
---

<objective>
Audit and verify compatibility of all test files with current project functionality and recent updates.

Purpose: Ensure test suite accurately reflects current codebase state and identify tests that need updates.
Output: Test audit report documenting passing/failing tests, compatibility issues, and recommendations.
</objective>

<execution_context>
@C:/Users/Peter/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md

## Test Structure Overview

### AURA-NOTES-MANAGER (Frontend)
- **Unit Tests**: Vitest + @testing-library/react (14 test files)
- **E2E Tests**: Playwright (6 spec files in e2e/)
- **Firestore Rules Tests**: Jest (1 test file, requires emulator)

### AURA-CHAT
- **Unit Tests (Python)**: pytest in tests/unit/ (9 test files, 118 tests)
- **Unit Tests (Frontend)**: Vitest (17 test files)
- **E2E Tests**: Playwright (8 spec files in client/e2e/)

## Recent Architectural Changes (from CLAUDE.md)
1. **Thinking Mode Implementation** (January 2026) - Dual SDK approach for AI
2. **Session-Based Chat Architecture** - Persistent study sessions with Neo4j
3. **Module Hierarchy Navigation** - 4-level hierarchy (Dept → Semester → Subject → Module)
4. **Dual Backend Strategy** - AURA-CHAT has server/ (modern) and backend/ (legacy)
5. **Feature-Based Frontend Organization** - Both apps use src/features/{name}/ structure

## Current Test Status (Preliminary)

### AURA-NOTES-MANAGER Frontend
- 14/15 test files passing (176 tests passed, 73 skipped)
- 1 failing: firestore.rules.test.ts (requires Firebase emulator)

### AURA-CHAT Client
- 11/17 test files passing (181 tests passed)
- 6 failing: 46 tests failed (hierarchy-related test issues)

### AURA-CHAT Python (tests/unit/)
- 115/118 tests passing
- 3 failing: credential path and module attribute issues
</context>

<tasks>

<task type="auto">
  <name>Task 1: Catalog all test files</name>
  <files>N/A (discovery only)</files>
  <action>
Find and catalog all test files in both projects:

1. AURA-NOTES-MANAGER:
   - Frontend unit tests (*.test.ts, *.test.tsx)
   - E2E tests (e2e/*.spec.ts)
   - Firestore rules tests
   - API tests (if any in api/tests/)

2. AURA-CHAT:
   - Frontend unit tests (client/src/**/*.test.ts, *.test.tsx)
   - E2E tests (client/e2e/*.spec.ts)
   - Python unit tests (tests/unit/*.py)
   - Integration tests (tests/integration/*.py)

For each test file, record:
- File path
- Test framework (Vitest, pytest, Playwright, Jest)
- Approximate number of tests
- Last modified date (if available)

Use glob patterns and directory listings to find all test files.
  </action>
  <verify>
    <automated>ls -la AURA-NOTES-MANAGER/frontend/src/**/*.test.* AURA-CHAT/client/src/**/*.test.* AURA-CHAT/tests/unit/*.py 2>/dev/null | wc -l returns > 0</automated>
  </verify>
  <done>Complete inventory of all test files in both projects with framework identification</done>
</task>

<task type="auto">
  <name>Task 2: Run all test suites and capture results</name>
  <files>N/A (test execution)</files>
  <action>
Run all test suites and capture detailed results:

1. AURA-NOTES-MANAGER Frontend:
   ```bash
   cd AURA-NOTES-MANAGER/frontend
   npm test -- --run 2>&1 | tee test-results.log
   ```

2. AURA-CHAT Client:
   ```bash
   cd AURA-CHAT/client
   npm test -- --run 2>&1 | tee test-results.log
   ```

3. AURA-CHAT Python:
   ```bash
   cd AURA-CHAT
   ../.venv/Scripts/python -m pytest tests/unit/ -v --tb=short 2>&1 | tee python-test-results.log
   ```

4. AURA-NOTES-MANAGER API (if tests exist):
   ```bash
   cd AURA-NOTES-MANAGER/api
   ../../.venv/Scripts/python -m pytest tests/ -v --tb=short 2>&1 | tee api-test-results.log
   ```

For each failing test, capture:
- Test name and file
- Error message
- Stack trace (first 10 lines)
- Category of failure (import error, assertion failure, timeout, etc.)
  </action>
  <verify>
    <automated>All test commands execute and produce output files with test results</automated>
  </verify>
  <done>Test results captured for all test suites with failure details documented</done>
</task>

<task type="auto">
  <name>Task 3: Analyze test compatibility and create audit report</name>
  <files>.planning/quick/2-check-if-the-current-test-files-are-comp/TEST_AUDIT_REPORT.md</files>
  <action>
Analyze test results and create comprehensive audit report:

1. **Compatibility Analysis**:
   - Compare test imports against actual file structure
   - Check for tests referencing renamed/moved files
   - Identify tests using outdated APIs or patterns
   - Check for tests not aligned with recent architectural changes

2. **Categorize Failures**:
   - **Infrastructure**: Missing emulators, credentials, TLS certs
   - **Code Changes**: Renamed functions, changed signatures, moved files
   - **Test Issues**: Flaky tests, incorrect mocks, outdated assertions
   - **Dependencies**: Missing packages, version mismatches

3. **Coverage Gap Analysis**:
   - Identify features without test coverage
   - Check for tests skipped with `.skip` or `pytest.mark.skip`
   - Note tests that require specific environment setup

4. **Create Report** (TEST_AUDIT_REPORT.md):
   - Executive summary (pass/fail counts per project)
   - Detailed findings per test suite
   - Failure categorization with specific examples
   - Recommendations for fixes (priority order)
   - List of tests requiring updates vs. tests requiring environment setup

Focus on actionable findings - what needs to be fixed vs. what needs to be configured.
  </action>
  <verify>
    <automated>TEST_AUDIT_REPORT.md exists with sections: Summary, Findings, Recommendations</automated>
  </verify>
  <done>Comprehensive test audit report created with categorized findings and recommendations</done>
</task>

</tasks>

<verification>
- [ ] All test files catalogued by project and framework
- [ ] Test results captured for all suites
- [ ] Failing tests categorized by root cause
- [ ] Audit report created with actionable recommendations
</verification>

<success_criteria>
1. Complete inventory of all test files across both projects
2. Test execution results documented for all suites
3. Failing tests categorized (infrastructure vs. code vs. test issues)
4. Audit report provides clear next steps for test maintenance
</success_criteria>

<output>
After completion, create `.planning/quick/2-check-if-the-current-test-files-are-comp/2-SUMMARY.md`
</output>
