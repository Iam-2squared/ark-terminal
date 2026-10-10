# Phase57 Minimal Stateful Hybrid Entry — implementation closeout

## Scope and impact audit

Architecture ID: `PHASE57_MINIMAL_STATEFUL_HYBRID_ENTRY_PHASE1`.

This is one isolated Full Hybrid Entry Replacement research line, not an extra filter after P21. P21 remains an immutable baseline/fallback. This task implements contracts, state, feature/target schemas and inference plumbing; **there is no fitted Entry model or new performance claim**.

Branch `research/phase57-minimal-stateful-hybrid-entry` starts from audited main `899d16b808dba0d5b2003228a5f46332b3a3ce09`. Draft PR #580 is separate from Baseline #579. No baseline files, Selector/P21 code, EXIT/Capital code or main history are changed. Baseline #579 remains at `938338199c861b1cd6345d08b311fbd85442e339`; its release SHA256 remains `2632d8c680ea7e388a736385936d7a3ed8b43e3e3a82f3194f26635bd78c9fa6`.

Feature/target/state/allocation contracts were committed as `fda198a24e540fbd75560205e14f891d7f903146` before the new outcome-blind sanity pass. No performance-driven feature changes followed that pass.

## State semantics

| Current state | Input | Next state / action |
|---|---|---|
| UNSEEN | Complete Hybrid selected event | WATCHING; evaluate available features/model |
| WATCHING | Best directional probability strictly exceeds the one threshold | ENTERED; exactly one Entry opportunity |
| WATCHING | Below threshold, tie, absent model or unavailable features | WATCHING; record reason |
| WATCHING | Absent from a complete scheduled Hybrid snapshot | EXPIRED |
| WATCHING | Missing/incomplete snapshot | WATCHING; unknown membership is not absence |
| WATCHING | Session close | EXPIRED |
| ENTERED | Further selection, absence or close | ENTERED; never reenter this symbol-session |
| EXPIRED | Later reselection | EXPIRED; terminal until next session |

There is no REJECT label or REJECTED state. Data-blocked is diagnostic metadata, not a fifth learned state. Terminal expiry is a deliberate minimal Phase1 interpretation: it does not create watch episodes after a confirmed selection interruption. This choice must be reviewed before Validation, not changed after outcomes.

## Feature/target/model contracts

Ten model inputs: direction-signed return from exact09:00 open; direction-signed typical-price VWAP distance; direction-signed three-bar momentum; direction-signed three-minus-six-bar momentum; directional pullback from last-six-bar high/low; last volume / previous-five mean volume; minutes since first selection; reciprocal unchanged Hybrid rank; prior selection count; direction (+1/-1).

LONG and SHORT share one Logistic model and are scored through direction-conditioned inputs. No duplicate side models or additional interaction columns are used. The greater probability is considered against one scalar threshold; exact direction ties WATCH. Hybrid rank is not reranked or normalized with an invented universe denominator.

Primary target: same-session directional +3 net return >0, round-trip5bps. Zero net is the negative binary class; missing is null, not zero. +1/+3/+6 gross returns, MFE3/MAE3, next-bar adverse and time-to-MFE3 are secondary diagnostics. No MFE100bps target, utility alpha or price cutoff exists. Target attachment requires frozen feature hash, event/direction lineage, exact three regular bar slots, same-session outcome availability and matching cost.

Daily features are omitted. Exact observed09:00 bar and seven consecutive completed recent slots are required. Scheduled lunch is skipped, missing bars are never fabricated, and current price remains the last completed close. Corporate-action and historical provider-vintage limitations remain explicit. These feature availability rules are not performance thresholds.

The implementation includes stable Logistic inference, train-only scaler artifact schema, artifact/feature-contract guards and synthetic tests. It intentionally has **no fitting API and no production coefficients or threshold**. A missing model returns WATCH with MODEL_UNAVAILABLE. Only explicitly tagged synthetic test artifacts can exercise ENTER transitions; they cannot be used by the real17-session sanity runner.

## Dataset schemas

Selected-event rows retain every Hybrid selected event, not only P21 ENTERs:

- eventId / symbolSessionId / sessionDate / symbol / decisionTimestamp
- original Hybrid rank and score, selection lineage, source class
- selectionIndex, priorSelectionCount, first and previous selection timestamps, elapsed minutes
- stateBefore/stateAfter, firstEnterTimestamp, entryCount, decision and diagnostic reason
- featureStatus, paired LONG/SHORT frozen feature records, prefix SHA and availability time
- P21-used-as-gate=false, safety flags

