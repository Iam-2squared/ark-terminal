# Phase57 Entry UNKNOWN Causal-Coverage Diagnostic v1 — Final Receipt

Status: `DIAGNOSTIC_COMPLETE_STOP_NO_POLICY_DECISION`

This receipt freezes the diagnostic result only. It does not create or change an Entry policy.

## Source / CI identity

- PR: #587
- Branch: `research/phase57-long-only-cash-equity`
- Diagnostic implementation HEAD: `b6dc569065777cef1056950703282d45e1b3cb1f`
- Dedicated workflow: `Phase57 Entry UNKNOWN Coverage Diagnostic v1`
- Workflow run: `35768561251` — PASS
- Job: `106884196437` — PASS
- Evidence artifact ID: `10712609654`
- Evidence artifact digest: `sha256:f6cd3e07a176f93d4f9098bd82d949119c8aca91140e88ca3ae8b640c8a32d68`
- Focused tests: 7 / 7 PASS
- Deterministic replay: PASS (`diff -qr` identical)
- Full Predict offline regression: 2,765 / 2,765 PASS
- Unexpected network attempts blocked by regression guard: 0
- Source integrity: PASS

## Frozen population

- All Opportunities: 2,155
- Initial UNKNOWN: 1,144 / 2,155 = 53.0858468677%
- Frozen causal estimator unchanged: `sign(returnPct[5])`; missing => UNKNOWN
- New provider requests: 0
- Protected Holdout / Fresh / OOS / Prospective opened: 0

## Why the initial State is UNKNOWN

| Reason | Count | Share of UNKNOWN |
|---|---:|---:|
| `NO_NEW_CLOSED_BAR_AT_ASOF` | 576 | 50.35% |
| `STRICT_CONTIGUOUS_WINDOW_UNAVAILABLE` | 568 | 49.65% |
| `INSUFFICIENT_PHASE_HISTORY_FOR_RETURN5` | 0 | 0.00% |

Additional causal availability facts:

- Previous-day data available: 1,132 / 1,144; unavailable: 12.
- New closed bar observed at decision: 568 / 1,144; not observed: 576.
- Phase-age buckets: 11–30 active min = 192; 31–60 = 234; 61+ = 718.
- UNKNOWN is distributed across all ten selector decision times rather than concentrated only near session open.

## Causal coverage after selection

The same frozen estimator was replayed at active-minute offsets without changing thresholds or State definitions.

| Offset | Cumulatively DEFINED by offset | Rate |
|---|---:|---:|
| T+1 | 40 | 3.50% |
| T+2 | 89 | 7.78% |
| T+3 | 119 | 10.40% |
| T+5 | 175 | 15.30% |
| T+10 | 241 | 21.07% |

At exact T+10 the State counts are DOWN 56 / NEUTRAL 8 / UP 45 / UNKNOWN 1,035. Therefore, some Opportunities that became DEFINED earlier reverted to UNKNOWN by T+10.

Through T+10, 903 / 1,144 remained `UNKNOWN` for the entire observed transition signature. 241 became DEFINED at least once by T+10.

Across the complete saved causal trajectory, 511 / 1,144 eventually became DEFINED and 633 remained `NOT_DEFINED_BY_LAST_CHECKPOINT`. First-defined State counts were DOWN 267, UP 185, NEUTRAL 59.

## Evaluator-only Immediate vs Entry-v1 WAIT anatomy

The UNKNOWN cohort and causal trajectories were fixed before opening the already-committed evaluator records.

| Metric | Immediate | Entry-v1 WAIT | Delta / paired result |
|---|---:|---:|---:|
| Fill | 954 / 83.39% | 851 / 74.39% | -9.00 pp |
| Pair status | — | — | BOTH 851 / BASE_ONLY 103 / NEITHER 190 |
| WAIT intent | — | — | FALLBACK 1,113 / SIGNAL 31 |
| Mean delay delta | — | — | +9.464 min; median +10 min |
| Mean price improvement | — | — | +0.00199% |
| Mean Low→Entry distance delta | — | — | -0.02312 pp |
| Mean EntryPosition delta | — | — | -0.03949 |
| Mean remaining-upside delta | — | — | +0.02457 pp |
| Mean Range-Retention delta | — | — | +3.5585 pp |
| 30m MFE delta | — | — | -0.01820 pp |
| 30m MAE delta | — | — | +0.17492 pp |
| 60m MFE delta | — | — | -0.01313 pp |
| 60m MAE delta | — | — | +0.26818 pp |

Interpretation is diagnostic only: UNKNOWN waiting is overwhelmingly fallback-driven (1,113 / 1,144), materially lowers fill and adds roughly ten minutes of delay, while mean buy-price improvement is approximately zero. It moves EntryPosition/Range Retention and MAE in the favorable direction on the paired evaluator sample, but does not establish a new Entry policy and does not justify threshold selection from this exposed evaluator anatomy.

## STOP / safety receipt

- `diagnosticOnly=true`
- `policyCreated=false`
- `policyChanged=false`
- `entryV2Started=false`
- `exitStarted=false`
- `capitalStarted=false`
- `thresholdSearch=false`
- Safety9: all false
- Frozen Selector unchanged
- State v2 unchanged
- Existing six Signals unchanged
- No main merge
- No paper/live trading

STOP here for human review. Do not automatically start Entry v2, EXIT, Capital Allocation, Fresh/OOS/Prospective evaluation, main merge, or trading.
