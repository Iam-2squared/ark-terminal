# Phase57 — 既存Entry×EXIT全4組合せの再監査とNEW EXIT方針 R17

Date: 2026-09-25 JST
Repo: Iam-2squared/ark-terminal
Branch: research/phase57-long-only-cash-equity / Draft PR #587
監査基準HEAD: 077b18773307c778312a76af3d2ca6f6cadbd2e9
Status: VERIFIED_EXISTING_BASELINE_RESULTS_NEW_EXIT_NOT_TRAINED_FULL_PORTFOLIO_BLOCKED

## 現状と今回の実作業

最新HEADを再取得した結果、旧報告の38fad13b時点より進んでおり、R13 EXIT adapter、R14 EXIT結果、R15 Capital契約、R16 Capital会計結果が既に保存されていた。今回の作業をその既存実装・計算の新規実行として数えない。

今回は既存EXIT workflow36115061827のjob108007095280を確認し、artifact10855136419を取得した。ZIP SHA、5出力のSHA、Run A/B byte一致を独立に検査した。保存済みexit-ledgersの全行から、四者共通集合、Entry内paired集合、個別resolved集合を独立再集計し、既存summary.jsonと数値一致を確認した。Entry envelopeの不変、非約定/未確定のnull維持、grossから0.05ppの控除、全2,155件/Entryの保持も確認した。

新しいEntry/EXITモデルの学習、パラメータ探索、戦略replayの再実行、provider新規取得は行っていない。新しいモデルが改善したという報告ではない。今回の独立監査assertionは既存26 synthetic testsとは別であり、新規EXITテスト数へ水増ししない。

## 最新ユーザー方針 — 旧R11からの変更範囲

EntryはIMMEDIATEとALL_MATERIAL_R1_TEMPORAL_NESTED_OOFの2本を固定する。Dual Freeze commit4878a1cc53430e816261dea0fb16aeb53b3c238dを維持し、再学習・追加最適化・旧Entryの最終候補復活はしない。

ユーザーはその後、EXITを一から研究し、既存EXITを比較基準にする方針を明示した。したがってR11の『Candidate Aを最終EXITとして接続して終了する』方向は、今後の研究方針についてのみsuperseded。本R17の次工程を使用する。R11/R13/R14/R15/R16のデータ、既存測定、baseline policy、コスト、失敗履歴は変更・削除しない。

- Fixed12: 単純baseline。
- NEW_LONG_EXIT_PROTECT_3_TO_1_FIXED12_V1 (Candidate A): immutable baseline。
- NEW Comprehensive EXIT Intelligence v1: 未構築・未学習・未測定。
- その他accepted/Frozen EXIT: canonical lineageと現2-Entryへの互換性の確認が必要。以下の4組合せの結果に混ぜない。今回、その他旧EXITの新しい比較測定は実施していない。

## 評価範囲と分母

各Entryの全2,155 Opportunitiesを保持する。outcome-exposed DevelopmentでありFresh/OOSではない。
R16の訂正を採用する: 固定カレンダー59営業日、Opportunity-bearing58日、期間2025-05-30〜2025-08-25。Opportunity0件の2025-07-14を勝手に削除しない。

以下の主表は4組合せ全てでEXITが確定した同じ1,093 Opportunity IDだけを比較する。これは事前に定義されたfour-cell common-resolved集計であり、EntryやCapitalの入力を1,093件へ絞るフィルターではない。未確定を含む全件成績やPortfolio Returnを表すものでもない。

## 主比較 — 全4組合せで共通の1,093件

単位: 1取引notionalに対するnet%。PFは同一notionalの正/負net合計比。保有時間は昼休みを含むclock minutes。

|Entry|EXIT|N|平均net %|中央値net %|PF|勝率 %|平均保有 分|
|---|---|---:|---:|---:|---:|---:|---:|
|IMMEDIATE|Fixed12|1093|-0.108351|-0.099975|0.908536|45.288198|67.937786|
|IMMEDIATE|Candidate A|1093|-0.081062|-0.099975|0.926421|46.294602|64.817017|
|ALL_MATERIAL R1|Fixed12|1093|-0.132048|-0.099975|0.885771|44.830741|74.331199|
|ALL_MATERIAL R1|Candidate A|1093|-0.088959|-0.099975|0.916383|45.837145|71.212260|

