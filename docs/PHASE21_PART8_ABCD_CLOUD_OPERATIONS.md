# Phase 21 Part 8A-D: Cloud Operations

## Part 8A — Cloud Sync Status UI

The Cloud Sync page now displays:

- configured / authenticated / storage-ready state
- local prediction count
- cloud-eligible prediction count
- offline queue count
- last sync time
- last successful sync time
- measured round-trip latency

Status is stored locally only and never includes credentials.

## Part 8B — Offline Queue

Ark Terminal uses the existing `OfflineSyncQueue` as the single source of truth.

Allowed collections:

- predictions
- prediction_outcomes
- learning_reports
- candidate_models
- model_versions
- forward_test_results

The queue:

- deduplicates by collection and record ID
- retries on demand and on reconnect
- rejects sensitive fields
- never stores real-account data
- never performs broker writes

## Part 8C — Learning Dashboard

A dedicated Learning Dashboard displays:

- Production model metrics
- Candidate count
- human-review queue
- Forward Test count
- learning-report count
- offline queue count
- last cloud sync
- AI health indicators
- Champion vs Candidate comparison
- learning / validation / approval timeline

The dashboard is read-only. It cannot promote a Candidate or activate a Production model.

## Part 8D — Safe JSON Backup

Safe backup export/import includes only:

- predictions
- learning reports
- Candidates
- Forward Test results
- model-version audit records
- offline queue records

The backup rejects:

- API keys
- access or refresh tokens
- passwords and passphrases
- cookies
- broker credentials
- account numbers
- private keys

Import supports merge and replace modes. Merge deduplicates records by ID and queue items by dedupe key.

## Safety invariants

```text
realAccountIncluded: false
brokerCredentialsIncluded: false
apiKeysIncluded: false
cookiesIncluded: false
ordersIncluded: false
automaticPromotionAllowed: false
productionUpdateAllowed: false
brokerWriteAllowed: false
liveTradingAllowed: false
```

## Validation

GitHub Actions must pass:

- Prediction tests
- Discovery tests
- RSS Bridge tests
- Cloud status persistence tests
- Offline queue retry and dedupe tests
- sensitive-field rejection tests
- safe backup merge tests

No new `/api` Function entrypoints are added.
