# Phase57 Capital Allocation Ledger Audit and Candidate Freeze

Status: **DEVELOPMENT_PRIMARY_CANDIDATE_FROZEN / VALIDATION_READY**

## Ledger verdict

Ledger audit: **LEDGER_AUDIT_PASS_NO_HIDDEN_LEVERAGE**. Hidden leverage found: **false**. Exposure is tested against current mark-to-market equity at every timestamp, not against the original JPY 1,000,000.

Under the inherited ledger contract, the cash-funded entry reference notional is itself the locked collateral; it is not a second additional charge. Required entry cash is reference notional plus the entry half-cost. SHORT sale proceeds are credited as JPY 0 and cannot increase buying power.

| Event | Timestamp | Current equity | Cash | Locked SHORT collateral | Gross | Signed net | Gross/equity | Abs net/equity | Positions |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MAX gross / max utilization | 2026-08-07T04:25:00.000Z | ¥1,300,690.05 | ¥40,240.05 | ¥932,200 | ¥1,213,950 | ¥-603,950 | 93.3312% | 46.4330% | 4 |
| MAX abs net | 2026-08-06T05:05:00.000Z | ¥1,313,824.4375 | ¥140,824.4375 | ¥1,144,350 | ¥1,115,700 | ¥-1,115,700 | 84.9200% | 84.9200% | 3 |

MAX gross exceeds initial capital by JPY 213,950, but remains JPY 86,740.05 below current equity. MAX abs net exceeds initial capital by JPY 115,700, but remains JPY 198,124.4375 below current equity.

## Worst day trace: 2026-07-24

Worst-day return -2.549371%. The complete all-timestamp trace is in JSON; transaction timestamps are shown below.

| Timestamp | Realized equity | Current equity | Available cash | Locked SHORT | LONG notional | SHORT notional | EXIT released | ENTRY consumed | Fees | Positions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-07-24T01:30:00.000Z | ¥1,235,115.75 | ¥1,235,115.75 | ¥847,115.75 | ¥388,000 | ¥0 | ¥388,000 | ¥0 | ¥388,097 | ¥97 | 1 |
| 2026-07-24T01:35:00.000Z | ¥1,235,029.05 | ¥1,232,029.05 | ¥500,229.05 | ¥734,800 | ¥0 | ¥737,800 | ¥0 | ¥346,886.7 | ¥86.7 | 2 |
| 2026-07-24T02:00:00.000Z | ¥1,207,042.35 | ¥1,204,042.35 | ¥819,042.35 | ¥388,000 | ¥0 | ¥391,000 | ¥318,813.3 | ¥0 | ¥86.7 | 1 |
| 2026-07-24T05:30:00.000Z | ¥1,206,980.975 | ¥1,213,980.975 | ¥573,480.975 | ¥633,500 | ¥0 | ¥626,500 | ¥0 | ¥245,561.375 | ¥61.375 | 2 |
| 2026-07-24T05:40:00.000Z | ¥1,204,819.6 | ¥1,203,819.6 | ¥816,819.6 | ¥388,000 | ¥0 | ¥389,000 | ¥243,338.625 | ¥0 | ¥61.375 | 1 |
| 2026-07-24T05:45:00.000Z | ¥1,203,722.6 | ¥1,203,722.6 | ¥1,203,722.6 | ¥0 | ¥0 | ¥0 | ¥386,903 | ¥0 | ¥97 | 0 |

## Twelve invariant gate

All 12 invariants pass across 14820 audited arm-timestamps. This includes nonnegative cash, non-reused SHORT proceeds, buying power excluding unrealized gains, full SHORT reference-notional collateral, EXIT-before-ENTRY, current-equity exposure limits, one round-trip cost, position/lot constraints, and realized-equity reconciliation.

## Development roles frozen

- MAX_5: PRIMARY_DEVELOPMENT_CANDIDATE
- MAX_10: LEGACY_BUDGET_BASELINE
- MAX_3: AGGRESSIVE_DEVELOPMENT_REFERENCE
- Integrated primary: Frozen Minimal Hybrid v1 x MSH-Entry v1 x V3_B_RISK x MAX_5 x EXIT_V5_DYNAMIC_RECLAIM_BAR_5

MAX_5 to MAX_3 adds 14 trades contributing only JPY 36.975 directly (JPY 2.641071 per trade). The previously inferred JPY 15,470.275 is not the direct 14-trade effect: JPY 15,433.3 comes from larger quantities on 21 trades already accepted by MAX_5. This corrected decomposition is recorded as diminishing marginal edge, not a new selection threshold.

## Validation preparation

Validation runner and output schema are ready but locked. No fresh/OOS source was opened or measured. A separate hash-bound authorization contract is required before execution.

This is not OOS PASS, VALIDATION PASS, FINAL PASS or Production Ready. Main merge, Ready conversion, auto-merge, execution and paper/live orders remain prohibited.
