# Phase57 Selector historical data source strategy

## Decision

The first runnable benchmark is a 200-symbol, approximately 60-day Yahoo Chart pilot. It is deliberately labelled `SURVIVORSHIP_LIMITED_RECONSTRUCTION`; it is not an exact replay and it cannot release untouched OOS. The workflow is manual and requires the operator to verify provider terms before any scaled retrieval.

The benchmark core itself is provider-neutral. A licensed/authorized source can be converted to the same dataset contract without changing frozen V3.0 semantics.

## Source lanes

### Lane H1 — Yahoo Chart pilot

Purpose: exercise the complete V1/V2/V3 paired pipeline over hundreds of symbols and at least 30 sessions.

Limits:

- later-fetched OHLCV, not the historical TradingView scanner payload;
- the current JPX symbol/sector list is applied historically;
- delisted issues, historical listings, market transfers, and symbol changes are not reconstructed;
- no historical spread, depth, quote staleness, tick order, or order book;
- sparse observations stay sparse;
- provider behavior and permitted usage are not treated as a stable public contract.

This lane is useful as a reconstruction benchmark, not final evidence.

### Lane H2 — authorized long-history intraday import

Preferred for the serious benchmark. JPX states that historical real-time cash-equity data (including tick data) and processed 10-level order-book history are available as paid data. This can support stronger point-in-time and microstructure evidence, subject to the purchased license.

Alpha Vantage's official documentation states that its premium intraday endpoint supports 1/5/15/30/60-minute bars, a historical `month` parameter, and 25+ years of depth. Actual JPX issue coverage, exchange mapping, adjustment semantics, rate limits, and license terms must be verified with a representative symbol sample before an adapter is accepted.

Twelve Data lists the Tokyo Stock Exchange (MIC `XJPX`) and current plan availability, but the exchange page does not by itself prove that the required historical 5-minute endpoint/depth is available for every JPX issue. An adapter remains blocked until endpoint-level sample verification and terms review pass.

### Lane U — historical point-in-time universe

JPX's J-Quants API describes listed-company information for past dates. Use that or another licensed historical security master to construct session-specific membership, listing dates, delistings, transfers, and symbol changes.

Until this is joined successfully, every benchmark remains `SURVIVORSHIP_LIMITED_RECONSTRUCTION`.

## Admission checks for another provider

A provider adapter must fail closed unless it records:

- provider and endpoint identity;
- acquisition timestamp and raw-file digest;
- explicit bar timestamp meaning and timezone;
- raw versus adjusted price semantics;
- session calendar and corporate-action handling;
- symbol/exchange mapping;
- missing and duplicate policy;
- historical universe status;
- permission/license attestation supplied by the operator;
- all research safety flags false.

No adapter may call a reconstruction exact, zero-fill unavailable microstructure, or alter the frozen V1/V2/V3 selectors.

