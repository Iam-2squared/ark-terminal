# 🔌 GitHubプラグイン限定の実データ入力整備 — 2026-10-13

未完成。今回、ブラウザ認証を進めずGitHubプラグインから実原本を追加取得した。
全入力familyの結合、市場fit/較正/Reportと旧Frozen比較はまだ未完了。
source ingestをSelectorの性能測定や普通株eligible universeの完成とは呼ばない。

## 📊 今回の実原本・取り込み

| 項目 | 今回の実測/確認 |
| --- | --- |
| 追加原本 | Eの保存済み日足API JSON40件、小容量native gzip4件 |
| 追加原本サイズ | 48,898,922 bytes。全44件で原本SHA256・bytes一致 |
| 日足source ingest | 既存1日と合わせ41日、180,161行、49,836,576 bytes |
| 財務・決算予定・TOPIX・投資部門別 | 10月/11月の8原本、5,567行 |
| 全source ingest | 49原本、185,728行 |
| 内訳 | DAILY180,161 / FIN_SUMMARY4,318 / EARNINGS_DATE1,172 / TOPIX41 / INVESTOR_TYPES36 |
| 現在privateへ保持したE原本 | 53件、50,590,193 bytes。残り4件はcalendarおよび旧header-only原本 |
| 累積原本hash照合 | 57件、404,873,995 bytes。過去の4添付分足を含む。今回全件を再取得した意味ではない |
| 独立source件数確認 | 標準JSON/CSV別経路とreadonly SQLiteの件数一致 |
| 前営業日 | 固定47対象日すべて原本calendarと台帳が一致 |
| 実計算feature / fit使用feature | 0 / 0。source行があることとfeature投入を区別 |

日足の母数は原本に収録された証券全体であり、普通株候補の銘柄日数ではない。
dated master未結合のため、普通株/優先株/ETF等の最終eligible集合は未確定。
原本のrepository、logical object key、actual storage path、Git blobとsource commitを
対応づけた。取得は全て正式なプラグインのUTF8または小容量base64応答から行った。
API JSONの再serialize、gzipの再圧縮、hashを合わせるための原本変更は行っていない。

source-only日足取り込みは6.484秒、peak RSS60,308KiBだった。
これは41原本の解析/SQLite保存だけであり、Tick全量・数千feature・モデル学習の
native規模RAM/時間資格認証ではない。4family側のsource ingestは別process。

## 🛡️ admission・公開時点・Report

固定計画はfit30日、較正10日、後続Report7日のまま。今回実行したのはsource ingestのみ。
全区間は既閲覧Developmentの許可済み再利用で、Freshへ戻していない。
REPORT19、Validation/OOS/Reserve、State/Dictionary Common Holdoutを解除していない。
Reportの株式日足原本は0件追加取得、Report label評価0、保護outcome数値追加開封0。

財務等の公表日は非営業日を取り得るため、unsealed Development内の10月1日〜
11月28日のcalendar dateをsource用に明示許可した。label sessionの分割とは別。
月次native原本は全圧縮byteとCSV行を機械的に通過した。未許可日行は出力/価格集計/
学習へ入れず、lexical traversalをaccess ledgerへ記録した。未開封byteとは主張しない。
公開時刻、実受信、改訂履歴、単位、因果的調整価格basisのfull snapshot認証は未完了。
source-only contractをfull candidateへ昇格させることは引き続き拒否する。

独立source監査は同じ実装者による別経路で、別作者の盲検監査ではない。
価格bucketの独立検算はまだ未実施。今回のsource件数一致をその代わりにはしない。

## ✅ コード・CI

検証code commit: `73150bf9cfdb5835e1e458bcb0ed327272652854`。
PR #593はOpen/Draft/未merge、base Freezeは`10c94c92c4bd2a59a22744667fd0210252602df4`。
変更は研究パス内の取得処理・人工試験と今回の非復元的な状態文書だけ。

GitHubプラグインのsmall-file base64応答をstrict decodeし、原本bytes/hash、private
root、上書き拒否、1MiB上限を検証する経路を追加した。Releaseダウンロードを
装ったものではない。大容量の空応答、壊れたbase64、boolean size、範囲外pathを拒否。

