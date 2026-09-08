# Capacity v2.2 Development-only final result

## Final status

**CAPACITY_V2_2_DEVELOPMENT_NO_GO**. No model freeze was created. Validation, OOS, and additional sealed reserve remain unreleased. All nine safety flags are false. Main, Lane Y, Frozen Hybrid, Entry, EXIT, and Capital Allocation were not modified.

- Source run: 34189128681, head f3543b5a604d25442c28fc3cb475e89274400bd5.
- Pre-training semantics audit run: 34214657195.
- Precommit commit: 7107e89e6cbb74967598540d77c2d10e9d10213d.
- Precommit SHA-256: 6750071042aa595c1f143e02a6f6e3dc83d4e220c42d45480106a14b1c985323.
- Development execution run: 34215429201, head bdbbdabbaede9b83660abc737e4c5b90e45a1496.
- Trainer SHA-256: bf887d18aa343d0f075a5c4b5ce4f006a7e1a893f0cf7d9fcb376219ff3576d3.
- Result digest (JSON core without resultDigest): 4bd6fbf95e5746a1d569f46c6479e0c29217414ecab18e11a20dd0fe7b0421ca.
- Actions artifact ID: 10051550945, ZIP SHA-256: 78c89cbc2900b0c3c20bdd42503e5e77383088b848f0fc172e582c35250c175a.
- Focused causality / metric / safety tests: 15/15 PASS locally (repo and predict cwd) and in the Development job.

The source six checkpoints (89 sessions / 1,780 decisions) were reused. No new market data was fetched or reconstructed. Nested-forward evaluation covers the final 44 Development sessions / 880 decisions; the first 45 sessions are initial training history. Utility uses 876 common-support observations. Paired coverage is 99.5455%.

## Required completion fields

| Field | Result |
|---|---|
| v2.1 preserved | Yes; original trainer, contract, diagnostic JSON/Markdown and Frozen Hybrid checked byte-for-byte |
| Target semantics audit | Complete; positive layer opportunity can dilute prefix average; direct baseline-relative target fixed |
| Prefix Utility audit | Complete; corrected Top-N substitution to cached Frozen-selected mean, with missing-label scope disclosed |
| Forward-only CV fixed | Nested expanding inner selection inside each outer past window |
| Future-fold lambda leakage removed | Yes; future outcome/feature mutation tests pass |
| Development sessions reused | 89 (1,780 decisions); 44 / 880 outer-held-out evaluation |
| New Fresh sessions consumed | 0 |
| Validation status | SEALED / UNRELEASED |
| OOS status | SEALED / UNRELEASED |
| Reserve status | No additional release |
| Baseline candidate count | 6.1625 |
| v2.2 candidate count | 5.0000 |
| Candidate increase | -1.1625 (-18.8641%) |
| Baseline Utility | 299.19572950 bps |
| v2.2 Utility | 248.28055157 bps |
| Utility difference | -50.91517793 bps |
| Worst forward-held-out difference | -61.71211870 bps |
| Jump rate | 0% |
| Prefix match | 100% rank-index prefix construction; adapter tests passed. Cached historical identity remains a source declaration, not a fresh symbol-level audit |
| Leakage | 0 detected in the new fitting/scaling/lambda pipeline; raw feed was not re-audited |
| Development Gate | FAIL: Utility, relative count, absolute count, every-block Utility |
| Final status | CAPACITY_V2_2_DEVELOPMENT_NO_GO; no Freeze |

## Forward blocks

| Block | Sessions | Baseline count | v2.2 count | Utility difference (bps) | Jump rate |
|---|---:|---:|---:|---:|---:|
| 1 | 15 | 6.8100 | 5 | -61.71211870 | 0% |
| 2 | 15 | 5.9667 | 5 | -30.82261448 | 0% |
| 3 | 14 | 5.6786 | 5 | -60.87477365 | 0% |

All four targets selected lambda=10 in every outer past window. All 880 decisions selected Top5; no larger prefix passed the fixed prediction floor. The fixed fallback does not guarantee realized Utility preservation and is NOT a keep-Frozen-selected action. No thresholds or gates were retuned after this result.

## Failure classification and uncertainty

- **Capacity mapping failure (observed):** no expansion; the candidate-count objectives fail.
- **Utility dilution (observed):** even the chosen Top5 prefix underperforms the corrected cached selected-subset baseline in all three blocks.
- **Forward-held-out failure / instability (observed):** no held-out block meets the -10 bps floor. This is performance failure, not renewed future-fold leakage.
- **Prediction failure / insufficient signal (not isolated):** paired MAEs are 111.18 / 90.48 / 85.92 / 86.82 bps for Top5/10/15/20. This alone does not establish whether a better predictor or a different allowed policy would meet the gates.
- **Target failure (not established):** the target now directly represents the selected cached metric. The data-scope limitation below remains.
- **Regime instability (not established):** these checkpoints do not provide a separately audited regime stratification; date-block variation must not be relabeled as proven regime causality.

This is one structurally redesigned, precommitted policy, not an impossibility proof for all Capacity research. It is not comparable to the old v2.1 Utility number without accounting for the corrected baseline and changed evaluation protocol.

## Important metric limitations

Utility is a +6-bar, cost-adjusted two-sided opportunity proxy, not realized or executable trading profit. The cached Frozen-selected field excludes missing labels and selected symbols outside source ranks 1..20. Per-symbol label counts, complete selected membership, and target-end timestamps are not stored. This run did not repair those limitations or claim full-selected Utility / raw-PIT parity. Only the already-cached metric was evaluated consistently.

Algorithmic forward-only predictions are not untouched research evidence: prior versions and the architecture audit already used these Development sessions. Fresh Validation/OOS were never opened in this redesign, including after the Development result.
