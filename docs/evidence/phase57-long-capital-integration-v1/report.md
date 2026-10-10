# Phase57 LONG-only Capital / Full Integration — Development Evidence

**CAPITAL_INTEGRATION_IMPLEMENTED_FULL277_MEASUREMENT_BLOCKED**. The event-time ledger and paired Allocation replay are implemented. Full277 final equity is UNKNOWN, not zero. No Allocation Development Final, Validation PASS, OOS PASS or Production Ready claim. EXIT is unchanged.

Source head `ba0ccdb2aea7e5fc9fee817c0bd95f09427108f8`; branch `research/phase57-long-only-cash-equity`, PR #587. Historical76 sessions / Frozen277 ENTER only. All data are Development, IN-SAMPLE, outcome-exposed. No provider requests, Fresh consumption or OOS access; Fresh195 remains untouched. This work does not reopen or consume Validation20.

## Lineage and frozen comparison

Latest existing allocation is **V3_B_RISK × MAX_3**, not Adaptive v2. The latest freeze is on `84b296102b85ab2909385a8f3ee7ef336c9b6129`, separate from the LONG-only branch. Its old MSH probability/features and risk window cannot silently be substituted with LONG E[L]. Exact V3 equal/rank arithmetic and contract files are imported verbatim; the old Entry builder, old EXIT adapters and risk scorer are not run. `phase57-long-only-session-allocation-v3.json` allocates data sessions, not money. See lineage-audit.json.

Three fixed arms: ONE_LOT_REFERENCE (one100-share lot per accepted Entry), EQUAL_MAX3 (equal simultaneous budgets), LONG_RANK_MAX3 (new LONG E[L] ordinal-rank adaptation). Budget divisor3 and maximum10 positions come from the latest lineage; no divisor search. V3_B_RISK remains INPUT_NOT_AVAILABLE on this post-entry-only bundle, not an equal fallback.

Initial cash ¥1,000,000;100-share lots; LONG/cash only. Same Entry identities/timestamps/prices, frozen LONG EXIT, costs, event ordering and missing rules in every primary arm. The sole extra Fixed12 arm uses Equal/MAX3 on the same pre-existing173 diagnostic identities. It is an EXIT transmission reference, not a reselection.

## Accounting and causal semantics

Completed-bar observation → unchanged EXIT state update → reference sale/cash release → simultaneous Entry sizing snapshot → symbol/eventId-ordered cash-constrained purchases → exact observed MTM. Timestamp formats are normalized before ordering. Entry allocator accepts only eventId/timestamp/symbol/frozen score, never EXIT results/MFE/MAE. Future bars reach the EXIT one completed bar at a time. Target and cash quantities are separately rounded down to100 shares. No unused-budget redistribution.

Cash cannot go negative; open positions cannot exceed10; quantity is in100-share lots. Cash + purchase notional of open positions = initial cash + ledger-realized PnL. Fees are0.025% of Entry notional at each side, exactly0.05% total, preserving the frozen EXIT reference-cost convention. This is not a broker-specific fee model. Unrealized gains never become available cash. Closed-trade net and realized ledger balance are reconciled separately to avoid double-charging Entry cost.

Missing expected bar before EXIT permanently censors that position; quantity and purchase capital remain locked. Later bars cannot resurrect/price it or invent a sale. Current-equity sizing then rejects CURRENT_EQUITY_UNKNOWN. One-lot sizing may still spend actual remaining cash; it eventually accumulates unresolved positions. Calendar-known zero-remaining-bar Entries are rejected without inventing positions. Unknown holdings are accounting liabilities, not a decision to carry an overnight trade.

**Fill limitation:** Entry decision-price and EXIT same-completed-close prices are research reference marks, not guaranteed fills. No spread, latency, queue, participation/volume constraint or slippage is proved. DD is sampled observed-close portfolio MTM, not intrabar worst-case DD. Thin/low-price names and large share quantities are especially exposed. No forward fill, interpolation, future substitution or auction repair.

## Primary: all277 ENTER, no future-completeness filtering

| Arm | Candidates | Accepted | Closed | Unresolved | Cash JPY | Locked purchase JPY | Final equity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ONE_LOT_REFERENCE | 277.00 | 45.00 | 35.00 | 10.00 | 5,747.65 | 992,400.00 | UNKNOWN |
| EQUAL_MAX3 | 277.00 | 1.00 | 0.00 | 1.00 | 667,416.88 | 332,500.00 | UNKNOWN |
| LONG_RANK_MAX3 | 277.00 | 1.00 | 0.00 | 1.00 | 667,416.88 | 332,500.00 | UNKNOWN |

