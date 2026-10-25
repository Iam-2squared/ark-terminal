# STEP 3 — Causal State Recognition v1 — Protocol Lock

Date: 2026-09-21 JST
Base HEAD: d5322ff8cb649fc26e01d6f4d64609c0c360d7e4
Status: PRECOMMITTED / MEASUREMENT PENDING

## One question

Using only information available at NOW, how well can the STEP 2 vocabulary be recognized?

This STEP measures recognition only. It does not evaluate Entry timing, Signals, BUY NOW/WAIT, fills, returns, learning, Dictionary, Holdout, EXIT, Capital, or Portfolio.

## Population and evidence boundary

- Fixed 2,155 Development Opportunities from the existing frozen census identity.
- Reuse only already authorized Development data and saved raw/substrate evidence.
- No Common Holdout, Fresh, OOS, Prospective, or new provider acquisition.
- Future STEP 1 anatomy may be used only as evaluator labels/witnesses after causal features are frozen for each checkpoint.
- Existing 5+1 label is lineage/reference only, not the canonical target.

## Causal inputs at each NOW

Allowed:
1. Recent Daily D-5..D-1, exact exchange-calendar sessions only.
2. Previous Day observed 1m for the actual immediately previous session.
3. Today Open -> NOW closed regular 1m only.

Forbidden:
- any bar after NOW,
- future MFE/MAE/high/low/terminal return,
- future Path predicates/witnesses as input,
- Dictionary,
- Signals or signal trigger fields,
- Entry/EXIT/trade/fill/outcome fields.

Missing observations remain missing. No forward fill, interpolation, nearest-future substitution, or invented bars.

## Checkpoints

Evaluate at fixed active-minute checkpoints relative to Selector T:
T+0, T+5, T+10, T+15, T+30.

Checkpoint requires the exact scheduled closed observation required by the causal feature. Missing checkpoints remain unavailable; do not substitute a later bar.

T+ is diagnostic elapsed active trading time, not a BUY time.

## Recognition target

STEP 2 representation is multi-layer and multi-label.

### A. Observation Status

Measure whether the causal prefix itself is:
- OBSERVED_SUFFICIENT
- OBSERVED_PARTIAL
- OBSERVATION_INSUFFICIENT

Keep explicit reason flags for sparse/missing/session-boundary conditions. Observation quality is never a behavior class.

### B. Behavior Attributes

Evaluate independently, not as mutually exclusive classes:
- CONTINUATION_UP
- PULLBACK
- RECOVERY
- CONSOLIDATION
- BREAKOUT_UP
- MULTI_SWING_CHOPPINESS
- WEAKNESS_DOWN

Where STEP 1 has an exact existing predicate/witness mapping, use it as evaluator anatomy. Where STEP 2 introduced a semantic split not uniquely identified by STEP 1 evidence (notably PULLBACK as distinct from RECOVERY), report TARGET_NOT_IDENTIFIABLE_FROM_STEP1 rather than manufacturing labels.

For each identifiable attribute and checkpoint report:
- evaluator-positive count,
- available causal-prefix count,
- recognized-positive count,
- precision,
- recall,
- F1,
- false-positive and false-negative counts,
- UNKNOWN/UNAVAILABLE separately.

No single overall accuracy may hide class imbalance.

### C. Temporal events / transitions

Only evaluate transitions whose STEP 1 observed witness timestamps establish an order. Report:
- ordered evaluator cases,
- causally recognizable by checkpoint,
- ORDER_AMBIGUOUS,
- missing-gap/same-bar ambiguity,
- transition type counts.

Do not convert co-occurring multi-label predicates into transitions.

### D. Continuous descriptors

Use causal prefix descriptors already available or mechanically derivable from closed OHLCV/value:
returns, efficiency, HH/HL/LH/LL, reversal/direction changes, realized volatility, range, drawdown, recovery position, VWAP distance/slope, volume/value ratios, previous-day descriptors, daily distances, and observation coverage.

