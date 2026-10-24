# No12 historical bootstrap in private market receipt
On the same local-only RssChart capture, the publisher checks current completed 5-minute bar freshness
and the previous five complete trading sessions. The latter is historical reconstruction only.
Private market JSON retains historyRows and a separate checksum; the receipt verifies both.
Missing prior sessions or gaps produce HISTORY_SOURCE_INCOMPLETE; no fabricated data.
Only anonymous prior session count/status is printed by CLI. Source has no Excel order calls.
No genuine online Selector/First Entry/State9, production readiness or broker arrival certificate is implied.
