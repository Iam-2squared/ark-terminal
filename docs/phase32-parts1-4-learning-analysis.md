# Phase32 Parts1-4 — Learning Analysis Foundation

## Scope

Phase32 converts Shadow/Forward evaluation rows into review-only learning signals.

### Part1 — Failure classification

Classifies:

- data quality failures
- cost estimate failures
- liquidity failures
- direction misses
- loss threshold breaches
- high-confidence failures
- missed upside on NO_TRADE

### Part2 — Weakness analysis

Aggregates failure rate and net return by:

- market regime
- symbol
- sector

A segment is flagged only after the configured minimum sample count is met.

### Part3 — Confidence calibration

Groups predictions into confidence bins and compares average confidence with observed directional accuracy. Overconfidence and underconfidence are review signals only.

### Part4 — Improvement proposals

Produces human-review-only proposals for:

- thresholds/features
- confidence calibration
- recurring failure clusters

No patch, Candidate model, Production update, broker write, or live order is created.

## Safety contract

The module is locked to `LEARNING_ANALYSIS_ONLY`.

- `automaticCandidateCreationAllowed: false`
- `automaticPromotionAllowed: false`
- `productionUpdateAllowed: false`
- `brokerWriteAllowed: false`
- `liveTradingAllowed: false`
- order create/transmit/cancel/modify disabled
- human approval required
- broker writes: 0
- live orders: 0

The highest reachable state in this phase is `READY_FOR_HUMAN_REVIEW`.
