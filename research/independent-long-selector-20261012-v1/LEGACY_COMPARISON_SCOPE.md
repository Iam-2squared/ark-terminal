# Exact Frozen comparison scope

Status: LEGACY_COMPARISON_PENDING. No legacy Open-to-High counts are inferred.
Prior recovered metadata pins FROZEN_LONG_SELECTOR_WITH_MIN_PRICE_75.
Current active-pointer/payload and parent-fit manifest revalidation remains pending.

| Identity | Pin |
| --- | --- |
| Active spec SHA256 | e75a49adb2a35497b6ac4d1afdd2942f87d9e139f04ae98e2478ca564ee874d8 |
| Min-price75 freeze payload SHA256 | d782bd93761db2fe524b040479c7b3fc3f28331cc21c5f97fd2ad3f2b6058fb4 |
| Parent Selector commit | 565d74b3dea823581fdb32380113aac5913a248d |
| Parent payload SHA256 | 3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59 |
| Parent model SHA256 | 994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb |

The min-price75 payload pins:

- docs/evidence/phase57-selector-min-price75-v1/decision/selected-and-excluded-identities.csv
  SHA256: 0db332537661c1dece6becdfac538e5eeb641fb52754ee9f5c607208abb92a23.
- docs/evidence/phase57-selector-min-price75-v1/measurement/new-paths.json.gz
  SHA256: eeb15545a278a7058a0b40042169df8ad7560077289c7bef3412977decc524d2.

Native event/paths artifacts have not been opened for outcome analysis in this
work. Recovery must stream only admitted Report dates2024-11-29 through2024-12-09
and retain exact event identity, scores, weights and times. Sealed dates stay closed.

Legacy selects Top5 at10 intraday times; new selects up to15 unique symbols
preopen. Legacy price75 uses decision price; new uses prior close. Legacy native
future continuous5m High remains its own metric. Any legacy selected-set all-day
Open-to-High table is retrospective, can include High before selection, and is
not legacy preopen ability or profits.

Deduplicate symbol-days separately from repeated native events. The parent
actual FIT intervals and their overlap with the new Report must be verified
from the original manifest. A 76-day Development universe is not automatically
a 76-day FIT or validation partition. Both sides have historical exposure; no
fresh/OOS credit is asserted. Info/K/universe differences must be disclosed.

Next evidence: exact pinned selected identities/native paths for7 admitted dates;
official same-session RAW OHLC in private storage; current reuse basis. No baseline
retraining or zero/previous-day substitution of intraday inputs is allowed.
# Hash-only recovery after owner renewal

Both pinned min-price75 evidence files were recovered read-only from the
unchanged Git blobs into the private workspace: selected/excluded identities
5086203 bytes and native new-paths1953620 bytes, total7039823 bytes. SHA256
0db332537661c1dece6becdfac538e5eeb641fb52754ee9f5c607208abb92a23 and
eeb15545a278a7058a0b40042169df8ad7560077289c7bef3412977decc524d2 matched.
All bytes were mechanically copied/hashed; CSV records and JSON outcomes were
not interpreted and gzip was not decompressed. Not "wholly unopened".
Numerical legacy comparison remains pending the new model/watchlist freeze.
No model, weights, threshold, decision time or protected session was changed.

# MA4 continuation 2026-10-13

The two private pinned originals were restored with all entry hashes matched.
Numeric records were not opened. Event and unique symbol-day recount, native
selection-time-to-future High, and retrospective all-day Open/High remain
NOT_MEASURED. Exact protected admission still precedes any legacy parsing.
