# Spec: Duplicate Department Warning Dialog

## Overview
Implement a sliding top-warning dialog that appears when attempting to create a department with a name that already exists. This replaces the current auto-rename behavior with a user-facing warning.

## User Requirements
- **Animation**: Sliding from top of screen
- **Content**:
  - Main message: "The file named [nameOfTheFile] already exists"
  - Subtitle: "Department names must be unique"
- **Placement**: Fixed position at top of screen (toast-style notification)
- **Trigger**: Only on department creation with duplicate name

## API Response Specifications

### Success Response (201 Created)
- HTTP Status: 201
- Response includes created department data

### Duplicate Name Response (409 Conflict)
- HTTP Status: 409
- Error response includes:
  - Error code for duplicate detection
  - Human-readable message about duplicate name

## Success Criteria
- [ ] Warning dialog slides in from top on duplicate name attempt
- [ ] Dialog displays correct messages with dynamic name insertion
- [ ] Auto-dismiss works correctly
- [ ] Manual dismiss works correctly
- [ ] Form resets and allows retry after dismissal
- [ ] All animations are smooth and performant
- [ ] Accessibility requirements are met
- [ ] Existing functionality remains unaffected
- [ ] Code follows project style guidelines
