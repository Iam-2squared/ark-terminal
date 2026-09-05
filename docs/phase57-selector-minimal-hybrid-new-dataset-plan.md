# Phase57 Minimal Hybrid — new dataset readiness plan

## Decision

Do not extend or refetch the consumed Yahoo 60-day window. It is already hypothesis-generation evidence through 2026-09-04 and cannot become new Hybrid evidence under another filename or dataset ID.

The preferred practical historical source is the official J-Quants Minute Stock Prices add-on:

- endpoint: `GET /v2/equities/bars/minute`;
- raw data: one-minute OHLC, volume, and turnover for TSE-listed issues;
- historical depth: two years under the add-on;
- sparse rule: periods without trades are absent and must remain absent;
- update timing: daily after the close;
- authentication: `x-api-key`;
- rate limit: 60 requests per minute for the Stock Prices add-on.

J-Quants Listed Issue Master can provide historical issue/segment information and should be joined by session date. This removes the current-constituent reconstruction defect when the join is complete.

## Proposed unused period

Candidate acquisition window: 2025-01-06 through 2026-06-11, subject to a repository-wide consumed-dataset registry check before acquisition. The hard rule is not the proposed dates; it is zero overlap with any already-inspected Selector outcome dataset and zero ancestry from the consumed Yahoo pilot.

At least 120 admitted sessions are required. The intended split is chronological 60/20/20 with one entire purge session before Validation and before untouched OOS. Exact dates are computed only after coverage and point-in-time membership checks; individual cross-sections are never split.

## One-minute to five-minute contract

Aggregate within each JST regular-session segment using fixed non-overlapping bins:

- open: first observed one-minute open;
- high: maximum observed high;
- low: minimum observed low;
- close: last observed close;
- volume: sum of observed volume;
- turnover: sum of observed turnover;
- timestamp: five-minute bin open;
- availableAt: five-minute bin close.

Lunch cannot be bridged. Empty bins remain missing. Partial bins, duplicates with conflicting values, out-of-session rows, impossible OHLC order, negative volume/turnover, and non-monotone pagination fail closed.

## Readiness gates

1. Entitlement: the Minute-OHLC add-on and permitted research use are explicitly verified.
2. Authentication: `JQUANTS_API_KEY` exists in the execution environment; the key is never logged or committed.
3. Provenance: acquisition time, endpoint, query range, raw payload digests, parser version, aggregation version, and dataset digest are recorded.
4. Universe: historical Listed Issue Master membership is joined per session or evidence is downgraded to survivorship-limited.
5. Coverage: at least 120 sessions and the predefined minimum cross-section coverage pass without fabricated bars.
6. Contamination: dataset identity, ancestry, and every session pass the Phase A admission guard.
7. Release: only Development becomes visible. Validation and OOS require later frozen contracts.

## Current readiness

- Architecture and contamination boundary: ready and frozen.
- Dataset admission guard: implemented.
- Official source contract: identified.
- Entitlement/API key: not confirmed in this Work environment.
- J-Quants parser, pagination client, and sparse one-minute-to-five-minute aggregation: implemented and mock-tested.
- Historical payload acquisition: not started.
- Hybrid model training: correctly blocked until a new dataset is admitted.
