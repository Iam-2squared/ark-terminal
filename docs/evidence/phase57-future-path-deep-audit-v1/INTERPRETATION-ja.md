# STEP 1 Future Path Deep Audit — Evidence解釈 / 人間確認待ち

2026-09-21 JST。これは保存済みSTEP 1 Evidenceの読解・集計であり、STEP 2のVocabulary変更ではない。既存Path分類・閾値・ラベル・Evidenceは変更しない。

## 実行と固定

- 開始時確認HEAD: `4ec55bb6923d0f69fbc9654ad33bb61cd2840780`
- 専用CI実行HEAD: `805c0ca5b05a6b0d2dc732afe47088d37eb7ef84`
- Evidence保存commit: `c7413c5bf274f1c3bb9bd8a32be7708976149aeb`
- 専用Actions run: `35560748821`。audit / preserveともsuccess。
- 2,155 Opportunities、58 nonempty Development sessions、2025-05-30〜2025-08-25。Fresh/OOSではない。
- 合成テスト16件PASS、全2,155件で既存分類の全フィールド一致、二重実行のファイルハッシュ一致。
- 110代表チャート保存。DIRECT全50件、CONSOLIDATION全10件を含む。代表抽出規則は事前プロトコルで固定。全件の数値・観測価格経路も保存。
- 取得したZIPのSHA256: `cf4c8678fd41be570e3d262bfca29710400db8b2119aaf0b43be1de813d9f5a5`
- measurement manifest SHA256: `7d37f7edfabf8da9f54dc4f11e47b96441788cdeba982a16311dcc60704350d5`
- raw/audit-records.json.gz SHA256: `c2c31dbf084683929fddc7299b5509cfedfd3b49bbf97efd28f42a1946c36565`

本解釈の数値は`ci-result/measurement/summary.json`と`raw/audit-records.json.gz`を使用。ダウンロード後にもreceiptの127ファイルのSHA256を検証した。分類再定義、再学習、Signal評価、Entry評価は行っていない。

## 1. なぜ2,155件が現在の件数になったか

| 分類処理上の分岐 | 件数 | 最終ラベルへの行き先 |
|---|---:|---|
| 観測Gate未達 | 496 | INSUFFICIENT_OBSERVATION |
| 観測Gate通過、5条件すべて不成立 | 355 | NO_DOMINANT_PATH |
| 観測Gate通過、1条件だけ成立 | 627 | DIRECT 50 / RECOVERY 202 / CONSOLIDATION 10 / CHOP 289 / WEAKNESS 76 |
| 観測Gate通過、2条件以上成立 | 677 | CHOP優先規則で539 / TRUE_MIXED_PATH 138 |
| 合計 | 2,155 | 元の5+1分類と完全一致 |

従って最終CHOPは289+539=828。Path6は496+355+138=989。複数条件成立677件の内訳は2条件609件、3条件68件。『複合Pathは138件だけ』ではない。

## 2. 観測不足496件

重複を排した管理上の内訳は、残り30 active minutes未満179件、残り30分以上だがfuture rowsが20未満312件、両条件を満たすが既存full-session評価不可5件。179件はすべてSelection 15:00、既存clock上の残りは25 active minutes。

各失敗条件は重複する。future rows<20は420件、remaining<30は179件、既存full-session評価不可は63件。63件のID集合は終端オークション足が観測されていないID集合と一致した。これは終端条件の不足を示すが、他の不成立原因が同時に存在しないという主張ではない。

| 元の失敗条件の組合せ | 件数 |
|---|---:|
| rows<20だけ | 263 |
| rows<20 + remaining<30 | 99 |
| remaining<30だけ | 71 |
| full不可 + rows<20 | 49 |
| full不可 + rows<20 + remaining<30 | 9 |
| full不可だけ | 5 |

時刻別は09:30=5、10:00=13、10:30=30、11:00=33、11:30=51、13:00=23、13:30=47、14:00=57、14:30=58、15:00=179。合計496。昼休みをまたぐ観測は80件、前引け近辺11:00〜11:30は84件。これらの併存フラグは相互排他的な原因ではない。

