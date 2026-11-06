# ARK TERMINAL RG01 — BLOCKED報告

文書ID: ARK_RANK_REWARD_DOWNSIDE_SEVEN_GRADE_RG01_20261008 / 2026-10-08

**新S〜Fはまだ生成していません。判定は `BLOCKED_INTEGRITY_OR_ASOF` です。**
RD01の指定原本 `SOURCE_BINDING.json` が固定commitに存在せず、元指示の欠落時停止規則に従い、precommit seal・COMPOSE・ASSIGN・EVALUATEを開始していません。これは性能不採用や新S=0という結果ではありません。RG01研究は未完了です。

## 1. 新S〜Fの実生成・人数

| method | S | A | B | C | D | E | F | 状態 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| U7 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 未生成 |
| G7_FULL | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 未生成 |
| B7_FULL | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 未生成 |
| G7_PRICE | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 未生成 |
| B7_PRICE | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 未生成 |

RANK_UNAVAILABLEへの割当も未実行です。欠落ファイルを理由に1039 EntryをFまたはRANK_UNAVAILABLEへ割り当てていません。Sが旧43件から減ったかは未判定です。

## 2. 新Sの成績と同数K

PLUS/MINUS、R<=-3/-5、R>=+2/+5、U5/U10、平均/中央値R、positive/negative mass、net pp-sumは全methodで未評価です。K=43/197/494、各blockのK_newS、U7とR0の集合一致も未実行です。数の削減・Winner保全・大Loser削減の成果を主張しません。

## 3. 旧S43件と移動

固定commitから実読したRD01/RD02の保存基準は旧S43件、PLUS10/43、MINUS33/43、R>=+2は7/43、R>=+5は3/43、R<=-3は3/43、R<=-5は0/43です。これは親研究の保存結果であり、RG01の再集計ではありません。
旧Sから新Sへの残留・降格人数、降格理由、lost Winners/Losers、旧33件の負けの改善は未評価です。元保存S/A/B/C人数は43/154/297/545で保持されています。

## 4. 全12帯・移動表・累積表

新7段階の全12帯、ZERO/UNKNOWN、4×7・7×7遷移、累積grade表は未生成です。`RANK_COUNTS_STATUS.csv` は未生成状態の一覧で、成績表ではありません。`REQUIRED_OUTPUT_STATUS.json` に必須成果物ごとの未実行状態を記録しました。元R0の全12帯は[固定RD02 REPORT](https://github.com/Iam-2squared/ark-terminal/blob/4383f7889b32bd60aef1b96b30bab0544889a509/research/downside-direct-rd02-20261008/REPORT-ja.md)に保存されています。

## 5. 同数K・Winner保全screen

A Upward foundation / B Tail-return / C Winner preservationはすべてNOT_EVALUATEDです。screenの値やrank境界・penalty定数は変更していません。新rankの上位集合が無いため、純risk選択や人数削減の効果と追加価値を比較できません。NO_INCREMENTに読み替えず、入力のBLOCKEDとして保持します。

## 6. FULL/PRICE・時間整合性・母集団

G7_FULL/B7_FULLとPRICE対照の比較、8block/38session、leave-one-out、全583symbol診断は未実行です。親保存母集団は1039 unique Entry、R既知1016/未知23、q5陽性23であり、新検証期間や重複窓を追加していません。これらは親記録の読戻し値で、RG01による全ID検証済みの主張ではありません。
RD01保存asof監査は厳密BUY_INTENTをNOT_CERTIFIEDとし、native V5のfill_minuteでのt_rankを参照しています。RD02 qはt_xのhistorical assumed available、実到着時刻UNKNOWNです。BUY_INTENT_DEPLOYABLE=false。strict共通subsetは行単位の検証未実行であり、ゼロ件と断定していません。解消後も証明が無ければHISTORICAL_MIXED_ASOF_RESEARCH_ONLYとする条件を保持しました。既露出DevelopmentからFresh/OOS・安全S・資産改善を主張しません。

## 7. 原本・hash・監査・再現・保存

RD02必須公開14ファイルを指定commitでactual GETしました。REPORT blob `614b98a185cf211435a352212d3b1662cad928cb`、V5 staircase blob `6863b2dded50e4d0caa4e2d470619017fcf0b759`、EXIT freeze SHA256 `a9845422555b478fe1ed34a95b97fa185f83c2c487c19926f72dbe628eec590d` は指定値と一致します。取得した27テキストファイルは返却Git blobと内容から再計算したblobが一致しました。これを全1039入力のHARD_INTEGRITY PASSと呼んでいません。
RD02の `NO_INCREMENT_UNDER_TESTED_DESIGN`、probability_ready=false、Winner保全不足を保持しています。private B01〜B08予測carrierの再結合GET・全row qのhash照合はこのWorkではまだ未実行です。
RG01の別実装rank検算・人工fixture・saved-assignment再現はNOT_RUN_BLOCKEDです。ソース読戻しの検査とrank監査を区別しています。モデルfit/refit、score再推論、実データassignment/evaluation/reproduction campaign、CapitalReplayはすべて0です。
この報告とcheckpointは新しい研究branchへappend-onlyで保存します。publication receiptに各payloadのcommit/path/bytes/SHA256/Git blobを記録し、そのreceiptを別actual GETしてからconfirmationを独立commitします。現時点の報告本文からGitHub保存完了を先取りせず、最終保存証拠は後続receipt/confirmationで確認します。

## 8. 正確な阻害原本

| 項目 | 値 |
| --- | --- |
| repo | Iam-2squared/ark-terminal |
| 指定commit | `6375a00458936078186a1637795241fedf0236a1` |
| 欠落path | `research/rank-reward-downside-rd01-20261008/SOURCE_BINDING.json` |
| direct GET | 404 NOT_FOUND |
| 同commit directory | 全44ファイル一覧にも該当なし |
| bytes / SHA256 / Git blob | 取得不能、null。元指定にも値なし |

実在する `SOURCE_INDEX.json` は診断目的だけでGETし、bytes=15597、SHA256=`036c44cb1ab6eec675edefd2b6761e0b90588e2cd80350435983677b41fad2e7`、Git blob=`fafc1dde9ffe4b340019f9e0974c9c6a54c394ae`を確認しました。指定原本の代替として採用していません。指示書が要求する欠落停止規則と「似た列名のファイルを代替にしない」に従い、原本指定の訂正または正確な権威あるbindingの提示が必要です。既存commitや旧成果物を書き換えて欠落を埋めることはしません。

## 9. 判定・次工程

判定はBLOCKED_INTEGRITY_OR_ASOF。Championなし、selectedNewRank=null、mainRank=SAVED_R0。terminal_status=BLOCKEDであり、COMPLETE_STOPは研究完了後のみ設定します。
唯一の次実験案は元指示を保持します。**もしasof・Winner保全・同数Kを満たすなら、別Workで7段階→V5のAdmission/Allocation意味のbridgeを凍結し、9×RESET20・100万円・同条件で研究用Capital比較する。** 本Workでbridge/Capitalを実装していません。先に不足原本指定を解消して、RG01の未実行工程を再開する必要があります。

mainRankChanged=false、firstLayerChanged=false、P1追加ゲートOFF、mainCapital=CAPITAL_MAX3_SLOT_RESERVE_V1、mainExit=SHARP_DROP_FIRST_OBSERVED_EXIT_V0、capitalImprovement=NOT_EVALUATED、freshValidation=NOT_RUN、productionReady=false、Safety9すべてfalseを保持しました。
