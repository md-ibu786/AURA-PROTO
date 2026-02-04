# Firestore Security Rules Architecture

## Overview

This document explains the RBAC (Role-Based Access Control) security rules for
AURA-NOTES-MANAGER. These rules enforce least-privilege access at the database
layer, even if backend authorization is bypassed.

## Architecture: Hybrid RBAC Model

We use a hybrid approach combining two Firebase features:

1. **Custom Claims** (in JWT tokens): For global roles (admin, staff, student)
   - Pros: Instant access, no database reads, free
   - Cons: Limited to 1KB total, requires token refresh to update
   - Used for: High-level role checks

2. **Firestore Documents**: For granular permissions (departmentId, subjectIds)
   - Pros: Unlimited size, instant updates, dynamic
   - Cons: Requires database read (costs money), adds latency
   - Used for: Resource-specific access control

## Collection Structure

Hierarchy collections are nested:

```
/departments/{departmentId}
  /semesters/{semesterId}
    /subjects/{subjectId}
      /modules/{moduleId}
        /notes/{noteId}
```

User documents are stored at the root level:

```
/users/{uid}
```

## Role Permissions Matrix

| Collection | Admin | Staff | Student |
|------------|-------|-------|---------|
| users | CRUD | Read self | Read self |
| departments | CRUD | Read | Read |
| semesters | CRUD | Read | Read |
| subjects | CRUD | Read/Update assigned | Read |
| modules | CRUD | Read/Update assigned subjects | Read |
| notes | CRUD | CRUD assigned subjects | Read own department |

## Helper Functions

### Authentication Checks
- `isAuthenticated()`: User is logged in
- `currentUserId()`: Get current user's UID
- `hasRole(role)`: Check Custom Claim for role

### Role Checks (Custom Claims)
- `isAdmin()`: User is admin
- `isStaff()`: User is staff
- `isStudent()`: User is student

### Granular Permission Checks (Firestore)
- `userDoc()`: Get user document from Firestore
- `isInDepartment(departmentId)`: Check if user's department matches
- `hasSubjectAccess(subjectId)`: Check if subjectId is in user's subjectIds
- `isDocumentInMyDepartment()`: Check if document's department matches user's

## Data Validation

Write operations include schema validation:

- `isValidUser()`: Enforces required user fields and role/status values
- `hasValidUserRoleFields()`: Ensures student/staff role-specific fields
- `isValidDepartment()`: Validates name/code
- `isValidSemester()`: Validates name + semester number
- `isValidSubject()`: Validates name/code
- `isValidModule()`: Validates name + module number
- `isValidNote()`: Validates title/content/subjectId/departmentId

## Security Rules Flow

1. **Authentication**: Is the user logged in?
2. **Authorization**: Does the user have the required role?
3. **Granular Check**: Does the user have access to this specific resource?
4. **Validation**: Is the data being written valid?

## Best Practices Implemented

1. **Deny by Default**: All access denied unless explicitly allowed
2. **Fail Fast**: Check Custom Claims before Firestore lookups
3. **Least Privilege**: Users only get minimum required access
4. **Defense in Depth**: Rules protect even if backend auth is bypassed

## Deployment

```bash
# Deploy rules to production
firebase deploy --only firestore:rules

# Test locally first
firebase emulators:start --only firestore,auth
```

## Testing

See: `02-03-PLAN.md` for security rules unit tests.