496件中460件には、予定されたregular minute stampに対応する足がない。これは『取得障害460件』ではない。保存済みcompact rowsだけでは、無約定・売買停止・provider欠落・元データからの除外を区別できない。昼休みや引け前オークション待機時間はmissing active minutesに数えていない。補間・架空足は作っていない。

元の`fullSessionEvaluable`も純粋な1分足本数フラグではない。`phase57_behavior_full144.labels_for_raw`での日足との出来高・高値・安値の照合と終端オークション等に依存し、`selectorOutcome.mfeEnd is not None`として継承される。今回の63件について、日足照合の全成分別失敗理由まで再構築したわけではない。

**判定:** 496件の機械的な振分け理由は全件説明可能。ただし欠けた足の現実の発生原因は一部未解決であり、Gate 3の留保は維持する。

## 3. NO_DOMINANT_PATH 355件

この箱は『特徴のない値動き』だけではない。

- 233/355件（65.63%）は、post-selection経路のどこにも連続10本のregular barsがない。既存CONSOLIDATION定義の観測前提を満たさない。
- 352/355件（99.15%）は確認済み0.5% reversalが4回未満。reversal計数は欠けた分・昼休みでresetするため、少ないreversal数をそのまま現実の波の少なさと解釈できない。
- 観測されたordered Low→Later High rangeの中央値は2.1254%。200件で2%以上、96件で3%以上、29件で5%以上の観測幅がある。未来anatomyの値幅であり、実現利益ではない。
- RECOVERYのlow→later high条件自体は81件に存在するが、元のterminal条件まで満たすものは0件。Consolidationのbreakout range条件まで満たす15件もterminal条件で不成立となる。

事前に定めたefficiencyの最小・中央値近傍・最大代表を価格チャートと照合した。

| ID | 観測された経路と不成立理由 |
|---|---|
| 2025-06-02\|44180 | 終端+0.0921%、ordered range0.9225%、reversal0。小幅往復で、元の振幅・効率条件に届かないケース。 |
| 2025-06-02\|45760 | regular missing139、連続10本なし。ordered range2.4793%の回復幅はあるがterminal条件が不成立。低密度観測と部分的回復が混在。 |
| 2025-08-07\|74260 | 終端-10.3620%という下落経路だが、途中のordered recoveryが2.0194%あるためWEAKNESSの『2%未満』条件を外れる。RECOVERYのterminal条件も不成立で、NO_DOMINANTとなる。regular missing188も併存。 |

最後のケースは『dominantな動きがない』という自然言語と、現行の全predicate不成立が同義ではない具体例。閾値を2.0194%に合わせて変更する等の調整は行わない。

**判定:** 観測前提不足、閾値による除外、途中イベントと終端状態の組合せを、単一のNO_DOMINANTにまとめている。355件全体を『本当にdominant pathがない』とは認定できない。

## 4. TRUE_MIXED_PATH 138件

全10組合せは保存済みREPORT/summaryに記載。最大はRECOVERY+CHOP79件、次いでCHOP+WEAKNESS19件、DIRECT+CHOP10件。残り30件は他の7組合せ。

複数条件の成立を、直ちにStateの連続遷移だとはみなさない。例えば事前抽出代表2025-08-15|48940では、既存RECOVERY witnessのlowは11:19、strictly later highは12:30、その後CONSOLIDATION witness開始15:02、breakout15:14となる。これは順序のある複数イベントが一つのOpportunityに存在する例である。一方CHOP+WEAKNESSでは、同じ下落区間に往復と下向きの特徴が同時に成立し得る。観測ギャップ内部や同一足内の順序は確定していない。

**判定:** 『複数Stateが順に移った』場合と『同一区間が複数性質を持つ』場合を区別する必要がある。具体的なState Transition Vocabularyの採用・実装は未決定。

