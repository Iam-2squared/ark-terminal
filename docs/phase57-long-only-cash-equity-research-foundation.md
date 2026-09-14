# Phase57 LONG-only Cash Equity — Research Foundation

## HEAD

| Field | Value |
|---|---|
| Branch | `research/phase57-long-only-cash-equity` |
| Phase | L0 Opportunity Census design |
| Current Task | Contract, data inventory, minimum acquisition plan |
| Data Block | No new J-Quants download authorized |
| Status | DEVELOPMENT / FORMAL L0 BLOCKED ON INPUT DATA |

## Conclusion

This branch is a separate cash-equity LONG-only research lane. It does not switch SHORT off inside the existing selector. It establishes a new objective: discover JPX names with material remaining upside before the move is exhausted. Existing LONG+SHORT research, Lane Y, `main`, and live-trading circuitry remain unchanged.

The repository does not currently contain a formal long-history, point-in-time JPX-wide daily-price artifact suitable for L0. Existing market-wide artifacts are valuable for later causal intraday work, but cover only a small recent session set and cannot support a multi-regime Opportunity Census. No J-Quants price request was made during this audit.

## Frozen research contract

| Capability | Contract |
|---|---|
| Cash-equity LONG | Allowed |
| Margin buy | Prohibited |
| Short sell / margin sell | Prohibited |
| SHORT Entry / position | Prohibited |
| Leverage | Prohibited |
| Quantity | Positive integer, default 100-share lot |
| Buying power | Current available cash only |
| Cash lifecycle | Lock on Entry, release on EXIT, causal reuse allowed |
| Order transmission | Prohibited during research |

## Existing data inventory

Inventory was made from repository and dedicated data branches at their audited heads. Counts are descriptive and do not open outcomes from reserved OOS/Fresh partitions.

| Asset | Audited coverage | Approx. payload | L0 use |
|---|---:|---:|---|
| `automation/p25-marketwide-5m-data` | 10 dated sessions, 2026-09-01 to 2026-09-14 | 28.0 MB | Insufficient: short recent window; scanner snapshots are not official adjusted daily closes |
| `automation/p25-day-data` | 9 sessions, 2026-08-19 to 2026-09-03 | 8.0 MB | Insufficient: selected research sessions, not a full JPX census |
| `automation/p25-dynamic5m-day-data` | 2 sessions | 2.3 MB | Insufficient |
| `automation/phase57-realtime-live-data` | 9 dated sessions, 2026-09-03 to 2026-09-14 | 114.0 MB | Reusable later for causal pipeline tests; insufficient for historical L0 |
| `data/screener-universe.json` | Current/rolling universe snapshot | 0.9 MB | Universe plumbing only; not historical membership truth |
| PR101 historical foundation | Pipeline contracts and normalization scaffolding | Code only | Reusable infrastructure, but not a J-Quants daily-price downloader or formal L0 dataset |
| J-Quants implementation on main | TDnet disclosure provider | Code only | Not a daily OHLCV pipeline |

## L0 minimum data contract

L0 uses daily bars only. It must not spend intraday quota or build a model.

Required row key: `sessionDate + symbol`. Required fields are adjusted close, adjusted previous close, and point-in-time market segment. The daily return is frozen as:

`100 × (adjustedClose / adjustedPreviousClose − 1)`

The initial visible run may consume only `DEVELOPMENT`. Validation, Untouched OOS, and Final Confirmation/Fresh remain sealed. The concrete date boundaries must be written to an immutable manifest after the user's J-Quants entitlement and available date range are confirmed, before downloading prices or inspecting outcomes.

### Minimum proposed acquisition block

| Item | Minimum request | Why | Existing substitute |
|---|---|---|---|
| JPX daily adjusted quotes | 252 consecutive trading sessions × all available domestic common equities | One full trading year is the minimum useful L0 seasonal census; daily data is sufficient for +3/+5/+10 counts | None found |
| Point-in-time listing/segment identity | Same 252 sessions, or a versioned listing-event reconstruction covering the block | Prevent survivorship and Prime/Standard/Growth misclassification | Current screener master is not point-in-time history |
| Market regime reference | TOPIX daily series for the same sessions | Optional predeclared regime breakdown | Can be omitted from L0 v1 rather than inferred from future data |

