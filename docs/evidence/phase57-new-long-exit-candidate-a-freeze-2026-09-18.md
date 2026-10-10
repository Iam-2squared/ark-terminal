# Phase57 NEW LONG EXIT Candidate A — Development Freeze

Date: 2026-09-18 JST

Canonical candidate name:

`NEW_LONG_EXIT_PROTECT_3_TO_1_FIXED12_V1`

Status:

**DEVELOPMENT_CANDIDATE_FROZEN_NOT_OOS_VALIDATED**

## Frozen logic

For each Frozen NEW LONG Entry opportunity:

1. Hold by default.
2. When a completed regular 5m bar first establishes running HIGH >= +3% from Entry, arm PROTECT.
3. After PROTECT is armed, the first later completed CLOSE <= +1% signals EXIT.
4. EXIT reference is the next regular 5m OPEN.
5. If no PROTECT signal occurs, use the exact frozen Fixed12 terminal cap/reference.
6. 0.05pp round-trip cost semantics remain identical to the comparator.
7. No Loss Defense, BAR5 no-reclaim, TWO_LOWER_CLOSES, model, symbol rule or cohort-specific threshold.
8. No re-entry.

## Development PASS

Candidate A pre-frozen gates all passed:

INITIAL n=1072:
- Fixed12 mean -0.328572% -> candidate **-0.263220%**
- PF 0.762478 -> **0.793880**
- p05 -5.855764% -> **-5.607821%**
- +3 preservation **314/314 = 100%**
- +5 preservation **137/145 = 94.4828%**

DIP_REPRICE n=397:
- Fixed12 mean -0.327801% -> candidate **-0.268698%**
- PF 0.741270 -> **0.768168**
- p05 -5.343625% -> **-5.189149%**
- +3 preservation **106/106 = 100%**
- +5 preservation **39/41 = 95.1220%**

## Robustness / freeze audit PASS

Chronological mean delta vs Fixed12:

INITIAL:
- block1 +0.01778pp
- block2 +0.10892pp
- block3 +0.18089pp
- block4 -0.05723pp
- 3/4 nonnegative

DIP:
- block1 -0.15860pp
- block2 +0.16902pp
- block3 +0.01659pp
- block4 +0.22255pp
- 3/4 nonnegative

Top-3-frequency-symbol exclusion:
- INITIAL mean delta **+0.02825pp**
- DIP mean delta **+0.06613pp**

Evaluator-only adverse subsets:
- 106 additional-drop >=2%: -1.484893% -> **-1.417007%**
- 21 additional-drop >=5%: -4.001442% -> **-3.684735%**

All robustness gates passed.

## Research history retained

Loss Defense v0/v1/v2/v3: KILL.
Profit Protection v0/v1/v2/v3/v4/v5: individual FAST-FAIL evidence retained.
Candidate A was not produced by threshold sweep. Its +3 activation and +1 floor are pre-existing Path Study milestones; integration was contracted before measurement.

## Important limitation

This candidate is **not profitable standalone on Development**: mean remains negative and PF remains <1 in both cohorts. The PASS means it is materially better than the frozen Fixed12 comparator on the pre-specified EXIT-quality gates, not that the full Selector→Entry→EXIT→Capital→Portfolio system is profitable.

Loss Defense is not claimed solved. The candidate's adverse-tail improvement is an observed consequence of its profit-protection behavior on overlapping paths, not a dedicated deterioration classifier.

Fresh/OOS remains sealed. No Capital/Portfolio tuning is authorized by this freeze.

## Safety / integrity

- Selector changes: 0
- NEW Entry changes: 0
- existing EXIT runtime changes: 0
- model fit/prediction: 0
- Fresh/OOS: 0
- provider requests: 0
- 1m research: 0
- Capital/Portfolio tuning: 0
- main merge: 0
- all trading/write/promotion flags: false

Freeze source audit workflow:
- Candidate A Development workflow: run `35304892577`, SUCCESS
- Candidate A robustness workflow: run `35304985360`, SUCCESS

The candidate logic is now frozen. Do not mutate it on exposed Development data.