|Entry|EXIT|p05 net %|p10 net %|最悪net %|平均勝ち %|平均負け %|
|---|---|---:|---:|---:|---:|---:|
|IMMEDIATE|Fixed12|-5.188972|-3.515725|-17.295678|2.376507|-2.165215|
|IMMEDIATE|Candidate A|-4.782354|-3.270786|-17.295678|2.204644|-2.051364|
|ALL_MATERIAL R1|Fixed12|-4.863693|-3.255964|-20.257963|2.284025|-2.095358|
|ALL_MATERIAL R1|Candidate A|-4.530194|-3.083496|-20.257963|2.126942|-1.964240|

p10/平均勝ち/平均負けは同じ保存ledgerの記述統計として再集計したもので、新候補の事後的な採用Gateではない。
全4組合せの保有時間中央値は60分。Candidate Aのexit reasonはIMMEDIATE: PROTECT113 / Fixed12 fallback980、R1: PROTECT107 / fallback986。

同じ1,093件でのCandidate A−Fixed12の平均改善は、IMMEDIATE +2.728926bps、R1 +4.308919bps。平均/PF/p05は改善するが、両Entryとも平均netは負、PFは1未満。各Entryの最悪損失は改善していない。
ImmediateとR1の小さな条件付き差を有意な優劣や最終Entry選定と扱わない。p05ではR1の方が軽い一方、worstではR1が悪く、『R1の方が安全』という一括判定もしない。

## 補助比較 — 各Entry内の最大paired集合

Entry間で分母が異なる。各Entry内でEXITを比較する用途に限る。

|Entry|paired N|Fixed12平均net %|Candidate A平均net %|平均差 A−Fixed bps|
|---|---:|---:|---:|---:|
|IMMEDIATE|1118|-0.076639|-0.054139|2.250068|
|ALL_MATERIAL R1|1105|-0.125400|-0.083436|4.196315|

これはR14/R16に記載済みの比較を再確認したもの。主表との差は1,093件/1,118件/1,105件の集計対象の違いであって、結果の上書きではない。
同一Candidate AのEntry間共通1,101件の結果もR14/R16に残る。今回の四者同時比較には1,093件を使用する。

## 全件の可用性 — 欠損を省略しない

|項目|IMMEDIATE|ALL_MATERIAL R1|
|---|---:|---:|
|全Opportunities|2155|2155|
|No Entry|192|270|
|Frozen Entry fills|1963|1885|
|Fixed12 EXIT確定|1118|1105|
|Fixed12 EXIT未確定|845|780|
|Candidate A EXIT確定|1133|1115|
|Candidate A EXIT未確定|830|770|
|Candidate A確定率 / Entry fills|57.717779%|59.151194%|
|Candidate Aのみ確定|15|10|
|Candidate A未確定の最初の欠損15:30|202|217|
|その他時刻の欠損による未確定|628|553|

全2155を保持し、未確定を0損益や決済済みにしない。4組合せ比較は現状ではcomplete-caseの条件付き記述である。15:25〜15:30問題だけを直しても、残り628/553件は解決しない。

個別に確定した全件の記述値も残す。分母が異なるため、以下をそのままpaired優劣判定に使わない。

|Entry|EXIT|個別resolved N|平均net %|PF|
|---|---|---:|---:|---:|
|IMMEDIATE|Fixed12|1118|-0.076639|0.934604|
|IMMEDIATE|Candidate A|1133|-0.042808|0.960453|
|ALL_MATERIAL R1|Fixed12|1105|-0.125400|0.890843|
|ALL_MATERIAL R1|Candidate A|1115|-0.078208|0.925640|

## Opportunity preservation

R14で保存済みの厳密なownership-time定義を使用する。Entry-stage Captureでも実現利益の勝率でもない。

|Candidate A|IMMEDIATE|ALL_MATERIAL R1|
|---|---:|---:|
|+3 preservation|305/305 = 100%|290/290 = 100%|
|+5 ownership-time preservation|136/145 = 93.7931%|129/137 = 94.1606%|

