# Spec: Fix Warning Dialog in Grid and List Views

## Overview
Replace the generic browser `alert()` with the custom, animated `WarningDialog` component in `GridView.tsx` and `ListView.tsx`. This ensures a consistent user experience across all parts of the application when a duplicate department name is encountered.

## Functional Requirements
- **Intercept 409 Errors:** Update the creation and renaming logic in `GridView` and `ListView` to catch `DuplicateError`.
- **Trigger Warning Dialog:** Instead of calling `alert()`, call `openWarningDialog` from the `useExplorerStore`.
- **Consistent Messaging:** Use the template:
    - **Main Message:** "The file named [name] already exists"
    - **Subtitle:** "Department names must be unique"
- **State Cleanup:** Ensure the creation/rename input remains active or resets gracefully after the warning is triggered, matching the Sidebar behavior.

## Acceptance Criteria
- [ ] Attempting to create a duplicate department in Grid View shows the sliding top-warning dialog.
- [ ] Attempting to rename a department to an existing name in Grid View shows the sliding top-warning dialog.
- [ ] The same applies to List View.
- [ ] Native browser `alert()` is no longer used for duplication errors in these components.
- [ ] The warning dialog displays the correct dynamic entity name.

## Out of Scope
- Implementing duplicate checks for other hierarchy levels (Semester, Subject, etc.) unless they already return 409 from the backend.
- Modifying the styling of the `WarningDialog` itself.
