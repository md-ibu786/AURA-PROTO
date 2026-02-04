# Roadmap: Firebase RBAC Migration

## Overview

This roadmap outlines the migration from mock authentication (`mock_db.json` / `mock_firestore.py`) to production Firebase Firestore & Authentication with robust Role-Based Access Control (RBAC). The implementation follows the **2025 Hybrid RBAC Model**: Custom Claims for coarse-grained global roles and Firestore Documents for fine-grained resource-specific permissions.

**Base Plan Reference:** @FIREBASE_RBAC_MIGRATION_PLAN.md

## Research Summary

### Best Practices Incorporated (2025-2026)

1. **Hybrid RBAC Architecture**
   - Custom Claims: `admin`, `staff`, `student` roles in JWT (free, instant checks)
   - Firestore Documents: `subjectIds`, `departmentId` for granular permissions (dynamic, unlimited)
   - Custom Claims limited to 1KB total - keep roles coarse

2. **Backend Token Verification (FastAPI)**
   - Use Dependency Injection over Middleware (better OpenAPI/Swagger integration)
   - `firebase_admin.auth.verify_id_token()` auto-caches Google public keys
   - Sync dependencies run in threadpool automatically

3. **Frontend Token Management (React)**
   - Use `onIdTokenChanged()` instead of `onAuthStateChanged()` to catch token refreshes
   - Never store tokens manually - use Firebase SDK's IndexedDB persistence
   - Use Axios interceptors for just-in-time token refresh before API calls

4. **Data Migration**
   - Use `BulkWriter` instead of `WriteBatch` for >500 documents
   - Ensure idempotency with migration state tracking
   - Backup via Managed Export before running migration scripts

5. **Security Rules Patterns**
   - Use helper functions to wrap RBAC logic
   - Test 100% in Firebase Emulator before production deployment
   - Deploy via CI/CD with `firebase deploy --only firestore:rules`

6. **App Check (Production Security)**
   - Use reCAPTCHA Enterprise provider for web apps
   - Verify `X-Firebase-AppCheck` header in FastAPI
   - Start in "Monitor" mode before enforcing

## Phases

- [ ] **Phase 1: Infrastructure & Configuration** - Firebase project setup and credentials
- [ ] **Phase 2: Firestore Schema & Security Rules** - Production schema and RBAC rules
- [ ] **Phase 3: Data Migration** - Seed production Firestore from mock_db.json
- [ ] **Phase 4: Backend Auth Refactor** - Real ID token verification in FastAPI
- [ ] **Phase 5: Frontend Firebase SDK Integration** - Real Firebase Auth in React
- [ ] **Phase 6: App Check & Security Hardening** - Production security measures
- [ ] **Phase 7: Testing & Verification** - End-to-end RBAC validation

## Phase Details

### Phase 1: Infrastructure & Configuration
**Goal**: Connect backend to real Firebase project with proper credentials and environment setup
**Depends on**: Nothing (first phase)
**Plans**: 2 plans

Plans:
- [ ] [01-01-PLAN.md](phases/01-infrastructure-config/01-01-PLAN.md): Firebase project setup - Create/configure project, enable Auth & Firestore, download service account key
- [ ] [01-02-PLAN.md](phases/01-infrastructure-config/01-02-PLAN.md): Backend configuration - Update `api/config.py` with environment-based Firebase initialization

Key Deliverables:
- Firebase project with Authentication and Firestore enabled
- Service account key with `Firebase Admin SDK Administrator` + `Cloud Datastore User` roles
- `.env` configuration: `USE_REAL_FIREBASE=true`, `FIREBASE_CREDENTIALS` path
- `init_firebase()` correctly loading service account
- `get_db()` switching between mock and real Firestore based on env

Technical Notes:
- Service account key MUST be in `.gitignore`
- Use `GOOGLE_APPLICATION_CREDENTIALS` environment variable for production deployments
- Consider using Google Cloud Secret Manager for credentials in production

---

### Phase 2: Firestore Schema & Security Rules
**Goal**: Define production user schema with RBAC fields and deploy security rules
**Depends on**: Phase 1
**Plans**: 3 plans

Plans:
- [ ] [02-01-PLAN.md](phases/02-firestore-schema-rules/02-01-PLAN.md): User collection schema - Define `users/{uid}` document structure with role, departmentId, subjectIds
- [ ] [02-02-PLAN.md](phases/02-firestore-schema-rules/02-02-PLAN.md): Security rules implementation - Write `firestore.rules` with helper functions for RBAC
- [ ] [02-03-PLAN.md](phases/02-firestore-schema-rules/02-03-PLAN.md): Security rules testing - Unit tests using Firebase Emulator and `@firebase/rules-unit-testing`

