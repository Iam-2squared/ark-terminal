# Phase57 LONG-only CURRENT Entry Filter Recovery Audit

**Verdict: D.MULTIPLE**

This is a descriptive pre-development audit on the same already-opened 76 Development sessions. No Selector or CURRENT Entry decision, model, feature, coefficient, threshold, state rule, Validation/OOS, EXIT, allocation, or order path was changed.

## Funnel

| Status | Count | Rate |
|---|---:|---:|
| PASS | 162 | 4.26% |
| WAIT | 956 | 25.16% |
| REJECT | 753 | 19.82% |
| BLOCKED | 1,929 | 50.76% |
| UNAVAILABLE | 0 | 0.00% |

## BLOCKED root causes

| Canonical reason | Count | All events | +1 | +2 | +3 | +5 | MFE mean | true MAE mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| RECENT_GRID_GAP_OR_STALE | 1,015 | 26.71% | 75.27% | 61.87% | 46.80% | 19.31% | 3.338% | -0.849% |
| INSUFFICIENT_PREFIX | 555 | 14.61% | 79.82% | 65.41% | 49.01% | 28.11% | 4.258% | -2.652% |
| SESSION_OPEN_MISSING | 359 | 9.45% | 77.72% | 57.66% | 43.18% | 26.18% | 3.904% | -3.583% |

## Lost opportunity attribution

| Source | +1 | +2 | +3 | +5 |
|---|---:|---:|---:|---:|
| BLOCKED:INSUFFICIENT_PREFIX | 429 | 350 | 260 | 147 |
| BLOCKED:RECENT_GRID_GAP_OR_STALE | 761 | 625 | 473 | 194 |
| BLOCKED:SESSION_OPEN_MISSING | 279 | 207 | 155 | 94 |
| REJECT:TERMINAL_EXPIRED_UNTIL_NEXT_SESSION | 560 | 470 | 385 | 210 |
| WAIT:LONG_NOT_ABOVE_FROZEN_THRESHOLD | 700 | 531 | 399 | 212 |

## Opportunity throughput

| Measure | Total | Per session mean | Per session median |
|---|---:|---:|---:|
| firstEntryCandidates | 2,743 | 36.092 | 36.000 |
| pass | 96 | 1.263 | 1.000 |
| preserved1 | 73 | 0.961 | 1.000 |
| preserved2 | 59 | 0.776 | 1.000 |
| preserved3 | 50 | 0.658 | 1.000 |
| preserved5 | 35 | 0.461 | 0.000 |

## Mismatch components

- MODEL_FILTER_TOO_STRICT: `True` — first-entry coverage=3.50%; WAIT-lost +3 share=22.28%
- FEATURE_AVAILABILITY_TOO_STRICT: `True` — BLOCKED rate=50.76%; BLOCKED +3 precision=46.76%
- STATE_FILTER_TOO_STRICT: `True` — REJECT rate=19.82%; REJECT +3 precision=51.13%

## MSH-Entry LONG v1 design requirements (requirements only)

### MUST_PRESERVE

- LONG-only JPX cash-equity direction with SHORT, margin and leverage absent.
- Frozen Selector Decision Price semantics, PIT feature availability and no future bars.
- Fast decisions: the existing Entry median first-PASS latency is 0 minutes and must not regress.
- The observed enrichment signal across +1/+2/+3/+5, not +5 alone.
- State safety, single entry per symbol-session, cost awareness and all execution locks.

### MUST_IMPROVE

- First-entry coverage above the current 3.50% while measuring precision, preservation and throughput together.
- Evidence-backed tolerance for missing session-open or non-consecutive 5m history; do not assume Selector freshness implies Entry feature availability.
- Opportunity preservation at +1, +2, +3 and +5, with +3 primary but not exclusive.
- Low- and mid-liquidity feature availability without segment or liquidity-specific thresholds.
- Explicit accounting for WAIT-to-expiry and terminal state loss.

### MUST_NOT

- Optimize only +5 precision or call the descriptive recoverable pool achievable performance.
- Reuse SHORT scores, targets, coefficients or fallback behavior.
- Require unavailable history without demonstrated value, impute missing bars, or use future information.
- Tune thresholds, select features, redesign WAIT, or fit architecture from this audit.
- Open Validation/OOS or change Selector, EXIT, Capital Allocation, portfolio or order paths.

STOP: no MSH-Entry LONG v1 architecture, target, feature, model, coefficient, threshold, or WAIT rule was created.
