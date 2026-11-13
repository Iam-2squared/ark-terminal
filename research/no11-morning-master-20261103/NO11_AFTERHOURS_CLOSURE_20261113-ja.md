# ARK No.1.1 — 2026-11-13 取引見送り後の問題解消台帳

## 固定方針

2026-11-13（金）は取引を見送る。No11のLIVE/自動注文を再開しない。検査と修正は**停止中のWindows環境・開発ブランチ・人工CI**に限定する。

- main、Frozen No.1/No.1.1、State9原本、既存Entry/EXIT/Capital、元Excel/RSSブック、取引台帳、既存order claimを直接変更しない。
- 既存の接続済みChart50試行を「終了」に書き換えない。未知注文、約定、保有の可能性を自動的にゼロ扱いしない。
- 修正をまとめて検証するまで、Draft PR #612・#613・#614をPCへ直接コピーしない。特に#613と#614は#612から派生した**別の兄弟PR**で、両者が共存した統合パッケージの実機検証は済んでいない。
- 発注、再発注、LIVE開始、Excel初期化、取引マーカー削除、取引日時の書換えを目的としたコマンドは提供しない。

## エビデンスに基づく障害一覧（未解決を未解決とする）

| ID | 確認された現象 | 修正候補・参照 | 閉鎖（CLOSED）に必要な証拠 |
|---|---|---|---|
| D01 | 11/13朝のbootstrap/sessionが11/12を参照し、`LIVE_CONFIG=WRONG_SESSION_DATE`。対象日のpreflightがローカルに見つからない報告 | 今回の読取専用censusと、#612 `Check-No11StartPrerequisitesReadOnly20261111.ps1` | 当日の日付を作り直すのではなく、次の予定営業日に元ソースから正規の夜間更新と別hash検証付きhandoffが再現できる。欠損スクリプトは原本pinで取得。再発防止テストPASS |
| D02 | 11/11に`NO11_PRESTART_RETRY_UNKNOWN_CONTROLLER_SOURCE`。retry claimを保存すべき状態 | #612 の再試行・controller identity診断 | 現地controllerの元bytes/manifest/hashと復旧条件を照合し、既存claimを消さずに原因確定。取引再発行無し |
| D03 | 11/6の45→40準備後、RSS物理通信初期化が失敗。元の詳細ログ不足 | #612 の読み取り限定COM retry・型/HRESULT/行番号の記録 | 現PCの同一元ソースで検査がPASS。Excel PID/開始時刻/3ブック/BD4、同時稼働、注文ゼロを独立証拠で検証 |
| D04 | 11/12 12:53:32 `NO11_SERVICE_NODE_TICK_FAILED`、元stderrは失われた | #613 のstrictly redacted Node失敗receipt | 今後の人工故障試験で原因分類可、元のfail-closed維持。11/12の根本原因はUNKNOWNとして保持 |
| D05 | Chart50の旧CONNECTED収集attemptが完全閉鎖未証明 | #612のsame-run recoveryと#613のfailure attribution | 原attemptとorder/fill/position/collectorを照合。閉鎖証明不可なら未解決のまま停止 |
| D06 | OneClick/Overlayのmigration source不一致とworker/UI running gate、installer ancestor誤検出 | #614の8 blob source-pinned direct-CMD stageとread-only gate probe | **新規独立CMD**から`probe`で `UNREADABLE=0`、`MATCHES=0`、`audit=READY_NOT_APPLIED`、取引終了後のみ確認式apply、終了後再audit。安全gateを免除しない |
| D07 | 通過候補を見送った理由の履歴欠落、後の表示が以前のdecisionを上書き | #613 のdurable decision audit | 人工候補・SQLite checkpoint の時刻/理由記録、ゼロ数量/古い候補の非再投入試験PASS。11/12既存データを後付け説明しない |
| D08 | 11/6からの週次・日次更新が未完、途中中断の安全復元が必要 | #612 のresumable nightly/receipt | 現地のdate/元hash/取得・公開receipt照合、途中中断ケースPASS、既存markerの削除無し |
| D09 | 既存PCでは#612、#613、#614の完成コードを単一の安全installerとして適用・検証していない | 統合patch・source-level/WinForms/Python/PowerShell/SQLite・実PC no-order試験 | 既知の元source hashに限定したトランザクション型install、復元、事後readback、全保護回帰をPASS |
| D10 | 実PCのbroker注文/約定/保有、Excel3ブック、RSS接続、アクティブworkerの完全な現状はGitHubから分からない | ownerの現地読取専用検証 | 不明をゼロと置かず、実機で日時・口座・未確定注文・建玉を照合して証跡化 |

**重要**: 今日の取引見送りを宣言したことと、Windows上のタスク・予約が物理的に停止したことは同義ではない。現地の予約、稼働プロセス、証券会社画面の注文・約定・保有は当事者が読み取り確認する。未知の注文を決して再送しない。

## 今回の新規作業（安全範囲）

`no11_afterhours_readonly_census.py` は、既存settings・binding・bootstrap date・prepared-day pointerのhashと日付・既存run/recovery markerを**読み取るだけ**。Excel COM、RSS、Node、broker、WinForms、取引サービスを開始しない。

```powershell
# 専用checkout/検証済みブランチ内で、通常のPowerShellから。
py -3.12 .\research\no11-morning-master-20261103\no11_afterhours_readonly_census.py --session-date 2026-11-13
```

結果は固定のステータス文字列のみ。ローカルパス、口座、銘柄、JSON本文、注文番号を表示しない。
`PREPARED_DAY=DATE_AND_HASH_MATCH_READONLY` であってもLIVE開始許可ではない。
`BROKER_STATE=NOT_OBSERVED_NO_ZERO_ASSUMPTION` は常に残る。

## 以降の進め方

1. 今日のPC上のTrade予約・各プロセス・broker状態を読取確認し、**再起動・取引しない**。
2. D01/D02の元sourceと日時を独立診断し、次回営業日向けの夜間更新・復元の人工/実機no-orderテストを実施。
3. #613/#614の候補改修を#612ベース上の**独立統合release候補**へ集約。既知hashだけ受理、実行中・未知状態でfail closed。既存注文関数・EXIT・Capitalルールを変更しない。
4. Windows 5.1/3.12実機のpreflight・3ブック・PIN/COM/Native・journals、人工故障・再起動・巻戻しを検証。安全な状態を説明できるまでは発注OFF。
5. 実機で承認済みのsource setに対するafter-hours installを行い、適用後read-only auditと新しい次営業日handoffを評価。**成功したテストのみをPASSと数え、実発注の証明とはしない。**

No11の統合修復と、研究専用のSelector V2（PR #594）は別系統。今回のノートと診断はNo11の起動・稼働上の問題に限り、モデル学習や買付は行わない。