## 5. MULTI_SWING_CHOP 828件

| 元の成立条件 | 最終CHOP件数 |
|---|---:|
| CHOPだけ | 289 |
| RECOVERY + CHOP | 450 |
| RECOVERY + CONSOLIDATION + CHOP | 56 |
| CONSOLIDATION + CHOP | 15 |
| CHOP + WEAKNESS | 18 |

539/828件（65.10%）は複数条件成立をCHOP優先規則で吸収したもの。純粋にCHOP条件だけ成立したのは289件。

終端変化は-1%以下413件、(-1%,0%)85件、[0%,1%)88件、+1%以上242件。終端変化の最小-19.6552%、中央値-0.9890%、最大+42.7313%。ordered range中央値5.3993%、reversal中央値18回、P90=51回、最大105回。価格基準はSelector選出時点でありBUY価格比較ではない。

事前抽出の終端変化最小/中央値近傍/最大代表は、2025-06-03|60810（大きく下げた途中にも反発）、2025-06-04|260A0（上昇・往復後に戻る）、2025-07-01|63470（複数回の大振幅変動と大幅上昇）。数値とチャートを照合した。CHOPという一語だけでは、終端方向、波の大きさ、回復やbreakoutの併存を表現しきれない。

**判定:** CHOPは有用な『往復性の属性』になり得るが、今回の828件を同質な単一の経路型として扱う根拠には不足する。正式な新しい群分けやクラスタリングは実施していない。

## 6. 少数Pathの希少性と定義

観測Gateを通過した1,659件で比較する。条件成立件数は重複を含む。

| Path | 現行ラベル数 | 条件成立数 | Mixedへの振分け | CHOP優先で吸収 |
|---|---:|---:|---:|---:|
| DIRECT | 50 | 67 | 17 | 0 |
| RECOVERY | 202 | 810 | 102 | 506 |
| CONSOLIDATION | 10 | 106 | 25 | 71 |
| WEAKNESS | 76 | 114 | 20 | 18 |

DIRECTは+1% high存在1,247件→最初の-0.5% dipより先685件→terminal非負444件→efficiency>=0.2を満たす67件→単独ラベル50件。50件という数字だけから直接上昇そのものの自然頻度は判断できない。高い全経路efficiencyと終端条件、さらに重複処理が影響している。

CONSOLIDATIONは連続10本が存在1,176件→圧縮幅条件505件→breakout close238件→breakout bar range223件→terminal held106件→単独ラベル10件。元の全条件を満たした106件のうち96件が別ラベルへ回る。『breakoutは10件しかなかった』という解釈は誤り。

各funnelは元の固定条件の監査であり、閾値探索や新しい分類器の比較ではない。

## 7. 総合判断とSTOP

現行5+1は、計算としては完全再現できる。しかし、そのまま『Entryが理解すべき値動き状態のVocabularyが確定した』とは扱えない。観測充足性、局所イベント、全経路の往復性・効率、終端条件、優先ラベル付与が混在している。

既存5+1の履歴は維持する。今後のVocabularyを現状のまま確定することは支持しない。観測可否とPath意味の分離、複数属性の併存と時系列の区別を、人間がSTEP 2の要否・範囲を判断する際の論点として提示する。具体的な置換定義は未作成・未適用。

保存済みCompletion Gate表示は1/2/4/5=PASS、3/6/7=PARTIALを維持。Gate3は取得欠落等の実原因が未解決、Gate6/7は同質性やVocabulary確定を認定しないという留保である。専用CI PASSと7項目すべてのPASSを混同しない。

**STEP 1の計測・Evidence保存は完了。全Gate無条件PASSではない。STOP FOR HUMAN REVIEW。STEP 2へ進まない。**

Frozen Selector、Entry/EXIT、Dictionary、Common Holdout、資本配分は変更していない。新規provider requests=0、holdout opened=0。Safety 9項目は全false。PR全体GREENやmerge可能という研究完了判定は出していない。
