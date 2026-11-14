# Phase57 — EXIT Feature Availability & Causality Matrix R23 (final pre-design admission)

Date: 2026-09-25 JST  
Basis HEAD before this append-only checkpoint: `ab5e68a26e628507f765ff5dc05bbffbe574a5df`  
Controlling contracts: R18 zero-base, R20/R20.1 sequential substrate, R22 census audit  
Status: **FEATURE_CAUSALITY_ADMISSION_COMPLETE_NO_NEW_EXIT_FIT_OR_PERFORMANCE**

## Conclusion

The R20 full census and its 34 causal/producer tests establish the EXIT-NOW
closed-prefix substrate for both Frozen Entry arms. This checkpoint completes the
column/family audit and provides an executable adapter in
`scripts/phase57_exit_feature_contract_v1.py`.

- State-v3 current/history: `MODEL_ADMITTED`, only with quality/coverage/missing flags.
- Six Timing Signals current/history: `MODEL_ADMITTED` as tri-state; UNKNOWN is not FALSE.
- Entry→NOW owned-prefix features: `MODEL_ADMITTED`; incomplete paths retain explicit
  completeness and observed-only semantics.
- Pattern-v2 registry: exactly 476 columns, 446 `MODEL_ADMITTED`, 30 `BLOCKED`, and
  zero intrinsically evaluator-only columns in this registry.
- Finite model search may use only a fixed 187-column curated Pattern subset, not
  all 446 legal columns and never all 476.
- Future geometry/outcome fields outside Pattern-v2 are `EVALUATOR_ONLY`.

`MODEL_ADMITTED` means causally legal, not selected, predictive or beneficial.
No model has been fitted and no candidate return/capture has been viewed.

## Source and join audit

| Source | Pinned SHA-256 | Result |
|---|---|---|
| Pattern registry `substrate/names.json` | `efcbcaf4c4024679dc5f6e7881dcccc7c0186361b6bd469b7d3a5e6a5421e8eb` | 476 unique sorted names |
| Pattern opportunity source | `1138960e489c3403e49f502a7ff7ab1fa1e9ef205910d2d018f2bb938df813ea` | exact 2,155 Selector-origin join |
| Frozen cohort protocol | `6b02b3088dd8ea7f8ce53112bc276df442bae3ce0716b8139c92733be4de2994` | exact 2,155 IDs |
| R20 raw paths | `37853e73799544be6fd6eb955de514073dd13671692426291a9fdb6d80056c6b` | exact allowlisted closed-prefix source |

Only `decisionPrice`, `decisionTimestamp`, `savedV1Score`, and `newEligibleRank`
are projected from the Selector origin. The exact sanitized 2,155-row projection
hash is `cac2eeeda308ffdff20fe09331aec3cb7b18da311cc2c753bb78978b43581761`;
zero outcome fields are projected.

The adapter calls the canonical
`scripts/phase57_entry_pattern_v2.py::features` producer with today's R20 strict
closed prefix, previous-session observed path, frozen Selector origin, and no
prior-daily context. It asserts the exact 476-name registry, returns the 446 legal
columns, exposes the 187 finite-search columns separately, and proves all 30
blocked outputs remain null. A today row whose bar end is after NOW is rejected.

## Pattern-v2 column-level disposition

The generator emits one machine-readable row per column with producer, source,
knownAt, closed-bar requirement, suffix dependence, missing semantics, status and
finite-search membership. Family counts are:

| Family | Registry | MODEL_ADMITTED | BLOCKED | Finite-search selected |
|---|---:|---:|---:|---:|
| ACCEL1 / 3 / 5 / 10 | 8 | 8 | 0 | 8 |
| AVAIL | 12 | 12 | 0 | 12 |
| CLOCK | 3 | 3 | 0 | 3 |
| LOCAL1 / 3 / 5 / 10 / 15 / 30 | 102 | 102 | 0 | 102 |
| LOCAL2 / LOCAL60 | 34 | 34 | 0 | 0 |
| PREV | 17 | 17 | 0 | 17 |
| PREV_AM / PREV_PM / PREV_LATE | 51 | 51 | 0 | 0 |
| RECENT | 24 | 0 | 24 | 0 |
| RVOL1 / 3 / 5 / 10 | 8 | 8 | 0 | 8 |
| SEL | 3 | 3 | 0 | 3 |
| SEQ_MICRO / SEQ_PREV / SEQ_TODAY | 138 | 138 | 0 | 0 |
| SIGNAL | 13 | 7 | 6 | 7 |
| SIGNAL_PATH1 / 3 / 5 / 10 / 15 / 30 | 36 | 36 | 0 | 0 |
| STRUCT | 10 | 10 | 0 | 10 |
| TODAY | 17 | 17 | 0 | 17 |
| **Total** | **476** | **446** | **30** | **187** |

