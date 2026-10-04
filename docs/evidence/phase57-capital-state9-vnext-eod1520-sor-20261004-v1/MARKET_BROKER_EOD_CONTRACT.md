# 🏛️ Market / Broker EOD Contract

確認日時: 2026-10-04T09:56:21.142126+09:00。適用対象はLONG現物、research/shadow。

| 項目 | 固定契約 |
|---|---|
| 東証ザラバ終了 | 15:25 JST |
| プレ・クロージング | 15:25–15:30、注文受付のみ |
| クロージング・オークション | 15:30、成立sourceがある場合のみ参照 |
| 15:20 intent | ザラバ終了5分前という運用buffer。performanceから選ばない |
| SOR intent | 売り、通常注文、全残数量、成行、本日中 |
| 未約定残 | 東証へ回送されたDAY注文はプレ・クロージングへ引き継がれる |
| commission | 楽天ゼロコース0JPY、SOR/Rクロス利用同意が前提 |
| execution friction | Frozen SELL×0.9995を5bps adverse conventionとして別計上 |
| SOR改善 / impact | 改善を仮定しない。market impactモデルを追加しない |
| RSS | 最新2026/9/19版。trigger0、呼出し0、送信0 |

15:29 negative EvidenceとFrozen receiptは維持する。市場価格barは個人注文の数量全量実約定receiptではない。historical referenceと実運用認証を分離する。SOR対象銘柄、同意・口座・注文受付・残数量の実運用確認はlive unlock時の事項で、このWorkでは認証しない。

## 🔗 公式出典

- [JPX_TRANSACTION](https://www.jpx.co.jp/equities/trading/domestic/04.html): Continuous until15:25; pre-closing15:25–15:30 accepts orders without executions; auction15:30. Existing unexecuted TSE orders transfer into pre-closing.
- [JPX_HOURS](https://www.jpx.co.jp/equities/trading/domestic/01.html): Cash-equity afternoon session12:30–15:30, with closing-auction sub-session.
- [ZERO_COURSE](https://www.rakuten-sec.co.jp/smartphone/commission/): Zero Course cash-equity broker commission0JPY; SOR including R-cross agreement required.
- [SOR_RULES](https://www.rakuten-sec.co.jp/web/domestic/sor/rule/ground_rules.html): SOR active12:30–15:25; supports MARKET and DAY; cannot select opening/closing conditions; MarketSpeed II supported. Broker-designated eligible securities only.
- [SOR_ATTENTION](https://www.rakuten-sec.co.jp/web/domestic/sor/rule/attention.html): SOR rules and broker eligibility apply; no guaranteed execution or price improvement is certified by this research.
- [SOR_EXECUTION](https://www.rakuten-sec.co.jp/web/domestic/sor/rule/agreed.html): SOR compares TSE/PTS/R-cross routes; a market-order example is supported. Do not assume improvement.
- [R_CROSS](https://www.rakuten-sec.co.jp/web/domestic/sor/rule/rx.html): Unmatched orders and residual quantity are routed to TSE. R-cross is cash-only, requires Zero Course; cannot designate R-cross directly.
- [RSS_CURRENT_PDF](https://marketspeed.jp/guide/manual/ms2rss_function.pdf): Current version2026/9/19; RssStockOrder trigger0=waiting, SELL1, regular0, SOR1, MARKET0, DAY1, market price omitted. SOR disallows conditions3/4. Account type must follow actual cash account.
- [RSS_ORDER_HELP](https://marketspeed.jp/ms2_rss/onlinehelp/ohm_002/ohm_002_06.html): Same field combination supported; no order call or Excel write performed.
- [JQUANTS_MINUTE](https://jpx-jquants.com/en/spec/eq-bars-minute): Unadjusted TSE on-auction 1m OHLC/Vo/Va; Time=start, O=first trade; no-trade minutes omitted; exact15:30 closing record has equal OHLC; no auction flag;15:25–15:29 normally absent. No PTS/ToSTNeT data; x-api-key and minute add-on required; no intraday time query parameter.
- [JQUANTS_DELIVERY](https://www.jpx.co.jp/markets/other-data-services/j-quants-api/index.html): Historical data delivered daily; API is not a real-time broker execution confirmation source.
