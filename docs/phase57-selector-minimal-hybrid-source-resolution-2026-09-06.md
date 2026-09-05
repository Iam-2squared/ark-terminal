# Phase57 Minimal Hybrid — Fresh Source Resolution (2026-09-06)

## Decision

`DATASET_NOT_READY` remains in force. No free, authorized, reproducible source has reached the frozen GO contract for at least 120 fresh JPX intraday sessions. No data was acquired, no source pilot was run, and training, feature selection, Validation, and untouched OOS remain unopened.

One-minute bars are not a requirement. The frozen research interval is five minutes. A direct five-minute source is acceptable when freshness, causality, coverage, reproducibility, authorization, and timestamp semantics pass admission.

## Frozen Yahoo ancestry interpretation

Phase A does not ban Yahoo as a provider. It rejects the consumed dataset identity, any parent or descendant ancestry, and every session overlapping 2026-06-12 through 2026-09-04. Completely unused and non-overlapping Yahoo observations could satisfy the freshness portion in principle. They are not admitted now because the five-minute retention path does not supply 120 unused sessions and does not provide a historical point-in-time universe.

## Source decision matrix

| Source | 120+ sessions | JPX | Direct 5m | PIT universe | Authorization | Fresh ancestry | Decision |
|---|---|---|---|---|---|---|---|
| J-Quants Minute add-on | Yes, documented two-year history | TSE listed issues | No; causal 1m aggregation | Partial / unproven delisted completeness | API key and add-on absent | Conditional for unused observations | `BLOCKED_AUTH` |
| Yahoo Finance Chart | No for the 5m retention path | Current-symbol reconstruction only | Yes | No | Prior operator terms attestation recorded | Conditional, provider not globally banned | `REJECT_INSUFFICIENT_RETENTION` |
| Alpha Vantage Intraday | Yes on premium history | Unknown | Yes, premium | Unknown | Premium key absent | Unknown until payload exists | `BLOCKED_AUTH_AND_JPX_COVERAGE_UNKNOWN` |
| Twelve Data XJPX | Unknown | License required or unsupported for market data | Unknown for XJPX | Unknown | License contact required | Unknown | `REJECT_FREE_PATH` |
| Marketstack Intraday | No for JPX intraday | Intraday is not worldwide | No for JPX | N/A | Plan required | N/A | `REJECT_NO_JPX_INTRADAY` |
| EODHD Intraday | Technically yes if Tokyo symbols are covered | Unknown without authorized query | Yes | Endpoint exists; not piloted | Paid token absent | Unknown until payload exists | `BLOCKED_AUTH_AND_JPX_COVERAGE_UNKNOWN` |
| MarketSpeed II RSS read-only | Historical window is insufficient; prospective only | Domestic stocks, capture-scope dependent | Yes via `RssChart` | Prospective capture possible | User-local runtime unavailable in Work | Yes prospectively after pilot exclusion | `PROSPECTIVE_PRIMARY_PENDING_PILOT` |

The official MarketSpeed II RSS function specification permits five-minute `RssChart` output with a maximum display count of 3,000. `RssChartPast` supports daily, weekly, and monthly periods, not intraday periods. At 66 five-minute bars per current full JPX cash session, 3,000 bars are approximately 45 sessions and cannot satisfy the 120-session historical contract.

## Admission pilot status

No historical candidate reached GO, and the Work environment has no authorized provider credential or local MarketSpeed runtime. The Small Admission Pilot was therefore not fabricated or simulated. Its status is `NOT_RUN`.

The next permitted pilot is `SOURCE_VALIDATION_ONLY`: the first two eligible JPX sessions after 2026-09-06, resolved from the official calendar at capture time, using a small symbol set. Those sessions are permanently excluded from the formal Development / Validation / untouched OOS dataset.

If that pilot passes timestamp, timezone, OHLCV, availability, lunch/session, missing/duplicate, corporate-action, and symbol-mapping checks, formal append-only prospective accumulation may start. Every raw session receives an immutable SHA-256 manifest. The existing five-symbol history pack is not a selector-wide dataset. Formal Development remains sealed until at least 120 non-pilot sessions pass the complete admission audit.

All execution, broker, Excel order, RSS order, live-trading, paper-trading, automatic-promotion, production-update, and transmission flags remain false.
