# 03-01 Mock DB Mapping

## Source Structure (mock_db.json)

Top-level keys are Firestore collection paths. Nested subcollections are
represented as flat keys with full paths.

Collections present:
- users
- departments
- departments/{departmentId}/semesters
- departments/{departmentId}/semesters/{semesterId}/subjects
- departments/{departmentId}/semesters/{semesterId}/subjects/{subjectId}/modules
- departments/{departmentId}/semesters/{semesterId}/subjects/{subjectId}/modules/{moduleId}/notes

## Fields By Entity

Users (keyed by mock user ID):
- email
- displayName
- role (admin | staff | student)
- status (active | disabled)
- departmentId (string or empty)
- subjectIds (array, staff only)
- createdAt (ISO string)
- updatedAt (ISO string)
- password (present on some records, mock-only)

Departments (documents under departments):
- id
- name
- code

Semesters (documents under departments/{id}/semesters):
- id
- name
- semester_number (int)
- department_id

Subjects (documents under departments/{id}/semesters/{id}/subjects):
- id
- name
- code
- semester_id

Modules (documents under .../subjects/{id}/modules):
- id
- name
- module_number (int)
- subject_id

Notes (documents under .../modules/{id}/notes):
- id
- title
- pdf_url
- created_at (ISO string)
- module_id

## Relationships

- departments -> semesters -> subjects -> modules -> notes (nested)
- users reference departmentId and subjectIds (subject IDs)
- semester.department_id links to department
- subject.semester_id links to semester
- module.subject_id links to subject
- note.module_id links to module

## Migration Order

1. users (auth + role metadata)
2. departments
3. semesters
4. subjects
5. modules
6. notes

## Destination Mapping (Firestore)

Users:
- Destination: users/{uid}
- uid is taken from mock_db.json user key
- Keep email, displayName, role, status, departmentId, subjectIds
- Normalize departmentId: empty string -> null
- Drop password (mock-only)
- Add _v (schema version) and migration metadata

Departments:
- Destination: departments/{departmentId}
- Keep id, name, code

Semesters:
- Destination: departments/{departmentId}/semesters/{semesterId}
- Keep id, name, semester_number, department_id

Subjects:
- Destination: departments/{departmentId}/semesters/{semesterId}/subjects/{subjectId}
- Keep id, name, code, semester_id

Modules:
- Destination: .../subjects/{subjectId}/modules/{moduleId}
- Keep id, name, module_number, subject_id

Notes:
- Destination: .../modules/{moduleId}/notes/{noteId}
- Keep id, title, pdf_url, created_at, module_id
- Add subjectId and departmentId derived from path (if missing)

Field Name Changes:
- Users: add uid field (document ID), no snake_case -> camelCase changes
- Hierarchy collections: keep snake_case fields to match existing API usage
