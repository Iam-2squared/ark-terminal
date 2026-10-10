# Phase57 G7 — Mechanical Adjudication

記録: 2026-09-22 10:22 JST  
開始確認HEAD: `e84fc07aef79448367a9ed198436ea05d277552d`  
対象: PR #587 / `research/phase57-long-only-cash-equity`

**結論: G7 v1のFAILを維持。レビュー用パッケージに時刻ずれを確認。State分類の全面改造ではなく、表示・時刻契約・レビュー資料の修正が先。**

これは作成者チャットによる非blindの機械的裁定であり、独立Reviewer CやG7合格ではない。A/B提出ラベル、既存G7配布ZIP、既存G7採点、mechanical-v1、State v2候補仕様を上書きしていない。

## 1. 原本・採点の再検証

実際にマウントされたZIPからadmin keyを読み、GitHubのA/B CSVと照合した。過去の会話で手書きされた代替keyは採用しない。G7-016と028はACTUAL、G7-005はCONTROL。

| 原本 | SHA-256 |
|---|---|
| Review ZIP | `303acb5c66b586917b75d1a48bb0e4b0fc848b7d48d86f9d63bb8273283676c1` |
| Admin ZIP | `15e389cbf3638e89e5555e934fe73152b3d4782b5304d4348372ea407d3d932b` |
| G measurement ZIP | `cc921c476af1079344975daa78e89fe03ee0dfc20ee62333170199178ade795e` |
| Measurement manifest | `4e11b8eb576dcdd0552f2461c699f57bdabc1db37d8e4c2be9a389a80748d6d1` |

Measurement manifestの179ファイルのSHAを再検算し、不一致0。77,214 checkpointのkey重複0を確認。実データの新規取得ではない。

A/Bの原文Git blob: A=`8b73e9c708c261e7836004754a4200c4b2cecb14`、B=`7fb1e841406b119fd7f5ce6a95b166415823180c`。今回のローカル採点入力はこれらからのタグ転記projectionであり、原文CSVを書き換えたものではない。

| 従来のany-issue-tag採点 | A | B |
|---|---:|---:|
| 回答 | 44/44 | 44/44 |
| Controlにissue tag | 6/8 | 7/8 |
| 実市場36件にissue tag | 19 | 16 |

実市場の二値一致: 19/36 = 52.7778%。Cohen's kappa = 10/163 = 0.0613497。前回数値を再現。両者問題なし10、Aのみ問題10、Bのみ問題7、両者問題9。A/B不一致17件、どちらかの疑義26件。

Control ID: 005 / 012 / 017 / 018 / 019 / 027 / 037 / 042。

**採点の限界:** 既存scorerは「何かissueがある」を検出と数える。Aの005は一般的欠損を指摘しただけで、潰された複数reasonの欠落を特定していない。Bの042はFuture card混入を指摘したが、欠落した第2censor flagそのものを特定していない。元スコアは変更せず、target-specific detectionとは区別する。

## 2. 確認した重大な表示不具合

Gの固定adapter `generate_reference.py::convert_rows` は、保存raw timestampを足の始端として `barEnd = rawStart + 1 minute` に変換する。checkpointは閉じた足の終端である。

ところが配布画像の少なくとも次のACTUAL 3件では、checkpointと同じrawStartを持つ、次の1分に確定する足の終値が末尾に描かれている。PNGを直接目視し、保存raw OHLCと照合した。OCRは使用していない。

| Case | checkpoint | 最新5分の先頭始値 | tまでの正しい終値 | 配布図の末尾 | 末尾の値が確定する時刻 |
|---|---|---:|---:|---:|---|
| G7-023 | 10:05 | 1179 | 1179 | 1173 | 10:06 |
| G7-039 | 09:30 | 96 | 96 | 98 | 09:31 |
| G7-030 | 10:45 | 1229 | 1230 | 1240 | 10:46 |

