# No.1.1 chart append / connection-check progress correction

## Scope

The user reported four captured frames, 47 selected symbols, 188 market rows, 12,112 chart rows, 3,028 unique unmodified bar keys, no revised keys, and zero accepted proxy Va rows. The reported rejections were 2,984 `CHART_NOT_CAUSALLY_AVAILABLE` and 44 `MISSING_OR_AMBIGUOUS_CUMULATIVE_BRACKET`. These are user-reported aggregates, not a replay of their private capture files in the authoring environment. Account observation reached sequence 3 with a clean close; detailed broker observation was still UNAVAILABLE.

The collector had read exactly the initial `HistoryBars` rows on every poll. Rakuten's official RssChart help specifies **initial display rows**, then appends new data as time passes. Thus a fixed initial read range can miss the appended bars even while the vendor feed is updating. This is a code defect consistent with the symptom; it does not by itself establish the state of every cell or prove that every cause of zero Va is resolved.

Source: https://marketspeed.jp/ms2_rss/onlinehelp/ohm_002/ohm_002_04.html (RssChart initial display count and appended data).

## Changes

- Keep the existing RssChart formula and chart-function count. Read the initial rows plus 392 rows of bounded same-session append capacity (the full 390-minute 09:00-15:30 wall-clock span plus two), with an additional overflow fence. A valid date in the fence fails closed. The same date, OHLCV and closed-bar checks remain.
- Do not change Va admission, freshness, cumulative-volume equality, model weights, Selector ranking, order permission or execution functions. Missing or unsuitable data still do not become artificial Va.
- The E2E wrapper forwards collector progress rather than withholding all output until exit, and propagates the collector's stop/ready control paths.
- The connection check publishes its result path immediately and checkpoints after stages. It no longer opens or indexes source ZIP archives. Its owned child is polled with a deadline and a five-second heartbeat instead of unlimited Start-Process -Wait. On a deadline it requests cooperative stop, gives a bounded cleanup period, records uncertainty if the child has not exited, and never forcibly terminates Excel. A cleanup-required marker blocks automatic reuse and is not silently cleared.
- `-MarketOnly` skips a repeated account read explicitly without marking it verified. This is suitable after the user's already reported clean account test.
- New saved-capture diagnostics verify immutable snapshot filename hashes and reuse the actual importer. They emit only aggregate counts/times, added bar keys, changed market row counts and cumulative validator statuses, not raw symbols/prices/holdings. Inputs are bounded to 2-10 frames. A zero-Va result no longer makes the connection check pass.

Microsoft references: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/start-process?view=powershell-5.1 and https://learn.microsoft.com/en-us/dotnet/api/system.diagnostics.process.waitforexit?view=netframework-4.8.1 . Waiting for a process tree is distinct from checking the direct child; an elapsed budget is not proof of cleanup or feed correctness.

## Verification and remaining boundary

Added Node synthetic tests and Windows PowerShell 5.1 mock tests for appended rows beyond the initial range, overflow, unchanged guards, zero-Va failure classification, hash checks, cumulative diagnostics, bounded process wait and cooperative stop. Test files are not evidence of passing tests. The authoring session's local execution tools failed to start; exact-commit CI results or a user's local test result are required. No live Excel/RSS execution is claimed by this patch.

A new capture is needed to confirm that newly appended bars are now seen. Zero Va may still arise from unavailable cumulative values, ratio mismatch, receipt timing or volume mismatch. Those must be investigated from the reported reasons, not bypassed. Existing bootstrap configuration, actual session master/evidence, full real-model Shadow, detailed broker attribution and same-run recovery remain separately unverified. No orders are sent and no production promotion is made.
