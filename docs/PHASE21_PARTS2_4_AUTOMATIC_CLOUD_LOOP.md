# Phase21 Parts2-4 Automatic Cloud Loop

## Scope

This bundle connects the Phase21 Part1 cloud persistence foundation to the live Prediction Lab workflow.

## Part2: automatic prediction mirroring

- A live prediction is saved locally first.
- Browser runtime then attempts to mirror the prediction to the authenticated cloud session.
- Cloud failure never rolls back or blocks localStorage / IndexedDB persistence.
- Walk-forward and backtest archive rows remain excluded by the cloud repository policy.

## Part3: startup restore and convergence

- The automatic cloud controller checks `/api/cloud-session`.
- Restore runs only when the cloud secret, storage adapter, and signed session are all ready.
- Local and cloud predictions are merged by record ID and timestamp.
- Resolved cloud outcomes are applied before the merged state is written locally.
- The merged state is mirrored back to the cloud so devices converge.
- `ark:cloud-history-restored` triggers a forced outcome refresh.

## Part4: outcome and learning synchronization

- `ark:prediction-outcomes-updated` mirrors only IDs that moved from pending to resolved.
- Resolved prediction data is stored in `predictions` and its deterministic result in `prediction_outcomes`.
- `ark:learning-feedback-ready` stores advisory learning reports in `learning_reports`.
- Learning reports are accepted only when `executionAllowed === false`.
- No Candidate promotion, Production update, broker write, or live order path is introduced.

## Consolidated API compatibility

The Vercel Hobby function-budget hotfix keeps the public endpoints `/api/cloud-session` and `/api/cloud-state` available through rewrites while the server implementation is consolidated behind `/api/cloud`. Existing browser clients therefore remain compatible without adding serverless functions.

## Safety invariants

- Local persistence remains the source of last resort.
- Cloud operations are best effort and fail closed.
- Real-account data remains outside cloud synchronization.
- Broker credentials, API keys, tokens, passwords, and account numbers remain rejected by the Part1 API boundary.
- Automatic cloud sync starts only in browser runtime.
- Node tests never initiate live cloud network calls.

## Required Vercel environment variables

- `ARK_CLOUD_SYNC_SECRET`
- `ARK_KV_REST_API_URL`
- `ARK_KV_REST_API_TOKEN`

Without these variables, all automatic cloud operations become safe no-ops and Ark Terminal continues using local storage.
