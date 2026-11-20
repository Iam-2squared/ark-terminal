# MSH-Entry LONG v2.1 — Separate-Axis Pre-Development Contract

**MSH_ENTRY_LONG_V2_1_PREDEVELOPMENT_CONTRACT_FROZEN**

Date: 2026-09-17 JST. Contract-only。v2.1 fit / prediction / OOF / threshold performance evaluation = **0**。

Frozen Selector → **Frozen v1 Opportunity Gate** → **Independent D30 Risk Gate** → ENTER / SKIP。

今回固定したのはv1のRefinement。Risk-onlyによるFull Replacementは行わない。D30はRiskの教師targetとして維持するが、Opportunity判定を置き換えない。既存v2/Root Causeの結果はDevelopmentに露出済みであり、v2.1の優位性はまだ測定していない。

## Git / identities

| Item | Frozen value |
|---|---|
| Repo / Branch | `Iam-2squared/ark-terminal` / `research/phase57-long-only-cash-equity` |
| PR | [#587](https://github.com/Iam-2squared/ark-terminal/pull/587), Draft / unmerged |
| Source / Root Cause head | `0ffdd8056489d7df7a9690df8047986a428eda4d` |
| Latest main at start | `c48be22db7deef286b0bb5dc1951964431145908` |
| Final head / final-head CI | Publication後のWork最終報告に記載。自己参照commit SHAをこの文書へ埋め込まない。 |
| Contract SHA | `82c17234b482118919b092df4af56c0e6a60d792de5ce3a551a509bcc3d293c7` |
| Selector freeze commit | `565d74b3dea823581fdb32380113aac5913a248d` |
| Selector payload SHA | `3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59` |
| Selector Ridge SHA | `994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb` |
| v1 candidate SHA | `4a2f52cd6f25f480fe6d7de9db525860ddf3c1600abed06b6222c0990c055a23` |
| v1 model SHA | `b053a858edda22bee7b9939162648740507964cc5ed8d613c2d778d15534589e` |
| v1 scaler SHA | `1e4865915a2ad1ec51dd4ebf2116d48b9f89b9b884f8dc732fdb2861dbf4fe4b` |
| v1 277 ENTER identity SHA | `72224ac9fd073f7da45c488aaf8ca999752b466e715837c21440e7dd93970236` |
| v2 Contract SHA | `18818ffd1157c7ba15c93eb4723c3e28945c238e0e2f6a2440bee98c7ad1267f` |
| v2 Development Evidence SHA | `35cec58faedcebfd09190ed5c404e2e874647eca90b92e12bc9021ff80385a75` |
| Root Cause Evidence SHA | `5e6f10fb978b06efb0bfdc842570c75d6a277c1515ee3b5ffca1e02e170dbe71` |
| Global Budget SHA | `b91699704f80ef7fda60fe0596e8f8736a181cd00dc879f5070f9caed4d4a62f` |

Machine-readable authority: [v2.1 Contract](../../../predict/research/phase57-msh-entry-long-v2-1-predevelopment-contract-v1.json).
100 source filesをSHAで保護。Selector/v1/EXIT/Equal/cash ledgerおよび旧Contract/Evidenceは変更していない。

## Claude review disposition

[claude-review-disposition.json](claude-review-disposition.json)に採用/不採用/理由を保存した。今回のsourceはユーザー提供のClaude review要約。新しいClaude review/API呼出を行ったという主張はしない。

- 採用：Opportunity/Risk/Executionの責務分離、Frozen v1 anchor、独立した低capacity Risk、ENTER/SKIP、Fresh温存。
- 不採用：E[L] tier別1.5/2.5/4/5%、絶対Precision/HHI/ENTER数/Sharpeの数値、未監査の新market feature。
- 自動追加なし：Two-Head、WAIT、tree ensemble、execution proxy、symbol/低価格filter。

## Opportunity axis / exact refinement boundary

v1 model/scaler、Score `E[L]=P1+2P2+3P3+4P4`、threshold `2.0`を固定。
Historical status BORDERLINE、Fresh PENDINGは維持。

| Population | N | Meaning |
|---|---:|---|
| Historical conditional Top5 universe | 3,800 | 760 decision timestamps / 76 sessions |
| E[L]>=2.0のraw event | 353 | 状態制約前のscore-qualified候補 |
| Frozen v1 ENTER anchor | 277 | 各symbol-sessionで最初のqualifying event |
| 後続のscore-qualified event | 76 | v1ではALREADY_ENTERED。v2.1で復活させない |
| Risk target labelable | 181 | supervised lossへ使える全期間のinventory |
| Risk target unlabelable | 96 | lossからのみ除外、decision ledgerに残す |

**v1 shadow stateをRiskより先に更新する。** v1が最初のENTERを出す時点でsymbol-sessionの資格を消費し、そのRisk判定がSKIPでも後続Entryを許可しない。Allocation拒否やEXIT後も再Entryなし。毎session reset。これによりv2.1 ENTERはFrozen v1の277 anchorsの厳密なsubsetになり、時刻・価格を動かさずRisk追加の効果を測れる。

Risk SKIP後の入り直しはWAIT/遅延Entryの別実験になるため今回禁止。v1 SKIP recoveryはFull Replacementの別研究。raw353を277と混同しない。

## Risk target / training population

**D30 disposition = A_KEEP_PRIMARY**：Risk training targetとして維持。最終Entry判断ではOpportunityに補助する軸で、sole ENTER gateではない。

`MAE30=min(0,100*(min future regular5m LOW / DecisionPrice - 1))`、`D30=max(0,-MAE30)`。
単位はpercentage points。Decisionからwall-clock30分、6本の5分足、同session/continuous segment。昼休み跨ぎ・session-end跨ぎ・expected bar欠損はcensored。Auctionなし、future labelは教師/evaluator専用、同一bar内の順序はUNKNOWN_INTRABAR_ORDER。

| Unlabelable reason | N |
|---|---:|
| PROVIDER_GAP | 51 |
| LUNCH_BREAK | 25 |
| SESSION_END | 20 |
| Total | 96 |

PROVIDER_GAPの内因をno-tradeと断定しない。0 label、次観測代入、補完なし。Label availabilityで先行anchorを飛ばして後続に入り直すことも禁止。

Risk anchorsは156 symbols、labelableは120 symbols。データ期間は2024-09-17〜2025-01-09。
Training rowは**Frozen v1 first-qualifying selection event**。181を一括で全foldへ渡さず、各FIT prefix内のlabelable anchorsだけ使用する。

Weight：`w_i=1/(S*d_s*n_sd)`。S=そのFITに含むsymbols数、d_s=そのsymbolのeligible sessions数、n_sd=そのsymbol-sessionのrows数。今回はn_sd=1。各symbolの総weightを同一にし、そのsessionへ均等配分する。held group/label mask適用後、FITごとに再計算。特殊symbol weightなし。

## Risk features / PIT / missing

**Selector Score inside Risk = NO。Selector Rank / v1 E[L] / probabilitiesもRisk入力にしない。** Opportunity gateでは元のScore/Rankをそのまま使用する。

| Order | Input | Definition | Available /277 | Available /181 |
|---|---|---|---:|---:|
| 1 | directionalMomentum3Pct | 最新completed close / 3 trading bars前のclose −1、% | 233 | 168 |
| 2 | directionalPullback6Pct | 最新completed close / 最新6 completed barsのmax HIGH −1、% | 197 | 144 |
| 3 | momentum3Missing | 原Momentumがunavailableなら1、availableなら0 | 277 | 181 |
| 4 | pullback6Missing | 原Pullbackがunavailableなら1、availableなら0 | 277 | 181 |

4 effective inputs、2 raw predictors。Feature追加、交互作用、多項式なし。P0/Root Causeは予測有効性を保証しない。SelectorをRisk入力から外すのは責務分離の設計判断で、ablation結果ではない。

両raw featureはsame-session completed5m prefix、availableAt<=decisionの既存code guardを継承。Scheduled lunchを跨ぐlookbackでは取引slotを数えるが、missing/no-tradeを飛ばして穴埋めしない。前sessionのOHLCを代入しない。

保存rowには各構成barの到着時刻がないため、PITは**既存source code/固定reference dataに条件付き**。L1のfuture-label-conditioned membershipや日次metadata release clockの制限も継承する。完全なlive-universe PIT証明はしない。

Missing処理は各FIT内のobserved finite値の**weighted median**。値、event ID順に並べ、観測分へweightを再正規化し累積>=0.5の最初の値を選ぶ。labelsの値やcalibration/evaluation情報を統計に入れない。

Impute後、FIT内weighted mean/population stdでraw2列のみstandardize。flagsは0/1のまま。true zeroとmissingを区別する。Observedなし・variance0・不正finite/statusは規則に従いFIT/INPUT失敗。評価時にFIT未観測のmissing bitが現れればunsupported/SKIP、v1 fallbackなし。全統計とmask supportを保存する。

## Model / CV / state / selection

Primary Risk modelは**Weighted Linear Ridge、lambda=1**のみ。切片あり、切片は非penalty。

`0.5*sum(w_i*(D30_i-b-z_i@beta)^2) + 0.5*sum(beta_j^2)`、sum weights=1。
`numpy.linalg.solve`、Python3.12 / NumPy2.3.5 / float64 / 1 thread。Randomnessなし。raw outputを保存し、physical readoutは`max(0,raw)`。Expected return/sizing score/tail probabilityとは呼ばない。

FIT support guardは既存の7 labelled rows / 2 symbolsを維持し、各raw predictorに2以上のobserved値と正のvarianceを要求する。これは数値上の最低条件で統計的十分性ではない。solver residual tolerance=1e-10×(1+rhs infinity norm)、失敗時の別model/fallbackなし。

| Fold | Inner fit ordinal | Inner calibration | Outer train | Outer evaluation | Inner fit labelable anchors | Calibration labelable anchors |
|---|---|---|---|---|---:|---:|
| 1 | 1–12 | 13–16 | 1–16 | 17–31 | 17 | 5 |
| 2 | 1–23 | 24–31 | 1–31 | 32–46 | 30 | 16 |
| 3 | 1–34 | 35–46 | 1–46 | 47–61 | 50 | 45 |
| 4 | 1–45 | 46–61 | 1–61 | 62–76 | 91 | 46 |

初期16sessionsは両armとも評価外。Primary outer比較は同じ60sessions / 3,000 candidate IDs、v1 anchors232、strict159。Risk scoreはanchorだけで計算し、non-anchorにはnull/NOT_OPPORTUNITY_ANCHOR。3,000記録を3,000 Risk predictionsと数えない。

Whole-session chronological splitを継承。Same symbol-sessionの跨ぎ0。FIT labelEndが次block start以上、または同symbolの評価windowと重なる場合はpurge。今回のmetadata監査では0。Imputer/scaler/modelはFIT内のみ。

Secondaryは既存固定hash `SHA256('PHASE57_MSH_LONG_V2_GROUP_V1|'+symbol) mod 5`。4fold×5groupでheld symbolsをinner fit/calibration/outer refitすべてから除外し、そのgroupの将来outer rowsだけ評価する。結果でgroupを入れ替えない。

**Frozen Selectorとv1 final modelは76sessions全体に学習露出済み。** Chronological/held-symbol評価が保護するのは追加Risk componentだけであり、全pipelineの独立OOF・OOSとは扱わない。初期calibrationは小さく、DevelopmentがBLOCKEDになる可能性をそのまま残す。

Joint decisionは `frozen v1 anchor AND valid Risk inputs AND predictedD30<=tau`。StateはENTER/SKIPのみ。
Threshold候補は **{1,2,5,10}**。全inner Entry gatesを満たす候補から**最大tau＝最も制限の弱いもの**を選ぶ。同じanchorsではtauを上げるほどv1機会の保持集合が広がるため、必要なRisk改善を満たした後の追加犠牲を避ける設計原則。v2のmin-mean選択からの変更を今回明示的にversion化した。

FeasibleなしはNONE。inner予測・全4候補・Gate理由を保存し、そのreplicaのouter refitへ進まない。Outer欠落をdefault v1で埋めない。最終76session modelやdeploy thresholdは今回Freeze/学習していない。

## Exact numeric gates

全てv2.1 outcomeを見る前に固定した**研究上の相対許容budget**であり、最適値の経験的証明ではない。10%/20%/5ppは以前のv2事前Contractを継承。絶対Precision80%・HHI.20等を採用していない。

| Class | Metric | Gate |
|---|---|---:|
| Primary | +1 Precision / v1 | >=0.90 |
| Primary | +2 Precision / v1 | >=0.90 |
| Primary | v1 +3 winner anchor retention | >=0.90 |
| Primary | v1 +5 winner anchor retention | >=0.90 |
| Primary | Mean D30 / v1 | <=0.90 |
| Primary | D30 ES95 / v1 | <=1.00 |
| Primary | ENTER count / v1 | >=0.80 |
| Guardrail | Strict-label coverage absolute gap | <=0.05（5pp） |
| Guardrail | Entry-symbol-count HHI / v1 | <=1.10 |
| Guardrail | Mean D30非悪化のchronological folds | >=3/4（strict majority） |
| Guardrail | Direct Risk reject mean D30 − accept mean D30 | >=0、両群のlabel必要 |
| Cross-symbol | Pooled Mean D30 / v1 | <=1.00 |
| Cross-symbol | Symbol-macro Mean D30 / v1 | <=1.00 |
| Cross-symbol | 非悪化hash groups | >=3/5、全5group評価可能 |
| Cross-symbol | +1/+2 Precision / v1 | 各>=0.90 |
| Cross-symbol | +3/+5 anchor retention | 各>=0.90 |
| Cross-symbol | Throughput / v1 | >=0.80 |
| Cross-symbol | Coverage absolute gap | <=0.05 |

Inner threshold選択には7 Primaryとcoverageだけを使う。Outerのconcentration、stability、cross-symbol、Portfolioでthresholdを選ばない。

Primary retentionの分母は、その評価windowの**v1が実際にENTERしたlabelable +k winner anchors**。分子はv2.1が保持した同じID。同じ時刻・価格・30分windowなので遅延機会を混ぜない。旧v2の「最初のSelector判断から元のendpointまで」のpreservationとは分母が異なる。旧metricは名前を分けてdiagnosticとして残す。

Precisionは各armのlabelable accepted集合、throughputはlabel可否を問わない全Entry信号。共通ENTER集合だけの比較は主評価にしない。HHI gateはEntry数のsymbol concentrationで、利益寄与HHIとは別物。

Macro Mean D30は各armのlabelable accepted symbols内平均を等weightで平均する既存定義。消えたsymbolへの数値代入なし。分母・完全棄却symbols・共通symbolのpaired診断を併記し、構成変化だけを汎化改善と主張しない。

Baseline burden0では非悪化はcandidate0のみPASS、10%改善はINCONCLUSIVE。winner分母0、空群、未評価groupもINCONCLUSIVE。epsilonで救済しない。単に取引を消してRisk/concentrationを下げても成功にしない。

将来のEntry Development PASSには必要なEntry/Guardrail/Cross-symbol gatesすべての定義済みPASSが必要。技術的/選定/OOF欠落はBLOCKED、完備したOOFで既知違反はFAIL。Portfolioは別statusで、UNKNOWNをEntry改善の証拠に置き換えない。

## Execution / Portfolio / fair comparator

Execution Qualityは**DIAGNOSTIC_ONLY_NO_GATE**。89180の1円刻みのhigh-touchと実際のfill/利益を区別する。Orderbook/spread/depthを推定で作らず、price/symbol/segment/liquidity/time filterを追加しない。

固定比較器：同じFrozen Selector → v1またはv2.1 exact-anchor refinement → `LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1` → `EQUAL_MAX3 / V3_0_EQUAL` → `scripts/phase57_long_capital_integration.py::replay`。

Initial cash1,000,000 JPY、lot100、max concurrent10、budget divisor3、round-trip cost0.05%（entry notional基準、半分をentry/半分をexit）。同timestampはEXIT/cash release後にsymbol順ENTRY。Sizing snapshotとsequential cash capも固定。Risk scoreをallocationへ渡さない。

Future exit-resolvableでEntryを事前filterしない。Missing前で未解決になったpositionは資金拘束を維持し、cash releaseや売却価格を作らない。v1 full streamの未解決1件/335,300円、Final Equity/MaxDD UNKNOWNを継承。+23.05%は以前の173 complete-case subsetで範囲が異なる。

Portfolioは**Secondary/Diagnostic**。Entry-level PASSとPortfolio PASSを分離する。Return/PF/DD/utilization/positive-negative HHI/effective contributors/Top-k/Top-symbol exclusionsは計算可能範囲のみ報告し、未解決ならUNKNOWN。Ledgerの修正は別Contractが必要。

## Required evidence in the next separately authorized run

今回欠けていたinner数値予測の保存を必須にする。Threshold選択前に、model artifact+SHA、全inner ID、anchorごとのrawPrediction/readout、input masks/変換4列、v1 shadow reason、全4候補のdecision reason/Gates/分母、FIT/exclusion/split ledgerを保存する。保存失敗はBLOCKED。

Outerは(eventId, scope)重複0、calibration/held symbols漏洩0、model serialization/reload parity必須。NONE/failureを隠さない。今回はこれらのmodel artifact/score/OOFを作っていない。

## Data / tests / STOP

Historical / Development / IN-SAMPLE / Outcome-exposedの既存76 sessionsのみ。Fresh195-session budget変更なし。

v2.1 fit=0、prediction=0、OOF=0、threshold performance=0、feature performance selection=0、Portfolio replay=0。
Fresh Validation / Entry OOS / EXIT OOS / Prospective=0。J-Quants / Yahoo / other price requests=0。SHORT evaluation=0。

executionAllowed / brokerWriteAllowed / excelOrderWriteAllowed / rssOrderFunctionAllowed / liveTradingAllowed / paperTradingAllowed / automaticPromotionAllowed / productionUpdateAllowed / transmitted：**全9項目false**。現物LONG-only。main merge禁止。

Contract static auditorと16 testsを追加した。SHA chain、277 shadow anchors、censor維持、Feature混入拒否、fold/group leakage、threshold/Gate変異拒否、downstream/Safetyを監査する。Test/CI結果は最終Work報告を参照。

**STOP。** 次工程は別指示でのv2.1 implementation → prefit tests → Development fit → chronological OOF → held-symbol evaluation → v1 incremental comparison。Contract Freezeはそれらの実行許可でも性能PASSでもない。