専用CI run[38319228544](https://github.com/Iam-2squared/ark-terminal/actions/runs/38319228544)、
job115043071525で32+72=104 testsと人工smoke PASSを実ログで確認。
補助run38319228485/38319234999も成功。公開artifact11777994217はcode-only105,938bytes。
価格行、private source envelope、日次候補、市場モデルを公開していない。

今回の人工head fit/較正はlocal10/10、CI20/20。累積は各130。
市場fit/較正は各0。target、モデル設定、K/cutoff、price75、日付、threshold探索0。
原本文末LF付加による未検証copy4件は隔離し、既存のenvelope materializerで正確な
原本を取得し直した。resource wrapperの起動エラー2件も記録。市場fitは開始していない。
旧1日分のSQLiteが前checkpointに含まれていなかったため、その日だけ新41日shardへ
再構築した。今回のcheckpointではSQLiteも保存し、次回の重複取り込みを避ける。

## 🚧 残障害と再開位置

プラグイン認証は確認済み。障害を「GitHubへサインインしていない」とは扱わない。
GitHubプラグインは大容量Contentsのbase64本文を返さず、Release asset binaryの
ダウンロードtoolを提供していない。A/C/Eの保存runも原本artifact0件を再確認した。
台帳の1,718原本/24,103,114,219bytesが、この環境へ全コピーされたわけではない。

必要な大容量原本は主に以下。privateのREQUIRED_ORIGINALS_PRIVATE.csvに正確な
ref/object key/bytes/hashを保存済みで、推測したmain/raw/Releaseへ置き換えない。

| 必要source | 正確な対象 |
| --- | --- |
| A前日Tick | 2024-10/11/12、asset614859581/614861315/614863556、計2,109,245,683bytes |
| C前日分足/残存機会 | 2024-10/11/12の保存gzip、計251,968,352bytes |
| E dated master | 2024-10/11/12の保存gzip。今日の一覧へ置換しない |
| E valuation | 2024-10/11/12の保存gzip。Dateだけで公表時点を認証しない |
| 日足長期履歴 | 初回fit日前のlookbackを追加取得・照合する。今回の41日だけでは完成しない |
| State/Dictionary | 前日原本と正式な上流fit lineage、保護/可用性照合が必要 |

日足APIのUTF8取得経路は利用できる。残る大容量原本には、正式なGitHubプラグインの
binary転送機能、またはimmutable原本の許可済みprivate受渡しが必要。ブラウザ認証、
秘密値の会話貼付け、data repoのpublic化/書込み、無断のprovider再取得は進めない。

privateに原本、source requests、hash receipts、native SQLite、別集計script、監査結果を
保持。実在CLIは既存`preopen_plugin_transfer.py`と`preopen_native_source_canary.py`。
新request名とreceiptはprivate bundleに対応づけた。full builder/train/predict/evaluateの
段階へは未昇格。全familyのPIT/basis/coverageを解決してから有限1candidateへ進む。

## 🧪 測定・運用判定

| 判定 | 現在 |
| --- | --- |
| ENGINEERING_PASS | 部分PASS：人工/private I/Oと許可済みsource ingest |
| MARKET_MEASUREMENT_COMPLETE | false |
| LEGACY_COMPARISON_COMPLETE | false / LEGACY_COMPARISON_PENDING |
| RESEARCH_QUALITY | NOT_CERTIFIED |
| LIVE_READINESS | NOT_CERTIFIED |

寄り→High6bucket、UNKNOWN、累積到達、Low/Close下落tail、同条件TopK/ランダム、
日別/順位別/時間帯残存機会と旧Frozen比較はすべて未測定。0件と推測しない。
旧min-price75の証拠2件はprivate保持したまま、numeric outcome比較は未開封。
旧の日中Top5選出集合へall-day Open→Highを付ける場合は事後記述であり、
寄り前能力や売却利益の同条件比較にはならない。
H>=Oは構造上の性質であり、下落損失や資金集中の安全性の認証ではない。

全11安全flags false。注文・main merge・force push・保護解除・新provider取得0。
RSS/cacheの継続更新とWindows実機は未認証。Entry/EXIT/Capitalへ進んでいない。
今回のCIは終了済みで、外部の市場学習jobを稼働中とは説明しない。


## 2026-10-14 実市場工程完了（以前の未実施記録を更新）

必要99原本、feature175,897行、登録554/FIT観測464/fit使用463。1candidate/10head/10較正、7日105候補を事前固定。主6bucket68/18/6/7/1/2、UNKNOWN3無約定。High≥1%=34は基準56以下、Low≤−1%=20、Close負35、品質未承認。旧350events/268銘柄日の2表、元原本別経路再計数と保存先復元PASS。市場job0、注文/実機PASSなし。WORK_HANDOFF_MA4_20261014-ja.mdとREPORT_AGGREGATE.jsonを参照。
