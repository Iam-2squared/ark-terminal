# Phase50.6 Yahoo minor OHLC range adjustment

This change handles provider-level floating point drift from Yahoo Chart data without weakening fail-closed validation.

- Scope: `YAHOO_CHART` OHLCV only
- Tolerance: 0.11 JPY
- Action: adjust the low/high boundary only when open/close exceeds it by no more than the tolerance
- Audit: preserve the original OHLC values in `normalizationAudit`
- Warning: emit `MINOR_RANGE_ADJUSTMENT`
- Safety: material inconsistencies remain blocked; no execution or order-write paths are changed