First unknown valuation: **2024-09-17T13:15:00+09:00**. Symbol17570 entered13:00 on2024-09-17, with missing slot3 before its frozen EXIT. Equal/rank accepted it causally and retain ¥332,500.00 purchase capital. Thereafter256 equity-based Entry attempts cannot be sized;20 have no remaining regular bar. They are not silently deleted from the277. Full return, full MaxDD and full utilization remain NULL. Closed-only one-lot PF is not full portfolio PF.

Source frozen EXIT availability by reason: `{"EXIT_REFERENCE": 192, "MISSING_BEFORE_EXIT": 65, "NO_REMAINING_REGULAR_BAR": 20}`. A missing expected bucket may represent no trading or missing observations; that distinction has not been repaired or assumed here.

| Arm | Rejected reason | Count |
| --- | --- | --- |
| ONE_LOT_REFERENCE | NO_REMAINING_REGULAR_BAR | 20.00 |
| ONE_LOT_REFERENCE | SYMBOL_ALREADY_OPEN | 24.00 |
| ONE_LOT_REFERENCE | INSUFFICIENT_CASH | 44.00 |
| ONE_LOT_REFERENCE | MAX_CONCURRENT_POSITIONS | 144.00 |
| EQUAL_MAX3 | NO_REMAINING_REGULAR_BAR | 20.00 |
| EQUAL_MAX3 | CURRENT_EQUITY_UNKNOWN | 256.00 |
| LONG_RANK_MAX3 | NO_REMAINING_REGULAR_BAR | 20.00 |
| LONG_RANK_MAX3 | CURRENT_EQUITY_UNKNOWN | 256.00 |

## Secondary ONLY: pre-existing173 common identities

**Not the result of the full277 strategy.** This previously outcome-exposed complete-case subset excludes104 identities using future-path availability inherited from EXIT Development. It is fixed before Allocation replay but not a deployable filter. All arms use the exact same173 and all76 session dates, including empty sessions. No new session replacement or exclusion is performed. Informative missingness can materially bias results.

| Arm | Final JPY | Return % | MTM MaxDD % | MaxDD JPY | Closed | PF | Win rate % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ONE_LOT_REFERENCE | 978,315.38 | -2.17 | 12.21 | 124,990.75 | 173.00 | 0.90 | 45.09 |
| EQUAL_MAX3 | 1,230,530.70 | 23.05 | 20.17 | 258,413.10 | 166.00 | 1.28 | 45.18 |
| LONG_RANK_MAX3 | 1,215,413.40 | 21.54 | 22.09 | 284,990.38 | 167.00 | 1.24 | 44.91 |

| Arm | Mean/median trade JPY | Worst session % | Session p05 % | Loss streak | Largest loss JPY | Net <=-10% |
| --- | --- | --- | --- | --- | --- | --- |
| ONE_LOT_REFERENCE | -125.34 / -0.40 | -4.86 | -1.45 | 4.00 | -49,309.00 | 4.00 |
| EQUAL_MAX3 | 1,388.74 / -185.57 | -8.00 | -2.86 | 4.00 | -87,385.30 | 4.00 |
| LONG_RANK_MAX3 | 1,289.90 / -192.80 | -10.62 | -2.90 | 3.00 | -117,849.90 | 4.00 |

| Arm | Avg utilization % | Peak % | Idle cash % | Turnover JPY | Cash releases | Same-time recycled Entries | Max/avg positions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ONE_LOT_REFERENCE | 1.79 | 82.83 | 98.21 | 25,123,100.00 | 173.00 | 7.00 | 4 / 0.27 |
| EQUAL_MAX3 | 8.26 | 97.35 | 91.74 | 116,136,700.00 | 166.00 | 5.00 | 3 / 0.26 |
| LONG_RANK_MAX3 | 8.41 | 99.84 | 91.59 | 117,791,200.00 | 167.00 | 5.00 | 4 / 0.26 |

Utilization is trading-time weighted over all76 sessions, including flat time; lunch and overnight are excluded. Mean low deployment and near-full peak deployment are both visible. Cash-release count does not mean every released yen was subsequently redeployed. Same-timestamp recycling is counted separately.

