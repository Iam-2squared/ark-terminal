# Phase57 P25.2B - Point-in-Time OOS Universe substrate

Status: **research infrastructure only / no performance claim**

P25.2B supplies the information-boundary layer required before the precommitted `FIXED_5 / OLD_FIXED_30 / DYNAMIC_30 / DYNAMIC_40 / DYNAMIC_50` comparison can be measured.

## Why this part exists

The live screener data branch is a rolling snapshot. Different symbols can have different `scannedAt` timestamps, and the latest snapshot cannot be projected backward into a historical OOS decision. Doing that would create a false historical cross-section even if no explicit future-return column were used.

Therefore P25.2B does **not** fabricate historical JPX rankings from today's/latest screener snapshot. For every frozen Day decision timestamp it requires a snapshot that actually existed at or before that timestamp. If a sufficiently complete point-in-time cross-section is unavailable, the decision is preserved as blocked rather than filled from a later snapshot.

## Frozen rules

- Snapshot `generatedAt` must be `<= decisionTimestamp`.
- Later-snapshot backfill is forbidden.
- Duplicate symbol rows inside a snapshot fail closed.
- Conflicting snapshots with the same `generatedAt` fail closed.
- Per-row `scannedAt` is passed through the existing P25 freshness guard.
- A default minimum of 3,000 eligible symbols is required before a JPX-wide dynamic ranking is considered representative enough for this research substrate.
- Dynamic 30 / 40 / 50 are prefixes of **one frozen DAY rank**. They are not independently reranked after seeing OOS outcomes.
- Sector cap remains fixed at the P25 default of 4 per sector unless a different value is preregistered before measurement.
- Future return, realized trade PnL, trade-win labels, outer-OOS performance and post-hoc winner fields are excluded from the substrate fingerprint and cannot affect the P25 selector.
- Entry threshold, horizon, model and Phase57 Fixed Horizon default are unchanged.
- Blocked decisions are retained in the timeline artifact.

## Reproducibility audit

Each accepted source snapshot receives a SHA-256 fingerprint over ranking-relevant/current fields only:

`symbol, sector, market, currentPrice, volume, volumeRatio, dailyChangePercent, atrPercent, discoveryScore, technicalScore, confidence, qualityScore, scannedAt, status`

Outcome/performance fields are deliberately absent. A poisoning-invariance test verifies that adding extreme future-return / realized-PnL / outer-OOS fields does not alter the fingerprint or Dynamic 30/40/50 membership.

## Important current data limitation

The repository's live screener workflow updates the JPX universe in rotating batches. That is useful for current Discovery, but by itself it is **not** a historical point-in-time OOS archive. P25.2B therefore makes the missing-history problem explicit instead of silently treating the latest rolling snapshot as historical truth.

The next measurement runner must use archived historical snapshots that satisfy this contract, or reconstruct the ranking inputs from data that was available at each historical decision time. If neither source exists for the common P24.10 OOS window, Dynamic 30/40/50 measurement is blocked until a legitimate point-in-time source is added.

## Safety

All of the following remain false:

- `executionAllowed`
- `brokerWriteAllowed`
- `excelOrderWriteAllowed`
- `rssOrderFunctionAllowed`
- `liveTradingAllowed`
- `paperTradingAllowed`
- `automaticPromotionAllowed`
- `productionUpdateAllowed`
- `freshHoldoutConsumed`

MARKETSPEED II / Excel / Python remain READ ONLY. No order function or `ARK_ORDER` write is introduced.
