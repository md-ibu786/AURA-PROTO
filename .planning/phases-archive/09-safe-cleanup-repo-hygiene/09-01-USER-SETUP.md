---
status: complete
phase: 09
plan: 01
service: google-cloud
started: 2026-04-06
completed: 2026-04-06
---

## User Setup: Google Cloud Service Account Rotation

**Service:** Google Cloud  
**Status:** ✓ Complete

### Why
Exposed service-account keys must be rotated or disabled after removal from git.

### Environment Variables Required

| Variable | Source |
|----------|--------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Local untracked credential file path after key rotation/reissue |
| `FIREBASE_CREDENTIALS` | Local untracked Firebase service account path if tooling still uses it |

### Dashboard Configuration

**Task:** Rotate or disable the exposed service accounts represented by the removed JSON files and create replacement local-only credentials if still needed.

**Location:** Google Cloud Console → IAM & Admin → Service Accounts

### Local Development Notes

- New credentials should be stored outside git using the existing `.gitignore` patterns (`serviceAccountKey*.json`)
- Do NOT commit new JSON keys back into the repository
- The gitleaks workflow will fail if any new secrets are committed

### Verification

Run `git log --oneline -3` to confirm recent commits, and ensure any local credentials are properly ignored.
