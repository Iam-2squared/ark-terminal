# Capacity v2.1 Development NO-GO diagnosis

Research-only evidence. Source run 34189128681; diagnostic run 34209072157. Frozen trainer SHA-256: b3bf9db5c33d282bcc9aabece765251f22923fe9f0bcf70afb028c182cef532b.

The diagnostic reused all six verified Development checkpoints: 89 sessions and 1,780 decisions. Only the existing OOF computation was repeated (880 decisions); no market data was downloaded or reconstructed. Validation and OOS remain unreleased. No model was promoted, no gate was changed, and main/Lane Y were not modified.

## Findings

All 64 unique precommitted threshold tuples were evaluated; none was eligible. Failure counts overlap:

| Gate | Failed tuples |
| --- | ---: |
| Global Utility | 44 |
| Relative candidate increase | 16 |
| Absolute candidate increase | 20 |
| Adjacent count stability | 17 |
| Utility in every held-out fold | 48 |

44 tuples satisfied both candidate-count constraints. All 44 failed global Utility. The best global Utility among those tuples also had their best worst-fold Utility:

- Baseline count: 6.1625; challenger count: 8.33522727 (+35.2572%, +2.17272727).
- Baseline Utility: 244.55035503 bps; challenger: 233.72092414 bps; difference: -10.82943089 bps.
- Fold differences: -6.22530907, -14.45976362, -11.87277636 bps.
- Global jump rate: 0.13083049 (passes 0.15).
- Both Utility gates require at least -10 bps. Therefore the setting remains ineligible.

These are Development selection diagnostics, not fresh Validation or OOS performance, a deployed model, accuracy, or realized trading profit. The result excludes only the 64 declared tuples; it does not prove every possible capacity policy infeasible. All layer MAEs and candidate metrics are retained in the accompanying JSON.

## Next investigation, before any new evaluation release

Hypothesis (not an established cause): positive absolute marginal opportunity is insufficient to preserve average prefix Utility when lower-ranked symbols are added. Audit whether the target should express incremental prefix Utility relative to the retained baseline, and examine any mismatch between frozen-selected Utility and prefix-count Utility. Use existing Development checkpoints only; keep v2.1 NO-GO intact.

Separately audit fold causality: chooseLambda pools errors from all three held-out folds, then uses that selected lambda for earlier-fold predictions. Each coefficient fit uses earlier sessions, but hyperparameter selection uses later Development outcomes. This is within Development, not evidence of Validation/OOS access; it limits a strict forward-only interpretation and must be resolved explicitly in any next-version contract.

Do not relax the old gates or open sealed data during diagnosis. Any changed targets, mapping, lambda protocol, or model must receive a separately versioned precommit and fresh freeze. No v2.2 training or evaluation has been launched in this change.
