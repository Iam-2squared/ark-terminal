# Phase57 LONG-only — 選定後＋5% North-Star監査

2026-09-15 JST / PR #587 / Measurement Contract `NS-MEASUREMENT-1`

## 1. Executive Verdict

**FIX MEASUREMENT/HORIZON SEMANTICS。次に直すべき最優先は測定です。**

現在の「30分」は実際には6観測先であり、実時間30分に一致するのは36.35%。中央値45分、最大355分でした。従来の参照価格も18.09%の行で20分超古く、MAEは正値を許して逆行を相殺していました。Target／Feature／Modelを変更する前に、この意味と欠測の扱いを整える必要があります。

一方、実現短期Return上位は「選定時点からその後＋5%」を強く濃縮しています。**TargetがNorth Starと無関係という証拠ではありません。** strict30mの方が濃縮に優れるという結果でもありません。

専用監査は成功し、固定4診断を一度実行しました。新モデル・新Target・新Feature・Top N変更は採用していません。Validation/OOSは未開封です。

**重要な実行逸脱：契約commitが既存PR向けCIを意図せず起動し、範囲外の再fitを含む処理が走りました。専用監査はそれらの新出力を使用していませんが、タスク全体で「再fitゼロ」とは言えません。確認不足をお詫びします。3件は完了、残りは取消済みで、自動再起動を抑止しました。統合ジョブはRidge fit後まで進み、Entry以降の正確な停止地点はログから確定できません。詳細は[実行逸脱記録](phase57-northstar-ci-replay-incident-2026-09-15.md)。**

## 2. Measurement Contract + SHA

