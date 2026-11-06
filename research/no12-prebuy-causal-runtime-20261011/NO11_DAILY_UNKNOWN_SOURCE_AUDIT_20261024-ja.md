# No.1.1 — RSS日足取得完了後のUNKNOWN原因調査（追加取得なし）

確認日: 2026-10-24 JST。対象は既存統合版 PR #592のみ。新Selectorの開発ではない。

## 確定した実測

受領済み集計 JSON (no11-daily-trend-summary-6f0c30d53c3398be.json): 2026-10-23をasOfとする4,328銘柄すべてが保存完了。上昇348 / 混在1,226 / 下降・横ばい2,044 / UNKNOWN710。UNKNOWN内訳はMALFORMED_SOURCE_ROWS489とSOURCE_UNAVAILABLE221。前回中断の1,568件は再開後に処理され、未取得0。

PASS 348 は表示上、市況500銘柄上限を下回るが、未確定710件が将来通過しうるので、500件以内認証ではない。RssChart50関数、企業行動、Master、元Selectorに必要な実1分Vaと市場・業種breadthも別に未接続。

## 次の工程

追加RSS取得より先に、既存保存原本に対する読み取り専用の原因内訳を診断する。

- tools/no11_rss_daily_unknown_audit.mjs --run [existing local run directory] を実行する。Excel、RSS、モデル、口座は使わない。
- 元のsource/plan hashとidentityを検証する。各不正行の日付は元収集時に保持していないため、原因が必要な76営業日の外かどうかは厳密には不明。
- MALFORMED489件のうち、parse済み76日期日がある件数と欠損する件数、重複、将来日期、invalidRows件数分布を集計する。parse済み76/76を正式PASSへ勝手に格上げしない。
- SOURCE_UNAVAILABLE221件は再取得対象と決め打ちせず、正しい取引所・上場時点・無約定・RSS応答/通信状況と分けて後で扱う。
- 共有用aggregate JSONとhashのみを返す。個別銘柄・欠損日付の詳細はPC内private保存。

原本上書き・新学習・元10時刻Top5の改変・実注文なし。

**固定の再開plan identityを守るため、元の5つのcapture/runtime工具は一切書き換えない。** この診断は新しいツールとテストだけ。現行Frozen No.1.1、PR #591、mainには影響しない。
