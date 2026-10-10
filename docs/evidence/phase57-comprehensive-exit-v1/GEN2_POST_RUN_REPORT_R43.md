# Ark Terminal Phase57 — Gen2 R41 Post-run Report R43

保存時刻：2026-09-26T20:28:05.975729+09:00。作成basis／監査保存HEAD：`596fc039618b4563313cdab07d6726ff7815d78d`。実行SHA：`c031976a319130b6be379586147fff53cee6f741`。 結果保存commit：`63a123a371d486f58c9c4d726a82a73e9c8a3c3b`。

## 🧭現在地

**正式結果はNO_SELECTION_STOP。16候補のうち全固定Gateを通過した候補は0件です。** 両Entryの32ケースすべてでPrimary Mean Net ≥2.00%を満たしません。EXIT Freeze・Capital replay・運用移行には進みません。

今回完了したのは、独立artifact監査→保存ledgerの正式R41採点→scorecard／selection A/B一致確認→追加報告→独立Gate数値照合です。今回のGen2監査・採点での再fit・policy再replay・追加候補はいずれも0。元の64 fitsと16 policiesの計算結果を使用しています。

採点対象は34 OOF score sessions・各Entry arm 1,267 Opportunitiesです。58 Development sessions／2,155 Opportunities全体を採点済みと扱いません。Filled EntryはIMMEDIATE 1,150／R1 1,107、No Entryは117／160です。

[候補全体CSV](r43-result/candidate-summary.csv)・[全bucket CSV](r43-result/bucket-summary.csv)・[完全なscorecard／追加報告ZIP](r43-result/full-scorecards-and-reports.zip)を併用してください。本文は小数丸め表示、JSON／CSVは保存値を保持します。完全ZIPは53ファイル、SHA-256は`2eae6515a198d1ee496e09948297c94a139be98230d65f0278ae39d7a494b402`です。

## 🔍Artifact監査

- GitHub Actions run：`36233758837`、artifact ID：`10904078164`。
- Archive SHA-256：`dbbc9e79292c8701d962a09f9ddf50d817241273fc50a5652d6b28d5580dffcd`。
- Protocol SHA-256：`5fdc059936ba31466a7dace520f218353c634e6c8444d20d5ab21069c745deb4`。
- [独立監査Evidence](r43-result/artifact-audit.json)：`GEN2_ARTIFACT_AUDIT_PASS`をGitHub保存した後に性能を集計。
- 656,247 rows、4 prediction specs、64 model bundlesの保存identityを確認。OOF scored rows 381,223、非score rowsのNaN 275,024。
- 全ラベルを独立再構成。head別mask、fold／purge／knownAt、重みの再構成、Entry・cost・execution reference・owned null semanticsを確認。
- 16候補＋非選択HOLD診断の17組ledger A/Bがbyte-identical。今回の16 scorecards＋selectionの17ファイルもA/B一致。
- 独立Gate数値照合は32 candidate-armケースで不一致0。Frozen scorerを呼ばない独立集計でもNO_SELECTION_STOP一致。

監査の範囲は明示保持します。Pattern187行列の全再生成、モデル再推論、policy全時系列の再replayは今回実施していません。モデルmetadata読取時のローカルscikit-learn 1.8.0／artifact 1.7.2差は記録済みで、推論を実行していません。元のfitが独立に二度再学習されたという主張もしません。

追加報告テスト13件を含むR43テスト35件と固定R41 contractテスト18件、計53件がdedicated CIでPASSしました。Run `36238525156`、exact head `63a123a371d486f58c9c4d726a82a73e9c8a3c3b`、artifact `10904557327`。全保存Evidence hashと固定selectionの再確認もPASS。詳細receiptは最終controlling handoffに保存します。

## 🧠Gen2 16候補の違い

Continuationは次回exact OPENを基準とする最大60 active bars内の上方1%到達、Failureは最大15 active bars内の下方0.75%到達という、事前固定された独立event labelです。残りcontinuous barsによるhorizon短縮、必要OHLC完全性、head別欠損、同一足の両到達を独立に扱い、intrabar順序を推定しません。Failureはadverse-excursion proxyであり、上昇仮説崩壊を直接証明するラベルではありません。

| 候補 | Prediction spec | 共通feature |
| --- | --- | --- |
| 01–04 | Logistic C=1 | CORE＋calendar |
| 05–08 | Logistic C=1 | CORE＋calendar＋Pattern187 |
| 09–12 | HGB leaf=7 | CORE＋calendar |
| 13–16 | HGB leaf=7 | CORE＋calendar＋Pattern187 |

