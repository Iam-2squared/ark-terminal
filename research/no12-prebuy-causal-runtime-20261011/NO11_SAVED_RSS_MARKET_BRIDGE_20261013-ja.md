# No.1.1 保存済みRSS市場データ → As-of市場入力のみ（2026-10-13）

## 実機証拠（ユーザー報告）

- 保存済み `C:\Users\Owner\Desktop\Ark_No11_MARKET_RSS.xlsx` は `RssMarket("7203.T","現在値")` と `RssMarket("7203.T","現在値詳細時刻")` を使用。実機で価格2968円・時刻11:30:00を観測。
- 既存 `Ark_No11_MSII_RSS.xlsx` は口座専用。変更・上書き禁止。
- ユーザー実行の修正版 `Watch-No11SavedMarketRssReadOnly.ps1` で5秒間隔の3サンプル連続取得・JSON更新に成功。時刻11:30のままなので3件ともSTALE。Nodeの旧consumerは `MARKET_SOURCE_STALE_NO_DECISION` を返した。
- これは**市場データの実機観測**であり、Frozen Selector / First Entry / State9 / H2/H3/H5 / Capital / EXITの実行証拠ではない。

## 今回のGitHub側接続

`runtime/no11_saved_market_shadow_bridge.mjs` は上記の `market_shadow_v2.json` を厳格に検証し、**市場入力だけ**をNo.1.1のAs-of形へ変換する。価格・時刻・同一営業日・PC観測時刻・暫定30秒鮮度・観測JSONの15秒期限を検証する。

`tools/no11_saved_market_shadow_check.mjs` は実PCのJSONを読み込むだけで、ExcelもBrokerも起動しない。市場休憩や取引終了時にSTALEをBLOCKするのは正しい。

```powershell
node C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011\tools\no11_saved_market_shadow_check.mjs --market-json "$env:LOCALAPPDATA\ArkTerminal\MarketData\market_shadow_v2.json"
```

- 正常かつ直近のデータ: `NO11_SAVED_RSS_MARKET_ASOF=PASS_MARKET_ONLY`
- 古いデータ/欠損/改ざん: `NO11_SAVED_RSS_MARKET_ASOF=BLOCKED`
- **どちらでも `NO11_PRODUCTION_READY=False` と `ORDER_TRANSMISSION=False`。**
- Excelセルは非原子的に読み取られ、RSS更新時刻の日付はPCのJST日付から推定。Broker配信時刻・時刻の正確性は未認証。
- JSONのSHA256は**ローカルファイルの同一性**であり、Broker署名ではない。

## 未完了

正式な数千銘柄Selectorデータ供給、Frozen First Entry/State9/24モデルの本番実行、Capital/EXIT、注文ID/部分約定・Safety照合、実資金発注の検証は未完了。**実注文は許可しない。**

このPRは隔離研究ブランチのみ。Frozen No.1.1 / main / PR #591は変更しない。