Key Deliverables:
- `users` collection schema:
  ```json
  {
    "uid": "string (matches Auth UID)",
    "email": "string",
    "displayName": "string",
    "role": "enum('admin', 'staff', 'student')",
    "status": "enum('active', 'disabled')",
    "departmentId": "string (required for student)",
    "subjectIds": ["string"] (required for staff),
    "createdAt": "timestamp",
    "updatedAt": "timestamp"
  }
  ```
- `firestore.rules` with:
  - `isAdmin()` helper using Custom Claims
  - `isStaffForSubject(subjectId)` helper using Firestore lookup
  - `isStudentInDepartment(deptId)` helper
- Security rules test suite with emulator

Technical Notes (from research):
- Use helper functions to keep rules DRY:
  ```javascript
  function isAdmin() {
    return request.auth.token.role == 'admin';
  }
  function hasSubjectAccess(subjectId) {
    return subjectId in get(/databases/$(database)/documents/users/$(request.auth.uid)).data.subjectIds;
  }
  ```
- Deny by default, allow explicitly
- `exists()` and `get()` count as document reads - use Custom Claims for frequent checks

---

### Phase 3: Data Migration
**Goal**: Migrate existing mock_db.json data to production Firestore
**Depends on**: Phase 2
**Plans**: 2 plans

Plans:
- [ ] [03-01-PLAN.md](phases/03-data-migration/03-01-PLAN.md): Migration script - Create `tools/seed_firestore.py` using BulkWriter for idempotent migration
- [ ] [03-02-PLAN.md](phases/03-data-migration/03-02-PLAN.md): Execute and verify - Run migration, verify in Firebase Console, document rollback procedure

Key Deliverables:
- `tools/seed_firestore.py` with:
  - BulkWriter for batch operations (handles throttling automatically)
  - Idempotency via `schema_version` field
  - Progress logging and error handling
  - Retry logic (up to 3 attempts per document)
- Migration order: `users` -> `departments` -> `semesters` -> `subjects` -> `modules` -> `notes`
- Verification script to compare document counts
- Rollback procedure documented

Technical Notes (from research):
- Use `BulkWriter` instead of `WriteBatch` for >500 documents
- Add `migrated_at: timestamp` field for tracking
- Always perform Managed Export backup before migration:
  ```bash
  gcloud firestore export gs://[BUCKET_NAME] --collection-ids=users,departments
  ```
- Test migration in Firestore Emulator first, then staging project

---

### Phase 4: Backend Auth Refactor
**Goal**: Replace mock token bypass with real Firebase ID token verification
**Depends on**: Phase 3
**Plans**: 3 plans

Plans:
- [ ] 04-01: Token verification refactor - Update `api/auth.py` to use real `verify_id_token()`
- [ ] 04-02: User sync endpoint - Create endpoint to sync Firebase Auth user to Firestore on first login
- [ ] 04-03: Remove mock login - Delete `POST /api/auth/login` and update user creation to use Firebase Auth

Key Deliverables:
- `verify_firebase_token()` updated:
  - Remove mock-token bypass (or limit to `TESTING=true` environment only)
  - Call `auth.verify_id_token(token)` for all production requests
  - Extract `uid` and lookup user in Firestore for fresh role/permissions
- `get_current_user()` dependency:
  - Fetch user doc from Firestore: `db.collection("users").document(uid).get()`
  - Merge Custom Claims with Firestore permissions
- User creation flow:
  - Admin creates user in Firebase Auth: `auth.create_user(email, password)`
  - Then creates Firestore user doc with metadata
  - Set Custom Claims: `auth.set_custom_user_claims(uid, {'role': 'staff'})`

Technical Notes (from research):
- Dependency Injection pattern for FastAPI:
  ```python
  from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
  
  security = HTTPBearer()
  
  async def get_current_user(res: HTTPAuthorizationCredentials = Depends(security)):
      token = res.credentials
      decoded_token = auth.verify_id_token(token)
      # Lookup user in Firestore for latest permissions
      user_doc = db.collection("users").document(decoded_token["uid"]).get()
      return UserInfo(**user_doc.to_dict())
  ```
- Token refresh: Claims don't update until token refreshes (~1 hour) - always check Firestore for dynamic permissions

---

### Phase 5: Frontend Firebase SDK Integration
**Goal**: Replace mock login with real Firebase Authentication in React
**Depends on**: Phase 4
**Plans**: 3 plans