各4候補の順序は `(C上限, F下限, fresh persistence)`＝`(0.35,0.60,1)`、`(0.35,0.60,2)`、`(0.50,0.60,1)`、`(0.50,0.60,2)`。C/Fは**未校正のclassification score**であり、校正済み確率とは呼びません。4 specs×4 folds×2 arms×2 heads＝64 fits。閾値違いで同一モデルを再fitしません。

## 📊16候補全数値表

IDは`GEN2_R41_`を省略。全行未選択です。Net単位は%、PFは比率、勝率は%。`N/R/M/C`＝Filled／Resolved／通常OPEN欠損を経験した件数／Censored。Mは他列と重複し、N=R+Cです。`保有A/W`はactive／wall分の中央値、`EXIT M/T/U`はMODEL／forced terminal／unresolved件数です。平均損失は負値。評価不能はnullで、0に置換しません。全体母数・No Entryは前節のとおりです。 Primary Netは既存buy-side 5bps込みFrozen Entry価格から計算し、sell-side 0.05ppのみを控除します。buy costを二重計上せず、stressはsell-side 0.10／0.20ppです。


### IMMEDIATE

| 候補 | N/R/M/C | Mean | Median | PF | 勝率 | 平均益 | 平均損 | p05 | p10 | worst | 保有A/W | EXIT M/T/U |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 01 | 1150/1137/124/13 | -0.171 | -0.100 | 0.883 | 43.98 | 2.919 | -2.596 | -6.938 | -4.383 | -29.033 | 136.0/150.0 | 364/773/13 |
| 02 | 1150/1136/79/14 | -0.196 | -0.265 | 0.877 | 43.40 | 3.205 | -2.804 | -7.787 | -4.860 | -29.033 | 145.0/150.5 | 223/913/14 |
| 03 | 1150/1137/158/13 | -0.121 | -0.100 | 0.896 | 43.62 | 2.390 | -2.064 | -5.651 | -3.329 | -19.568 | 66.0/74.0 | 613/524/13 |
| 04 | 1150/1136/104/14 | -0.164 | -0.184 | 0.879 | 43.49 | 2.754 | -2.409 | -6.662 | -3.884 | -19.568 | 115.0/120.0 | 432/704/14 |
| 05 | 1150/1139/203/11 | -0.134 | -0.100 | 0.890 | 44.16 | 2.471 | -2.194 | -6.050 | -3.352 | -29.033 | 70.0/85.0 | 599/540/11 |
| 06 | 1150/1137/154/13 | -0.121 | -0.134 | 0.914 | 44.06 | 2.940 | -2.533 | -6.805 | -4.071 | -29.033 | 115.0/120.0 | 383/754/13 |
| 07 | 1150/1140/205/10 | -0.126 | -0.100 | 0.876 | 43.51 | 2.059 | -1.809 | -4.861 | -2.885 | -29.033 | 45.0/51.5 | 724/416/10 |
| 08 | 1150/1137/175/13 | -0.129 | -0.100 | 0.895 | 44.68 | 2.466 | -2.226 | -6.100 | -3.586 | -29.033 | 85.0/90.0 | 519/618/13 |
| 09 | 1150/1135/63/15 | -0.159 | -0.255 | 0.902 | 43.00 | 3.414 | -2.855 | -7.795 | -5.126 | -29.033 | 174.0/179.0 | 129/1006/15 |
| 10 | 1150/1135/31/15 | -0.143 | -0.255 | 0.912 | 43.26 | 3.451 | -2.884 | -7.795 | -5.148 | -29.033 | 174.0/179.0 | 88/1047/15 |
| 11 | 1150/1135/107/15 | -0.085 | -0.218 | 0.941 | 42.91 | 3.170 | -2.532 | -6.828 | -4.294 | -20.090 | 145.0/150.0 | 327/808/15 |
| 12 | 1150/1135/92/15 | -0.110 | -0.227 | 0.927 | 43.52 | 3.189 | -2.652 | -7.066 | -4.604 | -29.033 | 145.0/150.0 | 264/871/15 |
| 13 | 1150/1135/83/15 | -0.111 | -0.235 | 0.933 | 43.17 | 3.566 | -2.905 | -7.922 | -5.148 | -29.033 | 174.0/179.0 | 150/985/15 |
| 14 | 1150/1135/36/15 | -0.106 | -0.255 | 0.936 | 43.26 | 3.603 | -2.933 | -8.037 | -5.238 | -29.033 | 174.0/179.0 | 77/1058/15 |
| 15 | 1150/1136/168/14 | -0.143 | -0.227 | 0.905 | 42.87 | 3.168 | -2.628 | -7.330 | -4.345 | -29.033 | 142.5/150.0 | 400/736/14 |
| 16 | 1150/1135/105/15 | -0.099 | -0.232 | 0.937 | 42.91 | 3.423 | -2.745 | -7.591 | -4.747 | -29.033 | 145.0/154.0 | 246/889/15 |


### ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF

| 候補 | N/R/M/C | Mean | Median | PF | 勝率 | 平均益 | 平均損 | p05 | p10 | worst | 保有A/W | EXIT M/T/U |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 01 | 1107/1097/120/10 | -0.090 | -0.100 | 0.929 | 45.67 | 2.593 | -2.346 | -6.235 | -3.621 | -32.017 | 115.0/125.0 | 360/737/10 |
| 02 | 1107/1096/84/11 | -0.142 | -0.100 | 0.900 | 44.71 | 2.849 | -2.560 | -7.055 | -4.558 | -32.017 | 134.5/147.5 | 226/870/11 |
| 03 | 1107/1097/146/10 | -0.033 | -0.100 | 0.969 | 45.49 | 2.205 | -1.900 | -4.686 | -2.858 | -32.017 | 61.0/70.0 | 552/545/10 |
| 04 | 1107/1096/104/11 | -0.089 | -0.100 | 0.926 | 44.53 | 2.497 | -2.165 | -5.520 | -3.322 | -32.017 | 95.0/101.5 | 385/711/11 |
| 05 | 1107/1100/201/7 | -0.054 | -0.100 | 0.953 | 45.55 | 2.391 | -2.099 | -5.314 | -3.062 | -32.017 | 73.0/86.5 | 551/549/7 |
| 06 | 1107/1098/111/9 | -0.098 | -0.100 | 0.926 | 45.26 | 2.735 | -2.441 | -6.866 | -3.968 | -32.017 | 115.0/130.0 | 343/755/9 |
| 07 | 1107/1100/197/7 | 0.092 | -0.100 | 1.099 | 45.82 | 2.232 | -1.717 | -3.903 | -2.526 | -32.017 | 49.0/62.5 | 650/450/7 |
| 08 | 1107/1098/132/9 | -0.011 | -0.100 | 0.991 | 45.36 | 2.577 | -2.158 | -5.566 | -3.284 | -32.017 | 89.0/100.0 | 461/637/9 |
| 09 | 1107/1095/29/12 | -0.161 | -0.140 | 0.895 | 44.47 | 3.082 | -2.759 | -7.632 | -4.851 | -32.017 | 166.0/172.0 | 119/976/12 |
| 10 | 1107/1095/21/12 | -0.151 | -0.207 | 0.902 | 44.11 | 3.149 | -2.755 | -7.632 | -4.896 | -32.017 | 171.0/176.0 | 89/1006/12 |
| 11 | 1107/1095/70/12 | -0.034 | -0.100 | 0.975 | 45.57 | 2.831 | -2.432 | -6.749 | -3.989 | -32.017 | 125.0/130.0 | 290/805/12 |
| 12 | 1107/1095/45/12 | 0.006 | -0.100 | 1.004 | 46.12 | 2.894 | -2.466 | -6.864 | -3.989 | -32.017 | 125.0/132.0 | 250/845/12 |
| 13 | 1107/1095/46/12 | -0.113 | -0.194 | 0.927 | 44.47 | 3.220 | -2.783 | -7.687 | -4.851 | -32.017 | 168.0/175.0 | 126/969/12 |
| 14 | 1107/1095/25/12 | -0.095 | -0.217 | 0.939 | 44.47 | 3.290 | -2.807 | -7.747 | -4.896 | -32.017 | 173.0/178.0 | 64/1031/12 |
| 15 | 1107/1096/111/11 | -0.082 | -0.100 | 0.943 | 44.34 | 3.046 | -2.573 | -7.544 | -4.471 | -32.017 | 125.0/137.0 | 325/771/11 |
| 16 | 1107/1096/53/11 | -0.089 | -0.203 | 0.940 | 44.53 | 3.158 | -2.696 | -7.565 | -4.674 | -32.017 | 154.0/160.0 | 202/894/11 |