023/039のUNCHANGEDは固定Direction式と一致する。図が次の足まで見せるため、ラベルと視覚印象が食い違う。030は両ReviewerがSEMANTICS_SUFFICIENTとしたACTUALケースだが、同じ時刻ずれがある。

原画像生成コードを今回取得できていないため、誤ったfilterのソース行までは断定しない。ただし上記3件の「表示された終値がtより後に確定する」という不整合は確認できた。36件中27件にrawStart=tのregular barが存在するため横展開監査が必要だが、27件すべての画像で漏れを目視確定したという意味ではない。

**したがって、単にReviewerの誤解として扱ってG7を通してはいけない。** 元protocolのactual future leakage hard-fail条件に該当するレビュー用表示欠陥がある。売買モデルにこの表示不具合が存在すると証明したわけでも、既に運用されたと主張するものでもない。

## 3. 固定ルールとの機械的照合

採用元: `mechanical-v1/reference.py` at `9a764e27086bf6bb1133c304b73c0027d1275760`。source SHA-256は `e57d41b1a9472fb0ed254895d956623a438557f540443c0bee14a6db8f2d8d3d`。

今回、公開済み関数本文を参照して別の監査用portを作り、36 ACTUALの保存inputsに適用した。これは元ファイルのbyte-identicalコピーでも、v2実装でも、元93テストの再実行でもない。

まず監査portのoracle modeが既存Gの全state辞書と一致することを36/36で確認。その後、同じ固定ルールをconfirmedAt<=tのfresh prefixで再計算した。

| 照合 | 結果 | 言えること |
|---|---:|---|
| Direction/観測可否と既存G CSV | 36/36一致 | 最新5分の符号と欠測扱いの照合 |
| 監査portのoracle state全体と保存G | 36/36一致 | 今回portの当該sampleにおける再現確認 |
| causal再計算と保存GのStructure種別・Phase集合 | 36/36一致 | 当該sampleの主要ラベルに相違なし |
| causal state全辞書とoracle state全辞書 | 19/36一致、17件相違 | bornAt/過去event等は同一ではない |
| 監査portの限定合成テスト | 12/12 PASS | audit helperの検証。v2 Acceptanceではない |
| 同一入力による監査2回 | 出力hash一致 | local replayのみ。GitHub CIではない |

**36/36は予測精度ではない。** ルール実装の照合であり、市場分類の唯一の正しさ、PIT provenance完了、Entry収益、OOS性能を意味しない。

また、`lateConfirmedPivots=0`だけでoracle出力全体をNOWとして流用してはいけない。今回も17件でbornAt・過去イベント等が異なる。NOWを表示する新しいproducerは、oracle辞書の流用ではなくclosed-prefix側を明示的に再計算する必要がある。

## 4. 主な疑義の裁定

| 疑義 | 固定ルール・実データ | 裁定 |
|---|---|---|
| Scale不可なのにDirectionあり | Direction = C(t) - O(最新5本先頭)。Scale非依存 | 不可だけを理由にDirectionを消す修正は不要 |
| 終日下落なのに最新Direction UP | 例040: 13:10時点1997→2002。全日方向とは別 | 定義説明・最新5分の表示が必要 |
| 016: local pivot2なのにDOWN | 前場11:11に確認済み、保護High16770。以降のclose最大16760 | 前場構造の継承。新規4pivot不足とは別 |
| 028: local pivot1なのにUP | 前場11:05に確認済み、保護Low477。以降のclose最小477 | strictな下抜けなし。継承の根拠を表示する |
| 035: pivot1なのにRANGE | 15:19成立の[71,76]。幅5<=2S=6、効率1/4<=1/3、上端4block/下端2block接触 | Rangeは4pivot成立を要求しない。固定規則上成立 |
| 014: High上昇・Low下降なのにNONE | High5670→5730、Low5620→5500。H_UP/L_DOWNでUP/DOWN両条件外 | NONEとpivotSignatureで記述可能。broadening新設は今回不要 |
| Bの014/022の語彙不一致 | 比較相手017/019は意図的control | 改変された相手との不一致だけではACTUAL欠陥を証明しない |
| Aが欠損そのものをissue、Bは適切な欠損表示を十分とした | 元配布rubricに「入力欠損」と「表現の欠陥」の区別がない | kappaは分類安定性だけでなくrubric不一致にも影響される |

