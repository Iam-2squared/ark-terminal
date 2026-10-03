# 144日Development Temporal Reliability Feasibility

**成立性診断のみ。旧GateはBLOCKED維持。時間再現性のPASS/FAIL、補正成績、収益性は測っていない。**

比較可能な旧USABLE cohort: **1498銘柄**。そのうち最新H/M候補にも含まれる銘柄: **1394銘柄**。
この比較可能cohortを成立させる最小追加Development日数: **0**。全銘柄・全traitの成立やGate通過を保証しない。

## 分割（実数値を見る前に日付だけで固定）

|役割|source開始|computedThrough日|prediction origin日|評価開始|評価終了|許可日数|calendar上の適格日上限|
|---|---|---|---|---|---|---:|---:|
|CALIBRATION|2024-08-15|2024-11-12|2024-11-12|2024-11-20|2025-05-01|26|20|
|VALIDATION1|2025-03-11|2025-06-06|2025-06-06|2025-06-16|2025-07-23|26|20|
|VALIDATION2|2025-04-18|2025-07-15|2025-07-15|2025-07-24|2025-08-21|20|20|

144日全体（2024-09-19〜2025-08-25）を利用可能範囲とし、必要な日足履歴は既存許可済みDevelopmentのみ。144日が連続日であるとは扱わず、sealed日・欠測はNaN、履歴resetとwarm-upを維持。source60取引所日、H/M coverage>=0.5、target20適格日、peer100など旧条件を保持。
最初のcalibration targetは空白を含み108取引所日にまたがる。検証targetは非重複だがiidや相場局面の独立を保証しない。後のsourceはその時点までに観測した前のtargetの一部を含み得る。calibration mappingは最初のtarget終了後に固定する設計であり、今回はfitしていない。
カレンダー規則は全144日の許可日メタデータのみを使用。成績の最大化、window再選択、Gate緩和、最低N緩和は実施していない。旧固定windowの正式結果は書き換えない。

## 旧USABLE 9件の比較成立数

|lane/trait|Calibration|Validation1|Validation2|全3期間共通|うち最新H/M|
|---|---:|---:|---:|---:|---:|
|daily/inside|0|0|0|0|0|
|daily/gap_fill|0|1|3|0|0|
|daily/gap_cont|0|0|1|0|0|
|daily/amihud|2103|1858|2168|1318|1203|
|intraday/amihud|1882|1831|2130|1145|1051|
|intraday/value_O30|590|704|869|413|402|
|intraday/value_AM|541|686|857|381|364|
|intraday/value_PM1|562|666|845|417|400|
|intraday/pdh_break|0|0|0|0|0|

symbol×trait別の証拠はmeasurement/04_comparable_cells.json.gz。各期間のminimum・nEff・peer人数・除外理由は02_trait_support.json。最新H/M cohortは説明用で、過去の適格銘柄選定には使わない。

## WATCH23

|lane/trait|Calibration fit pair候補|Validation1 pair候補|Validation2 pair候補|各期間100以上|
|---|---:|---:|---:|---|
|daily/body_range|3625|3269|3648|True|
|daily/large_up|3472|3121|3464|True|
|daily/doji|3537|3134|3564|True|
|daily/long_lower|3454|3035|3557|True|
|daily/outside|3668|3529|3687|True|
|daily/trend_day|3531|3129|3563|True|
|daily/range_s|2337|1155|2579|True|
|daily/range_exp|2943|1833|2801|True|
|daily/range_con|2850|2536|3223|True|
|daily/gap_up|3377|2844|3471|True|
|daily/gap_dn|3540|3163|3501|True|
|daily/overnight_var_share|3551|3095|3614|True|
|daily/value_shock|2402|1420|2172|True|
|daily/jump|3296|2745|3143|True|
|intraday/inside|3452|3512|3671|True|
|intraday/trend_day|3068|3129|3563|True|
|intraday/range_con|2627|2536|3223|True|
|intraday/gap_fill|0|1|6|False|
|intraday/overnight_var_share|2976|3095|3614|True|
|intraday/value_shock|1671|1420|2172|True|
|intraday/value_CL|0|592|1088|False|
|intraday/range_PM1|463|525|1088|True|
|intraday/volume_CL|0|594|1093|False|

時間順序とpair数のみ。実mapping作成・補正の安定性評価・WATCH昇格は行っていない。

## 判定と次工程

READY_TO_PRECOMMIT_REMEASUREMENT_SPEC_ONLY
0より多い比較可能cohortがあれば、現在のDevelopmentで事前固定した再測定へ進む根拠になる。ただし本工程は正式再測定ではない。measurement/05_validation_spec_proposal.jsonを別工程で採用・固定してから採点する。
比較cohortが0なら本規則での成立は未証明。別windowを成績で選ばない。全設計に対する不可能性や追加日数は断定しない。

## Entry / EXITへの144日再利用契約

同じ144日は将来のEntry/EXIT Developmentとして再利用可。各decisionのDictionary・peer prior・normalization・confidence・temporal reliability artifactは全てcomputedThrough < decisionTimeかつavailableAt <= decisionTimeを満たすpast-only再生成が必要。最終snapshotや最終H/M判定の過去行へのコピーは禁止。未成立・未利用可能はUNAVAILABLEのままとする。
今回の全期間診断や最終registry/Gate判断は事後の研究結果であり、過去に利用できたartifactとは認定しない。Development再利用は独立な評価ではない。学習・比較を行うfoldごとに学習済みartifactとtrait選択も過去側だけで固定する。採点対象より後のデータ・labelで作った辞書を特徴として使わない。
詳細はprecommitのentry-exit-past-only-contract.md。今回はEntry/EXIT学習・設計へ進まない。

## 検証・境界

Focused 219 PASS / regression 2949 PASS / 2回再生成manifest一致。旧Evidence hash不変。
原本再取得なし。既存144日の検証済みmatrix checkpointを使用し、元input ledgerと完全一致。Common Holdout244・REPORT19/Validation/OOS/Fresh追加開封0。過去Exposure Ledger維持。安全フラグ9項目は全false。
Execution HEAD a621aafcd8edf579ab4871481fa1da384ed803c6 / CI 35486961051 / PR587 Draft・未merge。STOP。
