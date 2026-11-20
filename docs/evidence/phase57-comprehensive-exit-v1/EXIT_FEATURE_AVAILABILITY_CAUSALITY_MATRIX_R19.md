# Phase57 — EXIT Feature Availability & Causality Matrix R19 (initial audit)

Date: 2026-09-25 JST
Basis HEAD: `2682f9e429844f2173950fb0c8cf7fa3256f03f3`
Controlling research contract: `NEW_EXIT_ZERO_BASE_CONTRACT_R18.md`
Status: `INITIAL_LINEAGE_AUDIT_NO_NEW_EXIT_PERFORMANCE_INSPECTED`

## Purpose

Start the required EXIT-NOW feature audit before any NEW EXIT candidate training or performance inspection. This matrix records what the repository proves today; it does not silently promote Entry-stage artifacts into EXIT features.

## Canonical State-v3 lineage found

- Contract: `docs/evidence/phase57-state-v3-9pattern/CONTRACT.json`
- Implemented classifier used by Entry replay: `scripts/phase57_state_v3_9pattern_entry_v1.py::classify_state_v3`
- Nine states: `RISE_STOP, RISE, SHARP_RISE, PULLBACK, RANGE, REBOUND, SHARP_DROP, DROP, DROP_STOP`.
- Contract inputs are previous-session PIT closed prices, today's official open if published, today's closed bars published by as-of, active-minute calendar, and source provenance/PIT adjustment.
- Contract explicitly forbids future bar/state/resolution, oracle Low/High, future MFE/MAE/path/return/outcome, opportunity capture, Entry result, Dictionary outcome, future-confirmed pivot and future-fitted scale; volume is not part of the State-v3 price layer.
- Implementation rejects today's bar starts >= as_of, validates previous-session identity, removes lunch from active-time geometry, does not backdate pivot availability, and exposes dataQuality/confidence/reason codes.

This is strong producer-level evidence that **current State at an EXIT NOW can in principle be recomputed from a strict closed prefix**. However, exact full Frozen-2,155 EXIT-time coverage and the post-Entry checkpoint builder have not yet been demonstrated in this R19, so it is not yet marked final MODEL_ADMITTED for the NEW EXIT matrix.

## Canonical six Timing Signal lineage found

- Producer: `scripts/phase57_entry_timing_signals.py::detect`
- Protocol: `docs/evidence/phase57-entry-timing-signal-census-v1/PROTOCOL.md`
- Families: `CONTINUATION, BREAKOUT, COMPRESSION_EXPANSION, HIGHER_LOW, LOWER_WICK, RECLAIM`.
- Producer asserts today's prefix bar starts < decision t and previous session identity < day.
- Protocol defines bar-start m as known at m+1, tri-state true/false/null, missing slots as insufficient observations, no forward fill/interpolation, pivot confirmation availability, lunch reset rules for local windows/swings, observed-VWAP coverage semantics, and source-level availability.
- Volume/traded-value context exists with explicit coverage/positive-denominator requirements and UNKNOWN strata.

The detector is a strong candidate for EXIT-NOW reuse because it already accepts a causal closed prefix. But R19 does not yet prove exact post-Entry checkpoint coverage for both Frozen Entry arms; signal-history features such as persistence/failure/transition must be generated causally and audited, not inferred from future census rows.

## Pattern-v2 / information lineage found

- Pattern-v2 protocol: `docs/evidence/phase57-entry-pattern-v2/protocol.json`.
- It documents strict closed-prefix chart construction, previous session + today prefix, missing source never imputed, and source/evaluator separation.
- Existing All-Material `FEATURE_SOURCE_AUDIT_R3.md` identifies direct causal producer evidence for `range6Pct`, `lastCloseLocation`, `lastUpperWickFraction`, `turnover6Jpy` through `scripts/phase57_entry_information_export.mjs`, including a future-suffix mutation invariance check.
- That R3 explicitly says its 3,800-event exporter is not proof of exact Frozen-2,155 coverage. `relativeVolume5`, `directionalVwapDistancePct`, prior-selection fields, prior-day/market/sector/tick/tradability/PIT-profile/Dictionary families remain unresolved until producer/knownAt/full-join proof.

Therefore **“Pattern-v2 has 476 columns” is not itself an EXIT admission rule**. Column/family admission must be rebuilt for EXIT NOW from canonical producer lineage.

## Initial matrix

