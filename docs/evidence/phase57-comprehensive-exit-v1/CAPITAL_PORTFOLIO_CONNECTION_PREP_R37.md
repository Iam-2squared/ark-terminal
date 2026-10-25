# Phase57 — Capital / Portfolio connection preparation R37

Date: 2026-09-26 JST  
Basis remote HEAD while prepared locally: `a10b3f25f79f8221c9a71c1b3ede245777bce058`  
Status: **INTERFACE_AND_SYNTHETIC_TESTS_ONLY; NO PORTFOLIO PERFORMANCE**

## Current state

The one-shot finite EXIT R36 workflow is the controlling critical path. This
checkpoint implements only work that is independent of which EXIT result, if
any, is selected. It does not attach a provisional EXIT to historical Entries
and does not calculate MAX3/MAX4/MAX5 performance.

## Implemented connection

`scripts/phase57_cash_portfolio_r37.py` wraps the already-tested R34 `CashBook`
with the exact R35 sizing rule. At an event timestamp it atomically applies:

1. confirmed EXIT fills release cash and capacity;
2. unconfirmed/unresolved EXITs release neither;
3. every remaining position must have a fresh exact-NOW mark;
4. portfolio equity is cash plus those fresh marked values;
5. target slot budget is equity divided by MAX_N;
6. simultaneous eligible Entries are ordered by `newEligibleRank ASC`, then
   `savedV1Score DESC`, symbol and Entry ID;
7. each quantity is the largest 100-share lot within both target slot budget and
   currently available cash.

Missing/stale marks make all new sizing at that timestamp unresolved. Cost or a
stale quote is never substituted. Unrealized value changes equity/target but
never spendable cash. The strict sizing-intent allowlist contains no future High,
bucket, EXIT outcome, PnL or capture field.

The module also supplies post-Freeze-only portfolio score and evaluator bucket
attribution interfaces. Both require an explicit SELECT candidate and 40-character
EXIT Freeze commit. `NO_SELECTION_STOP` cannot call them. The >=5% helper is
post-hoc evaluator-only and records that it is not fed back to ranking/sizing.
Canonical JSON hashing supports a later independent Portfolio Run A/B check.

## Focused verification

Ten new synthetic tests cover MAX3/4/5 sizing, confirmed cash release order,
missing fresh marks, unresolved EXIT ownership, future/outcome-field rejection,
rejected-intent non-reentry, SELECT-only score boundary, evaluator-only >=5%
attribution, portfolio equity/exposure alignment and Run A/B mismatch. Together
with the 25 R34 tests, 35/35 pass locally. No market data, provider,
candidate performance or protected partition is touched by these tests.

## Freeze, exposure and safety

Frozen Entries and the R25 finite EXIT search remain unchanged. This checkpoint
does not claim an EXIT Freeze or Portfolio result. Provider requests and protected
partition opens remain zero. MAX3 is primary; MAX4/MAX5 are the only sensitivity
capacities. LONG-only, CASH-only, 100-share lots, no borrowing/margin/leverage/
shorting and nonnegative cash remain enforced. Safety9 are false.

Next: wait for the sole R36 result. If it is `NO_SELECTION_STOP`, preserve this
adapter as tested preparation and prohibit historical Portfolio performance. If
it is SELECT, bind the frozen OOF ledger/model hashes, then run the same EXIT,
cost, rank and allocator for IMMEDIATE/R1 × MAX3/4/5 and no other variants.