### Bucket別の全16候補範囲

| Bucket | OOF母集団/arm | Filled IM/R1 | Mean Net IM | Mean Net R1 |
| --- | --- | --- | --- | --- |
| <1% | 85 | 60/57 | -0.684～-0.467 | -0.619～-0.545 |
| 1-2% | 220 | 200/183 | -0.868～-0.573 | -0.756～-0.531 |
| 2-3% | 246 | 234/226 | -0.927～-0.232 | -0.842～-0.277 |
| 3-4% | 151 | 144/140 | -0.897～-0.475 | -0.765～-0.153 |
| 4-5% | 106 | 103/103 | -0.808～-0.340 | -0.509～0.180 |
| >=5% | 393 | 387/381 | 0.437～1.330 | 0.581～1.100 |
| NOT_EVALUABLE | 66 | 22/17 | -0.851～-0.298 | -0.961～-0.486 |

全6評価bucketのGateは各armとも16候補すべてFAILです。NOT_EVALUABLE 66件はOOF母集団側の件数で、Fill後の該当数は22／17です。canonical全2,155件の>=5% N666と、今回OOF母集団393／Filled387・381を区別します。

### Cost robustnessとconcentration


| Entry | PF@0.10pp | PF@0.20pp | 最大trade寄与% | 上位5寄与% | 最大session寄与% |
| --- | --- | --- | --- | --- | --- |
| IMMEDIATE | 0.832～0.908 | 0.751～0.854 | 2.207～3.410 | 9.595～12.413 | 5.697～6.945 |
| R1 | 0.865～1.044 | 0.806～0.943 | 2.159～2.942 | 9.549～12.068 | 5.765～7.855 |

cost 0.10ppのPF≥1を通るのはR1 #07のみ、0.20ppのPF≥0.95は両armとも0/16です。R1 #07も0.20ppではPF0.943250、Mean Net−0.057559%。Concentration Gateは両arm16/16 PASSですが、正の無加重trade return寄与の集中度であり、未実施のCapital配分集中度ではありません。

## 🚀>=5%Winner Continuation

>=5%群のFilled＝ResolvedはIMMEDIATE 387件、R1 381件、post-Entry capture evaluableは377／363件。10／18件のcapture欠損を0に補完しません。全候補の>=5% Mean NetはIMMEDIATE 0.436674～1.329990%、R1 0.581115～1.100313%。固定bucket条件Mean≥3.25%、Median≥2%、capture中央値≥50%には届きません。

sameHighはcanonical Lowの**strictly-later High**、postEntryHighはEntry後の独立したbest Highです。両者の時刻・headroom・分母を混同しません。whole-opportunity capture、same-high capture、post-entry capture、High→Exit gap、owned givebackは別列で保存しています。

Winner capability GateのPASS数はIMMEDIATE 6/16、R1 3/16です。これはHOLD_TO_TERMINAL診断に対する固定相対条件の通過であり、>=5% bucket Gateや全条件PASSを意味しません。

診断上の>=5%最大Mean／最大capture中央値は#14（**未選択**）。以下は同じ#14の比較です。


| Entry | Mean Net% | Capture中央値% | capture N | 保有中央値分 | MODEL/terminal | ratio-of-sums% | HOLD同ratio% | MODEL時C平均 | MODEL時F平均 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IMMEDIATE | 1.330 | 19.208 | 377 | 235.0 | 33/354 | 21.030 | 21.366 | 0.280 | 0.654 |
| R1 | 1.100 | 20.764 | 363 | 215.0 | 32/349 | 21.433 | 22.404 | 0.267 | 0.676 |

#14の保有中・事後の上値と実現値は次の通りです（選択根拠ではなく診断）。

| Entry | post-Entry best High 平均/中央値% | Net中央値% | whole-opportunity Capture中央値% | best High→Exit gap平均pp | early exit cost平均/中央値pp |
| --- | --- | --- | --- | --- | --- |
| IMMEDIATE | 7.597527 / 5.406735 | 0.744673 | 11.231000 | 6.217536 | 0.158589 / 0.000000 |
| R1 | 7.250921 / 5.119854 | 0.899109 | 10.466667 | 6.100608 | 0.194333 / 0.000000 |

best High gapはEntry後best HighとEXITの価格差であり、そのHighがEXIT後に発生したことを意味しません。EXIT後に残された上値は独立したearly exit cost列で確認します。

