# ARK No.1.1 — Launcher 日次・週次ループ

## 自動化対象

これまで11月4日固定だった41銘柄ハンドオフを、翌日のものとして名前だけ書き換えることはない。Launcherの「WEEKLY / AFTER-CLOSE RSS UPDATE」から元の週次・日次RSSジョブを実行し、元のChart50・G1・前日1分足・JPX公開出典を検証して、**翌営業日専用の新しい不変handoff**を出力する。

- 週最終営業日後：実際のRSS全市場約4,328銘柄の日足から翌週の母集団を生成
- 通常の引け後：週次候補だけのD100・G1更新、翌日候補、前日1分足取得
- 翌営業日：Tradeボタンはその営業日に一致する保存済みhandoffを自動選択し、元のマスター準備・Entry/Capital/EXIT接続へ渡す
- 銘柄属性：JPXの普通株・近接権利日を機械的にチェックし、Entryからの除外だけを実施。元のランキングや閾値は変更しない
- Excel：元の2冊だけでなく、設定された正規の発注ID用3冊目が開いていても夜間RSS収集を許可する。未知の追加ブックは拒否。ブックの開閉・保存、注文セルの更新はしない

市場やRSSが欠損している場合には、古い日足を翌日に付け替えない。日次の証拠ZIP、手動価格入力、銘柄ごとの承認は要求しない。

## Launcherの操作

Market Speed II RSSと元のExcelを接続し、営業日18:00以降に「WEEKLY / AFTER-CLOSE RSS UPDATE」を押す。長時間ジョブは子プロセスとして実行され、Launcherのログから状態を確認できる。成功すると NO11_DAILY_CYCLE_STATUS=NEXT_SESSION_HANDOFF_READY が出る。翌営業日は普段どおりTradeボタンを使用し、従来の当日発注承認は1回だけ必要になる。

重要：この追加コードだけでは、18:00に毎日自動起動するWindowsスケジュールは登録しない。元RSSはユーザーの対話型Excelセッションが必要。ボタン操作なしの無人運用、および実注文/実約定/EXITの成功までは保証しない。

## 内部ファイル

- %LOCALAPPDATA%/ArkTerminal/No12/unified-launcher/daily-cycle/<日付>/master-materials：翌日マスター原本と新handoff
- daily-cycle/prepared-days/YYYY-MM-DD.json：日付・選定数・SHA256付きの引継ぎポインタ
- daily-cycle/logs/original-nightly-*.log：既存の週次・日次RSSジョブの出力
- unified-launcher/daily-cycle-install-*：適用前Launcher、夜間RSS収集スクリプトなどのバックアップ

元のFrozen Selector、State9、P1、H235、Capital V5、構造EXIT、現物一般・100株・MAX3、RSS買付可能額方式、注文の当日承認の意味は変更しない。新しいコードは未完了の取引を取り消したり、本人の保有をARK保有として採用したりしない。