The blocked 30 are exactly 24 `RECENT/*` columns and six
`SIGNAL/PDH*`/`SIGNAL/PDL*` columns. Their exact prior-daily/context lineage is not
pinned for EXIT-NOW recomputation. They cannot be imputed, recovered from future
data or added during the finite search. The 446 admitted columns are derivable
from already-known Selector context, previous-session observed path, current-day
strict prefix and deterministic clock. Missing observed inputs remain null with
availability features; missing minutes are not certified no-trade.

The 187-column set is fixed by family before performance: AVAIL, CLOCK, SEL,
TODAY, PREV, LOCAL1/3/5/10/15/30, ACCEL1/3/5/10, RVOL1/3/5/10, STRUCT and the
seven non-prior-daily SIGNAL columns. Dense sequence projections, raw micro lags,
redundant window families and prior-session subsegments remain legally admitted
but excluded from this finite search to constrain multiplicity.

## State-v3 contract at EXIT NOW

All nine labels remain available through the canonical producer: RISE,
SHARP_RISE, REBOUND, DROP, PULLBACK, RANGE, SHARP_DROP, DROP_STOP and RISE_STOP.
Allowed features are current State, Entry→current transition, reliable dwell,
known adjacent transition/churn counts over 3/5/10 observations, and the State's
dataQuality/confidence/reason. Dwell/history reset on UNKNOWN and lunch as R20
defines. DEGRADED is not converted to OK.

R22 shows Entry itself is often DROP/PULLBACK/REBOUND (for example IMMEDIATE has
1,261 DROP, 287 PULLBACK and 179 REBOUND). Therefore DROP, a negative current
return, or deterioration alone must not mechanically force SELL. The model must
learn only within the finite protocol whether the original upside thesis remains
alive; conceptual HOLD/RECOVERY/DETERIORATING/BROKEN names are not fixed classes.

## Six-signal contract at EXIT NOW

CONTINUATION, BREAKOUT, COMPRESSION_EXPANSION, HIGHER_LOW, LOWER_WICK and RECLAIM
may be used as current tri-state and past-only 3/5/10 true/false/unknown counts,
observed persistence, multi-signal agreement and observed TRUE→FALSE transition.
TRUE→UNKNOWN is neither disappearance nor failure. A failure claim must be
defined by an observed canonical FALSE/event transition, never by missing data.

The R22 UNKNOWN rates are 57.85%–86.90%, so every signal representation must
preserve UNKNOWN explicitly. Complete-signal filtering is prohibited.

## Entry→NOW owned path contract

Legal features include current fresh closed-reference return, observed running
High/Low, observed MFE/MAE to NOW, complete-prefix MFE/MAE, observed peak
giveback, active/wall minutes held, observed/missing bar counts, peak confirmation
time and active minutes since peak. Running extrema are known history, not future
MFE/MAE. Complete-prefix metrics are null when any owned scheduled bar is absent.
No intrabar High/Low order is inferred.

## Evaluator-only and forbidden decision inputs

Canonical ordered Low→strictly-later High, post-Entry best High, future MFE/MAE,
future State/pivot, final PnL, oracle EXIT, actual EXIT outcome, capture ratios,
High→Exit evaluator gaps and final owned-peak giveback are `EVALUATOR_ONLY`.
They may form training labels or scorecard outputs only as expressly frozen in
R24/R25. No future field enters the Pattern adapter or R20 decision snapshot.

## Exposure, freeze and safety

Entry Dual Freeze `4878a1cc53430e816261dea0fb16aeb53b3c238d` is unchanged.
Fixed12/Candidate A are not inputs, baselines, fallbacks, anchors or targets.
Provider requests, protected-partition opens, model fits, candidate evaluations
and legacy EXIT invocations remain zero. Safety9 remain all false.

