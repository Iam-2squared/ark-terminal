# MSH-Entry LONG v2 — Pre-Development Contract Freeze

**Verdict: `MSH_ENTRY_LONG_V2_PREDEVELOPMENT_CONTRACT_FROZEN`**

2026-09-16 JST task。契約のみを固定した。v2実装・fit・prediction・OOF・性能測定・閾値性能探索は行っていない。ここでSTOP。これはDevelopment候補の性能判定ではない。

機械可読の正式仕様は [contract](../../../predict/research/phase57-msh-entry-long-v2-predevelopment-contract-v1.json)。この文書はその説明であり、契約と異なる裁量を追加しない。

Contract SHA-256: `18818ffd1157c7ba15c93eb4723c3e28945c238e0e2f6a2440bee98c7ad1267f`

## RepoとFrozen identities

| Item | Identity |
|---|---|
| Branch | `research/phase57-long-only-cash-equity` |
| PR | [#587](https://github.com/Iam-2squared/ark-terminal/pull/587), Draft / unmerged |
| P0 / starting head | `13148321d7ef586975ab973a04392e2af73b6503` |
| Latest main at direct audit | `0fcc608e6d38671e3bfeb95566ac96d89b6a5433` |
| Contract publication head | The commit containing this immutable contract; exact final SHA and final-head CI are returned in the Work completion report. A file cannot contain its own enclosing commit hash. |
| Starting-head CI | 6 SUCCESS / 4 SKIPPED; [API receipt](github-start-audit.json) |
| Selector freeze commit | `565d74b3dea823581fdb32380113aac5913a248d` |
| Selector payload SHA | `3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59` |
| Selector Ridge SHA | `994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb` |
| v1 candidate SHA | `4a2f52cd6f25f480fe6d7de9db525860ddf3c1600abed06b6222c0990c055a23` |
| v1 model SHA | `b053a858edda22bee7b9939162648740507964cc5ed8d613c2d778d15534589e` |
| v1 scaler SHA | `1e4865915a2ad1ec51dd4ebf2116d48b9f89b9b884f8dc732fdb2861dbf4fe4b` |
| Frozen 277 ENTER SHA | `72224ac9fd073f7da45c488aaf8ca999752b466e715837c21440e7dd93970236` |
| P0 diagnostic SHA | `91019d3550bcfbf38e64cbc00e0f30b1cbefe44681152c82ed0b09bb3053c29d` |
| P0 verdict | `MSH_ENTRY_LONG_V2_ARCHITECTURE_DIAGNOSTIC_COMPLETE` |
| Global Budget SHA | `b91699704f80ef7fda60fe0596e8f8736a181cd00dc879f5070f9caed4d4a62f` |

Selector / v1 / EXIT / Allocation / cash ledgerを含む30 source pinsが一致した。v1の2.0 threshold、2 features、277 ENTER identityは変更していない。v1 statusはFROZEN_FOR_EXIT_RESEARCH / Historical BORDERLINE / Fresh PENDING。

## 固定した設計

**Frozen Selector Opportunity + Minimal Adverse Severity Component → ENTER / SKIP。**

初回は `MSH_ENTRY_LONG_V2_D30_RIDGE_V1` 1本。SelectorはOpportunity担当、Entryは今の価格からの逆行リスク担当とする。v2内部でv1のE[L]>=2を再度必須gateにしない。Two-Head、WAIT、ensemble、symbol model、Opportunity×Riskの積、score sizingは採用しない。

Primary Targetは **A: 30分MAEの連続逆行幅**。

`MAE30 = min(0, 100 × (minimum future LOW / DecisionPrice − 1))`

`D30 = max(0, −MAE30)`、単位はpercentage points。固定30分のwall-clock window、通常5分足6本、同一session。学習ラベルだけにfuture LOWを使う。逆行がない場合のD30=0は観測値であり、欠損を0にする処理ではない。10 extreme tailsだけのbinary target、label clipping、target transformationは使わない。

B: Frozen EXIT lossは初回Primaryにしない。3,800候補の選定EXIT pathはまだ全件投影されておらず、EXIT依存とcensoringを増やすため。固定EXITの損失は下流評価に残す。MAEはEXITが耐えられる一時逆行も含むため、+3/+5 PreservationとPortfolio gateでtrade-offを検証する。

### Universe・training row・反復観測

- **2024-09-17–2025-01-09、76 sessions / 760 timestamps / 3,800 Top5 events / 934 symbols。** 277 ENTERやstrict181に限定しない。
- 保存済みstrict30m label availabilityは1,828、未評価1,972。今回はavailabilityのみ照合し、v2のoutcomeは計算していない。
- Training rowはSelection Event。完全labelと必須入力があるtraining期間の行を使う。
- 全symbol共通で `w_i = 1 / (S × d_s × n_sd)`。symbolの合計weightを均等化し、その中でsymbol-sessionを均等化、同sessionの反復行で分割する。各fit対象内で再計算し、合計1。symbol-specific weightはない。
- 反復行を独立した証拠と扱わない。同一symbol-sessionをtrain/evalに跨がせない。
- label missingはtraining lossの対象外にするだけ。評価時のEntry可否にはfuture labelabilityを渡さない。各arm独自のcausal ENTER集合をPrimaryとする。

### Feature set / order / missing

| Order | Effective input | Available / 3,800 | 決定理由・制約 |
|---:|---|---:|---|
| 1 | `frozenSelectorRidgeScore` | 3,800 | Frozen Opportunity contextを1値で保持。リスク安全性は未証明 |
| 2 | `directionalMomentum3Pct` | 2,476 | completed close / 3 trading bars前close。4本の正確なslotが必要。P0分離はほぼ0で、方向性の補完という事前仮説 |
| 3 | `directionalPullback6Pct` | 2,210 | latest close / 最近6 completed barsのmax HIGH。局所path形状を補う事前仮説 |
| 4 | `momentum3Missing` | 全行でstatusから決定 | original unavailableなら1、availableなら0 |
| 5 | `pullback6Missing` | 全行でstatusから決定 | 同上 |

**3 raw predictors + 2 missing indicators = 5 effective inputs。** Pullbackを自動的にCoreと認定したわけではない。この1実験に限定した選択で、P0のrange overlap、8 observed extreme cases中5件の同一symbol依存、winner overlapを契約に残した。追加・差し替え・interactionsは別契約が必要。

Ridge rankは重複するOpportunity情報としてDiagnostic。volume/VWAPは将来の別契約でのみOptionalで、今回inactive。raw price、time、segment、liquidity、selection persistence、tick granularityはDiagnostic/State-only。raw-price filter、symbol blacklistはない。bid/ask未保存を価格granularity proxyで代用しない。

Momentum/Pullback欠損は**実際のfit期間内の観測値だけのweighted median + 各missing flag**。observed weightを再正規化し、値/eventId順で累積weight>=0.5となる最小観測値を使用。0埋め・forward-fill・interpolationはない。補完後の3 raw inputsをfit内weighted mean/population stdで標準化し、flagsは0/1のまま。volume/VWAPは入力にしないため補完もしない。

必須score不正はSKIP。AVAILABLEなのにnonfiniteならデータ整合性エラー。fit内に観測値なし、varianceなし、solver failureはFIT_FAILED。評価時だけ初出するmissing stateは `UNSUPPORTED_MISSING_STATE / SKIP` とし、v1へのfallbackはしない。

### PITとCoverageの限界

入力計算はcompleted bar availableAt<=decisionと正確なslotを要求する。Momentum/Pullbackは同一session、昼休みをtrading-slotとして数えず、missing slotは補完しない。saved rowsにはraw timestampの全履歴がないため、これは固定sourceのformula auditでありlive到着時刻の証明ではない。

L1 `matchedFeatures` にはfuture-label availabilityでmembershipを絞る既存処理がある。**3,800はHistorical Conditional Universe**として固定する。full live-universe PIT、full-stack OOSとは主張しない。daily adjustment / dated masterのrelease clockにも残る制約を明記した。

30分labelが昼休み/session-endに跨ぐ場合、auction、必要bar欠損はCENSORED。sparse-minuteを含む既存5分barはそのまま参照し、存在しないminuteを作らない。同bar内high/low順序はUNKNOWN_INTRABAR_ORDER。昼休み/late candidatesへの新しいtime filterは作らず、label censoringとEntry stateを分離する。

### ModelとCV

Modelはweighted L2 linear ridge regression 1本。interceptは非正則化、5 coefficientsを正則化。

`0.5 × Σ w_i (D30_i − b − z_i β)^2 + 0.5 × λ × Σ β_j^2`

**λ=1固定**。標準化入力と合計1のweightに対するunit regularizationという単純な安定化priorで、P0やv2性能から選ばない。Python 3.12 / NumPy 2.3.5 / float64 / threads=1、`numpy.linalg.solve`。乱数・shuffle・GPUなし。残差許容は `1e-10 × (1 + rhsInf)`。min rows=7、min symbols=2は数値計算の最低条件であり、統計的十分性ではない。

出力は `Dhat=max(0, rawLinear)`。これは非負の物理的domainへのprojectionでありpercentile clippingではない。raw outputも保存する。expected PnL、tail probability、execution qualityとは呼ばない。

| Fold | Outer training sessions | Inner fit | Inner threshold calibration | Outer evaluation |
|---:|---|---|---|---|
| 1 | 1–16 | 1–12 | 13–16 | 17–31 |
| 2 | 1–31 | 1–23 | 24–31 | 32–46 |
| 3 | 1–46 | 1–34 | 35–46 | 47–61 |
| 4 | 1–61 | 1–45 | 46–61 | 62–76 |

Inner model/imputer/scalerはinner fitだけでfit。calibrationで閾値を決めた後、同じfamilyをouter training全体でrefitし、次15 sessionsを評価する。outer結果から閾値を決めない。重なる同symbol future-label windowsをpurgeし、label availableAtを次block開始より前に限定する。whole-session分割なので通常この重複は空となる。

Primaryは同じ60評価sessions / 3,000 candidatesで両armを比較。最初の16 sessionsは両armで評価用Entryを出さずcash。v1 full76とv2 only60を比較しない。全76のinventoryと既知277 baselineは保持する。

Cross-symbol evaluationは `SHA256("PHASE57_MSH_LONG_V2_GROUP_V1|"+symbol) mod 5` で決定。group symbol数は194 / 195 / 163 / 189 / 193。各chronological foldでheld group全symbolをfitとcalibrationとrefitから除外し、そのgroupの将来行だけを評価。5 groupsを時系列に戻して集計する。fold replicasはensembleではない。89180/57590やTop contributorsからsplitを選ばない。今回作成したのは[identity-only split metadata](split-metadata.json)だけで、OOF予測はない。

v1とSelectorは全76 sessionsの結果にexposed。将来このCVを実行してもHistorical / Development evidenceであり、独立したFresh/OOSではない。

### State・decision・threshold selection

ENTER / SKIP_THIS_DECISION、WAITなし。`Dhat <= τ` をENTER条件とし、最初のENTER signalでsymbol-sessionをlatchする。資金不足で購入拒否されても再Entryしない。SKIP後は次のFrozen Top5 eventだけで再考する。

閾値候補は **[1, 2, 5, 10] percentage points**。ユーザーがP0以前に固定したseverity boundariesの全4点で、追加・補間・fine searchはしない。

Inner calibrationで以下のEntry側Primary/Guardrailsを満たす候補だけを残し、mean D30最小→同値ならmin(+3,+5 Preservation ratio)最大→ENTER数最大→τ最大の順で選ぶ。portfolio/HHI/cross-symbol結果は閾値選択に使わない。適格候補なしなら **SELECTION_INCONCLUSIVE**。default thresholdやgate緩和で救済しない。

## Numeric gates — v2 outcomesを見る前の固定

比率は必ず同じ評価期間・同じ定義での **v2 / v1**。これは研究上のutility policyであり、統計的有意差や達成可能性の保証ではない。10%の通常逆行改善を求め、機会損失10%、ENTER減少20%、副次リスク悪化10%までを事前のtrade-off budgetとした。coverage差5 percentage pointsは別の観測品質基準。P0のtail10件、HHI .1656、MaxDD20.17%から絶対値を逆算していない。

| Class | Metric | Frozen gate |
|---|---|---:|
| Primary | Mean D30 | ratio <= 0.90 |
| Primary | ES95 D30 | ratio <= 1.00 |
| Primary | +3 / +5 Preservation | 各ratio >= 0.90 |
| Primary | ENTER throughput | ratio >= 0.80 |
| Primary | Same-downstream net PnL | v2−v1 >= 0 JPY |
| Primary | Portfolio quality | PF改善 または MaxDD改善 |
| Primary cross-symbol | pooled mean D30 / symbol-macro mean D30 | 各ratio <= 1.00 |
| Primary cross-symbol | non-worse mean D30 groups | 5 groups中3以上、全5 groupsが評価可能 |
| Primary cross-symbol | +3 / +5 Preservation / throughput | >=0.90 / >=0.90 / >=0.80 |
| Guardrail | +1 / +2 Precision | 各ratio >=0.90 |
| Guardrail | Portfolio PF | ratio >=0.90 |
| Guardrail | Portfolio MaxDD | ratio <=1.10 |
| Guardrail | positive / negative symbol HHI | 各ratio <=1.10 |
| Guardrail | strict-label coverage rate | arm間の絶対差 <=0.05 |

Chronological streamに全Primary/Guardrailを適用する。cross-symbol streamにはcross-symbol PrimaryとEntry precision/coverage guardrailsを適用し、そのPortfolioはsecondary。inner calibrationはEntry risk/Preservation/throughputとprecision/coverageだけを使う。

D30/ES95は各arm独自ENTERのcomplete pathsで計算し、未評価ENTER数も必ず報告。ES95は最大ceil(0.05×N)件の平均。symbol-macroは各armの評価可能symbolごとのmeanを等weightで平均し、両armのsymbolリストとoverlapを併記。欠損symbolをloss=0にしない。

Preservationは共通のfirst Top5 eventにstrict30m +Kがあるsymbol-sessionを分母とし、その元の30分window内にEntryし、**Entry priceからまだ+Kを取れる**完全pathを分子とする。unknown numeratorはlower-bound metricでのみ0扱いし、unknown件数を別表示する。30分candidate cadenceでは通常first eventでの採用が必要。late same-session admissionや新しい機会の回収はsecondaryとして別集計する。既存の異なるPreservation定義をそのまま混ぜない。

baseline=0のratioにepsilonを足さない。undefined PF/HHI、評価不能hash group、未評価Portfolio exposureはINCONCLUSIVE。全Primary/Guardrail PASSでのみ将来のDevelopment PASS。既知違反はFAIL、unknownは併記。全metric同時改善は要求せず、Median/Win rate/個別foldはDiagnostic。利益を捨ててHHIだけ下げたり、取引をほぼ0にしてMAEだけ下げる設計をPASSにしない。

DiagnosticsはMAE median/p05/worst/−2/−5/−10率、MFE、+1/+2/+3/+5 precision/preservation、early adverse/reclaim、score calibration、time/segment/liquidity/missing、symbol contributions、HHI/effective contributors/top-k shares、median/dispersion、Top1/Top3除外、新recoveries/rejects、cash utilization、execution uncertainty。Top contributors除外は正式gateでもEntry ruleでもない。

## Fair comparatorと接続条件

| Component | Frozen |
|---|---|
| Baseline | saved MSH-Entry LONG v1 predictions、2.0、元のfirst ENTER semantics |
| Challenger | v2独自causal ENTER集合。共通intersectionはsecondaryのみ |
| Universe / Decision Price | 同じ3,800 events、同じ76 sessions、同一eventは同一price |
| EXIT | `LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1` |
| Allocation | Equal / `EQUAL_MAX3` / `V3_0_EQUAL` |
| Cash ledger | pinned `scripts/phase57_long_capital_integration.py::replay` |
| Initial capital / lot | 1,000,000 JPY / 100 shares |
| Concurrent limit / budget divisor | 10 / 3 |
| Cost | entry notionalの0.05% round trip、半分ずつEntry/EXIT |
| Event order / calendar / missing | 元契約の内容とSHAを固定。bar/EXIT処理後に同時刻Entry、symbol/eventId順 |

**接続上の発見:** 既存 `causal_envelopes` とweights CLIはv1 E[L]>=2をassertする。v2 severityをそこへそのまま渡せない。次工程でscore-free connectorを新設してpinned `allocateV3(..., V3_0_EQUAL)`を直接呼び、既存replayに同じweight mapを渡す。dummy E[L]=2、risk scoreの読み替え、Equal/ledger改造は禁止。v1 weight/ledger parityを先に確認する。この接続実装は今回行っていない。

3,800候補のchosen-EXIT pathsは既存76-session checkpointsから次工程で投影が必要。277のpath/173 complete-caseだけをv2全体のPortfolioとして使わない。missingはmissingのまま残す。未評価positionがあるcurveから完全なFinal Equity/MaxDDを主張せず、該当gateはINCONCLUSIVE。coverageの不足を理由にlabelable行だけからEntry streamを生成しない。

## Claude disposition・Data・Safety・検証

[Claude disposition](claude-review-disposition.json)はユーザーが今回提示したreview内容の採否を保存したもの。新しいClaude呼出や別transcriptがあるとは主張しない。small risk component、cross-symbol、Fresh温存などを採用し、OHLCVでspreadを80%代替、未保存bid/ask、volume20m新設、WAIT/XGBoost自動採用、VWAP=0、percentile clipping、P0に合わせた絶対numeric gateを不採用とした。

**Local tests: 21 PASS = contract 14 + Frozen upstream 7。** Linux kernel offline guard内で実行。model runtimeをimportしない静的監査、30 source SHA、3800 identities、fixed folds、symbol leakage防止、future/symbol inputs・0補完・gate緩和・threshold追加・safety有効化の拒否を検証した。CIはこの静的suiteだけの新workflowを追加した。最終head CIはpublish後の別確認で報告する。

今回のFresh / Entry OOS / EXIT OOS / Prospective / J-Quants / Yahoo / Other provider requests = **すべて0**。v2 fit / prediction / OOF / performance measurement / threshold performance search = **すべて0**。既存Historical / Development / IN-SAMPLE / Outcome-exposed dataのみ。Global Fresh Budget 195 sessionsを保護した。

executionAllowed / brokerWriteAllowed / excelOrderWriteAllowed / rssOrderFunctionAllowed / liveTradingAllowed / paperTradingAllowed / automaticPromotionAllowed / productionUpdateAllowed / transmitted = **全9項目false**。LONG-only / cash equity only、SHORT / Margin / Leverageなし。main mergeなし。

## Exact next action

**STOP。別指示があるまで学習しない。** 次は契約どおりのv2実装、score-free接続と既存baseline parity、3,800候補のcoverage確認。その後、別途許可されたDevelopment fit / nested chronological・symbol-disjoint OOF / same-downstream fair comparisonへ進む。今回のFreezeは設計の固定であり、モデル完成・性能改善・Fresh/OOS PASSを意味しない。