Plans:
- [ ] 05-01: Firebase SDK setup - Install and configure Firebase SDK in frontend
- [ ] 05-02: Auth flow implementation - Update LoginPage to use `signInWithEmailAndPassword()`
- [ ] 05-03: Token management - Implement `onIdTokenChanged()` listener and API client interceptors

Key Deliverables:
- `frontend/src/lib/firebase.ts`:
  ```typescript
  import { initializeApp } from 'firebase/app';
  import { getAuth } from 'firebase/auth';
  
  const firebaseConfig = {
    apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
    authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
    projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  };
  
  export const app = initializeApp(firebaseConfig);
  export const auth = getAuth(app);
  ```
- Updated `LoginPage.tsx`:
  - Replace `fetch('/api/auth/login')` with `signInWithEmailAndPassword(auth, email, password)`
  - Handle Firebase Auth errors with user-friendly messages
  - Get ID token: `await user.getIdToken()`
- `useAuthStore` updates:
  - Add `onIdTokenChanged()` listener (catches token refreshes)
  - Remove localStorage token storage (use SDK persistence)
- API client interceptor:
  ```typescript
  apiClient.interceptors.request.use(async (config) => {
    const user = auth.currentUser;
    if (user) {
      const token = await user.getIdToken(); // Auto-refreshes if expired
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });
  ```

Technical Notes (from research):
- Use `onIdTokenChanged()` NOT `onAuthStateChanged()` - it fires on token refresh too
- Never store tokens in localStorage manually - Firebase SDK handles IndexedDB persistence
- `getIdToken()` returns cached token if valid, auto-refreshes if expired
- For forced refresh (after role change): `user.getIdToken(true)`

---

### Phase 6: App Check & Security Hardening
**Goal**: Add Firebase App Check and production security measures
**Depends on**: Phase 5
**Plans**: 3 plans

Plans:
- [ ] 06-01: Frontend App Check - Initialize App Check with reCAPTCHA Enterprise provider
- [ ] 06-02: Backend App Check verification - Add FastAPI dependency to verify `X-Firebase-AppCheck` header
- [ ] 06-03: Security hardening - API key restrictions, domain restrictions, security headers

Key Deliverables:
- Frontend App Check setup:
  ```typescript
  import { initializeAppCheck, ReCaptchaEnterpriseProvider } from 'firebase/app-check';
  
  const appCheck = initializeAppCheck(app, {
    provider: new ReCaptchaEnterpriseProvider('SITE_KEY'),
    isTokenAutoRefreshEnabled: true
  });
  ```
- Backend verification dependency:
  ```python
  from firebase_admin import app_check
  
  async def verify_app_check(x_firebase_appcheck: str = Header(None)):
      if not x_firebase_appcheck:
          raise HTTPException(401, "App Check token missing")
      app_check.verify_token(x_firebase_appcheck)
  ```
- Debug token setup for local development
- API client updated to include App Check token in requests
- Security checklist completed:
  - [ ] Firestore Security Rules deployed
  - [ ] Service Account Key in `.gitignore`
  - [ ] Frontend API Keys restricted to domains in Google Cloud Console
  - [ ] CORS configured for production domains only
  - [ ] Rate limiting on auth endpoints

Technical Notes (from research):
- Start App Check in "Monitor" mode - check Firebase Console metrics before enforcing
- Use reCAPTCHA Enterprise (not v3) for better bot detection
- Debug tokens required for local development - generate in Firebase Console
- App Check tokens are short-lived, SDK auto-refreshes them

---

### Phase 7: Testing & Verification
**Goal**: Comprehensive testing of the complete RBAC system
**Depends on**: Phase 6
**Plans**: 3 plans

Plans:
- [ ] 07-01: Backend RBAC unit tests - Test decorators, dependencies, and permission checks
- [ ] 07-02: Security rules unit tests - Complete test coverage with Firebase Emulator
- [ ] 07-03: End-to-end integration tests - Full flow testing with real Firebase (staging project)

Key Deliverables:
- `tests/test_rbac.py`:
  - Mock `verify_id_token` to return specific claims
  - Test `require_admin`, `require_staff` decorators
  - Test access denial (Student trying to delete Department -> 403)
  - Test access grant (Staff editing assigned Subject -> 200)
- Security rules test suite:
  - Use `@firebase/rules-unit-testing` with emulator
  - Test all RBAC scenarios per role
  - Test edge cases (disabled user, missing permissions)
