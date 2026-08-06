# Phase43 — Model Registry & Training Pipeline

## Scope

Phase43 adds a safe, review-only model lifecycle above the Phase42 Feature Store.

## Included

1. Model version records
   - model ID and semantic version
   - algorithm
   - Feature Set ID and feature-manifest hash
   - dataset and model-artifact checksums
   - training, validation and test windows
   - evaluation metrics
   - deterministic registry hash

2. Registry governance
   - duplicate model-key detection
   - single-Champion invariant
   - immutable registry snapshots
   - explicit fail-closed blockers

3. Training-run evaluation
   - sample-size gate
   - Profit Factor gate
   - maximum-drawdown gate
   - confidence-interval gate
   - missing-integrity metadata blockers

4. Champion/Candidate comparison
   - Profit Factor delta
   - average-return delta
   - drawdown deterioration
   - Feature Set compatibility
   - no automatic promotion

5. Rollback planning
   - target model validation
   - mandatory reason
   - review-only rollback plan
   - no automatic execution

6. Governance dashboard payload
   - Champion and Candidate inventory
   - blockers and warnings
   - training, comparison and rollback counts
   - human-review status

## Safety guarantees

All paths remain advisory and READ ONLY.

- broker writes: disabled
- live trading: disabled
- order create/transmit/cancel/modify: disabled
- Excel order writes and trigger changes: disabled
- automatic Candidate promotion: disabled
- automatic Production update: disabled
- rollback execution: disabled
- human approval: required

Phase43 does not train or deploy a production model automatically. It records, evaluates and compares model versions so a human can review them safely.