This is a lower bound, not permission to fetch. Before acquisition, record the exact first/last session, expected rows, endpoint pagination, entitlement-visible history, and cache destination. If J-Quants can return all-market rows by session date, request each session once and cache raw immutable responses. Never request the same session again when source identity, session date, checksum, and timestamp contract match.

## Partition policy

| Partition | Initial state | Permitted use |
|---|---|---|
| Development | Open | L0 measurement, hypothesis formation, later feature/threshold research |
| Validation | Sealed | Single predeclared candidate validation; no feature/threshold selection |
| Untouched OOS | Sealed | Open only after independent review and freeze |
| Final Confirmation / Fresh | Sealed | Final confirmation only; never recycle into tuning |

No threshold, feature, model, winner, symbol, market, or horizon may be chosen after inspecting outer OOS.

## L0 execution gate

Formal L0 is currently blocked. It becomes runnable only when all of these are true:

1. Exact date partitions are frozen and non-overlapping.
2. Raw source identity and checksum are recorded.
3. Point-in-time listing membership is available.
4. Adjusted close semantics are unambiguous.
5. Only Development is mounted into the first run.
6. Duplicate keys, invalid OHLC, missing sessions, and unexplained coverage drops fail closed.

## Claude independent review request — L0 design

Please independently review the following Ark Terminal Phase57 LONG-only Cash Equity L0 Opportunity Census design. Do not assume the Ark design is correct and do not optimize it for agreement. The purpose is to find reasons the design could produce a misleading picture of genuine LONG-only opportunity in Japanese equities.

### Objective

Measure how many JPX-listed domestic cash equities finish a session at least +3%, +5%, and +10%, before building any selector. Report mean, median, P25, P75, min, max, session distribution, and Prime/Standard/Growth breakdown. Market-regime breakdown is optional and must be predeclared.

### Frozen measurement

- Unit: symbol-session.
- Return: `100 × (adjustedClose / adjustedPreviousClose − 1)`.
- Required membership: point-in-time listed status and point-in-time Prime/Standard/Growth identity.
- Initial visible partition: Development only.
- Validation, Untouched OOS, and Final Confirmation/Fresh remain sealed.
- No model, Entry, EXIT, allocation, or portfolio result is used in L0.
- Bad sessions are retained or explicitly blocked; they are never silently deleted.
- Cached inputs are reused only when source identity, session date, symbol coverage, checksum, and timestamp contract match.
- No J-Quants price download begins until exact endpoints, date range, session count, expected row count, pagination, and entitlement are recorded.

### Current repository evidence

- Recent market-wide 5-minute scanner artifacts exist, but only for a small August–September 2026 session set.
- They are not treated as official adjusted daily-price history.
- A current/rolling JPX universe exists, but it is not treated as historical point-in-time membership.
- The current J-Quants provider is for TDnet disclosures, not daily OHLCV.
- Therefore formal L0 is blocked pending a minimal, planned daily-data acquisition.

### Review questions

1. Does the return definition introduce split, dividend, price-limit, special-quote, or previous-close ambiguity?
2. What exact security types should be included or excluded: common stock, REIT, ETF, ETN, preferred, foreign listings, PRO Market, newly listed, delisted, suspended?
3. What point-in-time membership source is necessary to avoid survivorship bias and segment-history errors?
4. Is 252 sessions enough for an initial Development census? If not, state the minimum defensible range and why, while respecting limited data budget.
5. Should no-trade, zero-volume, limit-up, IPO first-day, ex-rights, and corporate-action sessions be separate strata rather than excluded?
6. Can adjusted close and adjusted previous close be compared safely across corporate actions in J-Quants? Specify a safer alternative if needed.
7. Which coverage and missingness gates should block an entire session versus individual rows?
8. Does reporting counts alone confound changing listing counts? Should rates per eligible universe accompany counts?
9. How should Prime/Standard/Growth transitions be represented on the transition date?
10. Propose a predeclared regime definition that does not use future information or outcome-driven bin selection.
11. Identify any future leak, selection bias, survivorship bias, label leakage, or human OOS overfitting risk not covered above.
12. Give explicit falsification tests: what result would show that the presumed LONG-only opportunity set is too sparse, too late, too illiquid, or too regime-dependent to justify L1?

Please return: Critical blockers, Major concerns, Minor concerns, required contract changes, recommended minimal data block, and a final verdict of PASS / PASS WITH CHANGES / BLOCKED. Separate measured facts from hypotheses and do not propose Selector features yet unless they are necessary to expose an L0 measurement flaw.