ratio-of-sumsは両者resolved・gross move有限・**両者positive headroom**を満たす同一ID上で`100×Σgross Entry→Exit% / Σpositive headroom%`を計算した補助診断です。個別capture比率の平均でも中央値でもなく、正式Gateには使いません。sameHigh版とpostEntryHigh版を別々に保存しています。小さいheadroomによりper-trade capture平均が大きな負値になる場合も、任意の除外・clipで消していません。

#14ではwinnerの354／349件がterminalまで残っています。長く保有することだけでは50% captureを実現しませんでした。MODEL EXIT時C/F平均は表記の33／32件に限定した値で、terminalケースを混ぜず、未校正scoreとして扱っています。

## 🛡️Loss Containment

Loss capability Gateは、同一OpportunityでHOLD診断と比較したp05改善≥0.25pp、worst悪化≤0.25pp、3/4 foldsでp10非劣後という固定条件です。PASS数はIMMEDIATE14/16、R1 10/16ですが、Primary／bucket／cost不合格を相殺しません。

全体p05はIMMEDIATE −8.037078～−4.860925%、R1 −7.747355～−3.902680%。worstはIMMEDIATE −29.032877～−19.567934%、R1全候補−32.016790%。<1%、1–2%、2–3%、3–4%群は両armで全候補のMean Netが負であり、単にWinnerの利確不足だけの問題とは言えません。実現負return subsetはEvaluator-onlyの独立表に保存し、モデル入力・次候補調整に還流させていません。

## 💰Profit Retention

Retention Gateはcertified owned Peak→Exit givebackについて、HOLD診断比の中央値悪化≤0.10pp、2/4 folds以上で0.10pp改善を要求します。PASS数はIMMEDIATE6/16、R1 12/16です。


| Entry | certified giveback中央値範囲pp | evaluable N範囲 | resolved内metric欠損N範囲 |
| --- | --- | --- | --- |
| IMMEDIATE | 0.737～2.225 | 136～371 | 769～999 |
| R1 | 0.737～1.503 | 165～343 | 757～930 |

incomplete owned prefixではcertified givebackをnullのまま保持します。Exit OPEN candleの後続High/Lowはownedではありません。post-EXIT Highへの取り逃しはearly opportunity costであり、owned givebackとは呼びません。#14の>=5% certified giveback中央値は4.582804／3.367262ppですが、evaluable Nは42／46に限られます。この部分標本の値を全387／381件の確定givebackと解釈できません。

## ⚖️IMMEDIATE vs R1

同一EXIT候補・同一cost・同一Frozen Entry sourceで比較し、追加paired表は**両EntryともEXIT resolvedかつ当該metricが両方有限**の共通IDだけを使います。metricごとにeligible N、欠損、除外censored、matched-ID hashを保存しています。正式R41 scorerをこの追加定義へ書き換えてはいません。


| 候補・未選択 | paired N | R1 Mean% | IM Mean% | 平均R1−IM pp | 差中央値pp |
| --- | --- | --- | --- | --- | --- |
| GEN2_R41_07 | 1098 | 0.093 | -0.126 | 0.219 | 0.000 |
| GEN2_R41_11 | 1095 | -0.034 | -0.086 | 0.053 | 0.000 |
| GEN2_R41_14 | 1095 | -0.095 | -0.114 | 0.019 | 0.000 |

R1がこれらの共通対象で上回っても、Final EXIT＋Capitalの正式選択ではありません。Capitalを実行していないため、最終Entryの採用判断もしていません。

### R36との診断比較

40候補（R36 24＋Gen2 16）のFrozen Entry identity・価格・fold・34 sessions・OOF母集団・costの一致を別途検証済みです。R36修正後の全体Mean Net最大はIMMEDIATE #17 +0.157788%（N1135）、R1 #22 +0.286923%（N1096）。Gen2最大はIMMEDIATE #11 −0.085373%（N1135）、R1 #07 +0.092441%（N1100）。>=5% capture中央値の別々の最大値はR36 30.545730%／19.306032%、Gen2 19.208241%／20.763551%。

これらは**失敗した固定grid内の別々の事後最大値**であり、選択policyやpaired architecture ablationではありません。共通Entry母集団でもEXITによってresolved／censored分母が変わります。R36をbaseline・fallback・新たな採用候補として復活させません。

## 🏁SELECT/NO_SELECTION

