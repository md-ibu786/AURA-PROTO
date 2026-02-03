# Test Credentials

## Mock Authentication Users

These accounts work when `USE_REAL_FIREBASE=false` (default for local development).

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@test.com | Admin123! |
| Staff | staff@test.com | Staff123! |
| Student | student@test.com | Student123! |

## Role Permissions

| Role | View All Depts | Upload Notes | Manage Users |
|------|----------------|--------------|--------------|
| Admin | Yes | No | Yes |
| Staff | Own Dept Only | Own Dept Only | No |
| Student | Own Dept Only | No | No |

## Running with Mock Auth

1. Ensure `.env` has: `USE_REAL_FIREBASE=false`
2. Start backend: `cd api && python -m uvicorn main:app --reload --port 8000`
3. Start frontend: `cd frontend && npm run dev`
4. Login at: http://localhost:5173/login

## Notes

- Mock auth stores tokens in localStorage as `auth_token`
- Mock tokens format: `mock-token-{role}-{uid}`
- No real Firebase credentials required for local development