| family / feature | canonical producer/source | EXIT NOW causality evidence | current R19 status | next proof |
|---|---|---|---|---|
| Current State-v3 | State-v3 contract + `classify_state_v3` | strict today prefix + prior session; future inputs forbidden | `SOURCE_CAUSAL_PROVEN / EXIT_2155_COVERAGE_PENDING` | build post-Entry NOW checkpoints on both frozen Entry ledgers; suffix invariance + coverage |
| State transition/history | repeated causal State-v3 classifications | derivable only from classifications already available by each NOW | `DERIVABLE_CAUSAL / IMPLEMENTATION_PENDING` | define checkpoint cadence, dwell/churn/missing semantics and mutation tests |
| Six current Timing Signals | `phase57_entry_timing_signals.py::detect` | prefix < t assertion; protocol knownAt m+1; tri-state | `SOURCE_CAUSAL_PROVEN / EXIT_2155_COVERAGE_PENDING` | replay after each Entry with exact NOW grid; coverage/missing census |
| Signal persistence/transition/failure | repeated causal signal rows | can be past-only if history is truncated at NOW | `DERIVABLE_CAUSAL / IMPLEMENTATION_PENDING` | formal definitions before performance; suffix mutation |
| Entry→NOW return/current PnL | frozen Entry price/time + closed/current causal reference | post-Entry past information | `DERIVABLE_CAUSAL / PRICE_REFERENCE_CONTRACT_PENDING` | freeze whether NOW uses last completed close/other reference and cost treatment |
| Running peak to NOW | frozen Entry + owned closed prefix highs | past-only if peak cutoff <= NOW | `DERIVABLE_CAUSAL / OWNERSHIP_CONTRACT_PENDING` | define bar ownership and no-after-exit credit |
| Giveback from running peak to NOW | running peak + causal NOW reference | past-only | `DERIVABLE_CAUSAL / OWNERSHIP_CONTRACT_PENDING` | same as above |
| Running trough / adverse excursion to NOW | frozen Entry + owned prefix lows | past-only | `DERIVABLE_CAUSAL / OHLC_ORDER_BOUND_PENDING` | preserve ambiguity when intrabar order matters |
| time since Entry / bars held | frozen Entry timestamp + active calendar | deterministic knownAt | `MODEL_ADMISSION_CANDIDATE` | freeze active-vs-clock convention |
| time since running peak | causal owned peak timestamp + NOW | past-only | `DERIVABLE_CAUSAL / PEAK_TIMESTAMP_RULE_PENDING` | freeze ties/intrabar availability |
| Pattern direct `range6Pct` | information exporter | direct closed-prefix producer evidence | `SOURCE_CAUSAL_PROVEN / EXIT_2155_JOIN_PENDING` | exact EXIT checkpoint join/coverage |
| Pattern direct `lastCloseLocation` | information exporter | direct closed-prefix producer evidence | `SOURCE_CAUSAL_PROVEN / EXIT_2155_JOIN_PENDING` | same |
| Pattern direct `lastUpperWickFraction` | information exporter | direct closed-prefix producer evidence | `SOURCE_CAUSAL_PROVEN / EXIT_2155_JOIN_PENDING` | same |
| Pattern direct `turnover6Jpy` | information exporter | direct closed-prefix producer evidence; no future fill | `SOURCE_CAUSAL_PROVEN / EXIT_2155_JOIN_PENDING` | same |
| `relativeVolume5`, `directionalVwapDistancePct`, prior-selection fields | inherited fields | producer/knownAt unresolved in R3 | `BLOCKED_PENDING_LINEAGE` | trace producer and exact 2,155 EXIT join |
| prior-day vol/TR/volume shock, market/sector, tick/tradability, PIT profile, Dictionary descriptors | unresolved conditional families | no sufficient full lineage in current audit | `BLOCKED_PENDING_LINEAGE` | producer/as-of/join/coverage/suffix proof |
| Future High/Low, full opportunity Low→later High | evaluator suffix | future at decision NOW | `EVALUATOR_ONLY` | use only after decisions for scorecard/buckets |
| Future MFE/MAE, final PnL, future State/pivot, oracle best EXIT | evaluator/labels | future at decision NOW | `EVALUATOR_ONLY` | never decision feature |
| Entry→strictly-later High, Entry→Exit capture, High→Exit giveback | evaluator geometry | depends on future suffix and/or final exit | `EVALUATOR_ONLY` | mandatory R18 scorecard, including <1/1-2/2-3/3-4/4-5/>=5% Low→High buckets |

## Critical geometry still to freeze before NEW EXIT performance

The repository currently contains several historical clocks/geometries. R18 requires a NEW EXIT-specific sequential NOW contract rather than silently inheriting an Entry 30-minute deadline or old Fixed12 geometry. Before candidate outcomes are inspected, freeze:

1. decision cadence (1m closed endpoint, 5m, or finite predeclared combination);
2. session terminal/overnight holding semantics;
3. current executable EXIT reference after a decision (e.g. next observed OPEN) and missing-reference handling;
4. active vs clock holding time;
5. owned-path HIGH/LOW timestamp semantics and intrabar ambiguity;
6. treatment of lunch and session end;
7. transaction cost accounting;
8. checkpoint feature history window limits;
9. finite labels/targets and training split/search budget.

No old EXIT policy is the comparator or fallback under R18.

## Exposure / safety / status

- Frozen Entry policies unchanged; no Entry fit/reselection.
- NEW EXIT candidate count evaluated: **0**.
- NEW EXIT performance inspected: **no**.
- Provider requests: **0**.
- New Common Holdout/REPORT19/Validation/OOS/Fresh/Prospective opened: **0**.
- Old Fixed12/Candidate A preserved as historical Evidence only, not comparison targets.
- Safety9 remain false; no main merge/live/paper/production.

## Next work

Build and test the post-Entry sequential checkpoint substrate for both Frozen Entry ledgers, while keeping evaluator suffix physically/logically separate. Use State-v3 and six-signal producers only through strict prefix calls. Simultaneously inventory Pattern-v2 columns/families to resolve which have canonical producer lineage at EXIT NOW. Then freeze the NEW EXIT evaluation scorecard and finite search protocol **before** any candidate performance run.