Directional feature rows contain contract SHA, symbol/time/direction, exactly ten named inputs and feature SHA. Future target attachment is a separate downstream API. P21 outputs may be held as a separate reference table, not passed into the model. Stateful opportunity identity is symbol-session; entryCount cannot exceed1. EXPIRED rows remain in the full selected-event denominator even though no new decision is issued.

## #572 read-only reuse audit

Pinned reference: #572 head `435466c49cf2de7915ec9fa530b7d0f98db914ad`, `predict/daytrade/phase57-entry-quality-v2-research.js` Git blob `27414a4a5784bd4480ce2ff0135747fde16f4971`.

The five overlapping intraday formulas are compared directly with the existing pure context builder: return/open, VWAP distance, momentum3, momentum3-minus6, and relativeVolume5. Extra strict completion/grid/open/zero-denominator guards are applied before reuse. The broader vector is not imported because it requires Daily data and includes more features than this contract permits. Old445 candidates and old Dynamic5m selections are never used as the new denominator. No #572 code is modified.

## Outcome-blind17-session sanity

All4,542 Hybrid selected events across17 sessions and720 symbol-sessions were retained. Feature-ready:1,346 events /2,692 directional feature rows. Blocked:3,076 missing exact09:00 bar;120 missing/stale recent grid. All13,460 shared-feature parity comparisons matched the pinned #572 formulas.

No model was fitted, no new future labels were generated and no new Entry performance was calculated. State/no-reentry/duplicate and logical PIT violations=0. Missing features are reported, not silently discarded. The all-WATCH/no-model run is a software sanity check, not a new Entry baseline or a quality result. Native provider vintage is unverified, independent of logical prefix PIT.

43 offline tests pass. A second metadata-chain verification reproduced the identical compressed sanity dataset: SHA256 `a7245bda1b379240dba846e1cce1b07d40ac00c51377a383c8f892e0f002c1f5`. The final audit verifies Baseline release → input manifest → Gate/inventory and release → evidence manifest → event files before use. No outcome/performance files are parsed by the sanity runner.

## Fresh reservation and convergence policy

The [JPX2026 calendar](https://www.jpx.co.jp/corporate/about-jpx/calendar/index.html) was used only to enumerate future session dates. The explicit arrays are in `phase57-minimal-stateful-entry-fresh-allocation.json`; no reserve-date mapping is inferred from this calendar.

| Role | Fixed window | Sessions | Access |
|---|---|---:|---|
| Fresh Validation | 2026-09-10–2026-10-05 |15| Reserved; no new outcomes |
| Purge/embargo | 2026-10-06 |1| Excluded |
| Untouched OOS reservation | 2026-10-07–2026-10-21 |10| Reserved; not certified CLEAN |
| Future Prospective | Not before2026-10-22 |Not yet allocated| Separate precommit required |

15/10 uses the upper end of the requested short windows because the baseline supplied only79 first P21 entries over17 sessions. It is not a power guarantee. A missed checkpoint or missing training authority does not silently move dates or convert Validation into Development. All windows still require a complete cross-research information-class access ledger.

One main architecture only; simplified challenger budget is voluntarily zero; unchanged P21 is the sole fallback. The fixed paired-session winner rule requires improved mean and median net+3 expectancy, majority-session improvement, lower immediate adverse, no reduced aggregate first-entry coverage and no worse label completeness. Every planned session and both sides must be evaluable; otherwise there is no promotion. Detailed rules are in the allocation manifest. No arbitrary absolute Hit/Coverage/MFE/adverse percentage is a target. No threshold-selection procedure is authorized yet; that must be fixed with the training contract before Validation outcomes.

Validation failure → New Entry NO-GO / P21 fallback, no architecture expansion. OOS failure → P21 fallback and Entry closeout. OOS pass → winner freeze only, then separately authorized paired Prospective; never automatic main integration.

## Current blockers and next highest-value step

**Validation cannot start.** The requested allocation has no training population: baseline17 is sanity-only, protected190 is excluded, and Fresh Validation/OOS must not train the model. Consequently fitted model/scaler/threshold artifacts do not exist. A code smoke test cannot resolve that governance gap.

Next: authorize a separate causal Development dataset and fixed training/one-threshold recipe without repurposing these17 or Fresh Validation/OOS. Address exact-open/recent-grid source availability during that admission, not by inventing missing bars. Complete the independent code/contract review in the accompanying Claude packet. If no suitable training data exists before the reserved window, keep it sealed and request an explicit outcome-blind scheduling decision; do not extend or consume it automatically.

Protected190 newly opened=0; new protected outcomes=0; Fresh Validation outcomes=0; OOS outcomes=0. All nine safety flags=false. No broker/order/paper/live integration exists.
