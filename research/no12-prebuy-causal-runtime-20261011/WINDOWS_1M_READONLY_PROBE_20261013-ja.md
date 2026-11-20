# 10/13（火）MarketSpeed II RSS 1分足 READ ONLY 実機検査

**現状:** Windows上で未実行。CIはExcel/MarketSpeed IIを使わない構文・静的・合成テストのみ。

## 実行条件

1. MarketSpeed IIを本人が起動・ログイン。Excel RSSの発注許可はOFF。
2. 既存No.1.1 UI2の30秒口座監視を停止し、既存の口座Workbookを安全に閉じる。個人保有・Safety台帳・既存注文設定を変更しない。
3. No.1.2隔離worktreeを最新検証済みPR #592 HEADへ更新し、NodeとWindows PowerShellを確認する。main/Frozen/PR #591は変更しない。
4. 同じPCのExcelで他のWorkbookが1つでも開いている場合、診断スクリプトは開始を拒否する。

## 検査コマンド（隔離worktreeルートから）

    powershell -NoProfile -ExecutionPolicy Bypass -File research/no12-prebuy-causal-runtime-20261011/windows/Probe-No12MarketRss1mReadOnly.ps1 -OfflineSelfTest

実機でExcelを起動するのは以下のみ（前提条件を満たした後）。

    powershell -NoProfile -ExecutionPolicy Bypass -File research/no12-prebuy-causal-runtime-20261011/windows/Probe-No12MarketRss1mReadOnly.ps1 -WaitSeconds 20 -HistoryBars 2000

公開固定サンプル銘柄7203.Tの1Mを1関数・最大2000本で取得する。本人の個人保有銘柄を入力に使用しない。スクリプトは**一時Workbookを新規作成**し、保存せず閉じる。注文関数・取消関数・実注文・Excel既存ブック書き込みはゼロ。

## 検査結果

画面は株価・口座番号を出さず、1M取得行数、5営業日履歴の完全性、ローカル検査結果を匿名表示する。

- NO12_1M_PRIVATE_READ_ONLY_RECEIPT=True はPCローカルの受信データを検証し、privateファイルへ書いた意味のみ。
- NO12_1M_HISTORY_STATUS=BACKFILL_1M_PREVIOUS_SESSIONS_AVAILABLE は通常営業日330本×5日が完全だった場合のみ。HISTORY_SOURCE_INCOMPLETEなら必要日の欠測や時刻ラベルを確認する。
- LOCALAPPDATA/ArkTerminal/No12/market-1m-readonly-observed.json は必要市場項目のみ、market-1m-readonly-receipt.json はSHA256のローカル記録。口座情報・Workbookは保存しない。
- SOURCE既知時刻・PC受信時刻は同じではない。historicalBrokerArrivalCertified=false、originalNativeState9Certified=false、productionReady=false、orderTransmission=false。

5Mの既存READ ONLY診断とは**順番に**実行し、同時にExcelを複数開かない。診断終了後、既存のNo.1.1監視を通常手順で復旧し、OwnershipとSafetyが元のままか確認する。

## 未認証

秒単位RssMarket/RssTickListのPC到着遅延、数千銘柄Selectorの実市場供給、正規First Entry/State9推論、H2/H3/H5の2026日付モデル選択、Capital/EXITの本番接続、注文ID/部分約定照合、独立OOSは未認証。**1M/5Mが取得できても自動発注を許可しない。**
