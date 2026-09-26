# Phase57 9-State Entry Audit — PROGRESS R1

2026-09-23 JST / PR #587 / research/phase57-long-only-cash-equity

## Scope

R0 protocol remains controlling. This receipt records infrastructure progress only. It does not claim REBOUND semantic classification accuracy, Entry improvement, Fresh/OOS evidence, or promotion.

## Git / CI identity

- Baseline research head: `0cb54331b7da1021a0244c625245c20b1694ec28`
- R0 protocol commit: `f2f5312312f9265ac6ee6c607bb1ca04e5567b6e`
- Blind-packet CI assertion repair head: `5c08a0944763846f960c413e82c949a5ed471693`
- Successful dedicated run: `35833003690`
- Successful job: `107089879173`
- Public blind packet artifact: `10738260743`
- Public artifact ZIP SHA-256: `ab61f475df650dfbb001448a94f971d1adac7572c64833bacd71fc510b16daef`
- Sealed mapping artifact: `10738275641`
- Sealed artifact ZIP SHA-256: `92f724dc444f354ac1efcd5f54f10ce04d2b7aae9cf864a61adb3f78722247fc`

## Prior failed run and minimal repair

Run `35828096417` failed after the packet builder itself had succeeded because the workflow asserted a hard-coded 36 charts. The frozen prefix-only comparator definition produced only 10 eligible RISE comparator cases, so the builder correctly emitted:

- REBOUND review cases: 24
- eligible full-recovery RISE comparator pool: 10
- comparator review cases: 10
- total blind cases: 34

The builder contract already uses `min(12, comparator_pool)`. The workflow assertion was repaired to validate that contract rather than weakening the comparator definition after seeing outcomes. This was a CI/cardinality bug repair only; no classifier, State definition, Signal, BUY/WAIT rule, Entry policy, outcome definition, threshold, or sampling predicate changed. It does not consume the one-performance-hypothesis budget for REBOUND.

## Successful blind-packet build

Run `35833003690` completed successfully. All relevant steps passed:

1. focused blind-packet unit tests: 3/3 PASS
2. approved raw-price substrate download and fixed SHA verification: PASS
3. frozen outcome-blind packet build: PASS
4. identity/outcome leakage guard: PASS
5. public packet upload: PASS
6. sealed map upload: PASS

Manifest facts:

- target state: `REBOUND`
- target population: 192
- target review cases: 24
- comparator definition: `T0 RISE with priorDir=-1 recentDir=+1 and abs(recentReturn)>=abs(priorReturn)`
- comparator pool / review cases: 10 / 10
- total review cases: 34
- provider requests: 0
- protected data opened: 0
- future or outcome sources opened: 0
- Entry or fill sources opened: 0
- public packet contains baseline State: false
- public packet contains Opportunity identity: false
- sealed map stored separately: true
- packet status: `PACKET_READY_BLIND_REVIEW_NOT_YET_COMPLETED`

The public packet contains 34 anonymized SVG charts (`RBV1-001` through `RBV1-034`) plus cases/review template. The sealed map has not been used for a semantic verdict in this receipt.

## Current audit state

- REBOUND blind packet generation: COMPLETE
- chart visual inspection: 0 / 34 claimed
- blind semantic judgment: NOT YET FIXED
- sealed-map comparison: NOT STARTED
- Low/High and Entry anatomy: NOT STARTED
- REBOUND repair hypothesis: NONE CONSUMED
- Entry/classifier code modification: NONE

Do not infer REBOUND accuracy from the successful packet CI. The next valid action is to inspect every blind prefix chart, record the judgment before opening the sealed mapping, and only then compare the fixed judgments with the baseline classification and attach evaluator-only anatomy.

## Safety / research boundary

Provider requests remain 0. No Common Holdout / REPORT19 / Validation / OOS / Fresh / Prospective data was opened. EXIT, Capital, Portfolio, main merge and production were not advanced. Trading/write/promotion flags remain false by protocol.