Descriptors are inputs/diagnostics, not silently threshold-searched classes.

## Recognition mechanism

This STEP is diagnostic, not model training.

1. Reuse the existing closed-prefix causal feature machinery where semantics match and verify suffix invariance/future rejection.
2. Do not reuse its old mutually-exclusive dominant-state assignment as the STEP 2 answer.
3. Build independent attribute recognizers from predeclared causal conditions only.
4. Thresholds must be precommitted from existing definitions/mechanics before evaluator outcomes are read; no sweep, optimization, or per-class rescue after results.
5. Recent Daily may add context only through D-5..D-1 causal features. Report intraday-only and intraday+Recent-Daily side-by-side when mechanically available; do not select a winner in this STEP.
6. No fitted classifier, hyperparameter search, clustering, or AI learning in STEP 3.

If an attribute cannot be mapped without inventing a new threshold/definition, mark it NOT_YET_OPERATIONALIZED and preserve the gap for human review.

## UNKNOWN policy

The goal is to explain and minimize avoidable UNKNOWN, not force UNKNOWN=0.

Every unrecognized row must be assigned a reason category:
- OBSERVATION_INSUFFICIENT
- CHECKPOINT_BAR_UNAVAILABLE
- TARGET_NOT_IDENTIFIABLE_FROM_STEP1
- RECOGNIZER_NOT_OPERATIONALIZED
- MULTIPLE_ATTRIBUTES_VALID
- ORDER_AMBIGUOUS
- OBSERVED_OTHER_PATTERN

Multiple attributes are valid and are not UNKNOWN.

Report UNKNOWN/reason rates at every checkpoint and whether they decline from T+0 to T+30.

## Required diagnostics

For every checkpoint:
- population/availability table,
- observation-status table,
- per-attribute metrics,
- multi-label cardinality distribution,
- top attribute combinations,
- transition recognition table,
- UNKNOWN reason table,
- selection-time and session-half strata,
- Recent Daily availability,
- Previous Day 1m coverage,
- representative false-positive/false-negative/unknown examples with causal prefix only plus evaluator annotation.

Also report stability across Development sessions/month/time bucket. These are diagnostics, not independent validation.

## Completion Gate

STEP 3 may be called COMPLETE only when:
1. All 2,155 IDs reconcile exactly.
2. Every causal input is demonstrably <= NOW.
3. D-5..D-1 and actual Previous Day contracts are verified.
4. Observation uncertainty is separated from behavior uncertainty.
5. Every STEP 2 attribute is either measured or explicitly NOT_YET_OPERATIONALIZED with reason.
6. Multi-label recognition is reported without exclusive winner assignment.
7. Transition claims use observed order only.
8. UNKNOWN is fully reason-coded at each checkpoint.
9. No threshold search/training/Signal/Entry evaluation occurred.
10. Raw/summary/plots/protocol/hashes/reproducibility evidence is saved.

Regardless of outcome, save Evidence and STOP FOR HUMAN REVIEW. Do not start STEP 4.

## Safety / Frozen boundaries

Frozen Selector unchanged. No retrain/rerank/refilter and no Opportunity rejection.
Dictionary excluded.
Common Holdout/Fresh/OOS/Prospective sealed.
Signal evaluation forbidden.
Entry Timing evaluation forbidden.
Entry vNext learning forbidden.
EXIT/Capital/Portfolio forbidden.

LONG-only / cash-equity-only.
executionAllowed=false
brokerWriteAllowed=false
excelOrderWriteAllowed=false
rssOrderFunctionAllowed=false
liveTradingAllowed=false
paperTradingAllowed=false
automaticPromotionAllowed=false
productionUpdateAllowed=false
transmitted=false

Measurement implementation: scripts/phase57_causal_state_recognition_v1.py. Results are generated only after this protocol lock.