正式R41判定：`NO_SELECTION_STOP / NO_CANDIDATE_PASSED_ALL_FROZEN_GATES`。selectedCandidateIdはnullです。PASS候補がないため、順位のtie-breakは実行対象になっていません。


| 固定Gate | IMMEDIATE PASS | R1 PASS |
| --- | --- | --- |
| Coverage | 16/16 | 16/16 |
| Primary ≥2% | 0/16 | 0/16 |
| 全bucket条件 | 0/16 | 0/16 |
| Winner capability | 6/16 | 3/16 |
| Retention capability | 6/16 | 12/16 |
| Loss capability | 14/16 | 10/16 |
| Cost 0.10pp | 0/16 | 1/16 |
| Cost 0.20pp | 0/16 | 0/16 |
| Concentration | 16/16 | 16/16 |

正式Gate・閾値・scorer・モデル・prediction・ledger・costは変更していません。独立照合のnumerical／boolean mismatchは0。追加pairedやratio-of-sumsで正式FAILをPASSへ置き換えていません。

## 🔒Freeze/Exposure/Safety

Entry Dual Freeze `4878a1cc53430e816261dea0fb16aeb53b3c238d`は変更なし。Gen2 protocol／64 models／4 saved prediction specs／16 candidate ledgers／正式scorecardsは失敗研究Evidenceとして保持します。**採用EXIT Freezeは作成していません。**

今回のGen2監査・採点は新規model fit 0、policy replay 0、候補追加0、Capital／Portfolio replay 0、provider request 0、protected partitions opened 0。GitHub pushに連動する既存CIの自動実行は別途最終handoffに記録し、リポジトリ全体のreplay件数0とは主張しません。Common Holdout／REPORT19／Validation／OOS／Fresh／Prospectiveを新規開封していません。2,155 Developmentは既にoutcome-exposedであり、今回のOOFを未見OOSとは称しません。bucket・future High/Low・captureはEvaluator-onlyです。

Safety9はすべてfalse：executionAllowed、brokerWriteAllowed、excelOrderWriteAllowed、rssOrderFunctionAllowed、liveTradingAllowed、paperTradingAllowed、automaticPromotionAllowed、productionUpdateAllowed、transmitted。main merge・force push・live・paper・production移行はありません。

## 💴SELECTならCapital進捗

今回SELECTは成立していないため、MAX3／MAX4／MAX5のhistorical Portfolio比較は実行しません。R34／R35／R37のcash-only準備部品を保持します。初期100万円・100株lot・confirmed EXITによるcash release・fresh known-now MTM・Frozen Selector causal rankという事前条件は維持されていますが、Gen2 EXITを実運用接続したとは主張しません。

SELECT＋正式EXIT Freezeが将来成立した場合のみ、必要adapterを検証してCapitalへ進む境界を維持します。仮EXITによる資金比較、負cash、leverage、未確定EXITからのcash捏造は行いません。

## ⚠️未解決

主たるhard blockerは技術的監査未完了ではなく、**固定16候補が全体として性能条件を満たさなかったこと**です。達成するまで閾値・feature・モデル・labelを自動追加しません。

既知制約は、historical bar-end knownAt proxyがlive latencyの証明ではないこと、非ランダムな価格欠損とowned-prefix不完全性、metricごとの評価可能母数差、未校正C/F score、Capital未実施です。R1 #07など一部の正Meanのみを採用根拠にできません。

必要なpost-run CIは上記exact headでSUCCESSです。最終handoff保存は文書とCI証跡のみで、検証済みのコード・protocol・scorecardは変更しません。

## ▶️次工程

今回の正式結果・全16候補・全bucket・厳密paired・監査・独立照合・source/hashをappend-onlyでGitHub保存し、必要CI結果をcontrolling handoffへ反映済みです。NO_SELECTION_STOPを維持し、次の研究範囲の指示を待ちます。

許可なしにGen3、17個目の候補、勝つまでの閾値探索、R36復活、EXIT Freeze、Capital性能比較へ進みません。次回はGitHubのlatest HEADと最終handoffを確認して、この失敗結果とExposureを引き継げます。

運用記録：checkpoint pushで既存の広域PR CIが自動起動し、旧研究replayの実行が観測されました。これはR43監査・採点とは区別し、件数・run ID・未確認範囲をcontrolling handoffと`r43-closure/legacy-auto-ci-snapshot.json`に保存しています。R41再学習・Capital workflowは起動していません。旧CIの完了は待ちません。
