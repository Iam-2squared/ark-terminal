# Phase57 EXIT v4 — Frozen Minimal Hybrid v1 × MSH-Entry v1 Large-Scale Historical Validation

Status: RESEARCH_ONLY / DRAFT / NO MAIN INTEGRATION

## Fixed upstream inputs

- Selector: Frozen Minimal Hybrid v1
  - model digest: `444e296d31b0e59263f268706b4c8a7c7e9e59d6f7c9547e9f90342a24040fc2`
  - freeze SHA: `a744d599e430d23efe4dea6600e418d3410d8a18df5055b35e1cc71432bf64da`
- Entry: MSH-Entry v1
  - threshold: strictly `> 0.60`
  - candidate SHA: `f05def20081e51dfe7391c7e80e8b8474e5c140c42a47dc29dcd94bca367ab8a`
  - allocation SHA: `7df4cb026d966628c9b3fbc91037eb13704397a700c076e865d817a273df00e6`
  - fit SHA: `e1567951bcc81d50497a42e24411a32112b36638fbc0ff67247a16a6ce80859c`
- One-bar WAIT: rejected; no timing challenger.
- Capital Allocation and cost semantics: fixed for paired comparison.

Do not change Selector, Entry features, coefficients, threshold, direction, entry reference-price semantics, EXIT v3/v4 policy, or allocation to improve the EXIT result.

## Objective

The immediate research goal is not a new EXIT v5. It is to test the existing frozen EXIT v4 across a much larger historical sample under the new Frozen Minimal Hybrid v1 × MSH-Entry v1 path distribution.

Primary question:

> Given the same frozen Entry event, does EXIT v4 improve realized management quality versus EXIT v3 and a fixed/session-end reference across many independent historical trades, symbols, sessions, directions and path regimes?

## Why large-scale replay is required

The current Entry handoff reports strong historical replication but only about 95 Development first ENTERs and 99 Historical Holdout29 first ENTERs. These are useful diagnostics, not enough by themselves for a durable EXIT generalization claim.

The new Entry also exhibits an important path structure:

- Immediate adverse: about 71% in both Development and Holdout29.
- Many adverse-first trades later recover.
- Mechanical one-bar WAIT reduced entry quality and MFE.
- SHORT dominates current first ENTER counts.

Therefore EXIT v4 must be stress-tested for two competing failure modes:

1. cutting continuation winners too early after ordinary adverse movement;
2. holding genuinely deteriorating trades too long.

## Historical data policy

Do not restrict the research to Ark's previously captured realtime evidence.

Use the largest defensible historical 5-minute dataset available for offline research. Later-fetched historical data must be classified explicitly, for example:

- `HISTORICAL_RECONSTRUCTION_LATER_FETCHED`
- `NON_PROSPECTIVE`

Never relabel retrospective reconstruction as ACTUAL_DURABLE, PROSPECTIVE or formal fresh evidence.

Existing durable/realtime data remains valuable as golden/reference evidence for timestamp, bar-completion, Entry replay and EXIT replay parity.

## Historical Entry substrate

Preferred substrate:

Historical market data
→ Frozen Minimal Hybrid v1 replay
→ MSH-Entry v1 replay
→ frozen Entry event
→ EXIT v3 / EXIT v4 / fixed reference paired replay

If full historical market-wide Selector replay is not defensible for a period, do not fabricate parity. Any alternative EXIT-development substrate must be separately classified and must not be described as a complete Lane Y replay.

For every Entry event preserve at least:

- symbol
- sessionDate
- decision timestamp
- entry reference price
- direction
- selector lineage
- entry candidate/fit lineage
- source class
- substrate class

## Strict point-in-time constraints

At each EXIT management timestamp `t`, decision inputs may use only information finalized by `t`.

Never use future extrema, final MFE/MAE, future volume, final daily values, future VWAP, later EXIT decisions or labels as decision features.

Running MFE/MAE through `t` are causal and may be used by the existing v4 implementation.

## Sparse / no-trade bars

Preserve canonical behavior:

- no synthetic bar
- no state advancement
- no streak advancement
- no forced EXIT
- position remains open
- `NO_OBSERVATION / NO_FINALIZED_BAR`

Do not forward-fill OHLCV.

## Paired comparison

For every independent Entry event, hold fixed:

- Selector
- Entry timestamp
- Entry price semantics
- Direction
- Market data
- Transaction cost assumptions
- Capital Allocation assumptions

Compare at minimum:

1. fixed/session-end reference
2. EXIT v3
3. EXIT v4

No parameter tuning of v4 is allowed during this frozen validation.

## Sample accounting

The primary unit is the independent Entry event/trade, not the number of 5-minute management states.

Report separately:

- independent Entry events
- total management states
- unique sessions
- unique symbols
- LONG / SHORT counts

Checkpoint targets:

- A: 200 independent Entry events
- B: 500
- C: 1000+
- D: 2000+ if data coverage permits

Do not inflate sample size by treating repeated states from one trade as independent trades.

## Required metrics

At minimum report paired metrics for v3 and v4:

- trade count
- after-cost Net
- PF
- Win Rate
- average trade
- median trade
- MaxDD
- Sharpe if meaningful
- realized MFE / MAE
- MFE Capture Ratio
- Profit Giveback
- holding bars / time
- winner hold time
- loser hold time
- post-exit regret (evaluation only)
- additional loss avoided (evaluation only)

Stratify by:

- LONG / SHORT
- immediate-adverse vs no-immediate-adverse
- session/month
- volatility regime
- time of day
- symbol
- sector where available
- fast-MFE / slow-MFE or equivalent causal path diagnostics

Do not use a stratum discovered after seeing results as a promotion filter.

## Validation layers

1. Large-scale historical stress/development replay
2. Locked retrospective holdout defined before inspection
3. Future Lane Y prospective paired evidence

Historical reconstruction is never Prospective.

Do not consume protected/fresh OOS allocations without explicit authorization.

## Promotion rule

A favorable large historical result does not change main and does not promote v4 automatically.

Any eventual Main EXIT decision requires separately governed OOS/prospective evidence and explicit approval.

## Safety

All must remain false:

- executionAllowed
- brokerWriteAllowed
- excelOrderWriteAllowed
- rssOrderFunctionAllowed
- liveTradingAllowed
- paperTradingAllowed
- automaticPromotionAllowed
- productionUpdateAllowed
- transmitted

No order function, broker write, Excel/RSS order write, paper execution or live execution is required for this work.

## Immediate next steps

1. Audit available large historical 5-minute source coverage and lineage.
2. Determine how many sessions/symbols can support defensible Frozen Hybrid × MSH replay.
3. Build a replay dataset without touching protected/fresh OOS allocations.
4. Verify parity on overlapping golden sessions.
5. Reach 200 independent Entry events before making any v4 quality claim.
6. Expand to 500 / 1000+ if coverage permits.
7. Run fixed vs v3 vs v4 paired diagnostics and stability analysis.

Until those gates are complete, EXIT v4 remains a frozen candidate under large-scale historical evaluation, not a proven Main EXIT.
