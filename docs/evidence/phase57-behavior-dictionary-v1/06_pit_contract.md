# Dictionary v1 PIT / as-of precommit

This is a new Dictionary contract, not a modification to Frozen Selector or historical Entry/EXIT semantics.

- Bitemporal: eventTime/effectiveFrom/effectiveTo describe the event; knownAt is the earliest evidenced availability of the exact immutable version. Acquisition fetchedAt is not historical knownAt. Backdating fetchedAt to eventTime is prohibited. unknown knownAt is blocked for Entry-facing use.
- Profile firstUseDate is strictly later than windowEnd. Windows are19 observed calendar sessions from the fixed allocation, exclude the current day, retain start/end; missing sessions are not silently compressed. At least12 effective session observations, no invented bars.
- A bar has start/end/availableAt; completed5m information is available no earlier than end and source knownAt. A session summary/label matures only at its session end. fitted artifact trainWindowEnd < firstUseDate and fittedAt/knownAt <= firstUse timestamp apply to EB priors, normalizers, bucket boundaries and bases.
- Stable securityId with dated code effective intervals and their knownAt is mandatory. Code alone is not proof of identity. Current master cannot backfill delistings, mergers or code changes. No raw ID, one-hot or embedding is exposed to Entry features.
- Raw unadjusted prices are retained. Adjusted historical data without action effectiveDate/announcement knownAt/version lineage is forbidden for cross-session comparisons. AdjFactor or dated master alone is not proof of a historically available version.
- JST: AM09:00-11:30 and PM12:30-close; separate opening/terminal auction semantics. Before2024-11-05 PM continuous slots end15:00 and terminal auction15:00. From2024-11-05 continuous slots end15:25,15:25-15:30 is preclose with no executions, terminal auction15:30. 11:30 is AM terminal auction; lunch is not trading time. Missing closing auction stays missing. Calendar dates come only from pinned allocation, no weekday guessing.
- NO_TRADE requires evidence of no trade with known feed coverage; a missing row alone is UNKNOWN. DATA_MISSING requires a known feed outage; HALT_SPECIAL_QUOTE needs exchange/status evidence; NOT_LISTED needs dated effective lifecycle evidence. These categories are not imputed from price/volume.
- Selector ranks, scores, selection/winner identity, path-anatomy outcomes, Entry/EXIT P&L are forbidden Dictionary inputs. Audit counts are not trait estimates.
- Truncation invariance, future-row poison, future-revision poison, negative canary, mapping/action cutoff and sealed-session access rejection are mandatory. Contract tests on synthetic fixtures are not evidence that production inputs satisfy the contract.
- Decrypt saved archives only in ephemeral CI. Inspect archive headers; extract only whitelisted57 Development dates and approved raw filenames. Never parse REPORT19/protected session payloads. Verify response page and aggregate SHA256. Do not emit private prices, volumes, security-level raw rows or reconstructable profiles to git.

Primary calendar references checked2026-09-19:
https://www.jpx.co.jp/corporate/news/news-releases/1030/20241105-01.html
https://www.jpx.co.jp/english/equities/trading/domestic/04.html
