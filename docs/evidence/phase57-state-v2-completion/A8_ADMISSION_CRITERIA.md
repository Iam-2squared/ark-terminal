# A8 admission criteria — frozen-rule implementation, before recovered-row inspection

Recorded: 2026-09-22 JST. Recovery run: 35709025581. No recovered raw daily rows or action-factor outcomes have yet been inspected in this completion task.

## Distinguish the two temporal claims

1. Historical effective-date common-price-basis reconstruction: admissible only from original pinned unadjusted fields and dated corporate-action facts at or before the checkpoint's session.
2. Actual receipt/announcement latency: NOT proven by an effective date, by a provider update schedule, or by a later raw-cache hash. knownAt remains null if absent. All rows remain HISTORICAL_CLOSED_RECONSTRUCTION, not prospective parity.

These are separate claims. Frozen section 9.1 permits historical reconstruction; section 9.3 still requires the *price-basis as-of semantics* to be independently established. No general knownAt-null rejection and no fabricated receivedAt are introduced.

## Primary provider evidence reviewed

- J-Quants minute specification: https://jpx-jquants.com/ja/spec/eq-bars-minute — Time denotes the start of a one-minute JST interval; O/H/L/C are unadjusted; 11:30 and 15:30 auction records are separate from regular-minute intervals.
- J-Quants adjustment methodology: https://jpx-jquants.com/ja/spec/eq-bars-daily/adj — unadjusted O/H/L/C/Vo plus only ex-date factors effective by the historical as-of date are the documented way to reconstruct point-in-time prices. Adj* fields are retrospectively revised and must not be used here. AdjFactor on date d applies to dates strictly before d, not to d's already post-event raw prices. The documented covered actions include splits, consolidations and rights issues; it is not a total-return adjustment.
- Provider update schedule: https://jpx-jquants.com/ja/spec/data-update — daily/minute API responses are published after the session; the response time is not the historical event time, and no independent receivedAt may be inferred.

## Exact admission predicates (no fitting or price/outcome heuristics)

- Verify all source identities back to the pre-existing encrypted archive, original raw daily-page SHA, security code and date. Compare original lag OHLC/Vo/Va projections to the corresponding raw prior-day fields exactly. Current-day OHLC, volume, turnover and Adj* values may NOT be used in admission decisions or NOW features.
- For a raw prior-day quantity at day d to be compared with day D in the same unadjusted units, inspect the exact scheduled sessions (d,D]. Every required dated factor must be present, finite and exactly one. An action factor at d itself concerns earlier dates; however, preserve any pre-existing G admission rejection instead of reopening it opportunistically.
- A non-unit factor or unknown/incomplete factor chain means PRICE_BASIS_UNVERIFIED for that comparison. Do not adjust numerical Scale, convert prices, search alternatives, or use a discontinuity threshold. Preserve the actual action witness in admission evidence.
- Previous-session Scale and previous-observed levels require the (previousDay,D] chain. Each Daily lag has its own (lagDate,D] chain. Mask only unsupported primitives and their dependencies; valid same-day Direction/attributes/context remain available.
- Only effective-date fields Date/Code/AdjFactor and documented action-kind metadata enter the basis proof. No event dated after D is read. Those fields are historical event facts, not a claim of live API availability; record their date precision and missing knownAt explicitly. D's effective-date boundary is the session open, not an invented receivedAt.
- Calendar and the once-only start-to-end normalization are audited separately using official rules and predeclared raw witnesses. Missing witness clocks are disclosed without outcome-based replacement.

## Required disclosure

Acceptance, if earned, is for the frozen historical-reconstruction contract only. It does not certify prospectively received corporate-action announcements or tradeable latency. Store the supplemented source vintage, full admission receipt, raw-source hashes, all masked primitive identities and before/after coverage. Retain the original G limitations/history rather than rewriting earlier receipts. Future provider corrections require a new vintage. All frozen numerical rules and all 2,155 /77,214 identities remain unchanged.
