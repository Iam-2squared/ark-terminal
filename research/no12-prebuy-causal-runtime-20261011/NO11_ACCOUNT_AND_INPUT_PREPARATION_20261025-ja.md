# No.1.1：当日入力の組立と既存Shadowへの口座読取接続

既存PR #592だけの変更。Frozen計算・モデル・Selector時刻・別branchは変更しない。実注文はOFF。

## 口座読取

既存の `Run-No11ReceivedSessionReadOnly.ps1` に任意の `-AccountWorkbookPath` を追加した。これを指定した通常起動では、読み取り専用の `Observe-No11AccountReadOnly.ps1` を一緒に起動し、終了時にstopファイルで停止する。Excel全体の強制終了・Workbook保存・注文許可変更はしない。既存の `-ResumeRun` と同じ台帳の復帰経路は変更しない。

口座ブックは絶対パスで一意に照合する。既存の市場ブック・収集用一時ブックが同時に開いていてもよい。元のbulk読取ヘルパーはblob `f8be4d704ebad539762471ba62476c32b02a65b1`を照合して再利用する。変更はブック選択、ヘッダー確認済みの注文行への口座/売買/取引区分追加、全行が真に空欄の場合の0保有受入。元Excelのレイアウトは変えない。

新しい観測JSONは、元の `inspectReadOnlySnapshot` と追加の数量・時刻・注文番号照合を通す。現在の個人保有、個人注文、個人約定銘柄を当日Shadowの新規BUYから除外する。注文番号ごとの累積約定数量後退、同じ番号の銘柄・口座・数量変更、未確定注文の消失は記録し、再起動だけでは解消しない。未知の通常注文状況も新規BUYを止める。

読取停止・欠損・タイムアウトでは、新たな模擬BUYを止め、既知の模擬未約定BUYにローカル取消要求を出す。一方、既存の仮想保有のState9/EXIT/15:20経路は動かす。UNKNOWNは勝手に取消済みへ変えない。実口座の残高・保有・約定を模擬台帳へコピーしない。

口座観測ファイルの保存先はconsumerのprivate-rootに永続化される。環境変数を消して再起動しても口座検査が黙って無効になることはない。読み取り時刻はPCが観測した時刻であり、楽天の更新時刻や鮮度を認証したものではない。特に `RssCapacityList` の完了表示だけで買付余力の再取得完了を保証しない。

`account-observation-latest-report.json`、`account-observation-state.json`、`account-observer-binding.json`はprivate保存。実口座残高を含むのでGitHubや公開ログには上げない。既存のportfolioレポートにも口座観測欄が増えるが、`realAccountExecutionConnected=false`、`realCashUsedForFunding=false`、`realFillsAppliedToShadow=false`のまま。

## 当日入力を一度に組み立てる

`Prepare-No11ReceivedInputsReadOnly.ps1`は、既存の日足exporterで選んだ最大50銘柄をそのまま使用する。全銘柄の再取得や新しい順位付けはしない。

1. 既存の日足runからPASS maskとChart50計画を出す。
2. `Capture-No11SessionReferenceReadOnly.ps1`が、RssMarketの銘柄コード・市場コード・現在日付・前日日付・前日終値・当日基準値・市場部名称・単位株数・権利落日・配当落日・中配落日を、保存しない一時Workbookで取得する。
3. `no11_prepare_received_inputs.py`が、その原本と**外部で確認済みの銘柄属性・価格基準・企業行動の証跡**を照合し、既存の `ARK_NO11_DATED_MASTER_RECEIPT_V1` へ組み立てる。
4. 既存の前日RSS archiveを元の変換・State9正規化経路へ渡し、previous-contextとbootstrap設定のコピーを出す。
5. 同じランチャーのpreflightを実行する。`-StartShadow`を明示した場合だけ、preflightではなく既存の注文OFF Shadowを起動する。

前日データがない場合は、先に既存の `Prepare-No11PreviousArchiveReadOnly.ps1` の取得経路が必要。今回、そのPC側の実物が揃っているとは主張しない。

### 外部証跡の入力契約

`--security-evidence` / `-SecurityEvidence`はprivate JSON。schemaは `ARK_NO11_SESSION_SECURITY_EVIDENCE_V1`。`validForSession`、`knownAtJst`、`reviewStatus="EXTERNALLY_REVIEWED"`、`productionReady=false`、`orderTransmission=false`を持つ。各rowsには `symbol`、`segment`（PRIME/STANDARD/GROWTH）、`sector`、`commonEquity`、`corporateActionsCleared`、`priceBasisVerified`、`reviewedPreviousClose`、`sourceDocumentSha256`配列が必要。

これは未確認項目をtrueへ埋めるテンプレートではない。以前の外部確認結果がない項目は入力不足のまま停止する。各根拠ファイルは `-EvidenceDocuments` 内の `<sha256>.source` としてbytesを照合する。hashは改変検出であって、内容の正しさ・発行元・企業行動不存在を自動認証するものではない。

RSSの前日終値と当日基準値が同額でも、それだけで企業行動確認済みにはしない。部名称から普通株かETFかを勝手に推定せず、業種をRssMarketから取れると偽らない。今回の取得項目は楽天公式HTMLの一覧で確認したものだけを使う。

`Prepare-No11ReceivedInputsReadOnly.ps1`の必要引数は既存設定の`-ConfigFile`、確認済み`-SecurityEvidence`と`-EvidenceDocuments`、実在する`-PreviousCaptureDir`、リポジトリ外の`-OutputRoot`、既存の固定依存環境の`-PythonExecutable`。任意の`-AccountWorkbookPath`は既存Runnerへ渡る。入力は当日朝に実際に観測して準備し、翌日の受信時刻を前日に捏造しない。

参照した公式仕様：
- https://marketspeed.jp/ms2_rss/onlinehelp/ohm_002/ohm_002_07.html （RssMarket出力項目）
- https://marketspeed.jp/ms2/onlinehelp/ohm_005/ohm_005_01.html （出来有・取消中・取消済等の注文状況）

## 検証と未完了の区切り

合成口座・合成RSS形状・テスト用モデルで、口座障害でもEXITが残ること、個人銘柄除外、読取先の復帰、累積数量の異常、当日masterから元State9 previous-context・起動設定への通過をテストする。Windowsの構文・元bulkヘルパーのhash照合もCIで検査する。CI成功は実Excelの成功ではない。

この変更は、口座**読取**と市場入力**組立**のコード接続。実注文・取消を送信するtransport、Ark発注IDへの実約定帰属、実保有への自動EXITは完成していない。実発注を有効化するコードやSafety解除は追加しない。実口座残高から発注可能額を算出して動かしたとも主張しない。

実データ・元非公開モデル・Windows/RSSを使う実機確認と、確認済み外部証跡の実物準備は引き続き必要。2026-10-27の実売買開始をこの変更だけで認定しない。
