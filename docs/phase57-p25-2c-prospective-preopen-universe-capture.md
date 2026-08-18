# Phase57 P25.2C - Prospective pre-open Dynamic Universe capture

P25.2B proved that the existing rolling screener snapshot cannot be projected backward into the P24.10 historical OOS window. P25.2C therefore starts a separate **prospective, point-in-time** research lineage instead of fabricating historical JPX cross-sections.

## Session contract

- A dedicated research workflow scans the JPX universe in six overnight batches.
- Scheduled cycle starts 22:15 JST and targets completion by 08:15 JST for the next JPX session.
- Batch size is frozen at 620, so six batches cover the current ~3,700-name domestic Prime / Standard / Growth universe.
- The first scheduled batch resets the dedicated cycle. Partial cycles never freeze a session universe.
- Capture cutoff is 08:50 JST. A cycle completing after that time is blocked rather than treated as a pre-open universe.
- Rows older than 12 hours are excluded by the P25.2B freshness guard.
- At least 3,000 eligible point-in-time rows are required.
- Dynamic 30 / 40 / 50 are frozen as nested prefixes of one DAY rank before the market opens.
- One successful universe per session is retained. Later reruns cannot replace an already frozen session universe.

## Data isolation

The workflow uses `automation/p25-universe-data`, separate from the normal Discovery screener data branch. It persists only research source state and a compact `data/p25-prospective-universe-timeline.ndjson` lineage. This avoids changing the existing UI screener cadence while giving P25.2 a prospective point-in-time evidence stream.

This is not a performance claim and does not select Dynamic 30 vs 40 vs 50. The actual Phase57 Frozen Entry / Fixed Horizon outcomes are joined only in the later P25.2 comparison runner.

## Safety

Execution, broker writes, Excel order writes, RSS order functions, live/paper trading, automatic promotion, production update, transmission, and fresh-holdout consumption remain disabled. MARKETSPEED II / Excel / Python remain READ ONLY.
