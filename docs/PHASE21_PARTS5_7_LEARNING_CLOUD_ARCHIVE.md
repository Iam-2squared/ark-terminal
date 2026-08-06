# Phase21 Parts5-7 Learning Cloud Archive

## Scope

This bundle extends the authenticated Phase21 cloud foundation to learning artifacts that must survive browser and device changes:

- Candidate model state
- Forward validation results
- Model-version approval and rollback audit records

The cloud copy is an audit archive. It is not an executable model registry.

## Part5: Candidate archive

Candidate state changes are stored in `candidate_models` only when all safety requirements hold:

- Human approval remains required.
- Automatic promotion is disabled.
- Runtime activation is disabled.
- Production update is disabled.
- Broker writes and live trading are disabled.

Unsafe Candidate payloads are rejected before the network request and again by the server-side sensitive-field and collection allowlist boundary.

## Part6: Forward validation archive

`recordCandidateForwardValidation` emits the complete deterministic validation result after the local orchestrator records the reduced metrics.

The cloud record includes:

- Candidate and Champion versions
- Out-of-sample and Paper-only context
- Same-symbol/session and future-leak checks
- Paired-sample diagnostics
- Champion and Challenger summaries
- Evaluation result and blockers

The record is stored in `forward_test_results`. A result marked ready for human review still cannot promote or activate a model.

## Part7: model-version audit and read-only restore

Human approval and rollback actions emit model-version audit events. These records are stored in `model_versions` with the human actor and audit timestamp.

At browser startup, Ark Terminal restores all three collections as a read-only archive and emits `ark:learning-cloud-archive-restored`.

Restore invariants:

- `readOnly === true`
- `appliedToRuntime === false`
- `automaticPromotionAllowed === false`
- `productionUpdateAllowed === false`
- `brokerWriteAllowed === false`

If any restored archive claims runtime application or an execution permission, the entire learning archive restore is rejected.

## Runtime separation

The restored archive is held by `LearningCloudAutoSyncController` for audit and future dashboard use. It is not written into:

- Production model configuration
- Continuous Learning orchestrator state
- Prediction scoring weights
- Broker adapters
- Paper or live order execution

Human approval inside the local orchestrator remains a local state transition only. This bundle records that transition but does not activate a deployment or brokerage write path.

## Events

The controller listens for:

- `ark:candidate-state-changed`
- `ark:forward-validation-recorded`
- `ark:model-version-audit`

It emits:

- `ark:learning-cloud-archive-restored`
- `ark:learning-cloud-candidate-saved`
- `ark:learning-cloud-forward-saved`
- `ark:learning-cloud-model-version-saved`
- `ark:learning-cloud-sync-error`

## Failure behavior

Cloud status, restore, or write failures are safe no-ops for the local learning workflow. A cloud failure never changes Candidate status, model weights, Production state, or broker permissions.

## Required Vercel configuration

The existing Phase21 variables remain required:

- `ARK_CLOUD_SYNC_SECRET`
- `ARK_KV_REST_API_URL`
- `ARK_KV_REST_API_TOKEN`

Code and CI success do not prove that the production KV contains real records. That requires an authenticated Cloud Sync session and an explicit browser-side Candidate or validation event after deployment.
