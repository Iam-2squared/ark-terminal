# No.1.1 V3 Bulk RSS candidate — Windows measured 2026-10-11
Status: **ISOLATED READ ONLY CANDIDATE; not wired to the one-click startup.**

PC evidence after SHA256 verified as 8B396BF22724ABBCA4BCEB7B93862AE46D40ACBDFE95B385F492E960E9F08DA3:
- Windows PowerShell 5.1 offline self-test PASS.
- Capture 2.86 seconds (prior pinned V2 33.25 seconds): around 11.6x faster for the measured snapshot phase.
- Broker positions 1, unused padding rows 197, orders 0, executions 0.
- EXCEL_MODIFIED=False, ORDER_TRANSMISSION=False, NO11_PRODUCTION_READY=False, ACTUAL_FEED_TIMESTAMP_CERTIFIED=False.

Tracked candidate is byte-exact. It bulk reads position/order/execution ranges via Excel COM Value2, confirms every required header, tests full 18-column padding rows and overflow sentinel rows, then **actually re-reads RSS status**. Feed observedAt records the final time observed, NOT the time brokerage market data arrived. Candidate has a stricter 25-second capture bound, does not touch official private snapshots, pinned capture v2 or the original Excel workbook.

Private parity helper `Test-No11V3LocalParity.ps1` compares the existing V2 snapshot against the most recent new V3 candidate in %LOCALAPPDATA% and reports only booleans, not broker account identifiers or values. A time-separated pair returns NOT_PROVEN. It cannot claim comparison when no timely V2 sample exists. Zero actual broker orders/fills cannot establish row parity for populated lists. Neither an offline CI PASS nor a V3 PC capture is an authorization to trade.

Formal desktop capture path remains SHA256-pinned to unchanged V2: 0EAB3CA3081B2E0CB323D8438719F2B820B69FC02F373AD843B5907315838E2C. Frozen research/main, Ownership, UI and safety ledger are unchanged. Later candidate adoption requires full-row/time-aligned parity, Windows source-health/Capital verification, and separate broker receipt-time evidence. Original ledger error latches must not be unconditionally reset. Excel order permission must remain OFF.
