# Entry LONG v2.3 Good-Trade Probability — minimal FAST-FAIL

**MSH_ENTRY_LONG_V2_3_FAST_FAIL_KILL**

Joint Good Tradeを安定して識別するEvidenceがない。9 fitは成功したが時系列AUROCは0.4700、銘柄分離は0.5005。定数base-rate予測よりBrier/log-lossが悪く、winner保持も未達。D30の観測subset平均低下だけで成功とは扱わない。追加fit・閾値変更・feature追加・Full Developmentは実施せずSTOP。

## Repository / preregistration

- Branch: `research/phase57-long-only-cash-equity`; [PR #587](https://github.com/Iam-2squared/ark-terminal/pull/587), draft/open/unmerged。main mergeなし。
- Start head: `bc013ae005416982fb389842be5f3ee25f993298`。
- Protocol remote precommit: `d869e56fb55323dbdad69b4e57d7591fe51213ec`。新ラベル件数・fit・predictionを見る前に公開。
- Latest main checked: `5484159a4edae50f6ebeecbbac6a7765bafdc61f`。
- Final publication head / CI: このファイルを追加したcommitに対応するGitHub checksと最終報告に記録。自己参照SHAを本文へ捏造しない。
- Protocol SHA: `e6fcff8580b6f7feed165a4a8272519dc5d7a661ec367eaf52961f71c1096f2c`。Evidence SHAは同directoryの`manifest.json.sha256`。

## One label / universe / model

`GOOD_REFERENCE_TRADE = frozen EXIT net reference return > 0% AND strict30m D30 <= 2%`。ProfitはLONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1のcompleted-close参照損益率からentry notionalの往復0.05%を控除。EXITは既存BAR5/two-lower-close、最大12 regular bars/remaining session。Riskはdecision後6本の連続5分bar、D30=max(0,-MAE)。両方のoutcomeが観測できる場合だけGOOD/BADを定義し、どちらか欠ければNULL。昼休み・session境界・bar欠損を0埋めしない。

Profit境界0はコスト控除後の損益分岐。D30境界2%は既存MAE2%評価境界を使用した事前の許容逆行予算であり、v2.3のpositive率・成績から最適化していない。唯一のPrimary label、supporting label0。Verified fill qualityを意味しない。

76 sessions、2024-09-17〜2025-01-09、Frozen Selector Top5 3,800 Selection Events / 760 timestamps。Historical conditional universe / Development / outcome-exposed。全stackのFresh/OOS性能を主張しない。

| Coverage | Count |
|---|---:|
| Candidates | 3,800 |
| Joint labelable | 1651 |
| GOOD | 565 |
| BAD | 1086 |
| UNKNOWN / excluded from supervised fit | 2149 |
| GOOD prevalence among joint observed | 34.22% |
| Frozen v1 raw E[L]>=2 / state anchors | 353 / 277 |

Input order: `frozenSelectorRidgeScore`, `directionalMomentum3Pct`, `directionalPullback6Pct`, `momentum3Missing`, `pullback6Missing`。Rankは重複するOpportunity情報として除外。Price/symbol/time/liquidityやfuture outcomesは入力なし。

PITは既存completed-bar availableAt<=decision guardを継承。ただし保存featureには生のfield到着時刻がないため、完全なlive-universe PIT認証とはしない。各fold内weighted medianとmissing indicators、raw3入力のweighted mean/std。欠損未経験状態はUNKNOWN。

Weighted L2 Logisticのみ、lambda=1、intercept無罰則。Objective=`sum(w*(logaddexp(0,z)-y*z)) + 0.5*sum(beta_nonintercept^2)`。Weight=`1/(S*d_s*n_sd)`。NumPy2.3.5 / Python3.12 / threads1、Newton np.linalg.solve、Armijo1e-4、最大100反復、gradient infinity norm<=1e-10。Hyperparameter search0。

出力はsymbol-balanced training measureでのGood Reference Trade probability。事前固定decisionは `pGood > training-fold weighted GOOD prevalence`。Cutoffはtraining labelだけで計算しOOFから選択しない。各symbol-session最初のqualified eventだけENTER、後続は消費済み。WAIT/reentryなし。Runtime eligibilityにfuture label availabilityは使わない。

## CV / fold results

Chronological4fold: train16/31/46/61 sessions→それぞれ次の15sessions。Symbol-disjoint5groupは事前固定hashで最後15sessionsを評価、先行61sessionsの非held-symbolでfit。後者は全76sessions OOFではない。Label endpointがeval開始以降のtrainをpurge。OOFはchrono3,000行、symbol750行、各scope重複0。2scopeを独立3,750標本として合算しない。

| Unit | Train events / joint labels | GOOD prior cutoff | Held events / joint scored | AUROC | ENTER |
|---|---:|---:|---:|---:|---:|
| chrono-1 | 800 / 347 | 41.47% | 750 / 344 | 0.4909 | 222 |
| chrono-2 | 1550 / 691 | 40.36% | 750 / 320 | 0.4567 | 387 |
| chrono-3 | 2300 / 1011 | 38.76% | 750 / 319 | 0.4700 | 408 |
| chrono-4 | 3050 / 1330 | 37.57% | 750 / 321 | 0.5210 | 394 |
| symbol-0 | 2381 / 1077 | 35.87% | 169 / 69 | 0.4744 | 96 |
| symbol-1 | 2315 / 1041 | 37.23% | 226 / 94 | 0.5817 | 112 |
| symbol-2 | 2505 / 1089 | 37.95% | 112 / 43 | 0.4561 | 65 |
| symbol-3 | 2531 / 1049 | 38.90% | 125 / 66 | 0.4085 | 48 |
| symbol-4 | 2468 / 1064 | 37.87% | 118 / 49 | 0.5368 | 75 |

No session overlap, held-symbol overlap0, purged rows=0。Model SHA/weights/medians/scaling/coefficients/training identitiesはmodels.json.gzに全保存。

| Probability diagnostic | Chronological | Symbol-disjoint last15 |
|---|---:|---:|
| GOOD prevalence | 33.13% | 36.76% |
| Weighted held prevalence | 36.90% | 41.27% |
| AUROC | 0.4700 | 0.5005 |
| Average precision / ranking | 32.05% | 35.01% |
| Selected GOOD precision | 30.41% | 34.56% |
| Selected GOOD recall | 40.97% | 39.83% |
| Brier skill vs train prior | -0.09% | -0.10% |
| Log-loss skill vs train prior | -0.07% | -0.07% |

AUROC>0.5はchrono1/4、symbol2/5。Brier/log-lossは各unit内symbol/session-balancedで計算しunit等重み集計。AUROC/APとprecision/recallはevent単位。単純accuracyを成功判定に使わない。

## Own causal ENTER comparison — chronological held60 sessions

| Metric | Frozen v1 | v2.3 |
|---|---:|---:|
| ENTER | 232 | 1411 |
| ENTER/session | 3.8667 | 23.5167 |
| Unique symbols | 135 | 628 |
| Strict risk observed | 159 | 645 |
| Mean D30 (%) | 2.6776 | 1.4951 |
| Median D30 (%) | 1.6260 | 0.9615 |
| D30 p90 (%) | 5.7055 | 3.6140 |
| D30 p95 (%) | 10.4976 | 5.0000 |
| D30 ES95 (%) | 16.0329 | 7.7255 |
| Worst D30 (%) | 35.2941 | 29.6703 |
| MAE median (%) | -1.6260 | -0.9615 |
| MAE bad-side5 (%) | -10.4976 | -5.0000 |
| MAE worst (%) | -35.2941 | -29.6703 |
| D30>=2% / MAE<=-2% count | 66 | 167 |
| D30>=5% / MAE<=-5% count | 23 | 34 |
| D30>=10% / MAE<=-10% count | 10 | 5 |
| MFE median (%) | 3.2362 | 1.3158 |
| +1 precision (strict observed) | 86.16% | 59.07% |
| +2 precision (strict observed) | 72.96% | 33.95% |
| +3 precision (strict observed) | 51.57% | 21.55% |
| +5 precision (strict observed) | 29.56% | 8.22% |
| Joint coverage | 64.66% | 41.25% |
| Strict coverage | 68.53% | 45.71% |

Riskは観測subsetで低下した一方、Entry数が6.08倍になりupside qualityを希釈。Strict coverage差22.82pp、joint coverage差23.41ppが許容5ppを超える。したがって平均D30低下を全候補の公平なrisk改善とは断定しない。

| v1 winner preservation | Known retained / baseline | Censored challenger | Lower–upper bound |
|---|---:|---:|---:|
| +3 | 15 / 82 | 13 | 18.29% – 34.15% |
| +5 | 9 / 47 | 7 | 19.15% – 34.04% |

事前定義はsame symbol-sessionのchallenger自身のEntry価格・30分windowでwinnerを保持したか。v1との完全同一anchor比較ではない。UNKNOWNを全件winnerと仮定した上限でも+3/+5とも約34%で90%未達。

## Frozen gates

| Gate | Observed | Frozen limit | Result |
|---|---|---|---|
| chronologicalPooledAUC | 0.4700 | >= 0.55 | FAIL |
| chronologicalDirection | 1.0000 | >= 3 | FAIL |
| chronologicalBrierSkill | -0.0009 | > 0.0 | FAIL |
| chronologicalLogLossSkill | -0.0007 | > 0.0 | FAIL |
| symbolPooledAUC | 0.5005 | >= 0.55 | FAIL |
| symbolDirection | 2.0000 | >= 3 | FAIL |
| symbolBrierSkill | -0.0010 | > 0.0 | FAIL |
| symbolLogLossSkill | -0.0007 | > 0.0 | FAIL |
| winnerPreservation3 | 0.1829–0.3415 | >= 0.9 | FAIL |
| winnerPreservation5 | 0.1915–0.3404 | >= 0.9 | FAIL |
| throughputRatio | 6.0819 | >= 0.8 | PASS |
| meanD30Ratio | 0.5584 | < 1.0 | PASS |
| ES95Ratio | 0.4819 | <= 1.0 | PASS |
| jointCoverageGap | 0.2341 | <= 0.05 | FAIL |
| strictCoverageGap | 0.2282 | <= 0.05 | FAIL |
| top2RemovedAUC | 0.4693 | > 0.5 | FAIL |
| top2RemovedBrierSkill | -0.0009 | > 0.0 | FAIL |

14 FAIL / 3 PASS。ラベル・入力・lambda・decision rule・Gateの結果後変更0。No retuning。

## Symbol dependence / execution uncertainty

Chronological GOOD件数上位2銘柄67400/57590をsupporting diagnosticとして除いてもAUROC0.4693、Brier skill -0.0907%。モデル再fit・blacklistなし。Signalが特定銘柄除去で救われるEvidenceなし。これは全price-regime一般化証明でもない。

All3,800 candidatesで89180はGOOD10/BAD26/UNKNOWN89。GOOD10件には7→8円などの参照値利益が残る。57590はGOOD13/BAD32/UNKNOWN18。注文板/spread/depth/fill未確認のため、joint labelであってもexecution-certified good tradeではない。各参照例はresult.jsonに保存。Raw-price predictor/filterやtick proxyは追加していない。

Portfolio: 新replay0。既存full-stream unresolved1 / locked cash335,300円、Final Equity/MaxDD UNKNOWNを維持。以前の+23.05%は173-trade subset。Frozen EXIT/Equal/cash ledgerは変更0。Portfolio coverageとEntry識別力の失敗を区別。

## Tests / data conservation / stop

Prefit synthetic12 PASS → Project9fits成功 → synthetic+saved evidence16 PASS。kernel offlineでprice/provider accessを遮断。最終GitHub CIは当該commitのchecksを参照。CIは合成fitと保存Evidence監査だけでProject再fit/新predictionしない。

Fresh Validation=0 / Entry OOS=0 / EXIT OOS=0 / Prospective=0 / J-Quants=0 / Yahoo=0 / Other price providers=0 / SHORT=0。既存76session以外を開いていない。Safety9項目すべてfalse。新fit9、保存prediction3,750行、旧v2/v2.1/v2.2再fit0、target1、decision-rule1、threshold/model search0。

次の推奨判断は **C: Entry探索を一旦終了し、Frozen v1を比較baselineとしてEXIT / Capital / Portfolio統合へ進む**。今回は統合作業・v1新昇格を実行しない。選択肢Aはv1暫定Finalの正式判断、BはSelector pass-through/minimal Entryの別比較、Dは明確な新Evidenceがある場合のみ新Architecture1案。既存features/dataでv2.4/v2.5 target cyclingは行わない。

このKILLは本事前固定label・5inputs・線形logistic・decision ruleの最小screenに対する判断。すべてのGood Trade予測が不可能という証明ではない。Full Developmentに進むEvidenceが不足するためSTOP。

## Referenced identities

| Identity | SHA |
|---|---|
| eventIdentitySHA | `103ae204ad93ec32a772f0bd966cab3c9072d9509bb78c5a243aea200bbe57fd` |
| frozenPredictionSHA | `a11313909248d2c8aa1c39bac807f8a5c476c19c0be75a0e15dde41690cdb8be` |
| globalBudgetSHA | `b91699704f80ef7fda60fe0596e8f8736a181cd00dc879f5070f9caed4d4a62f` |
| p0DiagnosticSHA | `91019d3550bcfbf38e64cbc00e0f30b1cbefe44681152c82ed0b09bb3053c29d` |
| rootCauseEvidenceSHA | `5e6f10fb978b06efb0bfdc842570c75d6a277c1515ee3b5ffca1e02e170dbe71` |
| selectorFreezeCommit | `565d74b3dea823581fdb32380113aac5913a248d` |
| selectorPayloadSHA | `3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59` |
| selectorRidgeSHA | `994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb` |
| v1CandidateSHA | `4a2f52cd6f25f480fe6d7de9db525860ddf3c1600abed06b6222c0990c055a23` |
| v1EnterIdentitySHA | `72224ac9fd073f7da45c488aaf8ca999752b466e715837c21440e7dd93970236` |
| v1ModelSHA | `b053a858edda22bee7b9939162648740507964cc5ed8d613c2d778d15534589e` |
| v1ScalerSHA | `1e4865915a2ad1ec51dd4ebf2116d48b9f89b9b884f8dc732fdb2861dbf4fe4b` |
| v21ContractSHA | `82c17234b482118919b092df4af56c0e6a60d792de5ce3a551a509bcc3d293c7` |
| v21EvidenceSHA | `c1c257a54ff733828135c248fa1b9b9713b737836ee2b369017b68b8639ace12` |
| v22EvidenceSHA | `8c023aea2be7340d0026200dab17536abebd95a2e918cb6c0d6f5b028ec66239` |
| v22ProtocolSHA | `5349d28259b0764385a8de3b29038464eb8d639c992427df76a3fceb671ee5c6` |
| v2ContractSHA | `18818ffd1157c7ba15c93eb4723c3e28945c238e0e2f6a2440bee98c7ad1267f` |
| v2DevelopmentEvidenceSHA | `35cec58faedcebfd09190ed5c404e2e874647eca90b92e12bc9021ff80385a75` |

## Evidence files

- `result.json`: all nine units, pooled metrics, all frozen gates, censor reasons and safety.
- `label-ledger.json.gz`: all3,800 joint labels/unknowns and label endpoints.
- `models.json.gz`: nine models, SHA/weights/train IDs/missing medians/coefficient/solver receipts.
- `predictions.json.gz`: chronological3,000 and symbol750 saved decisions; no future eligibility.
- `prefit.json`, `prefit-tests.log`, `tests.log`: prefit and saved evidence audit.
- `repo-audit.json`, `manifest.json`, `manifest.json.sha256`: upstream/reproducibility identities.
