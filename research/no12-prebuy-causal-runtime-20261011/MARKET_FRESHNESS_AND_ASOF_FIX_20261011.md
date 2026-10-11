# No12 market data observed freshness and causal binding, 2026-10-11

The actual latest MarketSpeed II RssChart 5-minute bar is compared with the decision time. Merely refreshing Excel can refresh the **COM observation clock** while the vendor's latest OHLCV bar has stopped updating. A bar whose conservative close is more than 15 minutes before the decision now blocks No12 candidate use with NO12_CHART_COMPLETED_BAR_TOO_OLD_FOR_DECISION, including lunch break/outage conditions. This is a low-cost in-memory check, not a 15-minute artificial wait: the already conservative bar-close condition is unchanged.

The caller can supply separate causal First Entry / State9 known-at time when binding a candidate to a chart receipt. The binder uses the **maximum of original candidate known-at and chart known-at**, never replacing a later Selector/State9 timestamp with an earlier market capture time. A future candidate is rejected.

A hash-matching private chart receipt older than 30 seconds is not a present-day market-ready receipt, preventing a read after restart from silently treating yesterday's file as fresh. Source hashes remain accidental-corruption checks, not a signature from Rakuten.

This code and synthetic tests do not access Excel, issue trading orders, reset Safety, imply MarketSpeed II broker-delivery timestamp certification, or claim economic proof of No.1.2. Original No.1.1 frozen unchanged. Both manual trade permission and private account data unchanged.
