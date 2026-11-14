# STATE9_STRUCTURAL_EXIT_V3_LOCAL_GUARD

Document: WORK_STATE9_STRUCTURAL_EXIT_V3_LOCAL_GUARD_FASTTRACK_20261003. One research policy, fixed before v3 outcomes. This contract freeze is not formal EXIT adoption.

Use all 1,600 unchanged Frozen FIRST ENTRY v2 P1_Q70 records, exact v2 Full State9/Path trace, saved raw fill/calendar lineage and saved v2 economic opportunity/results. Start actual GET HEAD must be 823fe3a7203e58fbc20fa73acab1d77e1da62c8e. Package, each of 1,606 components, trace container and Entry bytes must match saved manifests. Missing exact trace means BLOCKED_V3_FROZEN_TRACE_NOT_AVAILABLE; never reconstruct it. No State9 or Path engine is imported or run.

The v2 Lifecycle implementation is reused byte-identically for PRE, arm, quality/suspension and main EXIT-A/B. Only the v3 position scan is run. The exact v2 fill function and dated clock function source slices are reused. No v2 position Replay or Entry/model computation is performed. Saved v2 economics are joined after decisions by unchanged watch_key. No outcome, High, score or comparison result is a decision input.

## Local confirmed pivot cache

Read each original causal trace forward. The local pivot cache is an input-history view of exact saved local_pivot_confirmed objects, including their original kind/x/extremum_t/confirmed_at/generation_reason. Do not derive a new pivot or use intrabar High/Low. Retain only the current segment's latest consecutive three distinct confirmations, in confirmed_at order. At time t use the cache through the previous bar; append the current confirmation only after this bar's decision/update. All source confirmations satisfy extremum_t <= confirmed_at <= current as_of.

The cache may contain already known same-segment pivots preceding Entry or first UP arm: the user rules require confirmed_at<t and same segment, not confirmed_at after Entry. Reading that prefix is not a position decision or an Entry replay. The position LOCAL_UP_STRUCTURE_GUARD itself is managed only in UP_STRUCTURE_ACTIVE, never in PRE. At Entry it is unset; a valid current UP may arm and create a next-bar guard, but cannot cause same-bar SELL.

Clear both cache and guard on invalid/unobserved/null/rejected/unavailable endpoints, nonadjacent ordinals, or different causal segment/source/auction reset. Frozen Path/State adjacency is reused. New segment UP re-arms the unchanged v2 base and starts with no carried guard. Same-segment DOWN/RANGE observations in PRE never SELL.

## One local guard update

Frozen local scale=1U, main structure=4U, delta_break=0.5U and epsilon_progress=0.5U remain unchanged. All guard arithmetic uses exact Fraction on original RC2 numeric lexemes. No search or approximation tolerance enters decisions.

Only in valid observed active UP, after ruling out main A/B and before appending the current pivot, evaluate the previous-bar local pivot suffix L0/H0/L1. No search of older triples. Require all three confirmations strictly before t, same current segment, L1-L0>=0.5U, L1>existing guard (or unset), and Close_t>=H0+0.5U. Set guard_after=L1, effective_from=t+1. This update is not usable for this bar's break. Guard never decreases in an active uninterrupted UP segment. Store exact local triple, main _structure_pivots/_context_extreme, protected-before/after, activation distance and update times as metadata.

## First trigger and precedence

1. Exact v2 EXIT-A: adjacent same-segment observed UP→DOWN; Frozen main break and Path CONTEXT_CHANGE.
2. Exact v2 EXIT-B: independent RANGE/BALANCED/context NONE retirement; Frozen retirement and Path events.
3. EXIT-C LOCAL_UP_STRUCTURE_GUARD_BROKEN: still active, valid observed same segment, context=UP, effective guard_before exists, protected_before exists, guard_before>protected_before, Close_t<=guard_before-0.5U.

A/B keep the v2 reason if present on the same bar. C is considered only before the existing planned closing-intention deadline (900/925), so it is genuinely earlier than the v2 closing intention rather than relabelling that same clock. This is a causal calendar restriction from the existing liquidation plan; no future v2 result is read to accept/reject C. A/B remain unchanged at that deadline. Audit later checks every C intent is strictly earlier than saved v2 intent/planned deadline. Actual sell advancement is reported separately and can be zero if both fill at the same closing source.

