# 📌 寄り前Selector - 今回の到達点

未完成。実データ測定・旧Frozen比較・実原本との全family結合が未完了。
工学実装と人工private E2Eは進めたが、市場モデルは作成していない。
開始HEAD2fce2c02fce77bc7368cd00989a72fea78878e5c、PR#593の同じDraft研究。
最終HEAD・CI run・配布ZIPのhashはPR本文とprivate checkpointに保存する。

## 📊 市場測定

| 寄り→High | 新候補N/割合 | 前日売買代金基準 | 厳密ランダム期待 | 旧Frozen |
| --- | --- | --- | --- | --- |
| 0〜<1% | 未測定 | 未測定 | 未測定 | 未測定 |
| 1〜<2% | 未測定 | 未測定 | 未測定 | 未測定 |
| 2〜<3% | 未測定 | 未測定 | 未測定 | 未測定 |
| 3〜<4% | 未測定 | 未測定 | 未測定 | 未測定 |
| 4〜<5% | 未測定 | 未測定 | 未測定 | 未測定 |
| >=5% | 未測定 | 未測定 | 未測定 | 未測定 |
| 正確な0%・UNKNOWN | 未測定 | 未測定 | 未測定 | 未測定 |

選出数・評価可能分母・銘柄日数・Open→Low/Close・日別tail・時間帯残存機会
も未測定。空欄/nullは0件ではない。H>=Oは構造上の性質で、上昇精度や安全性
ではない。Highは約定売却価格や実現利益ではない。

## 🧾 原本・保護・実使用

A〜E台帳の1718原本/24103114219bytesの保存記録を確認した。今回実照合は
12原本/354759644bytes。E8原本はCRCとヘッダー、添付5〜8月分足4原本は
サイズ/SHA256を照合。市場価格・財務数値の解析0。gzip全体の機械的通過と
ヘッダー読取りは行っており、原本bytesを全く開かなかったとは主張しない。

| 項目 | 状態 |
| --- | --- |
| 台帳 | metadata照合。57 Development識別日を残し、native前日Tick期間に合わせ47日 |
| fit予定 | 30日、2024-10-02〜11-14。実fit0、銘柄日0 |
| 較正予定 | 10日、2024-11-15〜11-28。実較正0、銘柄日0 |
| Report予定 | 7日、2024-11-29〜12-09。実測0、銘柄日0 |
| Exposure | 過去閲覧済みDevelopment。Fresh/OOSではない |
| 保護 | REPORT19追加開封0、Validation/OOS/Reserve/Common Holdout開封0 |
| 実計算/fit使用 | 市場feature列0、行0、fit使用列0 |

3713は登録schema数で実使用数ではない。日週月足、前日minute/session・Tick、
財務/valuation/決算予定/TOPIX/投資部門別/過去cross sectionのadapterを追加。
市場原本への全結合と、正式State/Dictionary lineageの結合は未完了。

## 🔧 実装・検証範囲

SQLiteの並び順処理と原本checkpoint、float64列保存、Null/不正の分離、
日付別市場時間、前日Tick窓・同値同数量保存、source/unit/PIT根拠、
Report先読込み分離、ラベルなしexport、trusted model再読込み、正負Close
全1%区間、Fractionによる日別ランダム期待、独立再集計を実装。日別/
Top1・3・5・15/市場・規模・過去流動性・地合い/up×down、下落側とblock
感度を含むpaired日bootstrap、後半残存機会の計算部品も追加。

既存32+37と追加16人工試験を維持。native形式の人工gzipからcache/modelへ
接続し、Reportラベルを物理的に隠してtrain/predict、新processで同じ候補hash
を復元、復旧後の評価・別算式検算まで確認。別作者の盲検監査ではない。
最終releaseログとHEAD CIで確認する。

市場head fit0/較正0、追加model・target・K・threshold探索0。人工工学実行は
市場budgetと分ける。Native実規模RAM/時間は未測定。環境は9CPU、
RAM約9.8GiB、当初空き約26.9GiB。これをnative性能PASSにはしない。

## 🚧 実証済み障害

1. 現在の再利用根拠未確認。最新記録は10月6日の条件付き有効確認。
   予定期限だけで解約済みとは断定しない。根拠なくtrueへ書換えず、
   実preflightはCURRENT_MARKET_REUSE_BASIS_UNRESOLVEDで停止した。
2. private CLIは認証不足。大きいgzipのfetch_file(base64)は空payload、
   fetch/fetch_blobは非UTF8を拒否。Eの小さい原本は取得できたが、現在のlive
   行を2024年履歴の代用にしない。C2024-10原本も空payloadだった。
3. AのTick2024-10/11/12 assets614859581/614861315/614863556はmetadata200、
   合計2109245683bytes。binary未取得。無認証binary readは404。A/Eの保存run
   に原本artifactは0。新provider取得・secret/公開範囲変更0。

必要なのは現在有効な再利用根拠と、正規認証で必要original bytesをprivateへ
渡す経路。秘密値の貼付けは不要。正確なobject/ref/hash/asset一覧はprivate
checkpointに保存する。4添付分足は今回の47日とは別期間で代用しない。

## ▶️ 再開

実在するCLI。repo rootから実行し、/PRIVATEを確認済みprivateRootへ置換する。

~~~bash
python research/independent-long-selector-20261012-v1/preopen_session_admission.py --metadata-bundle /PRIVATE/admission-request.json --output /PRIVATE/admission-new
python research/independent-long-selector-20261012-v1/build_preopen_native_bundle.py --request /PRIVATE/native-request.json --output /PRIVATE/native-bundle
python research/independent-long-selector-20261012-v1/run_preopen_selector.py --bundle /PRIVATE/native-bundle/bundle.json --output /PRIVATE/run --stage train
python research/independent-long-selector-20261012-v1/run_preopen_selector.py --bundle /PRIVATE/native-bundle/bundle.json --output /PRIVATE/run --stage predict
python research/independent-long-selector-20261012-v1/run_preopen_selector.py --bundle /PRIVATE/native-bundle/bundle.json --output /PRIVATE/run --stage evaluate
python research/independent-long-selector-20261012-v1/predict_preopen_watchlist.py --request /PRIVATE/predict-request.json --output /PRIVATE/watchlist-export.json
~~~

actual header/dateField/単位/公表根拠/storage receipt/正確なallowedRecordDatesを
bindする。Tickヘッダーは実確認できていないので推測で埋めない。financeの
単位/訂正、dated普通株/lot、RAW action basis、profile lineageを監査し、実計算
したFEATURE_SOURCE_COVERAGE.csvを固定してから1candidateをfitする。
現在のcoverage表は未計算を明示。入力復元時はhashを照合し、完了済みfitは
再起動しない。学習/model/code/inputの日付とsoftware/hashをreceiptへ記録する。

旧主比較はmin-price75正式版。日中Top5×10と朝15の条件差、親modelの既存76日
fitに新Report日も含まれることを表示。旧全日Highは事後記述、旧future5m
Highは別表に残す。保護日を開けない。

## 🔒 判定

Engineeringは人工private E2Eの部分PASS。Market measurement/Legacy比較未完了、
Research quality/Live readinessはNOT_CERTIFIED。Windows/RSS実機、毎朝更新、
流動性/下落tail/較正・selection bias・過学習を未認証のまま保持。
全11フラグfalse。main merge/force push/provider新規取得/注文/本番昇格0。
自動freeze・main merge・Entry/EXIT/資金回転へ進まない。
