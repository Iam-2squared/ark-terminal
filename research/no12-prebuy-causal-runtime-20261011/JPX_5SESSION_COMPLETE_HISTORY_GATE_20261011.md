# No.1.2 five-session SOURCE history completeness gate — 2026-10-11 JST

This is isolated Draft PR #592 research-side hardening, NOT Frozen No.1.1 or execution authorization. No live broker/Excel access.

## Defects prevented
1. Old observation-driven `slice(0,5)` could silently replace a missing recent JPX session with an older one. The expected dates are now derived independently from an explicit, pinned JPX cash-equity 2026/2027 calendar.
2. Old `minimumBarsPerSession=60` with gap-only checks accepted truncated edges. Every required normal session now needs exactly 30 AM + 36 PM = 66 five-minute rows, complete slot coverage including the first and last slot.
3. Two exact label grids (bar START timestamps and bar END timestamps) are accepted as source shapes, but mixed label conventions fail closed. The actual RSS label semantics remain physically UNVERIFIED.
4. Future-session data and fake JPX-holiday bars fail closed before the unfinished-bar exclusion. No missing bars or missing days are substituted.

JPX source (cash market, not derivative holiday trading): https://www.jpx.co.jp/english/corporate/about-jpx/calendar/index.html ; reviewed 2026-10-11. In particular, Oct 12 is a JPX cash holiday and Oct 13 is a trading day. Unpinned years are refused, not guessed. Future calendar changes require deliberate source review.

A history returned on Tuesday for an earlier session is HISTORICAL RECONSTRUCTION; it does NOT prove historical broker delivery / PIT evidence. The exact live provider timestamp, wide-market Selector feed, native Selector/First Entry/State9/EXIT, broker order/execution identity, physical E2E and independent OOS remain unverified.

Expected synthetic tests: omitted newer day + older replacement, missing opening/closing edge, contiguous truncated bars, mixed label conventions, fully end-labelled path, fake holiday and future-source bar. No true trading permission, Excel modification, main merge, Frozen change or private account upload. Excel RSS order permission stays OFF; productionReady=false.
