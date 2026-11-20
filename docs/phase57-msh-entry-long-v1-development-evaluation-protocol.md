# First Development evaluation protocol (declared before Project fit)

The frozen Fit Contract SHA is `64c20d785be5f23b0a9103f419726b191a12a58fd5d3a7ad5185c69f9644a938`.
No change to that contract, its model implementation, Selector, or CURRENT Entry is allowed.

- Use only the three saved Development ledgers pinned by SHA in the runner.
- Verify all 76 sessions / 3,800 events / 1,828 labels and all four pre-fit gates before any fit.
- Fit exactly four fresh model objects, using only each chronological training prefix.
  No final 76-session refit is performed in this task. Do not retry or tune on failure.
- OOF predictions exist only for labelable events in sessions 17–76. Excluded events remain
  in a ledger with a reason. Evaluation labelability is hindsight ascertainment, not a
  deployable availability gate. Coverage conditional on this subset is NOT live coverage.
- Preserve the actual frozen selection schedule (10 decisions/day, 30-minute spacing,
  with lunch recess). Do not synthesize five-minute reselections.
- Event-level threshold qualification is reported separately from one first ENTER per
  symbol-session. Repeated events are correlated, never independent trades.
- Within the labelable OOF pool, each symbol-session's first eligible decision is its
  baseline. For every threshold, take the first qualifying later eligible decision only.
- HIGH and CLOSE are separate strict 30m metrics. Precision uses the entry event's own
  Decision Price and future window. At that event, selector and new-entry reference coincide;
  no fill, spread, cost, execution delay or profitability claim is implied.
- Opportunity admission preservation = first-eligible baseline winners eventually admitted /
  all first-eligible baseline winners. This alone does not prove a winner was retained.
  Also report admission before the first window ends and baseline-winner plus entry-time
  remaining-opportunity intersection separately. No later window is substituted for the first.
- Report latency/consumed return from both first eligible selection and first original
  selection. Same-event decision latency and consumed return are zero by reference semantics,
  not measured live execution latency.
- Reuse session-horizon MFE/true MAE from the unchanged transfer ledger as separate diagnostics.
  Strict 30m MFE = max(0, saved HIGH return). Strict 30m true MAE is unavailable in these
  ledgers and MUST NOT be replaced by session MAE or fabricated.
- Baseline A: paired Selector-only on identical OOF events, and first-eligible symbol-sessions.
- Baseline B: unchanged cached CURRENT Entry state. On the exact OOF event pool, a current
  first PASS is comparable at 30m only if its timestamp and reference price equal that
  saved event. ALREADY_ENTERED is not a new PASS. Other current PASS timings are explicitly
  unmatched, not negative outcomes. Separately compare actual cached first PASS on identical
  symbol-session pools using saved session-horizon outcomes. Also report all 60 OOF sessions.
- All thresholds 1/2/3 must be reported, with equal-threshold geometric balance from the
  frozen contract. No extra threshold, feature, fold, lambda or solver choice.
- Rank by the frozen balance metric only descriptively. A balance leader is not automatically
  selected if quality/stability/paired-evidence requirements are not met. If no candidate
  clearly satisfies the qualitative gates, select none and report BORDERLINE/FAIL/INCONCLUSIVE
  as justified. Do not invent post-result numeric materiality gates.
- Chronological Entry OOF is not independent validation of the upstream Selector: Selector
  was already developed/frozen using this outcome-exposed Development set.
- Validation/OOS/EXIT access and market-data provider requests remain zero. No trading.

Stop after the Development verdict. Validation requires separate authorization.