Stop all position decisions on the first A/B/C intent. PULLBACK, RISE_STOP, State strings, dwell, stop count and fixed loss/profit never trigger SELL alone. A C break may occur in PULLBACK, but must satisfy all exact structural guard conditions.

## Execution and evaluation

Execution is the exact v2 next eligible regular raw Open times 0.9995. Entry +5bps is already in the immutable fill and is never charged twice. Commission=0. Existing exact dated terminal-auction Close liquidation is the contingent fallback; missing eligible Open and exact closing source is UNRESOLVED. Never substitute the decision Close or last observed Close.

Reuse each saved v2 observed Entry→High, peak timestamps, completeness and exclusive bucket. Do not rerun that Entry opportunity evaluator. Compute only v3 sell-dependent return, pre-sell observed peak, later strictly-later High/missed upside, holding and realization from the same saved raw source. Full-session Peak Giveback pp=MFE_pct-return_pct; pre-sell peak uses raw start Entry<bar<sell, excluding sell-bar intrabar ambiguity. Later missed upside uses raw start>sell, sale-price denominator and max(0,value); absent later observed High is null. All baseline values remain saved v2 fields.

Primary table uses frozen exclusive <1,1–<2,2–<3,3–<4,4–<5,>=5 and UNKNOWN buckets. Report both full-group v2/v3 mean/median and their difference, plus Entry-ID paired delta N/mean/median where both values exist. A difference between group medians is not the median of per-entry differences. No null imputation. Sell-filled/unresolved and metric-specific denominators remain explicit.

For EXIT-C report intent and fill advancement separately, saved v2 intent reason/status, paired return/pre-sell giveback/later missed upside, each exclusive bucket, and a separate >=5 Winner C subgroup. Guard mechanics include observed/prefix pivots, unique eligible suffixes, higher-low suffixes, guard creation/tightening, unique guard positions, resets, activation distance, guard age and break Primary/context/three distinct Primary.

Independent audit uses a separate latch/pivot ledger and arithmetic implementation without importing primary lifecycle/guard/fill/evaluator. Audit all 1,600 Entries, exact trace reuse, causal pivot and effective-next-bar rules, same segment, monotonicity, first A/B/C precedence, execution, saved-result identity and paired economics. mismatch_N=0 and future_causal_leakage_N=0 are mandatory. Historical actual_known_at is UNKNOWN; causal verification uses the inherited bar_end availability assumption.

## Budget, checkpoints and STOP

New EXIT policies=1, local guard variants=1. Buffer/pivot/profit/dwell/model variants=0. New fit/teacher/OOF/probability/score/rank/search/provider/market data=0. Entry replay/refit, State9/Path full reconstruction, v2 Replay and old EXIT Replay=0. State9/Path/profile/M0 semantics unchanged. Hard1/fixed stop/fixed trailing/Protected/Fresh/Validation/OOS/Prospective/Re-entry/Capital/Portfolio/orders/main merge/force push=0.

All ten safety flags=false, LONG-only cash-equity-only, productionReady=false. Checkpoints only V3_S0_START_AND_CONTRACT, V3_S1_REPLAY_AND_EVALUATION, V3_FINAL_AUDIT_AND_EVIDENCE. Each records actual saved_at_jst and actual basis_head, then actual GET checks the committed result HEAD. No future SHA.

Normal STOP: STATE9_STRUCTURAL_EXIT_V3_LOCAL_GUARD_EVIDENCE_READY. Integrity stops: BLOCKED_V3_FROZEN_TRACE_NOT_AVAILABLE, BLOCKED_V3_LOCAL_GUARD_CAUSALITY, BLOCKED_V3_LINEAGE_MISMATCH, BLOCKED_V3_AUDIT_MISMATCH. Poor performance does not authorize a rescue candidate or threshold change. Formal EXIT Freeze, Re-entry and Capital require later human judgment and do not run automatically.
