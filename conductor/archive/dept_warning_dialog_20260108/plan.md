# Plan: Duplicate Department Warning Dialog

## Phase 1: Research & Best Practices
- [x] Task: Research React toast/notification libraries (react-hot-toast, sonner, etc.) [manual]
- [x] Task: Research CSS/framer-motion animation best practices for slide-in effects [delegated]
- [x] Task: Research error handling patterns for 409 Conflict responses [delegated]
- [x] Task: Research inline form UX patterns and accessibility [delegated]
- [x] Task: Research Zustand state management patterns for dialogs [delegated]
- [x] Task: Conductor - User Manual Verification 'Research & Best Practices' (Protocol in workflow.md) [skipped - research phase]

## Phase 2: Technology Decisions Document
- [x] Task: Create decision document specifying library, animation, error format, and state management [manual]
- [x] Task: Conductor - User Manual Verification 'Technology Decisions Document' (Protocol in workflow.md) [verified]

## Phase 3: Backend Implementation
- [x] Task: Write tests for duplicate department name check [manual]
- [x] Task: Modify Department Creation API to add duplicate validation and return 409 [manual]
- [x] Task: Update API documentation with new error response format [manual]
- [x] Task: Conductor - User Manual Verification 'Backend Implementation' (Protocol in workflow.md) [verified]

## Phase 4: Frontend State Management
- [x] Task: Write tests for new Zustand store slices [manual]
- [x] Task: Extend Zustand store with warning dialog state and actions [manual]
- [x] Task: Update and document TypeScript definitions for new state [manual]
- [x] Task: Conductor - User Manual Verification 'Frontend State Management' (Protocol in workflow.md) [verified]

## Phase 5: Warning Dialog Component
- [x] Task: Write component tests for WarningDialog [manual]
- [x] Task: Create WarningDialog component with UI structure and slide-in animation [manual]
- [x] Task: Implement auto-dismiss and manual dismiss functionality [manual]
- [x] Task: Implement accessibility features (ARIA, focus management, keyboard shortcuts) [manual]
- [x] Task: Conductor - User Manual Verification 'Warning Dialog Component' (Protocol in workflow.md) [verified]

## Phase 6: API Client Updates
- [x] Task: Update Fetch wrapper to handle 409 Conflict responses [manual]
- [x] Task: Ensure consistent error type detection [manual]
- [x] Task: Conductor - User Manual Verification 'API Client Updates' (Protocol in workflow.md) [verified]

## Phase 7: Inline Creation Form Updates
- [x] Task: Enhance SidebarTree with inline creation form [manual]
- [x] Task: Implement form submission and API integration [manual]
- [x] Task: Handle duplicate name errors and trigger warning dialog [manual]
- [x] Task: Implement form UX improvements (validation, loading states, keyboard handling) [manual]
- [x] Task: Conductor - User Manual Verification 'Inline Creation Form Updates' (Protocol in workflow.md) [verified]

## Phase 8: Styling & Theming
- [~] Task: Apply cyber yellow theme and styling to WarningDialog
- [ ] Task: Style inline creation form inputs and buttons
- [ ] Task: Conductor - User Manual Verification 'Styling & Theming' (Protocol in workflow.md)

## Phase 9: Component Integration
- [x] Task: Integrate WarningDialog into ExplorerPage [manual]
- [x] Task: Connect WarningDialog to global store [manual]
- [x] Task: Conductor - User Manual Verification 'Component Integration' (Protocol in workflow.md) [verified]

## Phase 10: Testing
- [x] Task: Implement unit tests for visibility toggling and dismiss logic [manual]
- [x] Task: Implement integration tests for the complete duplicate name flow [manual]
- [x] Task: Implement accessibility tests (keyboard, screen reader) [manual]
- [x] Task: Conductor - User Manual Verification 'Testing' (Protocol in workflow.md) [verified]
