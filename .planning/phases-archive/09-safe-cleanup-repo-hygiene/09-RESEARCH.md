# Phase 09 Research: Safe Cleanup & Repo Hygiene

**Phase:** 09 — Safe Cleanup & Repo Hygiene  
**Researched:** 2026-04-06  
**Discovery level:** 2 — repo-specific evidence review for hidden-consumer cleanup risk  
**Confidence:** High for tracked-secret and generated-artifact cleanup; medium for broader dead-code deletion outside the audited candidates

## What this phase needs to solve

Phase 09 is the final brownfield cleanup pass after verification, shared seams, and runtime hotspots were stabilized. The safe path is to remove only high-confidence leftovers already evidenced by the repo state, and to quarantine or document anything with possible hidden consumers.

## Evidence gathered

### High-confidence secret-like residue

These files are currently tracked and contain real private key material:

- `serviceAccountKey-auth.json`
- `serviceAccountKey-old.json`
- `config.json`

Evidence:

- `serviceAccountKey-auth.json` contains `private_key_id`, `private_key`, and `client_email`
- `serviceAccountKey-old.json` contains `private_key_id`, `private_key`, and `client_email`
- `config.json` contains `private_key_id`, `private_key`, and `client_email`

This directly matches the milestone audit note in `.planning/PROJECT.md` about a secret-like legacy credential file, but the repo currently has three tracked secret-bearing JSON files.

### High-confidence generated artifacts committed to git

Tracked generated output currently includes:

- `frontend/coverage/**`
- `firestore-debug.log`
- `frontend/firestore-debug.log`
- `e2e/playwright-report/**`
- `e2e/test-results/.last-run.json`

These are safe cleanup targets because they are deterministic outputs, not source-of-truth inputs.

### High-confidence stale duplicate test stack

Phase 06 already established `frontend/e2e/` as the canonical E2E stack and deprecated root `e2e/`:

- `AGENTS.md` says root `e2e/` is deprecated
- `e2e/DEPRECATED.md` says the root stack can be deleted once consumers are confirmed absent
- `frontend/package.json` contains the active Playwright commands
- root `e2e/` still contains duplicate implementation files:
  - `e2e/package.json`
  - `e2e/package-lock.json`
  - `e2e/playwright.config.ts`
  - `e2e/run-tests.sh`
  - `e2e/tests/*.spec.ts`
  - `e2e/page-objects/*.ts`
  - `e2e/README.md`
  - `e2e/data/hierarchy.json`

Search results show no active code paths referencing `e2e/data/hierarchy.json`, and repo references to the root E2E stack are now mostly documentation and planning-map drift.

### Documentation drift that would make cleanup incomplete

Several docs still describe the deprecated stack or stale credential practices:

- `README.md` still instructs users to run E2E from `e2e/`
- `frontend/CLAUDE.md` still describes root `e2e/` as active
- `.planning/codebase/STRUCTURE.md`, `.planning/codebase/TESTING.md`, `.planning/codebase/ARCHITECTURE.md`, and `.planning/codebase/STACK.md` still model root `e2e/` as an active testing surface
- `documentations/migration-playbook.md` and `SECURITY.md` still need explicit post-leak credential rotation/remediation guidance

## Research-backed approach

### 1. Treat committed credentials as an immediate remediation stream

The safest sequence is:

1. Remove tracked secret-bearing files from git
2. Add a repo guardrail so similar secrets fail future review
3. Require human rotation/reissue of the exposed Google Cloud / Firebase service accounts

### 2. Remove generated artifacts outright

Coverage reports, Playwright HTML/video outputs, debug logs, and test-result caches are high-confidence deletes. They should be removed and blocked by `.gitignore` patterns that cover both root and nested tool outputs.

### 3. Delete the deprecated root E2E implementation but keep a tombstone

Because Phase 06 already migrated the valuable tests and created `e2e/DEPRECATED.md`, the root stack no longer needs executable code. The safest brownfield compromise is:

- delete the duplicate implementation files
- keep `e2e/DEPRECATED.md` as a tombstone and rationale file
- update docs/planning maps so only `frontend/e2e/` remains canonical

### 4. Do not overreach into uncertain “legacy compatibility” placeholders

Files such as `services/embeddings.py`, `services/vertex_ai_client.py`, and other compatibility shims contain placeholder/legacy wording, but current evidence is not strong enough to delete them safely in this phase. They should remain out of scope unless execution discovers direct proof of non-use.

## External guidance used

### Gitleaks

Official CLI guidance supports repository scans, JSON/SARIF reports, custom config, and CI failure on findings. Relevant documented commands include:

- `gitleaks git --verbose`
- `gitleaks git --report-path findings.json --report-format json`
- `gitleaks dir --redact=50 --verbose`

This is a good fit for Phase 09 because the repo already contains committed private keys.

### Knip

Knip is appropriate for report-first dead-code checks in TypeScript projects:

- `npx knip`
- `knip --production`
- config via `knip.json`

For this phase, Knip is useful as evidence if the executor wants extra confirmation before deleting stray TS/JS files, but the audited cleanup candidates above are already strong enough to plan without making Knip adoption a prerequisite.

## Recommended verification strategy

Use proof that is fast and local:

- `git ls-files` to prove tracked secrets/artifacts are gone
- `npm run build` from `frontend/` to prove E2E cleanup did not break active frontend tooling references
- targeted `rg` / `git grep` checks to prove docs now point to `frontend/e2e/` and no longer advertise root `e2e/` as active
- if Gitleaks is available during execution, run a repo scan after secret-file removal; otherwise verify the workflow/config exists so CI can enforce it

## Cleanup candidate inventory

### Safe-remove now

- `serviceAccountKey-auth.json`
- `serviceAccountKey-old.json`
- `config.json`
- `frontend/coverage/`
- `firestore-debug.log`
- `frontend/firestore-debug.log`
- `e2e/playwright-report/`
- `e2e/test-results/.last-run.json`
- root `e2e/` implementation files other than `e2e/DEPRECATED.md`

### Keep but document

- `e2e/DEPRECATED.md` — keep as tombstone after implementation-file deletion

### Defer

- Compatibility shims and placeholder-marked runtime files without explicit non-use evidence
- Any broad API/router deletions not already covered by prior phases

## Planning implications

This phase should be split into three focused execute plans:

1. Secret-like residue removal + secret-scan guardrail + credential-rotation checkpoint
2. Generated artifact purge + deprecated root E2E implementation removal + ignore hardening
3. Documentation and planning-map cleanup so the repo’s written guidance matches the cleaned state

## Sources

- Repo evidence: `.planning/PROJECT.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/codebase/CONCERNS.md`, `.planning/codebase/STRUCTURE.md`, `.planning/codebase/TESTING.md`
- Prior phase summaries: `06-05-SUMMARY.md`, `07-03-SUMMARY.md`, `08-02-SUMMARY.md`
- Existing milestone research: `.planning/research/SUMMARY.md`, `.planning/research/STACK.md`, `.planning/research/ARCHITECTURE.md`, `.planning/research/FEATURES.md`
- Context7: `/gitleaks/gitleaks`, `/webpro-nl/knip`
