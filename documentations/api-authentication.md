# API Authentication (Firebase)

## Overview

AURA-NOTES-MANAGER uses Firebase Authentication for user sign-in. The frontend
signs in with the Firebase JS SDK, retrieves a Firebase ID token, and sends it
to the backend. The backend verifies the token with the Firebase Admin SDK,
fetches the user's Firestore document, and enforces role-based access control
(RBAC).

## Authentication Flow

1. Frontend signs in with Firebase (email/password).
2. Frontend requests a Firebase ID token (`getIdToken()`).
3. Frontend calls backend endpoints with `Authorization: Bearer <ID_TOKEN>`.
4. Backend verifies the ID token via Firebase Admin SDK.
5. Backend loads the user's Firestore document for roles/permissions.
6. Backend returns user profile data or enforces RBAC rules.

## Endpoints

### POST /api/auth/sync

Create a Firestore user document on first login, or return the existing
profile on subsequent logins.

- Auth: `Authorization: Bearer <ID_TOKEN>`
- Request body (optional):
  - `displayName` (string)
  - `departmentId` (string)
  - `subjectIds` (string[])
- Response:
  - `message` (string)
  - `isNewUser` (boolean)
  - `user` (FirestoreUser)

### GET /api/auth/me

Return the current authenticated user's profile.

- Auth: `Authorization: Bearer <ID_TOKEN>`
- Response: User profile fields (id, email, display_name, role, department_id,
  subject_ids, status, created_at, updated_at)

### POST /api/admin/users

Create a new user in Firebase Auth and Firestore (admin only).

- Auth: `Authorization: Bearer <ID_TOKEN>`
- Request body:
  - `email` (string)
  - `password` (string, minimum 6 characters)
  - `displayName` (string)
  - `role` (`admin` | `staff` | `student`)
  - `departmentId` (string, required for students)
  - `subjectIds` (string[], required for staff)
  - `sendEmailVerification` (boolean, optional)
- Response:
  - `message` (string)
  - `uid` (string)
  - `user` (FirestoreUser)

### PUT /api/admin/users/{uid}

Update an existing user in Firebase Auth and Firestore (admin only).

- Auth: `Authorization: Bearer <ID_TOKEN>`
- Request body (any subset):
  - `displayName`, `departmentId`, `subjectIds`
- Response: Updated FirestoreUser

### DELETE /api/admin/users/{uid}

Delete a user in Firebase Auth and Firestore (admin only).

- Auth: `Authorization: Bearer <ID_TOKEN>`
- Response: `{ "message": "User deleted successfully" }`

## Roles and Permissions

- `admin`: Full access to user management and hierarchy data.
- `staff`: Limited to assigned subjects and department.
- `student`: Read-only access to assigned department content.

The backend verifies roles from Firebase Custom Claims and cross-checks
Firestore user documents for current permissions.

## Error Responses

Common responses across auth endpoints:

- `401 Unauthorized`: Missing/invalid/expired ID token.
- `403 Forbidden`: Authenticated but lacks required role or status.
- `404 Not Found`: Target user does not exist.
- `409 Conflict`: Duplicate email on user creation.
- `500 Internal Server Error`: Unexpected server-side failure.

## Token Refresh Handling

Use the Firebase SDK for token lifecycle management:

- Call `getIdToken()` before API requests (auto-refreshes when expired).
- Use `onIdTokenChanged()` or `onAuthStateChanged()` to react to auth changes.
- After role updates, call `getIdToken(true)` to force refresh.

## Security Notes

- Never store Firebase ID tokens in localStorage manually.
- Keep service account keys out of git (`serviceAccountKey.json` is ignored).
- Use HTTPS in production.
- Enforce App Check for additional request integrity where applicable.

## Frontend Integration Examples

### Login and Sync

```typescript
import { signInWithEmailAndPassword } from 'firebase/auth';
import { auth } from '../api/firebaseClient';

const credentials = await signInWithEmailAndPassword(auth, email, password);
const token = await credentials.user.getIdToken();

await fetch('/api/auth/sync', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  },
  body: JSON.stringify({ displayName: credentials.user.displayName ?? '' }),
});
```

### Authenticated Request

```typescript
const token = await auth.currentUser?.getIdToken();
if (!token) throw new Error('Missing ID token');

const res = await fetch('/api/users', {
  headers: {
    'Authorization': `Bearer ${token}`,
  },
});
```
