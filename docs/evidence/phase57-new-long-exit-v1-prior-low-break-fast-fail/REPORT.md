# NEW_LONG_EXIT_LOSS_DEFENSE_V1_FAST_FAIL_KILL

Date: 2026-09-18 JST

Structural challenger: **prior completed bar LOW breakdown** while DEFENSIVE.

Workflow run: `35302983150`

## Verdict

**NEW_LONG_EXIT_LOSS_DEFENSE_V1_FAST_FAIL_KILL**

The v1 rule was pre-frozen before replay and was not numerically tuned:

- first negative completed CLOSE -> DEFENSIVE;
- Entry reclaim -> HOLD;
- while unreclaimed, current completed CLOSE strictly below the immediately prior completed bar LOW -> EXIT signal;
- EXIT reference = next regular 5m OPEN.

## Gate result

| Gate | Result |
|---|---|
| INITIAL +3 preservation >=90% | FAIL — 89.8876% |
| INITIAL +5 preservation >=90% | PASS — 92.6829% |
| DIP +3 preservation >=90% | FAIL — 89.8551% |
| DIP +5 preservation >=90% | PASS — 92.5926% |
| 106 continued-drop >=10% mean-loss improvement | FAIL — **-18.2315%** relative improvement |
| 21 deep-drop non-worse | FAIL |
| INITIAL own60 mean non-worse | FAIL |
| DIP own60 mean non-worse | FAIL |
| Safety | PASS |

## Own60

| Cohort | Baseline mean | v1 policy mean | Signal rate |
|---|---:|---:|---:|
| INITIAL | -0.21556% | **-0.24649%** | 46.01% |
| DIP_REPRICE | -0.17896% | **-0.24732%** | 48.86% |

The stronger breakdown condition preserved +3 winners slightly better than v0, but the price-path mean became worse in both cohorts.

## 106 continued-drop identities

Fixed12:
- **-1.48489%**

v1:
- **-1.75561%**

Relative mean-loss reduction:
- **-18.2315%** (materially worse)

Signals:
- 84 / 106

## 21 deep-drop identities

Fixed12:
- **-4.00144%**

v1:
- **-4.61378%**

Relative mean-loss reduction:
- **-15.3029%**

Signals:
- 20 / 21

Unlike v0, v1 also loses the useful deep-tail improvement.

## Disposition

Kill this exact prior-bar-low-break architecture.

Retained cross-experiment lesson:

- v0 lower-CLOSE persistence was early enough to improve the deepest 21 cases, but too blunt for winners and the 106 broader cohort.
- v1 stronger range-break confirmation is more selective but **too late**; it worsens the 106 cohort, the 21 cohort and overall means.
- Therefore the next Loss Defense design should not be obtained by merely making the same breakdown confirmation stricter or looser.
- This narrows the problem toward a different information structure: recovery/reclaim trajectory and adverse duration/state history, rather than a single breakdown event.

No threshold adjustment is authorized. No v2 Loss Defense is automatically launched from this result.

Selector / NEW Entry / existing EXIT runtime / model / Fresh/OOS / 1m / Capital / Portfolio / main remain unchanged; all trading/write/promotion flags remain false.