旧slot定義のImmediate137/145はEXITバーOPENで手放した後のHIGHを1件含むため、保有中に獲得した+5としては使わない。旧値自体はR14から消さない。
MFE capture ratio、MAE、State/Signal別の新EXIT評価などはこのbaseline再監査で新たに完成したものではない。NEW EXITの評価契約で定義・実装・検証する。

## Capitalの現状 — 会計PASSと成績PASSを分ける

R16の専用CI36117117239 / job108013713013はSUCCESSを再確認した。今回Capital全ledgerの独立再計算は実施しておらず、以下は保存済みR16結果である。
初期cash100万円、100-share lot、LONG/cash-only。EQUAL_MAX3の3は予算分割数で、maximumConcurrentPositionsは10。3ポジション上限へ読み替えない。

|項目|Immediate100株固定|R1 100株固定|Immediate Equal/MAX3|R1 Equal/MAX3|
|---|---:|---:|---:|---:|
|受付|26|24|3|2|
|決済済み|16|14|2|1|
|未確定ポジション|10|10|1|1|
|期末cash円|483929.51|639372.39|653643.71|658146.68|
|未確定取得原価拘束円|485342.55|313356.60|329764.80|329764.80|
|決済済みだけの損益円|-30606.60|-47192.67|-16509.05|-12006.08|
|全Portfolio Return|算出不可|算出不可|算出不可|算出不可|
|全Max Drawdown|算出不可|算出不可|算出不可|算出不可|

決済済み取引は2025-05-30分だけであり、59営業日の収益成績ではない。cash減少を損失にしない。取得原価拘束を時価評価にしない。
未確定ポジションが資金を拘束し、100株固定は保有上限、EqualはCURRENT_EQUITY_UNKNOWNで後続を拒否している。旧277 EntryのCapital結果を新統合版へ流用しない。

## 再現性・CI・入力identity

- EXIT execution/preregistration: 416595cc824068fb34abcdc2e2bc368e8c155831。
- EXIT workflow36115061827 / artifact10855136419。
- ZIP SHA256: 7cbf9df8df91f390cba1e89cbdfd400802bcfb3b8812a226ff1ea66b067796f1。
- summary.json SHA256: fb86acb8fb0a61c90e905d44837cbc5c9055b2602fdb7a9114c9e2ec9158f6ca。
- audit.json SHA256: 828600ac8588353e318fd99ea9ccd65e98e11412df3e99ce304a43c39ea0d386。
- entry-envelopes.json.gz SHA256: 0918314fbf363e4d0a04717a81c51321080391827b533302c29ee2b68fd3c513。
- exit-ledgers.json.gz SHA256: 0afdb59bc476f7085955b3ac30efdf875402fb1d68b316181f483b3486c8e9c6。
- manifest.json SHA256: 7542f7cb0bd60c7e3c063189cd3ec928b582bef01164ca85106830675786b685。
- 5出力のRun A/B一致と上記hashを今回も確認。元CI26 synthetic tests PASSをログで確認。
- Capital execution: fd68460930a3198e3976aba057d41cde1c2c9c97。専用CI36117117239 SUCCESS。
- 基準HEAD077b1877のworkflow failure検索では6件。check-runsにはin_progressもある。専用CI成功をPR全体GREENと呼ばない。本書追加後のCIは別HEADで再確認する。
- GitHub artifact期限: EXIT2026-10-25T08:50:29Z。期限付きartifactを永久保存と呼ばない。

## 基準の実行時刻・コスト意味

Entry price/timeは保存値そのまま。09:31 Entryなら最初の対象regular5mは09:35〜09:40。Entry前HIGH/部分バーをPROTECTへ入れない。Fixed12は12分ではなく最大12本の対象5分足で、残りcalendar slotsが少ない場合は既存terminal capに従う。
昼休みはregular slotsから除外するが保有clock時間には含む。疎なバーのOPENは最初の実在1分足時刻とし、nominal時刻へ逆算しない。
保存Entry価格には既に5bpsの買いslippageが含まれる。既存round-trip0.05ppをさらに1回だけ控除する。全コスト合計5bpsという表示は誤り。これはreference-price Development replayであり、実市場での約定保証ではない。