Rangeの語感と広いチャートの見た目が合わない点は、固定ルールとの整合とは別のsemantic adequacy問題として残す。今回の36例照合だけで「市場的に最善」と断定せず、しかし見た目に合わせて閾値を変えない。

## 5. 引き渡し・表示・評価方法の不足

配布ZIPのINSTRUCTIONS.mdにはrubricと制約はあるが、Directionの正確な5分式、Scale非依存、Range条件、昼休みを跨ぐ既存構造の扱いがない。ZIPには仕様本文もない。Reviewerにはそのファイルと図だけで採点するよう依頼していたため、これは作成側の引き渡し不足である。

必要な表示も不足していた: 最新5本のO/C、構造のbornAt/confirmedAt/保護水準、active Rangeの固定上下限・成立根拠、local pivotsと構造を生んだpivotsの区別、pivotSignature。

012/030/037/042、014/017、019/022等の同一元チャートがcontrol/actual双方にあり、Bは実際にケース間比較を判断理由にした。これは独立ケース採点の解釈を難しくする。次のblind runでは改変controlがactualの正解を相互に示唆しない構成が必要。

042はFuture evaluatorのcensor不整合を、NOW-onlyと説明した図に同居させている。カードの長文末尾は画像右端で切れており、狙った不整合の可読性にも問題がある。NOWの禁止データ検出とFuture evaluatorの複数censor保持は、別の検査として明示すべき。

## 6. 今回のDispositionと最短修正範囲

状態: **G7_V1_FAIL / REVIEW_PACKAGE_DEFECT_CONFIRMED / ADJUDICATION_COMPLETE / STATE_V2_NOT_FROZEN**。

次の修正対象を以下に限定する。

1. 表示器: rawStartではなく正規化済みbarEnd/knownAtでt以下に制限。closed-prefix側のNOWを使う。予定欠損位置と実足位置も同じ時刻系に揃える。実際に描くデータ列のsidecar/hashを保存し、未来suffix変更で実例カードが変わらないことを機械検証する。
2. 根拠表示と配布資料: 固定ルールカード、最新5分の拡大とO/C、構造継承元、Range境界、軸ごとのreasonを付ける。市場ルール・閾値・新Stateは変えない。
3. 検査方法: binary issueを表現上の欠陥に限定する新protocol案、target-specificなcontrol採点、NOW/Future controlの分離、重複controlの問題を整理する。元ラベルの事後改訂や元G7のPASS化には使わない。

修正版は別runとして事前登録し、人間確認前に再レビューやFreezeを自動開始しない。元の36ケースは回帰用に使えても、新しい独立確認とは呼ばない。Holdoutは使わない。新たなState分類研究を増やす必要を今回の疑義からは確認していない。

## 7. 保存・限界・Safety

全44件の役割とタグ、36件の機械照合表、17不一致と26疑義の裁定、3件の時刻ずれの数値witness、監査コード、12合成テストlog、二重実行hashを保存する。元画像・元判定は不変。

独立して証明していない事項: historical receivedAt、corporate-action PIT、provider timestamp規約の外部一次資料照合、全77,214件のv2結果、全27候補画像の漏れ件数、PIT clean/Realtime parity、モデル精度・収益性。adapterで固定されている時刻契約に対する内部整合性の裁定である。

新規market provider取得0、保護データ開封0、State閾値変更0、v2実装0、v2全件生成0、学習0、Signal/BUY-WAIT/Entry/EXIT開始0。既存Safety9=falseをadmissionで確認し、売買コードは変更していない。
