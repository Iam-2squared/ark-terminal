# PC市場RSS最初の手動チェック：別Workbook限定

この診断スクリプトは `RssChart` の5分足を**発注不可のまま**確認するためのもの。公式の2026/3/30 RSS関数表 p.18, p.33, p.38に基づく。購入・売却関数は一切呼び出さない。

重要：すでに実機PASSした No.1.1 Desktop 監視は**開いたExcelブックがちょうど1冊**であることを前提とする。したがって監視UIとアカウント用Workbookが動いたまま別のチャートWorkbookを追加すると、監視がERRORになりかねない。**現在は実行しない。**

実市場データを確認する次の取引日以降に必要になった場合のみ：
1. No.1.1 READ ONLY UIを停止（黒いPowerShellウィンドウでCtrl+C）。Excel側の発注許可は引き続きOFF。
2. 既存のアカウント用Excelブックを保存せずに閉じる必要がある場合は、意図せぬ編集や削除をしない。
3. テストスクリプトを一度だけ実行する。既存のExcelにWorkbookが一冊でも開いていたら中止する設計。新規の**未保存一時Workbook**のみにチャート式を書き込み、数秒後に値の形式と行数だけを検査し、必ず保存せず閉じる。
4. 別途No.1.1 READ ONLYデスクトップを再起動。

チャートは **一般に公開されているサンプルの固定銘柄コード7203.T**だけ。コードも株価も口座金額もチャットには送らず、行数と数値化できた件数などの匿名結果だけを表示する。

`powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011\windows\Probe-No12MarketRssChartReadOnly.ps1"`

実機で株価セルが数値表示されても、それは**RssChartの動作確認のみ**。価格更新の正確なブローカー到着時刻、State9の原本推論、取引成績、本番注文は未認証。Excel発注機能をONにしない。

Windows CIでは `-OfflineSelfTest` のみ実行。COM、Excel、市場、注文、ユーザーのファイルに一切触れない。

## 2026-10-11 追記：非公開の市場データ保存

最新版のRssChart診断は、元の匿名行数に加え、読み取った5分足を閉足時刻検証後に **PC内だけ** `%LOCALAPPDATA%\ArkTerminal\No12\market-readonly-observed.json` と同じ場所のSHA256 receiptに記録する。Excelの一時Workbookや候補一時JSONは保存しない。口座・保有銘柄・注文情報は含まず、GitHubやチャットへ転送しない。実際のBroker配信到着時刻とNative State9/Entry/EXITの推論は未認証。取得できない場合は古いファイルをFRESHとして使わない。

現在のPC worktree HEADは初期版の可能性があるので、火曜日にテストする前に**最新PR #592のcommitを検査してから取り込む**。発注不可のまま実行し、`NO12_RSS_CHART_PRIVATE_READ_ONLY_RECEIPT=True` が出ても自動売買解禁とは扱わない。


## 2026-10-11 追加：直近5営業日と最初の市場バー観測の分離

No.1.2最新probeは、Windowsで観測した500本のチャートデータを元に、
**履歴（Historical Backfill）**と**実際にそのPCが観測した新規足**を区別します。
歴史的Backfillは「当時すでに受信済みだった」とは扱いません。
過去5営業日の完全性はJPX現物カレンダーに基づき、必要日ごとに66本を検査します。
営業日不足・始値端/終値端の欠落・欠測はHISTORY_SOURCE_INCOMPLETEです。

新たに `%LOCALAPPDATA%\ArkTerminal\No12\first-seen-7203-T.json`
にローカル初観測時刻のハッシュ連鎖を保持するようにしました。
同じ最新確定足は二重保存しません。再受信で既存OHLCVが変更された場合、
記録破損、時刻巻き戻り、競合プロセス、stale receiptを検出した場合はBLOCKします。
観測間隔が飛んだ場合は `GAP_OR_CLOCK_MISMATCH` で明示します。

画面には口座・株価の実数値を表示せず、`NO12_5DAY_HISTORY_STATUS`、
`NO12_5DAY_HISTORY_PREVIOUS_SESSIONS`、`NO12_FIRST_SEEN_STATUS`、
`NO12_FIRST_SEEN_CONTINUITY` の匿名状態のみを追加します。
この初観測は**PC時刻**でありBroker配信到着時刻の証明ではありません。
1銘柄のProbeでオンラインSelector/First Entry/State9/EXITが完成したとはしません。
実注文とExcel注文機能はOFFを維持してください。
