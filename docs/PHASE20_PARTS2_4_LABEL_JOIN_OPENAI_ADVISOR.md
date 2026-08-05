# Phase20 Parts2-4: Label Audit, Data Join Audit, OpenAI Learning Advisor

## Status

- Part2: prediction label and horizon audit — implemented
- Part3: symbol/date/price join audit — implemented
- Part4: OpenAI Learning Advisor — implemented as advisory-only API

## Why this bundle exists

Accuracy cannot be improved reliably while labels or joins are ambiguous. The previous walk-forward path sorted all rows by date and could evaluate a prediction against a row belonging to another symbol when mixed-symbol data was supplied. Non-directional decisions could also enter the same summary as BUY/SELL predictions.

This bundle fixes the deterministic audit layer before OpenAI is allowed to propose improvements.

## Part2: deterministic label policy

Directional Accuracy now uses only resolved BUY and SELL predictions.

Excluded from the Accuracy denominator:

- HOLD
- NO_TRADE
- UNKNOWN
- unresolved predictions

The evaluation target is close-to-close directional return. The horizon unit is explicitly `TRADING_SESSIONS`, not calendar days. A five-session horizon therefore means the fifth later valid daily row for the same symbol.

Every evaluated prediction records:

- label policy version
- horizon
- horizon unit
- predicted direction
- actual direction
- resolution status
- Accuracy eligibility
- trade-performance eligibility

## Part3: deterministic join policy

Rows are grouped by normalized symbol before any forward evaluation.

Join key:

- normalized symbol
- normalized trading date

Rules:

- cross-symbol fallback is prohibited
- calendar interpolation is prohibited
- each horizon is counted inside one symbol series
- duplicate symbol/date rows use the last input row
- invalid symbol, date, and close rows are excluded and counted in diagnostics
- explicit entry/exit symbol mismatch fails closed

The audit output includes source counts, normalized counts, invalid counts, duplicate counts, symbol counts, and per-symbol row counts.

## Part4: OpenAI Learning Advisor

Endpoint:

`POST /api/ai-learning-advisor`

The endpoint sends only bounded, deterministic audit information to OpenAI:

- audited metrics
- label and join policy versions
- data-quality diagnostics
- current model metrics and numeric weights
- resolved directional failure examples

It does not send pending outcomes as failures. It does not ask OpenAI to recalculate price returns, labels, Accuracy, or P&L.

The response may contain:

- data warnings
- failure patterns
- candidate hypothesis
- bounded weight-change suggestions
- threshold-change suggestions
- exclusion-rule suggestions
- validation plan

## Safety boundary

OpenAI is an advisor, not the production model controller.

The response contract requires:

- `advisoryOnly: true`
- `humanApprovalRequired: true`
- `productionUpdateAllowed: false`
- `brokerWriteAllowed: false`

The same contract is checked again after parsing. Any response that grants production or broker-write permission is rejected.

OpenAI cannot:

- change the Production model
- create or approve a Candidate automatically
- alter deterministic labels
- bypass Out-of-sample Walk-forward validation
- bypass future-leak checks
- submit, cancel, or modify real brokerage orders

The connected real brokerage account remains read-only.

## Next bundle

Phase20 Parts5-6 should convert an accepted advisory hypothesis into a bounded Candidate draft, run deterministic Out-of-sample Walk-forward comparison, and leave final promotion behind explicit human approval. No live-trading permission should be added.