- Integration test scenarios:
  1. Admin login -> Create Staff user -> Verify in Firebase Auth + Firestore
  2. Staff login -> Try delete Department -> Should fail 403
  3. Staff login -> Add Note to assigned Subject -> Should pass 200
  4. Student login -> Try edit Note -> Should fail 403
  5. Token refresh after role change -> Verify new permissions applied

Technical Notes (from research):
- Use Firebase Emulator Suite for local testing:
  ```bash
  firebase emulators:start --only auth,firestore
  ```
- Security rules tests:
  ```javascript
  import { assertSucceeds, assertFails } from '@firebase/rules-unit-testing';
  
  await assertFails(studentContext.firestore().doc('notes/x').delete());
  await assertSucceeds(staffContext.firestore().doc('notes/x').update({...}));
  ```
- Run emulator tests in CI/CD pipeline before deployment

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Infrastructure & Configuration | 0/2 | Not started | - |
| 2. Firestore Schema & Security Rules | 0/3 | Not started | - |
| 3. Data Migration | 0/2 | Not started | - |
| 4. Backend Auth Refactor | 0/3 | Not started | - |
| 5. Frontend Firebase SDK Integration | 0/3 | Not started | - |
| 6. App Check & Security Hardening | 0/3 | Not started | - |
| 7. Testing & Verification | 0/3 | Not started | - |

## Plan Files

All executable plans are located in `.planning/firebase-rbac-migration/phases/`:

```
.planning/firebase-rbac-migration/phases/
├── 01-infrastructure-config/
│   ├── 01-01-PLAN.md   # Firebase project setup
│   └── 01-02-PLAN.md   # Backend configuration
├── 02-firestore-schema-rules/
│   ├── 02-01-PLAN.md   # User collection schema
│   ├── 02-02-PLAN.md   # Security rules implementation
│   └── 02-03-PLAN.md   # Security rules testing
├── 03-data-migration/
│   ├── 03-01-PLAN.md   # Migration script
│   └── 03-02-PLAN.md   # Execute and verify
├── 04-backend-auth-refactor/
│   ├── 04-01-PLAN.md   # Token verification refactor
│   ├── 04-02-PLAN.md   # User sync endpoint
│   └── 04-03-PLAN.md   # Remove mock login
├── 05-frontend-firebase-sdk/
│   ├── 05-01-PLAN.md   # Firebase SDK setup
│   ├── 05-02-PLAN.md   # Auth flow implementation
│   └── 05-03-PLAN.md   # Token management
├── 06-app-check-security/
│   ├── 06-01-PLAN.md   # Frontend App Check
│   ├── 06-02-PLAN.md   # Backend App Check verification
│   └── 06-03-PLAN.md   # Security hardening
└── 07-testing-verification/
    ├── 07-01-PLAN.md   # Backend RBAC unit tests
    ├── 07-02-PLAN.md   # Security rules unit tests
    └── 07-03-PLAN.md   # E2E integration tests
```

Execute plans with: `/run-plan .planning/firebase-rbac-migration/phases/01-infrastructure-config/01-01-PLAN.md`

## Rollback Strategy

If migration fails at any point:
1. Revert `.env`: `USE_REAL_FIREBASE=false`
2. This switches `api/config.py` back to `mock_firestore.py`
3. Restore Firestore from Managed Export if data was corrupted

## User Roles Reference (Unchanged from Mock Auth)

| Role | Dashboard Access | Users Mgmt | Department/Semester/Subject Mgmt | Module/Note Mgmt |
|------|------------------|------------|----------------------------------|------------------|
| **Admin** | Full Access | Full CRUD | Full CRUD | Full CRUD |
| **Staff** | Restricted | View Self | Read-Only (Assigned Dept) | Edit (Assigned Subjects Only) |
| **Student** | Read-Only | View Self | Read-Only (Assigned Dept) | Read-Only |

## Technical Stack

**Backend:**
- FastAPI with Firebase Admin SDK (Python)
- Firebase Authentication (ID Token verification)
- Cloud Firestore (production database)
- Firebase App Check (request verification)

**Frontend:**
- React 18 + TypeScript 5.6
- Firebase JS SDK v10/v11
- Zustand for auth state
- Axios with interceptors for token management

**Security:**
- Firestore Security Rules with RBAC helpers
- Custom Claims for global roles
- App Check with reCAPTCHA Enterprise
- HTTPS-only, domain-restricted API keys

## Dependencies

```
# Backend (add to requirements.txt)
firebase-admin>=6.0.0

# Frontend (add to package.json)
firebase: ^10.0.0 or ^11.0.0
```
