# FIRST LAYER 時間制限解除後の研究結果

研究用の主候補はC08_STATE_COMPACT/CAL95へ更新。探索322件でPLUS KEEP133/144＝92.36%、MINUS KEEP149/172＝86.63%。目標未達。C03/CAL95よりMINUS KEEPを1件減らし、PLUS KEEPは3件減った。事前の選定規則（PLUS保持≥90%の中でMINUS KEEP最小）に従った更新であり、全指標でC03を支配するとは言わない。C03もPareto候補として保持。

07:04:33 JSTのユーザー指示で07:00終了と従属06:00探索停止を解除。元の40通常fit/42総試行、8cycle、2構成/cycle、120新閾値＋9旧閾値、6報告fit等は変更していない。台帳・親・V1を初期化していない。現在は8cycle上限に到達しており、新規fitは開始しない。

## 探索の同条件比較

先頭40sessionsのS1/S2比較を合算322 Entry（PLUS144、MINUS172、UNKNOWN6、ZERO0）。ADAPTIVE_DEVELOPMENT、全58sessionsは露出済み、Fresh/OOS=0。

|候補/CAL|PLUS KEEP/DROP（P144）|PLUS保持|MINUS KEEP/DROP（M172）|MINUS残存|MINUS除去|
|---|---:|---:|---:|---:|---:|
|V1/95|138/6|95.83%|163/9|94.77%|5.23%|
|C03_STATE_CHART_LOGIT/95|136/8|94.44%|150/22|87.21%|12.79%|
|C05_REG_WEAK/95|137/7|95.14%|153/19|88.95%|11.05%|
|C05_REG_STRONG/95|138/6|95.83%|157/15|91.28%|8.72%|
|C06_ORDERED_CHAMPION/95|133/11|92.36%|156/16|90.70%|9.30%|
|C06_ORDERED_REJECT_BRANCH/95|133/11|92.36%|160/12|93.02%|6.98%|
|C08_STATE_COMPACT/90|123/21|85.42%|138/34|80.23%|19.77%|
|C08_STATE_COMPACT/95|133/11|92.36%|149/23|86.63%|13.37%|
|C08_STATE_COMPACT/99|144/0|100.00%|168/4|97.67%|2.33%|

整数目標:PLUS KEEP≥130、MINUS KEEP≤34。C08/CAL95は133≥130だが149>34で未達（MINUSをさらに115件DROPする必要）。CAL99ではV1のPLUS144/MINUS170に対してPLUS144/MINUS168で、PLUS減少なしにMINUS2件を削減。ただし主動作点は95のまま、動作点を組み合わせた架空成績は作らない。

## 今回行った未実施工程

C05: FIT内定数列除去＋事前固定1/3・3倍正則化の2構成、4fit。C03を更新せず、PLUS高保持側のPareto拡張を保存。列除去552/539、符号化を別実装で再構成し検算。

C06: 購入前に確定するactive-time prefixを固定8区間へ分割し、順序形状88項目。C03と保存済み低MINUS側C05_STRONGの2枝、4fit。教師を読まない純粋builder、全1600件future suffix/order不変、空区間・欠測・昼休み・flat・ゼロ出来高等21906検査PASS。RAW再走査0。主候補を更新せずPareto拡張と派生入力を保存。

C07: 準備済みV1入力/仕様と提供済みDictionary方針を照合。Entry一覧だけでは全Selector候補snapshotを証明できず、旧v0研究Profileも2025時点の正式PIT profileではない。今回使用可能なpeer/membership/effective-date入力が未認証のため追加だけSKIP、0fit。他所にも存在しないとの主張はしない。新provider取得やProtected開封で穴埋めしない。

C08: C03の凍結State意味を変えず、細粒度run属性の一部を省いた表現とFIT定数列除去、1構成2fit。実列785/813。C03の市場/State元入力は同一hash、currentなし910・historyなし209 Entryを保持。研究親として昇格。全Pareto9点と全不採用モデルを保存。

## 最終501件との区別

前回固定PRIMARYはC03/CAL95のまま。保存済み結果はPLUS218/230＝94.78%、MINUS252/261＝96.55%、目標未達。C04副候補はPLUS230/230、MINUS256/261。これらは既に閲覧したDevelopmentであり、今回の5新構成で501件のスコア/集計を追加生成していない。新しい研究主候補C08の501件成績は未測定。今回の探索成績を501件成績に置換しない。report6fit枠は前回使い切っており、再測定/候補すり替え/閾値調整は0。

## 実行量と監査

再開後4cycle（C07はSKIP）、5新構成、10追加fit。累計8cycle、30fit試行/成功、30前処理fit。内訳基準2＋探索22＋報告6。新閾値90＋旧保存V1再確認9＝99。retry0。全30封印model/preprocessor/prediction hashを照合しPASS、台帳の新規ズレ0。元のC02イベント欠落の補正Evidenceは保持し再fit/時刻捏造0。台帳更新へ排他lockを追加し、single writerで進めた。

主集計をimportしない独立count検算: C05各4509 checks、C06各5037 checks、C08 4083 checks、すべて不一致0。別encoder/列選択再構成: C05各3276、C06各3628、C08 2489 checks、fit0、不一致0。各S1をseal後にS2を進め、成熟教師・FIT-only前処理・CAL-only整数順序統計・同点KEEPを維持。

Entry/EXIT/費用/teacher/source/State9/Path/reset/gapを変更しない。旧Sign資産復活0。新provider0、保護データ開封0、Freeze変更0、Capital0、orders0、本番0、第2/第3層0、main変更0、force push0、新schedule0。

## 次工程と必要な許可

時間上限は解除済み。別の上限であるcycle8/8へ到達したため保存して停止。残り通常fit10、探索fit枠10、新閾値30は残るが、cycle上限を黙って拡張しない。

最小の追加許可案はcycle上限のみ8→11へ変更し、累計通常fit40、新閾値120、reportfit6を維持すること。次の単一仮説C09: C08の同じcompact入力で既存の小型HGB7leaf/15leafの2構成を比較（4fit）。後続は結果から選ぶ事前固定仮説、最大残り6fit。旧REPORT501で追加選定しない。期限・予算のリセット、Phase0、ゼロ設計へ戻らない。

NEXT_ACTION:Cycle budget8/8 reached, time limit cancelled by user. Preserve C08_STATE_COMPACT/CAL95 as research parent and C03/Pareto. Request only cycle cap extension8→11; use at most remaining10 normal fits within total40 and new threshold120, no new501 REPORT fits. Next single hypothesis C09: same compact input with two fixed small HGB structures. No Phase0, no reset, no REPORT retuning.

Git保存・actual GET照合はCONTINUATION_READBACK_RECEIPT参照。コード・model・行別入力/教師/予測はprivate、公開は仕様・集計・hash。実保存後のSHAのみ記録する。
