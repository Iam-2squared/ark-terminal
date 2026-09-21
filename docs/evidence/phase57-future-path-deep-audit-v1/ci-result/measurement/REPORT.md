# STEP 1 Future Path Deep Audit — STOP FOR HUMAN REVIEW

Reused Development; evaluator-only. Existing 5+1 labels are unchanged. No State, Signal, Entry, learning, Dictionary or EXIT evaluation.

## Reconciliation

All 2155 IDs and every original classifier field reproduced exactly.

| Original Path | Count |
|---|---:|
| DIRECT_CONTINUATION | 50 |
| PULLBACK_RECOVERY | 202 |
| CONSOLIDATION_BREAKOUT | 10 |
| MULTI_SWING_CHOP | 828 |
| PERSISTENT_WEAKNESS | 76 |
| AMBIGUOUS_INSUFFICIENT | 989 |

## Observation insufficiency

Exact original gate failures (overlap retained):

```json
{
  "ROWS_LT20": 263,
  "ROWS_LT20|REMAINING_LT30": 99,
  "REMAINING_LT30": 71,
  "INHERITED_FULL_UNAVAILABLE|ROWS_LT20": 49,
  "INHERITED_FULL_UNAVAILABLE|ROWS_LT20|REMAINING_LT30": 9,
  "INHERITED_FULL_UNAVAILABLE": 5
}
```
Insufficient cases with missing regular minute stamps: 460; inherited full-session unavailable: 63; terminal auction absent: 63.
Unresolved compact-source cause cases: 460. Missing compact bars cannot distinguish no-trade, halt, filtering and provider loss. Lunch is not counted as missing trading minutes. Calendar and coverage co-occurrence does not prove causation.

## Mixed paths and CHOP override

539 CHOP assignments also pass another original Path predicate. CHOP is therefore not automatically a pure, mutually exclusive motion type.

```json
{
  "PULLBACK_RECOVERY|MULTI_SWING_CHOP": 79,
  "DIRECT_CONTINUATION|CONSOLIDATION_BREAKOUT": 2,
  "DIRECT_CONTINUATION|PULLBACK_RECOVERY|MULTI_SWING_CHOP": 3,
  "MULTI_SWING_CHOP|PERSISTENT_WEAKNESS": 19,
  "PULLBACK_RECOVERY|CONSOLIDATION_BREAKOUT|MULTI_SWING_CHOP": 9,
  "PULLBACK_RECOVERY|CONSOLIDATION_BREAKOUT": 9,
  "DIRECT_CONTINUATION|MULTI_SWING_CHOP": 10,
  "CONSOLIDATION_BREAKOUT|MULTI_SWING_CHOP": 4,
  "DIRECT_CONTINUATION|PULLBACK_RECOVERY": 2,
  "CONSOLIDATION_BREAKOUT|PERSISTENT_WEAKNESS": 1
}
```

Mixed combinations here mean jointly true frozen predicates. Witness timestamps permit chronological inspection, but do not establish a causal State transition or intrabar ordering.

## Rare Path clauses

| Predicate | True anywhere | Exclusive label | Mixed Path6 | CHOP absorbed |
|---|---:|---:|---:|---:|
| DIRECT_CONTINUATION | 67 | 50 | 17 | 0 |
| PULLBACK_RECOVERY | 810 | 202 | 102 | 506 |
| CONSOLIDATION_BREAKOUT | 106 | 10 | 25 | 71 |
| MULTI_SWING_CHOP | 952 | 289 | 124 | 539 |
| PERSISTENT_WEAKNESS | 114 | 76 | 20 | 18 |

Exclusive label counts are not the same as the frequency of the underlying predicate. atomicPassCounts in summary.json additionally separates structural breakouts/recoveries from the terminal condition. No threshold was changed.

## NO_DOMINANT_PATH and CHOP shape

All 355 no-dominant cases retain their exact failed-clause signatures, observed price paths, event witnesses and whole-path metrics. No passed predicate is a definition-level result, not proof of no movement.
CHOP is tabulated by original predicate signature, net return band, ordered range, efficiency, amplitude, direction changes, volatility, low/high timing and recovery. See distributions and chopReturnRangeSignatures in summary.json. These are descriptive partitions, not newly trained or installed Path classes.

## Evidence navigation

raw/audit-records.json.gz: all 2,155 IDs with gates, metrics, clauses, witnesses and original labels.
raw/future-paths.json.gz: all observed post-selection OHLCV/value rows used here; no interpolation.
raw/observations.csv and selection-time.csv: per-ID and clock-time coverage/reason evidence.
summary.json: full distributions, combinations and clause incidence; representatives.json and plots/index.md: deterministic chart selection.
110 representative charts; all 50 DIRECT and all 10 CONSOLIDATION labels are included, along with predeclared median/extreme representatives. Full population numerical outputs are not restricted to chart samples.

## Completion gates

| Gate | Status | Evidence / limitation |
|---|---|---|
| 1 All 2,155 label counts explained | PASS | Exact original field replay and predicate incidence |
| 2 Path6 989 reasons explained | PASS | 496/355/138 reconciled; raw gate masks and failed clauses |
| 3 Insufficient 496 root causes | PARTIAL | Mechanical gate causes and observed gaps explained; provider/halt/no-trade provenance not available from compact rows |
| 4 No-dominant 355 typical paths | PASS | Full metric/failure-signature records and deterministic charts; semantic interpretation requires human review |
| 5 Mixed 138 combinations | PASS | All original combinations and chronological witnesses; concurrent predicates are not assumed sequential states |
| 6 CHOP 828 single-group suitability | PARTIAL | Heterogeneity and absorption evidence recorded; not certified as one homogeneous semantic group |
| 7 Keep/revise vocabulary decision | PARTIAL | Evidence ready for human review; no replacement vocabulary selected or installed |

## Audit conclusion

Do not treat 5+1 labels as a validated causal State vocabulary. Keep these historical labels immutable. Review observation availability separately from path semantics, and review whether overlapping events should be represented as sequences rather than forced single labels. This is an audit recommendation, not STEP 2 implementation.

STEP 1 evidence recorded with explicit limitations. STOP. Human review is required before deciding STEP 2; no later work is authorized. Dedicated CI success is not a claim that the entire PR is GREEN.

## Safety

{"automaticPromotionAllowed": false, "brokerWriteAllowed": false, "excelOrderWriteAllowed": false, "executionAllowed": false, "liveTradingAllowed": false, "paperTradingAllowed": false, "productionUpdateAllowed": false, "rssOrderFunctionAllowed": false, "transmitted": false}

providerRequests=0; holdoutOpened=0; training=false; statePrediction=false; entryTimingEvaluated=false; dictionaryUsed=false; exitResearch=false; nextStepStarted=false.
