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

## Independent pre-review integration — Claude 2026-09-10

An external pre-review judged the plan `GO WITH CONDITIONS`. We adopt the methodological guards below, but do **not** blindly freeze reviewer-suggested numerical performance thresholds (for example PF 1.30, WinRate 58%, MFE Capture 60%, substrate score 0.70, p<0.05) because those values were proposed heuristically rather than derived from an Ark-specific utility/risk contract. Any promotion/failure threshold must be separately justified and precommitted before locked holdout inspection.

### Mandatory pre-condition A — Historical data quality audit

Before Checkpoint A performance claims, produce a data-quality report covering:

- timestamp / completed-bar semantics
- session/lunch boundaries
- adjusted vs unadjusted OHLCV
- corporate actions
- missing/no-trade bars
- historical universe reconstruction and survivorship risk
- later-fetched historical revision / source lineage
- source query/fetch time/fingerprint where available

Each item must be PASS / CONDITIONAL_PASS / FAIL. Critical unresolved timestamp, adjustment, or survivorship errors block performance claims.

### Mandatory pre-condition B — Entry substrate fidelity tiers

Classify every historical Entry event into a reproducible substrate tier. Suggested semantics:

- `TIER_1_GOLDEN_OR_FULL_REPLAY`: exact/golden or defensible full Frozen Hybrid × MSH replay with strong parity evidence.
- `TIER_2_RECONSTRUCTED_REPLAY`: later-fetched historical reconstruction with causal replay but weaker market-wide/microstructure fidelity.
- `TIER_3_PARTIAL_SUBSTRATE`: incomplete Entry reconstruction; excluded from primary v4 validation and, if retained, diagnostic only.

Report counts and performance separately by tier and by period. Do not collapse Tier 1/2/3 into one claim if performance or data quality differs materially.

A weighted substrate score may be displayed only as a descriptive diagnostic. It is not a promotion gate unless its weights and threshold are independently justified and frozen before outcome inspection.

### Mandatory pre-condition C — Freeze checklist before locked holdout

Before opening locked holdout, freeze and hash:

- EXIT v4 policy SHA / implementation ref
- EXIT v3 baseline ref
- fixed/session-end baseline definition
- paired evaluator implementation
- Entry/Selector identifiers
- cost assumptions
- session-end and sparse/no-trade semantics
- metrics definitions
- predeclared subgroup definitions
- statistical unit / resampling method
- promotion criteria
- failure criteria
- data lineage manifest
- holdout date/session allocation

No result-driven change after holdout access.

## Statistical design

The independent unit for headline claims is the Entry event/trade. Because trades within the same session are correlated, also report session count and use a session-aware uncertainty method for paired deltas.

Preferred hierarchy:

- paired trade-level summaries for descriptive effect sizes;
- session-cluster/bootstrap confidence intervals for paired v4-v3 and v4-fixed deltas when enough sessions exist;
- block/session resampling for large historical samples;
- effective N / ICC where estimable.

Do not use naive row-level standard errors on repeated management states.

Do not precommit an arbitrary p-value gate solely because the reviewer suggested one. Economic effect size, uncertainty, stability, and paired downside behavior are primary; inferential tests are supporting evidence.

## Required subgroup diagnostics

Predeclare these before large-scale result inspection:

1. LONG / SHORT
2. Immediate adverse YES / NO
3. volatility regime using a frozen causal definition
4. time-of-day / session segment using exact JST boundaries
5. source/substrate tier
6. period chunking using a frozen calendar rule

Evaluation-only path groups such as MAE-before-MFE or MFE-before-MAE may be reported to explain behavior, but may never become decision features or retroactive promotion filters in this frozen v4 study.

Additional symbol/sector/day-of-week slices are exploratory unless predeclared before outcome inspection. Multiple-testing/significance hunting is prohibited.

## Failure taxonomy

Use explicit paired taxonomy to distinguish early cuts from slow rescue without hindsight-perfect-price optimization:

- `EARLY_EXIT_CONTINUATION_WINNER`: v4 exits and a fixed predeclared post-exit horizon subsequently shows material favorable continuation; evaluation only.
- `GOOD_EARLY_RISK_EXIT`: v4 exits before a predeclared adverse continuation and avoids additional loss.
- `EXCESS_PROFIT_GIVEBACK`: causal running MFE existed before exit and a large share was surrendered by realized exit.
- `GOOD_WINNER_HOLD`: v4 remains open through ordinary adverse noise and later captures additional favorable return.
- `SLOW_LOSS_RESCUE`: deterioration persists before v4 exits and paired baseline indicates avoidable additional loss.
- `SESSION_END_FALLBACK`: no policy exit before canonical session-end handling.
- `NO_OBSERVATION_HOLD`: canonical sparse/no-finalized-bar hold.

Exact materiality thresholds, if any, must be frozen before the locked holdout and cannot be selected from holdout outcomes.

## Checkpoint protocol

### Checkpoint A — 200 independent Entry events

Primary purpose: **data/substrate validation and obvious failure detection**, not a final performance claim.

Required report:

- Entry events / sessions / symbols / LONG-SHORT
- substrate tiers
- parity / PIT / duplicate / missing-bar violations
- paired Fixed vs v3 vs v4 headline metrics
- immediate-adverse stratification
- exit timing distribution
- symbol concentration

Do not stop merely because one performance metric is below a reviewer-proposed arbitrary threshold. Stop if the data contract is invalid, pairing is broken, v4 implementation parity is broken, or a precommitted economic failure rule is triggered.

### Checkpoints B/C/D

B=500, C=1000+, D=2000+ if coverage permits. Expand only if data integrity remains acceptable. Track period-by-period and tier-by-tier stability rather than treating cumulative N as proof of generalization.

## Concentration and stability diagnostics

Report at minimum:

- Top 1 / Top 5 / Top 10 symbol contribution to total PnL
- session contribution concentration
- period-chunk paired deltas
- LONG and SHORT separately
- v4 exit-bar distribution
- giveback by EXIT reason/state
- immediate-adverse path behavior

Any concentration threshold used as a formal failure gate must be justified and frozen before holdout.

## Promotion rule

A favorable large historical result does not change main and does not promote v4 automatically.

Any eventual Main EXIT decision requires separately governed OOS/prospective evidence and explicit approval.

Reviewer-suggested values such as `PF>=1.30`, `WinRate>=58%`, `MFE Capture>=60%`, `PF delta<0.15`, `MaxDD<15%`, or `p<0.05` are **not adopted automatically**. They are hypotheses for a later promotion-contract design, not facts established by the current source material.

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

1. Resolve the Stage 0 J-Quants blockers recorded in `phase57-exit-v4-jquants-data-capacity-audit.md`; the audit is complete but conditional and stopped before outcomes.
2. Run only a separately authorized, predeclared Stage 1 quality/parity pilot; do not bulk-fetch or open outcomes.
3. Complete Mandatory pre-condition B: substrate-tier classifier and counts without opening protected/fresh OOS.
4. Freeze a result-blind data allocation contract, then freeze the historical replay/parity contract and paired evaluator.
5. Verify overlap parity on golden sessions.
6. Reach Checkpoint A: 200 independent Entry events only after explicit Development unlock.
7. Ask for independent post-Checkpoint-A review before expanding to 500.
8. Only after stress work is complete, write and hash Mandatory pre-condition C before any locked holdout access.

Until those gates are complete, EXIT v4 remains a frozen candidate under large-scale historical evaluation, not a proven Main EXIT.
