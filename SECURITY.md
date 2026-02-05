# Security Documentation - AURA-NOTES-MANAGER

**Document Version:** 1.0.0
**Last Updated:** 2026-02-05
**Owner:** Development Team

---

## Table of Contents

1. [Authentication](#authentication)
2. [Authorization (RBAC)](#authorization-rbac)
3. [App Check Security](#app-check-security)
4. [API Security](#api-security)
5. [Database Security](#database-security)
6. [Secrets Management](#secrets-management)
7. [Deployment Checklist](#deployment-checklist)
8. [Incident Response](#incident-response)
9. [Security Update Procedures](#security-update-procedures)

---

## Authentication

AURA-NOTES-MANAGER uses **Firebase Authentication** for all user authentication.

### Token-Based Authentication

- All API requests must include a valid Firebase ID token in the `Authorization` header
- Tokens are Bearer-encoded: `Authorization: Bearer <token>`
- Tokens are verified server-side using Firebase Admin SDK
- **Clock skew tolerance:** 10 seconds (prevents "token used too early" errors)

### Token Verification

```python
from firebase_admin import auth

decoded_token = auth.verify_id_token(token, clock_skew_seconds=10)
```

### Session Management

- Tokens are validated on every protected request
- Users are looked up in Firestore for current permissions
- Disabled users receive 403 Forbidden responses
- Token expiration is handled by Firebase SDK

### Protected Endpoints

All endpoints under `/api/*` require authentication except:
- `GET /health` - Health check endpoint
- `GET /ready` - Readiness probe
- `GET /departments` - Public hierarchy read
- `GET /departments/{id}/semesters` - Public hierarchy read
- `GET /semesters/{id}/subjects` - Public hierarchy read
- `GET /subjects/{id}/modules` - Public hierarchy read

---

## Authorization (RBAC)

Role-Based Access Control (RBAC) is implemented through Firebase Custom Claims and Firestore user records.

### User Roles

| Role | Description | Access Level |
|------|-------------|--------------|
| `admin` | Full system access | All departments, all subjects, all modules |
| `staff` | Staff member | Assigned subjects only |
| `user` | Regular user | Read-only access to published content |

### Role Assignment

Roles are assigned via **Firebase Custom Claims** (set by admin) and stored in Firestore.

### Role Checking Dependencies

```python
from api.auth import get_current_user, require_admin, require_staff

@app.get("/admin-only")
async def admin_endpoint(user = Depends(require_admin)):
    ...

@app.get("/staff-only")
async def staff_endpoint(user = Depends(require_staff)):
    ...
```

### Access Control Functions

| Function | Description |
|----------|-------------|
| `has_subject_access(user, subject_id)` | Check if user can access a subject |
| `has_department_access(user, department_id)` | Check if user can access a department |
| `can_modify_note(user, note_data)` | Check if user can modify a note |
| `can_create_note_in_subject(user, subject_id)` | Check if user can create notes in a subject |

### Firestore Custom Claims Setup

```python
from firebase_admin import auth

# Set custom claims
auth.set_custom_userClaims(uid, {
    "role": "admin",
    "departmentId": "dept-123"
})
```

---

## App Check Security

Firebase App Check helps protect your API from abuse by verifying that requests come from your legitimate app.

### App Check Enforcement

- **ReCaptcha Enterprise** is configured for web clients
- App Check tokens are verified on all protected endpoints
- Requests without valid App Check tokens are rejected

### Configuration

```python
# Frontend - Initialize App Check
import { initializeAppCheck, ReCaptchaEnterpriseProvider } fromfirebase/app-check'

const app = initializeAppCheck(app, {
  provider: new ReCaptchaEnterpriseProvider('SITE_KEY'),
  isTokenAutoRefreshEnabled: true
});
```

### Verification

App Check is verified in the API middleware for all requests to protected endpoints.

---

## API Security

### CORS Configuration

Cross-Origin Resource Sharing (CORS) is configured to allow only specific origins.

**Environment Variables:**
```
ALLOWED_ORIGINS=http://localhost:5173,https://yourdomain.com
```

**Default Origins (Development):**
- `http://localhost:5173`
- `http://localhost:5174`
- `http://localhost:3000`
- `http://127.0.0.1:5173`
- `http://127.0.0.1:5174`
- `http://127.0.0.1:3000`

**Production:** Only your production domain(s) should be configured.

### Rate Limiting

Rate limiting is implemented using `slowapi` to prevent abuse.

| Endpoint Type | Rate Limit |
|--------------|------------|
| Auth endpoints | 5 requests/minute |
| General API | 100 requests/minute |

**Exceeded Limit Response:**
```json
{
  "detail": "Rate limit exceeded. Try again in 30 seconds."
}
```

### Security Headers

All API responses include the following security headers:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevents MIME type sniffing |
| `X-Frame-Options` | `DENY` | Prevents clickjacking |
| `X-XSS-Protection` | `1; mode=block` | Legacy XSS protection |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Enforces HTTPS (prod only) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Controls referrer info |
| `Content-Security-Policy` | (customized per env) | Restricts resource loading |

### Environment Mode

The application detects production mode via the `ENVIRONMENT` variable:

```bash
ENVIRONMENT=production  # Enables enhanced security features
ENVIRONMENT=development # Default, for local development
```

---

## Database Security

### Firestore Security Rules

Firestore Security Rules enforce data access control at the database level.

**Key Rules:**

```javascript
// Users can only read/write their own data
match /users/{userId} {
  allow read, write: if request.auth != null && request.auth.uid == userId;
}

// Staff can read departments
match /departments/{departmentId} {
  allow read: if request.auth != null;
  allow write: if request.auth != null && request.auth.token.role == 'admin';
}

// Staff can only access assigned subjects
match /subjects/{subjectId} {
  allow read: if request.auth != null && (
    request.auth.token.role == 'admin' ||
    request.auth.token.role == 'staff' &&
    resource.data.staffIds.hasAny([request.auth.uid])
  );
}
```

### Security Rules Deployment

```bash
firebase deploy --only firestore:rules
```

---

## Secrets Management

### Environment Variables

All secrets are managed via environment variables in `.env` file.

**Required Variables:**

| Variable | Description | Required |
|----------|-------------|----------|
| `FIREBASE_CREDENTIALS` | Path to Firebase service account | Yes |
| `VERTEX_PROJECT` | Google Cloud project ID | Yes |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to GCP service account | Yes |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | No |
| `ENVIRONMENT` | `development` or `production` | No |
| `REDIS_URL` | Redis connection string | No |

### Service Account Keys

Service account keys are **never committed** to the repository.

**Protected by .gitignore:**
```
serviceAccountKey.json
serviceAccountKey*.json
*adminsdk*.json
.env
*.key
*.pem
*.crt
```

### Credential Storage

- **Development:** Local `.env` file (not committed)
- **Production:** Environment variables or secret manager
- **Never:** Commit credentials to version control

---

## Deployment Checklist

Before deploying to production, complete this checklist:

### Pre-Deployment

- [ ] **Firebase Console:**
  - [ ] API keys restricted to production domains
  - [ ] Firebase Security Rules deployed and tested
  - [ ] App Check enabled and enforced
  - [ ] Authentication providers configured

- [ ] **Google Cloud Console:**
  - [ ] API restrictions enabled on all keys
  - [ ] Application restrictions configured
  - [ ] IAM permissions reviewed

- [ ] **Application Configuration:**
  - [ ] `ENVIRONMENT=production` set
  - [ ] `ALLOWED_ORIGINS` configured with production domains only
  - [ ] Service account keys not in repository
  - [ ] `.env` file secured

- [ ] **Security Headers Verified:**
  - [ ] HSTS enabled
  - [ ] CSP configured
  - [ ] X-Frame-Options: DENY
  - [ ] X-Content-Type-Options: nosniff

### Post-Deployment Verification

- [ ] Rate limiting tested (verify 429 responses)
- [ ] Security headers present in responses
- [ ] Unauthorized access blocked
- [ ] Health check endpoint responding
- [ ] App Check verification working

---

## Incident Response

### Security Incident Contacts

| Role | Contact |
|------|---------|
| Security Lead | [Your Name/Email] |
| Firebase Support | https://support.firebase.google.com/ |
| Google Cloud Security | https://cloud.google.com/support/ |

### Incident Severity Levels

| Level | Description | Response Time |
|-------|-------------|---------------|
| **Critical** | Data breach, unauthorized access | Immediate |
| **High** | Exploitation attempt detected | < 1 hour |
| **Medium** | Policy violation, suspicious activity | < 4 hours |
| **Low** | Minor issue, informational | < 24 hours |

### Immediate Actions

1. **Assess the incident** - Determine scope and severity
2. **Contain** - Block suspicious IPs, revoke compromised credentials
3. **Notify** - Contact security team and stakeholders
4. **Document** - Record all actions taken
5. **Remediate** - Fix vulnerabilities
6. **Review** - Post-incident analysis

### Credential Compromise Response

If credentials are suspected compromised:

```bash
# 1. Rotate Firebase service account keys in GCP Console
# 2. Revoke and reissue Firebase Custom Claims
# 3. Force token refresh for affected users
# 4. Review Firestore audit logs
# 5. Check Cloud Audit Logs for unauthorized access
```

---

## Security Update Procedures

### Dependency Updates

1. **Regular Audits:** Run weekly dependency audits
   ```bash
   npm audit
   pip-audit
   ```

2. **Critical Updates:** Apply within 24 hours of release

3. **Testing:** Always test updates in staging before production

### Security Rule Updates

1. Create branch for rule changes
2. Test rules using Firestore emulator
3. Review with security team
4. Deploy to staging environment
5. Run integration tests
6. Deploy to production
7. Monitor for breaking changes

### Access Control Changes

1. Document the change request
2. Review with team lead
3. Implement custom claims changes
4. Test in development
5. Deploy to staging
6. Validate with unit tests
7. Deploy to production
8. Update this document

---

## References

- [Firebase Security Rules](https://firebase.google.com/docs/rules)
- [Firebase App Check](https://firebase.google.com/docs/app-check)
- [OWASP Secure Headers Project](https://owasp.org/www-project-secure-headers/)
- [Google Cloud Security](https://cloud.google.com/security)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

---

## Document Maintenance

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-02-05 | Claude | Initial security documentation |
