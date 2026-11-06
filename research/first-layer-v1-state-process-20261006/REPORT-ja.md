# FIRST LAYER V1 — State Process / Two Metrics

**FIRST_LAYER_V1_IMPLEMENTED_AND_EVALUATED_DEVELOPMENT**

実装・固定モデル・全1600 EntryのKEEP/DROP・有限評価を完了。PRIMARY95 TEST:本来PLUS230件中222件KEEP、8件DROP、保持率96.52%。本来MINUS261件中10件DROP、251件KEEP、除去率3.83%。PLUSは多く保持したがMINUS除去は少数にとどまった。性能PASSは宣言しない。

評価期間:2025-07-30〜2025-08-25、s41..s58の18 sessions、TEST501 Entry(PLUS230/MINUS261/UNKNOWN10/ZERO0)。全研究1600 Entry(PLUS706/MINUS854/UNKNOWN40)と区別する。先頭40 sessions1099件のscoreはFIT/CAL参考であり、主成績に合算しない。全58sessionsは閲覧済みDevelopment、Fresh/OOS0。

|本来の結果|元の件数|KEEP|DROP|評価|
|---|---:|---:|---:|---:|
|PLUS|230|222|8|保持96.52%|
|MINUS|261|251|10|除去3.83%|

|固定CAL動作点|PLUS KEEP/元P|PLUS DROP|保持率|MINUS DROP/元M|MINUS KEEP|除去率|
|---|---:|---:|---:|---:|---:|---:|
|95% PRIMARY|222/230|8|96.52%|10/261|251|3.83%|
|99% diagnostic|224/230|6|97.39%|5/261|256|1.92%|
|100% diagnostic|224/230|6|97.39%|5/261|256|1.92%|
|全KEEP比較|230/230|0|100.00%|0/261|261|0.00%|

99/100%はCAL PLUS66/78/78件がすべて100未満でk=0になるため、3blockとも同じ閾値となった。動作点名はTEST保持率の保証値ではない。

|PRIMARY95内訳|PLUS KEEP/P|保持率|MINUS DROP/M|除去率|
|---|---:|---:|---:|---:|
|全体|222/230|96.52%|10/261|3.83%|
|現在Stateあり|90/94|95.74%|6/124|4.84%|
|現在Stateなし|132/136|97.06%|4/137|2.92%|
|Block1|76/78|97.44%|1/76|1.32%|
|Block2|72/78|92.31%|7/99|7.07%|
|Block3|74/74|100.00%|2/86|2.33%|

Block2はPLUS72/78保持(92.31%)。期間差を隠さず、TEST後の閾値・分割・モデル変更0。日別・block別4cellはTWO_METRICS.jsonへ保存。

UNKNOWNはTEST10件ともKEEP、DROP0。全1600のUNKNOWN40件はPRIMARYでKEEP39/DROP1、99/100%ではKEEP40/DROP0。正負の分母・学習・閾値へUNKNOWN/ZEROを入れていない。未推論/エラー0。

実装:新規Q+S+H+T+P+A+Mの379 canonical fields、1つの正則化logit family、最大6run、5/15予定slot市場窓。current formal nullは維持し、last observedは過去事実として別保持。履歴あり1391件、履歴なし209件も市場/品質から有限score。current unobserved910件を除外せず、一律ABSTAIN/KEEP0。原本バーの0埋め/forward-fill0、raw ID/security/絶対日付のモデル入力0。条件付きcurrent効果とhistory効果を区別し、r0/Hの完全同義列はaliasで一度のみencode。

固定モデル:blocks1/2/3のFIT既知成熟教師912/1069/1223件、特徴列1429/1435/1448。model3fit、preprocessor3fit、CAL threshold9決定。係数初期0、float64、解析gradient、L-BFGS-B指定設定。旧Sign行列/モデル/score/threshold/32slotを継承せず、追加family/grid/seed/window/run長探索0。初回CAL/TESＴが低くても指定固定TESTを測定した。

QA:future RAW/State suffix改変・削除に対するfeature bytes不変を全1600件で確認。current null/history有無、null/segment越し偽TRANSITION・HOLD・dwellの拒否、future run closure、部分市場窓/Volume/Value、teacher capability拒否、整数k+1/tieKEEP fixtures PASS。新設QA4829checks+continuity7fixtures、独立集計14634checks、mismatch0。独立count evaluatorはprimary evaluatorをimportせず、元教師IDとKEEP/DROP、FIT mean/std/語彙、CAL order statistic、501件TEST unionを再構成。analytic gradient fixture PASS。

原本/系譜:最新Phase0 PASS public351f287edae4c869b83bf16ee38e03306bd99b8a / private6a10d1709daffe18e46ca4a969721ad73102a8cfからappend-only研究branch。C4原本354,283,802 bytes/SHAを再利用、購入前市場123557 bars/State prefix246512 endpointsの認証cacheを共有し、月次RAW全走査0、State engine再生0。SOURCE_PIN/Frozen Entry/teacher/State9/Path/EXIT semantics変更0。

PRECOMMIT:入力registry・正式field対応・実日付split・モデル/環境・3fit・CAL閾値・2指標・UNKNOWN・Development TEST範囲をGitHub保存し、本文/bytes/SHA256/blob readback6/6 PASS後に実装/fit。後blockで元TESTをFIT/CALとして使う前に前block予測sealをrunnerで照合。3block全TEST予測seal後にTEST主集計を開いた。

制約:元Teacher SIGN_TARGETS(78,284 bytes/SHA37395d7567df741a74b1ff749a32118cec04ed988da101b81634c2c55ae9ae0d)を固定し、native EXIT/EOD売fill・cost/netの全行計算はPhase0正式certificationを再利用。今回のEXIT replay0。actual historical receive chronology UNKNOWN、凍結bar_end availability仮定を維持。独立評価をFresh/OOS認証や資産増加の証拠としない。

成果物: public仕様/集計/hash/実施量、private canonical features・元教師・前処理・固定coefficients・CAL/TEST seal・全Entry decisions・実装code。infer_fixed.pyは教師を読まず、固定blockモデルからoffline KEEP/DROPを返す。モデル/閾値の再fitや本番接続は行わない。

保存:研究branchの本文/blob/bytes/SHA256/branch HEADをactual GETで読み戻しREADBACK_RECEIPTへ保存。大きい新規feature archiveは512KiB以下のbyte chunksとして保存し、順序連結後の元archive hashも照合する。元RAW原本は改変/再圧縮しない。

実行量:model fit3 / preprocessing fit3 / CAL threshold9 / feature build1 / TEST予測seal3 / technical retry0。provider request、protected commonHoldout/Fresh、旧Sign再開、State/Entry/EXIT変更、追加model、Capital、orders、本番、main merge、force pushはすべて0。

**次方針:この有限Workを完了しSTOP。MINUS除去の弱さを記録する。第2/第3層・Capital・productionへ進まない。**

実時計JST 2026-10-06T23:34:07.120958+09:00 / UTC 2026-10-06T14:34:07.120958+00:00。owner Iam-2squared / Codex。
