# FIRST LAYER V1＋α 継続改善 最終報告

固定PRIMARYはC03_STATE_CHART_LOGIT / CAL95。目標は未達。探索比較では同条件V1よりMINUS KEEPを13件減らし（163→150）、PLUS KEEPは2件減った（138→136）。しかし固定501件ではその改善が再現せず、V1 CAL95よりPLUS KEEPが4件減り（222→218）、MINUS KEEPが1件増えた（251→252）。最終結果を理由にPRIMARYをすり替えず、V1・C03・全Pareto候補を保持する。

状態: PROGRESS_SAVED_TARGET_NOT_REACHED。計測完了: 2026-10-07T06:55:03.959405+09:00。元の07:00 JST上限を延長せず、06:00以降の新規探索は0。C05〜C08は未実施であり、性能FAILではない。

## 固定報告期間

2025-07-30〜2025-08-25、s41..s58、501 Entry。PLUS230 / MINUS261 / UNKNOWN10 / ZERO0。全Development、Fresh/OOS=0。UNKNOWNは別保持し正負分母に混ぜない。

|候補 / CAL動作点|真PLUS|KEEP|DROP|PLUS保持|真MINUS|KEEP|DROP|MINUS残存|MINUS除去|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|V1旧CAL95（今回再計算一致）|230|222|8|96.52%|261|251|10|96.17%|3.83%|
|V1 CAL90 /0fit|230|212|18|92.17%|261|237|24|90.80%|9.20%|
|固定PRIMARY C03 /95|230|218|12|94.78%|261|252|9|96.55%|3.45%|
|固定SECONDARY C04_B /99|230|230|0|100.00%|261|256|5|98.08%|1.92%|
|V1同条件CAL99|230|224|6|97.39%|261|256|5|98.08%|1.92%|
|全KEEP|230|230|0|100.00%|261|261|0|100.00%|0.00%|

目標の整数条件はPLUS KEEP≥207/230かつMINUS KEEP≤52/261。PRIMARYは218≥207を満たすが252>52で未達。SECONDARYも230≥207だが256>52で未達。PRIMARYに必要な追加MINUS DROPは200件。CAL90/95/99はCAL上の動作点名であり、報告保持率を保証しない。

## 探索比較（報告期間と混ぜない）

先頭40sessionsのS1/S2 DEV_COMPARE合算322 Entry、PLUS144 / MINUS172 / UNKNOWN6。選定に反復利用したADAPTIVE_DEVELOPMENTであり独立評価ではない。下表は同条件CAL95比較。全3動作点はSEARCH_ARCHIVE/TWO_METRICSに保存。

|候補 / CAL動作点|真PLUS|KEEP|DROP|PLUS保持|真MINUS|KEEP|DROP|MINUS残存|MINUS除去|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|V1 /95|144|138|6|95.83%|172|163|9|94.77%|5.23%|
|C01_CHART_LOGIT /95|144|136|8|94.44%|172|151|21|87.79%|12.21%|
|C02_D1_LOGIT /95|144|135|9|93.75%|172|156|16|90.70%|9.30%|
|C02_D5_LOGIT /95|144|136|8|94.44%|172|156|16|90.70%|9.30%|
|C03_STATE_CHART_LOGIT /95|144|136|8|94.44%|172|150|22|87.21%|12.79%|
|C04_HGB_A /95|144|132|12|91.67%|172|150|22|87.21%|12.79%|
|C04_HGB_B /95|144|126|18|87.50%|172|151|21|87.79%|12.21%|

主候補選定はPLUS KEEP≥130/144を満たす点のうちMINUS KEEP最小、続いてPLUS KEEP最大等の事前規則。C03 /95は136・150。副候補C04_B /99は137・161で、主候補よりPLUS KEEPが高いPareto点からREPORT前に固定した。最終501件では副候補のPLUS保持100%だったが、それを主候補へ書き換えていない。

## 追加情報と継承

C01: BUY_INTENT前の当日チャート38項目（位置、進行、観測済み高安、連結経路、ローソク、強度、単位検証済みVWAP等）。C02: 承認済み58日付内の直前観測日/最大5観測日の無次元文脈。連続取引日D-1/D-5とは呼ばない。企業行動basis未認証の価格差比較はSKIP。C03: 凍結StateとC01の12交互作用。C04: 事前固定2構成の小型HGB、seed sweepなし。

