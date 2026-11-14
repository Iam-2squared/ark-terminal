# Ark Terminal — Entry Geometry / Capture Baseline — Checkpoint 00

JST: 2026-10-02T22:57:52+09:00
Repository: Iam-2squared/ark-terminal
Branch: entry-geometry-capture-baseline-20261002-v1
Parent V6 delivery HEAD: 10a8278e2107185bcf8842b7d10af3bbff435dea
V6 C7 HEAD: 4d07d3eefd53229da2384acac648ed4e1dea3285
Source handoff manifest SHA256: 19729cc96ed3d567d891e2fb91efb52973354d5b22814e4a4e560fee8bf58b3b

## Current state

V6 is formally closed as `STATE_R2_SIGNAL_NOT_REPLICATED`.
Do not continue State-only prediction loops. State9 remains a causal feature family,
but V6 did not authorize calibrated probabilities or rank-based Entry thresholds.

V6-only dangerous UP→DOWN:
- R1: 10.186757%
- R2 Full State9: 9.665227%
- improvement: +0.521530 pp
- 95% CI: [-1.630718, +2.367065] pp

V5+V6 pooled:
- R1: 11.025943%
- R2: 9.671848%
- improvement: +1.354095 pp
- 95% CI: [-0.171312, +2.723970] pp

Integrity remains PASS for TRUE_NULL / sample / concentration / independent/core audit,
mismatch=0, direct future leakage=false. Calibration FAIL remains preserved.

## New authorized direction

Start Entry research with a descriptive ENTRY GEOMETRY / CAPTURE BASELINE before
any Hybrid Entry model fit or threshold optimization.

Primary question:
Of Selector→High opportunity, how much remains at Entry→High, and how far is Entry
from the post-Selector Low?

Core metrics:
1. Selector→High
2. Entry→High
3. Upside Retention = Entry→High / Selector→High
4. Selector→Low
5. Low→Entry
6. Entry→Low / post-entry adverse excursion
7. Selector→Entry time
8. Entry→High time
9. Missed Winner count/rate
10. Breakdowns by Selector-upside bucket, State9, time-of-day, security/date
    and already-existing causal volatility/liquidity context when available.

Design intent:
- Exact bottoms/tops are not required.
- Some delay after Low/confirmation is acceptable.
- Prefer causal Entry points retaining meaningful upside to later High.
- Remaining reversal risk is handled jointly with EXIT later.

## Existing evidence already verified for reuse

Frozen Selector / path anatomy:
- 76 Development sessions
- 760 frozen decision timestamps
- exact Top5 = 3,800 original Selector rows
- 10 decision times/session: 09:30, 10:00, 10:30, 11:00, 11:30,
  13:00, 13:30, 14:00, 14:30, 15:00
- Decision Price = exact saved PIT Decision Price; not first subsequent OPEN
- post-selection path starts at bars >= decision timestamp
- path ends 15:00 before 2024-11-05 and 15:30 thereafter
- no next-session or auction supplementation

Existing Development split evidence:
- TRAIN 38 sessions
- VALIDATION 19 sessions
- DEVELOPMENT_TEST 19 sessions
- protected/fresh/OOS/prospective remain unopened by this checkpoint

Existing Entry evidence:
- All-Material R1 contract/evaluator asserts population 2,155
- preserved current one-minute parity also asserts 2,155 records
- the frozen fill proxy records entryMinute/price and explicit missing/unfilled reasons
- geometry should reuse preserved Entry records rather than regenerate old Entry decisions

## Important geometry distinction

Do not silently treat the global post-Selector Low as if it necessarily occurred before Entry.
For Low→Entry reporting, preserve whether Entry is:
- before the oracle Low,
- at/after the oracle Low.

Likewise Entry→High must use a High that occurs after Entry when measuring remaining realizable
same-session upside. Global Selector→High and ordered/later High must remain distinguishable.

## Next checkpoint

1. Pin exact source files and hashes for:
   - canonical Selector/opportunity rows
   - post-Selector Low/High oracle
   - IMMEDIATE Entry records
   - All-Material R1 Entry records
   - State9-at-entry/current-state mapping
2. Freeze metric equations, missing-data handling and denominators.
3. Reuse saved evidence only; no provider acquisition, no old model rerun.
4. Run one descriptive aggregation and independent arithmetic/hash audit.
5. Save tables/plots, current status, next direction, JST and resulting HEAD.

## Prohibited in this baseline

- new Entry model fit
- threshold search/optimization
- EXIT modification
- profit/capital/portfolio optimization
- Holdout / Protected / OOS / Prospective opening
- live/paper/order execution
- main merge
