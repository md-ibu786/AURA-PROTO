# AURA-NOTES-MANAGER Authentication

**Status:** v1.0 Shipped (2026-03-08)
**Last updated:** 2026-03-08 after v1.0 milestone

---

## What This Is

AURA-NOTES-MANAGER is a staff portal for document management and knowledge graph processing. The v1.0 milestone delivered a complete role-based authentication system that enables:

- Secure user login with email/password (mock auth for local development)
- Three-tier access control (admin, staff, student)
- Department-level data isolation
- Session persistence across page refreshes
- Protected routes with role-based guards

---

## Core Value

**Secure, role-based access to departmental content management.**

The system ensures that staff can only manage notes in their assigned department, students can only view content, and administrators have full user management capabilities—all without requiring real Firebase credentials for local development.

---

## Requirements

### Validated (v1.0)

- ✓ Users can log in with email/password and receive a mock token — v1.0
- ✓ Protected routes redirect unauthenticated users to login page — v1.0
- ✓ Admin users can access `/admin/*` routes and user management endpoints — v1.0
- ✓ Staff users can access their assigned department's data — v1.0
- ✓ Student users have read-only access to their department's notes — v1.0
- ✓ Auth state persists across page refreshes — v1.0
- ✓ Mock authentication works without real Firebase credentials — v1.0

### Active (Next Milestone)

- [ ] Real Firebase Authentication integration
- [ ] Password reset functionality
- [ ] Email verification
- [ ] Session expiration warnings
- [ ] Audit logging for user actions

### Out of Scope

- OAuth/social login providers — not needed for internal staff tool
- Multi-factor authentication — deferred until security audit
- Mobile app authentication — web-first approach

---

## Context

### Current State (v1.0)

**Codebase:**
- Backend: FastAPI with Python 3.10+, mock Firestore implementation
- Frontend: React 18 + TypeScript 5.6 + Vite + Zustand
- Lines of Code: ~2,000 (auth system only)
- Test Coverage: 8 integration tests, 8 unit tests for mock Firestore

**Shipped Features:**
- Mock Firestore with collection/document/query support
- Token verification supporting mock tokens (`mock-token-{role}-{uid}`)
- FastAPI dependencies for role-based protection
- User CRUD API (admin only)
- Zustand auth store with localStorage persistence
- Login page with form validation
- ProtectedRoute component
- Logout functionality in sidebar
- Seed script with 3 test users

### Key Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| Mock Firestore for local dev | Avoid Firebase credential requirements for development | ✓ Good |
| Zustand for auth state | Lightweight, no Redux boilerplate | ✓ Good |
| Three-tier role system | Matches organizational structure (admin/staff/student) | ✓ Good |
| Bearer token auth | Standard approach, works with both mock and real Firebase | ✓ Good |
| localStorage for session | Simple persistence, acceptable for v1.0 | ⚠️ Revisit (consider httpOnly cookies) |

### Technical Debt

- Mock Firestore is in-memory only (data lost on restart)
- No session expiration handling on frontend
- localStorage session storage (vulnerable to XSS)
- No rate limiting on login attempts

---

## Current Focus

**Planning next milestone** — Considering:
1. Real Firebase Authentication integration
2. Knowledge Graph processing improvements
3. Note management UI enhancements

---

## Files

**Backend:**
- `api/mock_firestore.py` — Mock Firestore implementation
- `api/auth.py` — Authentication module
- `api/users.py` — User management endpoints
- `api/test_auth_integration.py` — Integration tests

**Frontend:**
- `frontend/src/stores/useAuthStore.ts` — Auth state
- `frontend/src/api/client.ts` — API client with auth headers
- `frontend/src/pages/LoginPage.tsx` — Login UI
- `frontend/src/components/ProtectedRoute.tsx` — Route guards

**Tools:**
- `tools/seed_users.py` — Database seeding
- `TEST_CREDENTIALS.md` — Test account reference

---

*Last updated: 2026-03-08 after v1.0 milestone*