- 開始時remote HEAD：`9d29ad7688677124ec584da346846c68fc6a40a0`。PRはopen/draft。既存CI完了・当該ブランチの実行状況を確認して開始。
- 診断コード前にcommitした[契約](https://github.com/Iam-2squared/ark-terminal/blob/9acfd892ce8b86b8e70795e4f3950e3052529c67/docs/phase57-long-only-northstar-measurement-contract-2026-09-15.md)：`9acfd892ce8b86b8e70795e4f3950e3052529c67`。
- 診断コードSHA：`d7d6cb8ed35405d973be802185aaae6a9f7f9a6c`。
- [成功した専用Actions run 34976208234](https://github.com/Iam-2squared/ark-terminal/actions/runs/34976208234)。artifact ID `10399014576`。
- [集計JSON原本ZIP](evidence/northstar-measurement-34976208234.zip)：ZIP SHA256 `c5d7c05cda5a9e4028f5ba79f86dfa19932e2768818198be092ccf54ac713fa6`。
- JSON内の自己hash：`0e1325520223a9109b5bad0034e259ca045aa274325fe76f793680539c84e2a3`。`reportSha256`を除くsort-key compact JSONから再検算し一致。
- 全数表・分位点・全15特徴量は[数値付録](phase57-northstar-numeric-appendix-2026-09-15.md)、session別その他は原本JSONに保存。

固定：保存Developmentのみ、専用監査の新規provider request 0、fit/refit 0、現在weights／Target／15 causal features／timestamp Top5不変。Future＋1/2/3/5はevaluator-only。閾値探索・結果後の追加診断・再実行なし。

| 保存データ | 利用session数 | causal row数 | finite-y30 eligible数 |
|---|---:|---:|---:|
| 既存L1 | 16 | 576,581 | 422,980 |
| v2用追加Development | 20 | 717,029 | 521,992 |
| Development C | 20 | 726,617 | 526,930 |
| Development D | 20 | 738,114 | 550,181 |
| 合計 | 76 | 2,758,341 | 2,022,083 |

要求80session中、既存L1の2024-09-10〜13は元データ未提供のため未使用。新規取得・別sessionへの置換はしていません。利用期間は2024-09-17〜2025-01-09。rowはsymbol×session×decision eventであり、独立した銘柄数ではありません。

### モデル出所の制約

| 対象 | 新North-Star KPIの可否 |
|---|---|
| 元のC-only v1（D平均＋117.21bpsのモデル） | **UNAVAILABLE**：保存weight／scoreなし。hashのみでは復元できない |
| v2 HistGradientBoosting | **UNAVAILABLE**：保存 fitted weight／scoreなし |
| 保存済みC+D再fit Ridge | 未変更でscoring可能。以下では **V1_SAVED_CD_REFIT** と明記 |

保存artifact SHA256：`994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb`。学習行1,077,111、学習partition C+D。今回新たにfitしてNorth-Star用モデルを復元することはしていません。元v1やv2と数値を取り違えないでください。

C/Dはこのモデルの**学習内**。A/B36sessionも既観測Developmentであり、学習C/Dより過去の時間逆向き診断です。A/Bを新しいforward holdout／Validation／OOSと扱えません。

## 3. Horizon Semantics

finite-y30 2,022,083行について、decision→6観測先のelapsedを計測。残る736,258行は現行6観測先がなくNAです。

| 統計 | 分 |
|---|---:|
| Min / P1 / P5 / P10 / P25 | 30 / 30 / 30 / 30 / 30 |
| Median | 45 |
| Mean | 74.59 |
| P75 / P90 / P95 / P99 | 95 / 165 / 210 / 285 |
| Max | 355 |

| elapsed bucket | 行数 |
|---|---:|
| 30分 | 734,971 |
| 30超〜35分 | 152,655 |
| 35超〜45分 | 167,665 |
| 45超〜60分 | 162,036 |
| 60超〜90分 | 246,233 |
| 90分超 | 558,523 |

30分超は**63.65%**。午前中央値90分／午後35分。11:30判定は最短でも90分、中央値95分。欠落観測・昼休みをまたぐ「観測数」と「時計時間」は同じではありません。

strict30mは事前契約どおり、t＋30分以前で最新のclosed continuous 5m bar、実ソースcloseの経過5分以内、tより後。未来側nearest・補間・昼休み跨ぎの延長なし。endpoint不在はNAです。これは許容幅5分のas-of測定で、必ずちょうどt＋30分の約定価格という意味ではありません。

| 同一legacy分母・共通1,294,339行 | 値 |
|---|---:|
| Pearson / Spearman | 0.85130 / 0.85234 |
| Mean absolute label difference | 12.56bps |
| Median absolute difference | 実質0bps（3.5e-9） |
| 符号不一致 | 13.98% |
| ＋50 / ＋100 / ＋200bps membership不一致 | 4.29% / 1.66% / 0.41% |

strict endpointは1,474,001行で得られ、fresh decision分母も得られるのは1,183,233行。共通・freshな同一1,077,667行での濃縮比較は第7節。分母をfreshにするだけの共通行感度は差0で、主にcoverageが変わります。

## 4. Decision-price Freshness

Minuteの開始時刻＋1分をcontinuous closeの利用可能時刻、auctionはそのtimestampとする既存bar contractを採用。5m bucket-endの年齢と、実際に寄与したMinute closeの年齢を分けました。

| 従来参照価格の実ソース経過時間 | 行数 | 全row比率 |
|---|---:|---:|
| 0〜5分 | 1,728,636 | 62.67% |
| 5超〜10分 | 268,417 | 9.73% |
| 10超〜20分 | 262,183 | 9.51% |
| 20分超 | 499,105 | 18.09% |

実ソース年齢は中央値2分、P75 13分、P90 37分、P95 64分、P99 152分、最大359分。bucket-endだけで見ると20分超15.78%であり、実ソースの古さを過小表示します。

20分超の499,105行の内訳はStandard72.96%、Growth20.13%、Prime6.90%。Liquidity Low83.08%、Mid16.18%、High0.74%。これはstale群内の構成比であり、各市場内のstale発生率ではありません。

最新の利用可能Minute／auctionへ参照を取り直すevaluatorでも、5分以内は**1,755,720行＝63.65%**。1,002,621行は新North-Starを採点せずNAとしました。参照価格変更は91,762行。stale選定を別銘柄で補充していません。

これは保存Minuteのobservation freshnessです。最終約定tickの年齢、配信遅延、bid/ask、取引可能性まで証明していません。日付別取引時間・auction仕様の正しさも別途契約化が必要です。

## 5. MAE Semantics

現行はpositive raw MAEを許し、平均で逆行が相殺されます。true adverseは`min(0, raw)`とするevaluator-only比較です。

| 同じ母集団・同じhorizon | raw平均 | true平均 | 相殺量（percentage point） |
|---|---:|---:|---:|
| full・6観測先 | −0.3940% | −0.4119% | 0.0179 |
| full・従来same-session | −0.5985% | −0.6300% | 0.0316 |
| 保存CDモデルTop5・6観測先 | −0.9718% | −1.1100% | 0.1382 |

6観測先のpositive raw MAEは153,979行＝7.61%。従来same-sessionでは231,908行＝8.41%。新North-Starのfresh分母＋当日残時間で測るTop5 true MAEは−2.5360%ですが、horizonが違うため上表との差をすべてMAEクリップ効果と解釈してはいけません。

## 6. Future＋5% North-Star Prevalence

定義：選定時点で利用可能なfresh referenceから、その後の同一sessionの観測highへ到達する割合。最初から上がっていたかは成功条件ではありません。高値touchであり、必ずその価格で売れる／利確できるという意味でもありません。

| Future upside | Opportunity events | fresh評価可能1,755,720行内の率 |
|---|---:|---:|
| ＋1% | 331,006 | 18.853% |
| ＋2% | 102,424 | 5.834% |
| ＋3% | 45,879 | 2.613% |
| ＋5% | 15,667 | 0.892% |

Future＋5%全体の到達時間中央値115分。これは全Opportunityの値であり、Top5選定されたhitの到達時間とは別です。

| decision時Current Return | 評価可能行 | Future＋5%件数 | そのbucket内の率 | 全＋5%機会の構成比 |
|---|---:|---:|---:|---:|
| ＜0% | 819,850 | 6,018 | 0.734% | 38.41% |
| 0〜＜1% | 542,769 | 2,722 | 0.502% | 17.37% |
| 1〜＜2% | 216,919 | 1,475 | 0.680% | 9.41% |
| 2〜＜3% | 87,317 | 1,115 | 1.277% | 7.12% |
| 3〜＜5% | 56,121 | 1,489 | 2.653% | 9.50% |
| ≥5% | 32,744 | 2,848 | 8.698% | 18.18% |

**11,330件＝72.32%は当日騰落率＋3%未満から、さらに＋5%へ到達。** 38.41%はマイナス圏からです。前日終値基準Final＋5%をNorth Starと同一視すると、これらの機会の意味を取り違えます。

## 7. Target Alignment

Outcome同士が共通の未来価格経路を含むため、以下は**結果間の関係**であって学習モデルの予測能力ではありません。Top1%等は各decision断面のpercentile、上位bandはnestedです。

母集団・欠測差を除くため、legacy/strict/fresh future pathがすべて得られた同一1,077,667行でpercentileを再計算。無条件Future＋5%率は両方1.0948%。

| 実現Return band | 6観測先：Future＋5%率 | strict30m：Future＋5%率 | 6観測先Lift | strict Lift |
|---|---:|---:|---:|---:|
| Top1% | 34.03% | 32.78% | 31.09× | 29.94× |
| Top5% | 10.97% | 10.61% | 10.02× | 9.69× |
| Top10% | 6.20% | 6.05% | 5.66× | 5.53× |
| Top20% | 3.47% | 3.39% | 3.17× | 3.10× |
| Middle20–80% | 0.387% | 0.397% | 0.35× | 0.36× |
| Bottom20% | 0.851% | 0.899% | 0.78× | 0.82× |

**短期Return上位とFuture＋5%のalignmentは強い。strictの方が強いとは言えない。** 測定定義の修正が必要なのは、望む30分の意味と一致しないためであり、今回の濃縮率を最大化したいからではありません。

保存CD Ridge scoreのfull cross-sectionでは、Top1%のFuture＋5%率11.48%、Top5%4.42%、Top20%1.54%、Middle0.357%、Bottom20%1.96%。上位tailには濃縮がある一方、Bottom20%も無条件0.892%より高く、全域を単調に並べるには不十分です。C/D学習内を含む参考値で、元v1の新holdout成績ではありません。

## 8. Feature Sufficiency

同一session・decision時刻・市場・Current Return bucket・Liquidity bucket・causal volatility quintileで1:1 matching。未来Outcomeはcohort定義のみ。新しいmodelのfitはありません。

- 全Future＋5%：15,038対、match率95.99%、未match629。
- Early（Current Return＜3%）：11,126対、match率98.20%、未match204。
- 各対は非Opportunity controlを重複なしで対応。閾値緩和なし。

主要差（各群N＝15,038、percentage表記featureは%）：

| 既存feature | Opportunity中央値 [P25, P75] | Control中央値 [P25, P75] | SMD | 分布重なり |
|---|---|---|---:|---:|
| Range expansion | 4.889 [2.695, 8.845] | 3.597 [2.130, 6.192] | ＋0.309 | 84.72% |
| VWAP distance | −0.095 [−1.174, 0.748] | −0.004 [−0.734, 0.759] | −0.189 | 89.29% |
| 30m momentum（既存定義） | 0 [−0.981, 0.903] | 0 [−0.631, 0.771] | −0.111 | 88.64% |
| Log cumulative turnover | 18.324 [16.723, 19.926] | 18.099 [16.650, 19.400] | ＋0.117 | 92.03% |
| Volume acceleration | 0.645 [0.290, 1.354] | 0.616 [0.279, 1.232] | ＋0.032 | 97.17% |
| VWAP slope | −0.00039 [−0.08284, 0.09228] | −0.00042 [−0.06484, 0.07918] | −0.009 | 91.85% |

Earlyでも最大はRange expansion（SMD＋0.335、重なり83.08%）、VWAP distance−0.242、Current Return−0.209、momentum−0.198。差は存在しますが、単一featureの大部分は大きく重なります。Volume accelerationの平均3.04対1.51だけを強い識別根拠にするのは不適切で、中央値・SMD・重なりは差の弱さを示します。

Market／Time／Liquidityや同時刻market breadthの差ゼロはmatchingで固定されたためです。「これらに情報がない」証拠ではありません。周辺分布の重なりはinteraction情報の不存在も証明しません。したがってFeature information insufficiencyは懸念ですが、ここで確定診断しません。

## 9. Timestamp-level Top5 North-Star Metrics

元C-only v1／v2の新North-Star KPIはUNAVAILABLE。以下は**未変更の保存CD再fitモデルのみ**。9判定/session×Top5を維持し、stale選定を補充せず、採点可能分母と全選定分母の下限を併記します。

| 指標 | 全76session（学習内混在） | A/B36（学習外だが時間逆向き・既観測） | C20（学習内） | D20（学習内） |
|---|---:|---:|---:|---:|
| 全選定events | 3,420 | 1,620 | 900 | 900 |
| 採点可能events | 2,729 | 1,259 | 737 | 733 |
| 採点coverage | 79.80% | 77.72% | 81.89% | 81.44% |
| Future＋1% Precision@5 | 81.60% | 78.71% | 84.12% | 84.04% |
| Future＋2% Precision@5 | 67.42% | 63.07% | 69.74% | 72.58% |
| Future＋3% Precision@5 | 53.10% | 48.21% | 55.90% | 58.66% |
| Future＋5% Precision@5 | 29.61% | 23.43% | 32.84% | 36.97% |
| ＋5% hits / 全選定（下限） | 23.63% | 18.21% | 26.89% | 30.11% |
| Future＋5% Recall | 5.286% | 4.759% | 5.288% | 6.006% |
| Future＋5% hit件数 | 808 | 295 | 242 | 271 |
| ＋5%到達時間中央値・hit限定 | 28分 | 38分 | 22.5分 | 20分 |
| 当日残時間MFE平均 | ＋4.186% | ＋3.870% | ＋4.253% | ＋4.664% |
| 当日残時間true MAE平均 | −2.536% | −2.405% | −2.389% | −2.909% |

全76sessionの691選定＝20.20%が採点不能。29.61%を全選定に対する確定精度や、元v1の汎化成績として宣伝できません。hit/allの下限も欠測を実際の負例と認定した値ではありません。

Secondary/referenceのみ：前日終値基準Final＋5% Precisionは全体12.37%、Recall1.001%。これは別の成功条件・分母です。North-Star Precisionの29.61%との増減をモデル改善とは扱いません。

## 10. Daily Distinct-symbol Diagnostic

各日の同一symbolは**最初に選ばれたevent**で判定。best-of-day scoreや後で有利な時刻への差替えなし。

| 指標 | 全76session | A/B36session |
|---|---:|---:|
| 判定回数/session | 9 | 9 |
| Top5 selection events/session | 45 | 45 |
| distinct symbol-days | 2,372 | 1,124 |
| distinct symbols/day平均 | 31.21 | 31.22 |
| 採点可能distinct | 1,947 | 903 |
| Future＋5% distinct hits | 529 | 195 |
| ＋5% distinct hits/day | 6.96 | 5.42 |
| 採点可能distinctでのPrecision | 27.17% | 21.59% |
| 初検出時刻中央値（全selected distinct） | 11:00 | 11:00 |
| 初検出時刻中央値（＋5% hits） | 10:30 | 10:30 |
| hitの追加upside中央値 | ＋6.74% | ＋7.46% |

全体のrepeat selections/symbol-dayは平均0.442回、中央値0、最大7回（初回を除く）。**これは1日5銘柄だけを選ぶpolicyの成績ではなく、平均31銘柄/日の診断です。**

## 11. Capacity-aware Recall / Precision Lift

全76session、元policy-eligible universe2,022,083行、North-Star採点可能1,478,110行内の比較。第6節のfull universeとは分母が違います。

Random expected hits＝`Σ_t O_t × K_t / N_t`、Random recall＝expected hits／`Σ_t O_t`。900／Opportunity総数ではありません。Precision Liftは採点可能universeの無条件率との比であり、Recall Liftとは別です。

| Future | Actual Recall | Random Expected Recall | Recall Lift | Precision@5 | 無条件率 | Precision Lift |
|---|---:|---:|---:|---:|---:|---:|
| ＋1% | 0.708% | 0.16192% | 4.37× | 81.60% | 21.288% | 3.83× |
| ＋2% | 1.865% | 0.15999% | 11.66× | 67.42% | 6.674% | 10.10× |
| ＋3% | 3.256% | 0.15969% | 20.39× | 53.10% | 3.011% | 17.64× |
| ＋5% | 5.286% | 0.15968% | 33.10× | 29.61% | 1.034% | 28.63× |

異なる断面人数・freshnessを反映したRandomの採点可能選定数期待値は2,521.78。対応するRandom Precisionは＋1/2/3/5で20.204% / 6.259% / 2.818% / 0.968%。これは表のpooled unconditional prevalenceとは異なる量です。

A/B学習外診断のFuture＋5%はRandom recall0.16096%、Actual4.7588%、Recall Lift29.56×、Precision Lift26.17×。時間逆向き・既観測の制約は残ります。

## 12. What v1 Actually Does Well

今回新たに確認できたのは保存CD Ridgeの性質です。score upper tailには、選定後の大きなupsideを濃縮するsignalがあります。A/Bで＋5% Precision23.43%、Randomに対するRecall Lift29.56×は、単なる無作為選択とは異なる記述的結果です。

当日マイナス〜小幅プラスからの追加＋5%機会も実在します。Ridgeの反発候補への偏りを「既に上がっただけの銘柄を選んでいる」と一律に解釈することはできません。ただし元C-only v1のNorth-Star新測定値としては未確定です。

## 13. What v1 Actually Fails At

- 現行6観測targetを実時間30分と説明することは不正確。従来の＋117.21bpsも、厳密30分の数値と同一視できません。
- 保存CDモデルでも高確信・ほぼ100%のNorth Starには届かず、全selectedの20.20%が新鮮な価格で評価不能です。
- score下位にも＋5%機会が残り、全域での単調rankingではありません。
- full-session true MAE−2.54%など大きな逆行を伴うため、upside touchを実収益と混同できません。最悪値−60%も含みますが、今回は個別再調査・除外・retuneを追加していません。
- 保存された元v1／v2のweight・score不足が、厳密な再測定とモデル間比較を妨げています。

## 14. Root-cause Ranking

| 優先順位 | 領域 | 今回のEvidenceと判定 |
|---|---|---|
| 1 | Measurement | 強く支持。6obs elapsed、stale denominator、positive MAEが具体的に確認された |
| 2 | Evaluation / provenance | 強く支持。旧Final＋5%との意味違い、timestampとdailyの違い、future-y30有無によるeligible条件、元weight／score不在 |
| 3 | Model / Ranking | 残課題として支持。保存score upper tailは有用だが下位にもOpportunityが残る。測定是正前に新familyの優劣は断定しない |
| 4 | Feature | 識別差は小〜中、分布重なり大。情報不足の可能性はあるがinteractionまで否定できず確定しない |
| 5 | Target redesign | 現時点の支持は弱い。実現短期returnはFuture＋5%を強く濃縮し、変更を正当化するだけの結果ではない |

順位は次に対処すべき優先度であり、各原因の因果寄与率を推定したものではありません。

## 15. Recommended Next Research — 1つだけ

**Measurement Semantics修正の研究を次の1件として承認待ちにする。** 実時間30分・price freshness・日付別session/auction・欠測とeligibility・true adverse MAEの契約を整え、今回固定した保存データで影響を明確化する工程です。モデル／Targetの自動変更や再fitを意味しません。

今回は影響の診断のみで終了。v3、v2再tune、Target変更、新feature、Top N変更、Daily Top5、Validation/OOS、Entry/EXIT/Allocation、旧Selector、News/Event、新規データ取得には進みません。**STOP。次工程の承認を待ちます。**

### 留意事項

- 全数測定は保存・受理済みMinuteの観測範囲です。未観測Minuteのhigh/lowや取引可能性を補間・保証していません。
- 残りsession長は判定時刻により異なり、午後遅い判定では同じ＋5%機会でも観測可能時間が短くなります。
- 元policyのfinite-y30 eligibilityは未来の観測本数に依存します。今回は比較互換性のため維持しただけで、リアルタイム選定母集団のcausal認証ではありません。
- staleルールはevaluator-onlyであり、low liquidity／高volatility／当日騰落率の新hard trading filterは加えていません。
- 専用監査の安全flagsと、周辺CIで生じた再fit逸脱は別です。[実行逸脱記録](phase57-northstar-ci-replay-incident-2026-09-15.md)を併読してください。
