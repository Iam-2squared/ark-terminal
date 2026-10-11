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