採用した研究用親はC03。追加情報/表現の改善であり閾値変更だけではない（探索CAL95対CAL95）。探索のPareto Archiveは10点保存。不採用モデル、C02の派生情報、C04全モデル、V1は廃棄しない。最終報告で改善を確認できなかったことを隠さず、未知市場の性能や予測不能性へ一般化しない。

## Block別内訳

|候補 / CAL動作点|真PLUS|KEEP|DROP|PLUS保持|真MINUS|KEEP|DROP|MINUS残存|MINUS除去|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|PRIMARY B1|78|76|2|97.44%|76|75|1|98.68%|1.32%|
|PRIMARY B2|78|70|8|89.74%|99|94|5|94.95%|5.05%|
|PRIMARY B3|74|72|2|97.30%|86|83|3|96.51%|3.49%|
|SECONDARY B1|78|78|0|100.00%|76|76|0|100.00%|0.00%|
|SECONDARY B2|78|78|0|100.00%|99|97|2|97.98%|2.02%|
|SECONDARY B3|74|74|0|100.00%|86|83|3|96.51%|3.49%|

## Current State有無別

報告対象にはcurrent=nullの280 Entry（PLUS136 / MINUS137 / UNKNOWN7）を残した。全1600件ではcurrentなし910件・historyなし209件を除外せず、2固定候補とも全1600推論を保存。早期1099の学習内参照推論は主成績に混ぜない。nullを過去Stateで現在値へ補間していない。

|候補 / CAL動作点|真PLUS|KEEP|DROP|PLUS保持|真MINUS|KEEP|DROP|MINUS残存|MINUS除去|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|PRIMARY current=available|94|90|4|95.74%|124|118|6|95.16%|4.84%|
|PRIMARY current=unavailable|136|128|8|94.12%|137|134|3|97.81%|2.19%|
|SECONDARY current=available|94|94|0|100.00%|124|120|4|96.77%|3.23%|
|SECONDARY current=unavailable|136|136|0|100.00%|137|136|1|99.27%|0.73%|

## 実行量・検算

4cycle、探索6新構成＋同条件V1、14探索fit＋6固定報告fit＝20fit試行/成功、20前処理fit。新CAL閾値60＋保存V1再ベンチマーク9＝69。retry0。上限40通常fit/42総試行、120新閾値＋9旧閾値を超えていない。C05〜C08未開始。CI起動0。記録上の最初fit 2026-10-07T00:39:02.486823+09:00、最後fit 2026-10-07T06:54:58.540640+09:00。無人夜通し連続稼働とは主張しない。

台帳13件に対し14封印済み探索モデルがあったため、モデル/前処理/CAL/予測hashから14件へ補正。欠落はC02_D5_LOGIT S2イベント群。原台帳保持、欠けた実時計は捏造しない。原因は未認定（旧台帳read-modify-writeにlockがなかった）。最終工程はsingle writerで順次実行。再fit0。

C01 future/cutoff/missing QA6402 PASS、C02日付/cutoff等QA4801 PASS。当日123557barのOHLC・Value/Volume検査違反0。独立count verifierは主集計をimportせず、各最終候補7943checks・不一致0。FIT-only前処理、成熟教師、CAL-only整数順序統計、同点KEEP、全Entry収支、各予測sealを検算。各候補の全3REPORTblockをseal後、2候補ともseal済みであることを確認してから最初の集計を開いた。

## 境界・保存・再開

Entry/EXIT/費用/State9/teacher/sourceを維持。旧Sign資産再利用0。元source hashとV1 cacheを再利用し、RAW4か月をcycleごとに走査していない。新provider0、protected開封0、Freeze変更0、Capital0、orders0、本番接続0、第2/第3層進行0。

専用branchは両repoともresearch/first-layer-v1-plus-alpha-night-20261007。main変更/merge/force push0。REPORT前pin commit:3b4c9b6856eeba697a7ef3c9de77636c5a4ffbf7。最終HEAD/実GET本文・bytes/blob・SHA256照合はREADBACK_RECEIPT参照（実保存後に記録）。モデル、前処理、行別予測、教師、入力はprivateのみ。公開は仕様・集計・hash。

NEXT_ACTION: New time authorization required. Continue from C03_STATE_CHART_LOGIT and preserved Pareto archive; next single hypothesis: C05 FIT-only compact representation/regularization. No Phase0, no refit of completed work, no retuning on the501 REPORT. Original deadline remains2026-10-07T07:00:00+09:00.

同じREPORT501で追加の選定・閾値調整をしない。次の研究はC03とPareto資産から継続し、ゼロ設計へ戻らない。元の上限後の再開は新しい期限/予算の許可が必要。
