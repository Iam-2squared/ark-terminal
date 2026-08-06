# Phase 21 Part 8A-D Operations

## Scope

Phase 21 Part 8 adds an offline-capable Operations surface without adding any new Vercel API Function entrypoint.

### Part 8A — Cloud Sync Status UI

- Cloud configuration, storage, authentication, last check, and queue status
- Healthy / Attention / Local Only health states
- Direct links to Cloud Sync and AI Performance

### Part 8B — Offline Queue

- Local-first queue for:
  - predictions
  - prediction outcomes
  - learning reports
  - candidate models
  - model versions
  - forward test results
- Deduplicate by collection and record ID
- Keep failed items with attempt count and error code
- Remove only after confirmed cloud save
- Flush on manual action and browser online recovery
- Reject credentials, secrets, API keys, account numbers, and sensitive fields

### Part 8C — Learning Dashboard

- Prediction count
- Resolved result count
- Candidate count and review state
- Forward Test count
- Model audit count
- Read-only Candidate and Forward / model timeline
- Restored cloud archive always remains:
  - `readOnly: true`
  - `appliedToRuntime: false`
  - `automaticPromotionAllowed: false`
  - `productionUpdateAllowed: false`
  - `brokerWriteAllowed: false`

### Part 8D — Safe Backup / Restore

- Export only safe prediction and learning collections
- Reject credentials, tokens, account numbers, real-account values, and unsupported backups
- Merge predictions by identity and freshness
- Restore Candidate / Forward / model audit data as read-only local archive
- Never activate Production weights or broker execution

## Safety Boundary

The following remain forbidden:

- broker writes
- live order creation or cancellation
- real-account cloud upload
- API key, token, password, cookie, or account-number persistence
- automatic Candidate promotion
- runtime activation of restored models

## Validation

GitHub Actions covers:

- queue deduplication
- failed item retention
- successful item deletion
- sensitive-field rejection
- queued cloud fallback
- safe backup validation
- freshest-record merge
- automatic prediction queueing while cloud is unavailable
- Operations page structure
- Vercel API Function budget remains 12 or fewer
