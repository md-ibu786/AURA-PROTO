# Roadmap: AURA-NOTES-MANAGER Authentication

## Overview

This roadmap outlines the implementation of a complete authentication system for AURA-NOTES-MANAGER, ported from AURA-PROTO-ADMIN-PANEL. The system provides three-tier role-based access control (admin, staff, student), department-level data isolation, mock authentication for local development, and secure route protection on both backend (FastAPI dependencies) and frontend (React route guards).

## Reference Documentation

- @AUTHENTICATION_DOCUMENTATION.md - Complete specification and implementation guide

## Phases

- [x] **Phase 1: Backend Auth Foundation** - Core auth module, mock Firestore, and config updates
- [x] **Phase 2: Backend User Management** - User CRUD endpoints and login API
- [x] **Phase 3: Frontend Auth State** - Zustand auth store with session persistence
- [x] **Phase 4: Frontend Auth UI** - Login page and protected routes
- [x] **Phase 5: Seed Data & Integration** - Test users, environment config, and E2E validation

## Phase Details

### Phase 1: Backend Auth Foundation
**Goal**: Create the core authentication infrastructure with token verification and mock database support
**Depends on**: Nothing (first phase)
**Plans**: 2 plans

Plans:
- [x] [01-01-PLAN.md](phases/01-backend-auth-foundation/01-01-PLAN.md): Create `api/mock_firestore.py` with MockFirestoreClient, MockAuth, MockQuery classes
- [x] [01-02-PLAN.md](phases/01-backend-auth-foundation/01-02-PLAN.md): Create `api/auth.py` with UserInfo model, verify_firebase_token(), authentication dependencies

Key Deliverables:
- MockFirestoreClient with collection/document/where/stream support
- MockAuth with verify_id_token and mock token parsing
- UserInfo Pydantic model with uid, email, role, department_id, status
- Token verification supporting both mock tokens and real Firebase
- FastAPI dependencies for role-based endpoint protection

### Phase 2: Backend User Management
**Goal**: Complete backend API with login endpoint and user CRUD operations
**Depends on**: Phase 1
**Plans**: 1 plan

Plans:
- [x] [02-01-PLAN.md](phases/02-backend-user-management/02-01-PLAN.md): Create `api/users.py` with user CRUD endpoints (list, create, update, delete, get me) and mount routers

Key Deliverables:
- POST `/api/auth/login` - Mock login with email/password validation
- GET `/api/auth/me` - Current user profile
- GET `/api/users` - List all users (admin only)
- POST `/api/users` - Create user (admin only)
- PUT `/api/users/{id}` - Update user (admin only)
- DELETE `/api/users/{id}` - Delete user (admin only)

### Phase 3: Frontend Auth State
**Goal**: Implement Zustand-based authentication state management with session persistence
**Depends on**: Phase 2
**Plans**: 2 plans

Plans:
- [x] [03-01-PLAN.md](phases/03-frontend-auth-state/03-01-PLAN.md): Create `src/stores/useAuthStore.ts` with AuthUser interface, state, and actions
- [x] [03-02-PLAN.md](phases/03-frontend-auth-state/03-02-PLAN.md): Update `src/api/client.ts` to include Bearer token in all requests

Key Deliverables:
- AuthUser interface with id, email, role, departmentId, status
- useAuthStore with login/logout/refreshUser actions
- Permission helper functions (isAdmin, isStaff, canUploadNotes, etc.)
- initAuthListener() for session restoration from localStorage
- fetchWithAuth wrapper attaching Authorization header

### Phase 4: Frontend Auth UI
**Goal**: Create login page and protect all routes with role-based guards
**Depends on**: Phase 3
**Plans**: 2 plans

Plans:
- [x] [04-01-PLAN.md](phases/04-frontend-auth-ui/04-01-PLAN.md): Create `src/pages/LoginPage.tsx` with email/password form and error handling
- [x] [04-02-PLAN.md](phases/04-frontend-auth-ui/04-02-PLAN.md): Create `src/components/ProtectedRoute.tsx` and update `src/App.tsx` with protected routes

Key Deliverables:
- LoginPage with form validation and loading states
- Redirect after login (admin -> /admin, others -> /)
- ProtectedRoute component with requiredRole and requiredDepartment props
- App.tsx with auth listener initialization and route guards
- Loading spinner during auth initialization

### Phase 5: Seed Data & Integration
**Goal**: Finalize with test data, environment configuration, and end-to-end validation
**Depends on**: Phase 4
**Plans**: 2 plans

Plans:
- [x] [05-01-PLAN.md](phases/05-seed-data-integration/05-01-PLAN.md): Create seed script with test users and update `.env` configuration
- [x] [05-02-PLAN.md](phases/05-seed-data-integration/05-02-PLAN.md): End-to-end testing of complete auth flow and documentation update

Key Deliverables:
- Seed script with 3 test users in mock Firestore
- `.env` updates for USE_REAL_FIREBASE toggle
- E2E test: login -> protected route access -> logout
- Verification of role-based API protection
- Updated project documentation

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Backend Auth Foundation | 2/2 | **Complete** | 01-01 ✅, 01-02 ✅ |
| 2. Backend User Management | 1/1 | **Complete** | 02-01 ✅ |
| 3. Frontend Auth State | 2/2 | **Complete** | 03-01 ✅, 03-02 ✅ |
| 4. Frontend Auth UI | 2/2 | **Complete** | 04-01 ✅, 04-02 ✅ |
| 5. Seed Data & Integration | 2/2 | **Complete** | 05-01 ✅, 05-02 ✅ |

## Plan Files

All executable plans are located in `.planning/phases/`:

```
.planning/phases/
├── 01-backend-auth-foundation/
│   ├── 01-01-PLAN.md   # MockFirestoreClient implementation
│   └── 01-02-PLAN.md   # auth.py with dependencies
├── 02-backend-user-management/
│   └── 02-01-PLAN.md   # User CRUD endpoints
├── 03-frontend-auth-state/
│   ├── 03-01-PLAN.md   # useAuthStore implementation
│   └── 03-02-PLAN.md   # API client auth headers
├── 04-frontend-auth-ui/
│   ├── 04-01-PLAN.md   # LoginPage component
│   └── 04-02-PLAN.md   # ProtectedRoute and App.tsx
└── 05-seed-data-integration/
    ├── 05-01-PLAN.md   # Seed script and .env config
    └── 05-02-PLAN.md   # E2E testing and docs
```

Execute plans with: `/run-plan .planning/phases/01-backend-auth-foundation/01-01-PLAN.md`

## User Roles Reference

| Role | Permissions |
|------|-------------|
| **admin** | Full CRUD on users, view all departments/notes, cannot upload notes |
| **staff** | Upload/manage notes in assigned department, view own department data |
| **student** | Read-only access to assigned department's notes |

## Technical Stack

**Backend:**
- FastAPI with Firebase Admin SDK
- Firestore (or MockFirestoreClient for local dev)
- Bearer token authentication

**Frontend:**
- React 18 + TypeScript 5.6
- Zustand for auth state
- react-router-dom for routing
- sonner for toast notifications