## 今後の方針と次の具体作業

1. R13/R14/R16のbaseline結果を再利用し、既に成功したadapter/replayを最初から重複開発しない。先に保存済みcurrent-Development raw/manifestで欠損を監査する。最初の共有blocker2025-05-30|61770|570、確定参照欠損10:10 JST、終盤15:30由来とそれ以外を分ける。真の未取得、無約定、calendar/adapter問題を証拠で区別する。補間・前値埋め・auction代替・架空決済・結果ベースの日/銘柄除外は禁止。
2. 同時にEXIT Feature Availability & Causality Matrixを作る。State-v3/9-State、6 Signals、Pattern-v2/476列とEntry→NOW情報のcanonical producer、source、knownAt、closed-prefix、coverage、missing/tri-stateを確認する。Entryで利用可能だったことをEXIT時点の採用証明に流用しない。MODEL_ADMITTED / BLOCKED / EVALUATOR_ONLYを分離し、UNKNOWNをFALSEにしない。
3. NOWまでのrunning return、peak、giveback、MFE/MAE、State/Signal履歴は、EXIT NOWで観測済みの場合だけ候補。future suffix、future pivot、future State、future MFE/MAE、final PnL、oracle exitはdecision featureへ渡さない。Dictionary等PIT未証明情報はBLOCKEDのまま。
4. NEW EXITの目的関数・scorecard・有限model/feature/label/search回数・selection rule・temporal/purged/session-grouped分割をNEW候補性能を見る前にprecommitする。今回既存baseline数値は既に閲覧済みと記録し、未見データとは呼ばない。証明済みの同じpolicy/semanticsを両Entryへ適用し、利益継続・利益保護・損失抑制を分離評価する。
5. NEW EXIT研究、causal replay、robustness、concentration、再現性、採用/不採用判定へ進む。有限探索終了時に勝つまで追加しない。必要な工程がPASSなら中間ごとに機械的STOPせず次工程へ進めるが、データ/因果性/権限blockerを突破しない。
6. 最終EXIT固定後に新ledgerでCapital、Portfolio比較。全件の未確定と評価価格問題が解消するまではfull Portfolio Return/MDDを捏造しない。最終Entry決定は保留。

GitHub保存checkpointごとに現状・実作業・根拠SHA/CI・主要数値・未解決点・次工程・変更禁止事項を追記する。後続は本R17とその後の最新checkpointを先に読む。

## データ境界・変更禁止事項

Provider新規市場データ取得0。Common Holdout / REPORT19 / Validation / OOS / Fresh / Prospective新規開封0。
Evidence append-only。旧結果/失敗履歴を削除・上書きしない。他作業者の変更上書き、force push、main merge、live/paper/productionは禁止。
executionAllowed=false / brokerWriteAllowed=false / excelOrderWriteAllowed=false / rssOrderFunctionAllowed=false / liveTradingAllowed=false / paperTradingAllowed=false / automaticPromotionAllowed=false / productionUpdateAllowed=false / transmitted=false。

## 参照する既存Evidence

- docs/evidence/phase57-entry-all-material-v1/ENTRY_DUAL_FREEZE_R10.json
- docs/evidence/phase57-entry-all-material-v1/EXIT_CAPITAL_INTEGRATION_PLAN_R11.md (研究の次工程のみ本R17がsupersede)
- docs/evidence/phase57-dual-entry-exit-integration-v1/ADAPTER_CONTRACT_R13.json
- docs/evidence/phase57-dual-entry-exit-integration-v1/EXIT_RECEIPT_R14.json
- docs/evidence/phase57-dual-entry-exit-integration-v1/EXIT_RESULT_R14.md
- docs/evidence/phase57-dual-entry-exit-integration-v1/CAPITAL_CONTRACT_R15.json
- docs/evidence/phase57-dual-entry-exit-integration-v1/CAPITAL_RECEIPT_R16.json
- docs/evidence/phase57-dual-entry-exit-integration-v1/INTEGRATION_RESULT_R16_JA.md
