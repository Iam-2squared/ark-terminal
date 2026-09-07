# Phase57 J-Quants timestamp gate — blocked, not a completed Pilot

Status: `BLOCKED_TIMESTAMP_CONTRACT_UNRESOLVED`.

The bounded edge probe disproves the previous **uniform BAR_END** hypothesis. It does not yet establish the complete minute/auction reconstruction contract. No timestamp shift, adapter change, five-minute reconstruction, formal acquisition, fitting, or Validation benchmark was performed.

## Real source-only observations

[Actions run 34028131686](https://github.com/Iam-2squared/ark-terminal/actions/runs/34028131686), job `101472666044`, code commit `df677bf8e92832eec4410e5b7c7e97db0e2bf1e6`.

Scope: 2025-01-08 and 2025-01-09; two symbols; four HTTP 200 requests; 1,305 rows. Pagination terminated normally. Invalid OHLC/volume/turnover, duplicate/conflicting rows, query mismatches, and interior-lunch rows: zero. Only structural summaries were retained; no raw price rows, API key, headers, pagination tokens, or response error bodies were emitted.

| Source Time | Groups with row, out of 4 | Groups with H != L | Interpretation |
| --- | ---: | ---: | --- |
| 09:00 | 4 | 4 | Contradicts a universal end-labelled minute before session opening |
| 09:01 | 4 | 4 | Observed; not alone decisive |
| 11:29 | 4 | 4 | Observed continuous-session row |
| 11:30 | 4 | 0 | Terminal single-price row; not automatically lunch contamination |
| 12:30 | 4 | 4 | Also contradicts universal BAR_END |
| 12:31 | 4 | 4 | Observed; not alone decisive |
| 15:24 | 4 | 4 | Observed continuous-session row |
| 15:25 | 0 | 0 | Absent; no synthetic row inserted |
| 15:29 | 0 | 0 | Absent; no synthetic row inserted |
| 15:30 | 4 | 0 | Terminal single-price row |

These observations are consistent with start-labelled continuous minutes and separate closing-auction events. That is a candidate interpretation, not an authoritative interval/auction contract. Globally subtracting one minute would move opening-minute information before the market opens.

The earlier failure evidence remains immutable. Its BAR_END suggestion is superseded, not silently rewritten. Its original lunch counter covered a time range rather than directly proving exact source timestamps; this new probe reports each edge explicitly.

## Official contract and unresolved items

The [official Minute API specification](https://jpx-jquants.com/ja/spec/eq-bars-minute) describes one-minute tick aggregation, omits no-trade intervals, and includes a non-flat 09:00 example. It only defines Time's format; it does not explicitly define interval closure, closing-auction bin membership, or minute corporate-action adjustment basis.

[JPX trading rules](https://www.jpx.co.jp/english/equities/trading/domestic/04.html) describe opening/closing call auctions and the 15:25–15:30 no-trade pre-close. This explains why closing rows cannot be classified as lunch merely from their timestamp, but is not the provider's aggregation contract.

[Provider update timing](https://jpx-jquants.com/en/spec/data-update) places minute/tick publication around 16:30 JST daily. Market information cutoff, reconstructed bar availability, actual provider availability, and fetch time must therefore remain separate. A later-fetched research reconstruction must not claim the Minute endpoint supplied bars intraday or claim exact PIT replay.

Required before adapter normalization: authoritative interval/auction confirmation, or a bounded tick-to-minute reconciliation on quarantined data; explicit timestamp timezone and corporate-action basis. Absence alone cannot distinguish no trades, a halt, and missing observations without additional source evidence.

## Integrity changes made

- Permanent source-only registry now rejects Jan 6/7/8/9 from admission and direct split planning, irrespective of filename/provider/dataset ID.
- Admission rejects zero-bar datasets/sessions, empty symbol rows, and missing/nonfinite/nonpositive turnover; it does not fabricate sparse bars.
- Legacy probe no longer equates timestamp format/column names with semantic PASS; empty HTTP 200 is not a PASS.
- New probe is bounded to eight requests maximum, stops on HTTP/auth/rate-limit/integrity failure, and cannot release any research split.
- Actions use the same-repository research branch, no persistent checkout credential, and only the request step receives the API key. Evidence-only commits do not re-fetch source data.

The first new CI attempt skipped API execution because `rg` was unavailable on its runner. The follow-up removes that dependency; only the run linked above produced the new live observations. CI success means the audit ran correctly, **not** that the source gate passed.

## Downstream state

| Item | State |
| --- | --- |
| Pilot semantic PASS | No — unresolved contract |
| Formal dataset/allocation/manifest | Not created |
| Development fitting and Hybrid freeze | Not run; no new model SHA |
| Validation comparison/leader | Not run / none |
| Untouched OOS | SEALED, not accessed or allocated |
| Reserve | Unallocated and unanalyzed; remaining session count UNKNOWN |

Exact 72/24/24 means 120 usable sessions **plus** at least two additional whole-session purges. The existing percentage splitter does not yield those exact counts; an explicit allocation contract is required after Pilot PASS. No Phase A bytes or split algorithm were changed here.

Main, Lane Y, V1/V2/Frozen V3.0, Entry/EXIT/Allocation, production workflows, realtime state and prior durable evidence remain unchanged. PR #577 remains Draft. All nine safety flags remain false. No winner or readiness claim is made.

Evidence: `predict/research/phase57-selector-jquants-timestamp-audit-2026-09-06.json`.

SHA-256: `7c973fbf5f08175ebc75a1fc03d0217dfa28150ce2319f3510725113dd92e541`.
