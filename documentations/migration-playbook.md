# Firestore Migration Playbook

## Overview

This document describes the data migration process from `mock_db.json`
to Firestore and provides rollback procedures.

## Pre-Migration Checklist

- [ ] Cloud Storage bucket created for backups
- [ ] `serviceAccountKey-auth.json` downloaded and secure
- [ ] `mock_db.json` is up to date
- [ ] Firebase project configured (Phase 1 complete)
- [ ] Security rules deployed (Phase 2 complete)

## Migration Process

### 1. Create Backup

```bash
python tools/backup_firestore.py --bucket gs://[your-bucket]
```

Save the backup path output.

Example from 2026-02-05:
`gs://aura-auth-proj-firestore-backups/firestore-backup-20260205_070340`

### 2. Dry Run

```bash
python tools/seed_firestore.py --dry-run --credentials serviceAccountKey-auth.json
```

Review output for errors or unexpected behavior.

### 3. Execute Migration

```bash
python tools/seed_firestore.py --credentials serviceAccountKey-auth.json
```

Monitor output for errors.

### 4. Verify (Automated)

```bash
python tools/verify_migration.py
```

All checks should pass.

### 5. Manual Console Verification

- Open Firebase Console → Firestore Database
- Verify document counts
- Spot-check documents for correct data
- Check `_migrations` collection has success record

## Rollback Procedure

If migration fails or data is corrupted:

### Option 1: Restore from Backup (Recommended)

```bash
gcloud firestore import gs://[your-bucket]/firestore-backup-[timestamp]
```

Note: This will OVERWRITE current Firestore data with backup data.

### Option 2: Partial Re-migration

If only specific collections have issues:

```bash
python tools/seed_firestore.py --collection users \
    --credentials serviceAccountKey-auth.json
```

### Option 3: Reset and Re-run

**WARNING: This deletes ALL data**

```bash
python tools/seed_firestore.py --reset \
    --credentials serviceAccountKey-auth.json
```

You must confirm by typing "yes".

## Troubleshooting

### Issue: "Service account key not found"

**Solution**: Download `serviceAccountKey-auth.json` from Firebase
Console → Project Settings → Service Accounts → Generate new private key.

### Issue: "Permission denied"

**Solution**: Check IAM roles for service account. Must have:
- Firebase Admin SDK Administrator Service Agent
- Cloud Datastore User

### Issue: Documents not appearing

**Possible causes**:
- Dry-run mode is still on
- Wrong Firebase project selected
- Security rules blocking writes

**Solution**: Check Firebase Console for errors, verify credentials.

### Issue: "Rate limit exceeded"

**Solution**: Migration uses BulkWriter with automatic throttling.
If you see this error, wait a few minutes and re-run (it's idempotent).

## Schema Versioning

Documents have `_v` field indicating schema version.

Current version: 1

Future migrations can check `_v` to determine if update is needed.

## Migration History

Migrations are tracked in the `_migrations` collection.

Each document contains:
- `started_at`: Migration start timestamp
- `completed_at`: Migration completion timestamp
- `status`: `completed`, `failed`, or `in_progress`
- `stats`: Count of created/updated/skipped/errored documents
- `schema_version`: Schema version used

## Re-running Migrations

The migration script is **idempotent** and can be safely re-run.

On re-run:
- Documents with `_v` >= current version are skipped
- Documents with `_v` < current version are updated
- New documents are created
- Existing documents with same `_v` are skipped

## Post-Migration Steps

After successful migration:

1. Update backend to verify real tokens (Phase 4)
2. Update frontend to use real Firebase (Phase 5)
3. Test authentication flow end-to-end
4. Archive or delete `mock_db.json` (optional)
