# No.1.1 学習準備 / RSS追加取得へ移る境界（2026-10-13 JST）

## 今回の依頼と制約
利用者指示：保存済み原本＋MarketSpeed II RSSで取得できる範囲だけを使用し、RSS取得が必要になるところまで進める。新しい市場データproviderの探索・購入・取得はしない。Frozen No.1.1、PR #591、別Selector研究PR #593、main、口座原本は変更しない。新しい学習結果の自動昇格・実注文は行わない。

## 実行したローカル準備（ユーザー提供ZIPを使用）

- Capital v4 private nested packageを復元し、元PACKAGE_MANIFESTの142件をSHA256照合：142/142。
- Structural EXIT v2 private source/trace packageを復元し、MANIFESTの1,606件をSHA256照合：1,606/1,606。
- H2/H3/H5の元runtime特徴量・teacher・First Entryをentry_idで1,600/1,600結合。期間2025-05-30〜2025-08-25の58営業日。58日という元研究期間を一般的な学習最低条件へ読み替えない。
- 元State9/Path trace 1,600ファイル・523,200行を読み、元core_features.projectの数値27列・カテゴリ7列を1,600件すべてで原本runtimeと照合一致。
- H2/H3/H5計24モデルのhash・train ID・学習側だけの前処理を照合：24/24。モデル係数の新しいfitは0。
- 元の8時系列分割に沿いX_train/X_test/y_train行列を生成。20→25→…→55学習営業日、次の5日（最終3日）を検証区間。検証対象1,039行/38営業日。これは既存Developmentの再構築でありfresh OOSではない。
- 原本の前処理は欠損0＋欠損indicator、train-only mean/std、train-only category vocabulary。LogisticRegression固定設定：L2/C=1.0/lbfgs/max_iter=2000/random_state=57/class_weight=null。
- 元教師の54件のterminal Potential=0慣例を変更していない。教師は特徴量・購入前source viewと別ファイルへ保存。

## 購入前データの切り出しと残課題
BUY_INTENTまでのState/Path prefix、確定足と仮定できる過去価格、P1 score/threshold、Selector時刻を1,600件分のsource viewへ切り出した。実fill時刻/価格、future High、label、EXIT結果はこのviewに入れない。

**これは完成した購入前27列のfeature adapterではない。** 元のfill時点Xを購入前Xとして使わない。切り出しでは状態未観測910件、最新の保存価格足の古さ最大295分を検出した。値を埋めて正常化せず、利用可能性・sourceの不足として保持。正しいas-of feature mapping、native Selector/First EntryのRSS入力対応、教師対象時点の整合は残っている。過去の実受信時刻はUNKNOWNのまま。

## 保存済み市場原本と追加取得対象

2025年5〜8月の4つのCSV.gzを実際にstream走査：8,939,727 / 9,109,854 / 9,674,299 / 9,565,067行。合計37,288,947行・83営業日。raw code 4,332種類のうち、明示的な末尾0コード規則で4,328種類をRSS symbolへ変換。規則に合わない4件は別台帳に保持し、勝手に切り落とさない。

raw83日をそのまま学習83日とは呼ばない。モデル入力・教師が揃う元候補は上記58日/1,600件。現在の上場全銘柄集合・普通株適格集合が4,328銘柄だとは認証していない。

取得用順序は元の全watch950銘柄（NO_ENTRYを含む）を先に、その後に残り保存raw銘柄を安定順で並べる。利益/ラベルで取得銘柄を選ばず、売買Selectorにも転用しない。symbol一覧・市場原本・学習係数・行単位データはprivate成果物のみ。新規の2026年上場銘柄等がこの古い集合に含まれる保証はない。

ユーザー提供RSS7203.T証跡SHA256 d46d1c2bfb49c46f571ad480ef01662da2fd054119bb44c80dc4eb4917de4735 を検査。10/1,2,5,6,7,8,9,13の各327本、1M合計2,616本。5M197本との完全5本組比較は191/191一致、比較不能6本。市場の足仕様認証ではない。先頭10/1の前営業日入力はこのJSONにない。新しい2026年教師付き学習行は0。

## 実装した次の収集ツール
`windows/Capture-No11RssTrainingBatchReadOnly.ps1`

- private symbol TXTを入力とし、最大20銘柄/temporary workbook単位で順次取得。
- 1M又は5M、要求本数最大3,000。旧Workbookに存在するchart/trend formula数を差し引き、合計50を超えれば停止。
- 同じ既存RSS有効Excelへ接続する。口座・市場の原本Workbookはidentityとformula容量のみ検査し、口座値を取得・出力しない。
- 新しい未保存WorkbookだけにRssChart式を書き、原本は変更・保存しない。各wave後にtemporary workbookを閉じてから次へ進む。
- symbol毎のsource JSON、SHA256、progress ledgerをprivateディレクトリへCreateNew保存。未取得/不正は記録し、全件不取得waveは停止。
- 最大3,000本指定で3,000本の返却は保証しない。過去known_at、vendor decimal元token、確定足ラベルの認証もしない。
- 初回は`-MaxSymbols 20`でWindows実データのbatch容量/書式を確認する。このツールの本番RSS取得実績はまだ0。

`tests/no11_rss_training_batch_safety.test.mjs`はBOM/入力上限/immutable/no-order規則を検査し、Windows CIでPowerShellのOfflineSelfTestを実行する。CIの合成検査を実機収集成功と呼ばない。

## 現在の判定

PREPARATION=EXISTING_INPUTS_RESTORED_AND_PARTITIONED
NEXT_PHYSICAL_INPUT=MULTI_SYMBOL_RSS_SOURCE_CAPTURE
new_fit=0
new_2026_supervised_rows=0
new_external_market_provider_acquisitions=0
productionReady=false
orderTransmission=false

RSSを追加取得しただけでは学習完了しない。source検査→native候補/Entry生成→正しい購入前X/教師結合→学習/過去時系列検証→別名モデル保存、の未完工程を保持する。