| Arm | Positive trade Top1/3/5 shares | Positive symbol Top1/3/5 shares | Symbol notional HHI | Position-size HHI |
| --- | --- | --- | --- | --- |
| ONE_LOT_REFERENCE | 0.1572 / 0.4487 / 0.5565 | 0.1727 / 0.4929 / 0.5940 | 0.02 | 0.02 |
| EQUAL_MAX3 | 0.0843 / 0.1855 / 0.2813 | 0.3782 / 0.5358 / 0.6200 | 0.03 | 0.01 |
| LONG_RANK_MAX3 | 0.0814 / 0.1946 / 0.2871 | 0.3742 / 0.5280 / 0.6108 | 0.04 | 0.01 |

Top shares use positive-profit sums, never a misleading net denominator. Full symbol/session PnL, HHI, all session returns, exit-reason performance, rejected opportunity outcomes and every cash/position decision are in summary.json and measurement.json.gz.

Equal/MAX3 net ¥230,530.70 includes symbol89180 contribution ¥334,449.55. Subtracting that accounting contribution gives ¥-103,918.85. This is NOT a leave-symbol-out cash replay and is not used to make a symbol exception. The positive result is materially concentrated.

## Fixed EXIT transmission reference — same Equal/MAX3 and173

| EXIT | Final JPY | Return % | PF | MaxDD % | Avg utilization % | Accepted |
| --- | --- | --- | --- | --- | --- | --- |
| FIXED12 | 1,220,585.60 | 22.06 | 1.21 | 21.37 | 12.68 | 166.00 |
| FROZEN_LONG_EXIT | 1,230,530.70 | 23.05 | 1.28 | 20.17 | 8.26 | 166.00 |

Frozen LONG EXIT improves this reference final balance by ¥9,945.10. Lower holding time lowers average deployment. This is a Management × Allocation interaction, not proof that EXIT is solved or the causal largest bottleneck. EXIT code/rules were not changed.

## Bottleneck attribution and decision

1. **Data coverage first:** all277 portfolio value is unidentifiable under the unchanged missing rules. Do not present173 returns as277 or delete unresolved cash exposure.
2. **Execution/price semantics:** no executable fill or volume capacity proof; sparse and low-price paths can dominate.
3. **Concentration/tail:** secondary Equal MaxDD20.17%; one-symbol contribution exceeds aggregate net.
4. **Cash utilization:**8.26% mean but97.35% peak; increasing nominal sizing blindly is unsupported.
5. **Concurrency/lot:** Equal has0 position-limit rejects,6 below-lot and1 cash reject; concurrency10 is not the main observed173 constraint. Rejected outcomes are evaluator-only.
6. **Allocation:** rank is lower-return/higher-DD than simple equal in this limited sample; no reason to prefer complexity.
7. **Selector/Entry/EXIT:** frozen and not marginally identifiable here; no retuning or EXIT v2 initiation.

**No Capital Allocation Development Final is selected.** Keep Equal/MAX3 as the comparison reference, not a proven winner. The next concrete task is to audit existing archived Development minute checkpoints for missing/no-trade versus cache gaps, and recover an exact causal7-close risk window if available without any new provider/Fresh/OOS access. A separately frozen executable-fill/latency/liquidity and unresolved-position contract is needed before truthful full portfolio claims. Do not invent missing prices to force completion.

Existing-Ark fair-comparison architecture can reuse the sanitized Entry envelopes, frozen EXIT callbacks and common ledger. Actual Existing-Ark same-window replay has NOT been performed. Current legacy evidence uses different periods/Entry/EXIT and is not a fair performance comparator. Validation20 remains protected, not consumed for this Development tuning.

## Evidence / verification

Contract and candidate family were written locally before the first Allocation replay; they are published with results, not separately timestamped remote preregistration. No parameter sweep, post-result policy change, independent Claude review or winner promotion. Engineering fixes/tests do not alter frozen upstream. Fresh/OOS access0; Safety all9 false; no main merge.

The17 existing EXIT/upstream tests are preserved, alongside new cash-ledger/causality/reproduction tests. Final publishing-head CI is recorded by GitHub, not assumed by this report. Compressed evidence expands byte-for-byte to the original measurement; publication manifest records its raw/compressed hashes.
