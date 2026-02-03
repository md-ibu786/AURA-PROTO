# AURA-NOTES-MANAGER Authentication

**One-liner**: Implement role-based authentication system ported from AURA-PROTO-ADMIN-PANEL to secure the AURA-NOTES-MANAGER application.

## Problem

AURA-NOTES-MANAGER currently lacks any authentication or authorization, allowing unrestricted access to all endpoints and data. This poses security risks and prevents proper content management where staff should only manage their department's notes, and students should only view their assigned department's content.

## Success Criteria

How we know it worked:

- [ ] Users can log in with email/password and receive a mock token
- [ ] Protected routes redirect unauthenticated users to login page
- [ ] Admin users can access `/admin/*` routes and user management endpoints
- [ ] Staff users can only access their assigned department's data
- [ ] Student users have read-only access to their department's notes
- [ ] Auth state persists across page refreshes
- [ ] Mock authentication works without real Firebase credentials for local development

## Constraints

- Must use existing tech stack: FastAPI backend, React + Zustand frontend
- Must support mock authentication for local development (no Firebase credentials required)
- Must be compatible with existing Firestore database structure
- Port from AURA-PROTO-ADMIN-PANEL implementation (reference: @AUTHENTICATION_DOCUMENTATION.md)
- Three user roles only: admin, staff, student

## Out of Scope

What we're NOT building:

- Real Firebase Authentication integration (mock auth only for now)
- Password reset functionality
- Email verification
- OAuth/social login providers
- Multi-factor authentication
- Admin dashboard UI (just the authentication layer)
