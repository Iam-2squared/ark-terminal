# MSH-Entry LONG v1 Historical Re-Measurement

**MSH_ENTRY_LONG_V1_HISTORICAL_REMEASUREMENT_BORDERLINE**

2026-09-16 JST。過去研究でoutcome-exposedなHistorical Dataを再利用した診断Evidence。全76 sessionsは最終Entryモデルの直接学習期間でもあるため、**IN-SAMPLE / DEVELOPMENT-EXPOSED**。正式Fresh確認はPENDING、OOSはSEALED。

Quality enrichment・Preservation・ThroughputはHistorical上で支持された。一方、strict30mの下方リスクがSelector baselineより重く、無条件のHistorical GOとは判定しない。新たな数値hard gateは設定していない。Entry・threshold・期間を変更せずSTOPする。

| 管理項目 | 内容 |
|---|---|
| Repo / branch / PR | Iam-2squared/ark-terminal / research/phase57-long-only-cash-equity / #587 |
| Dataset事前固定commit | 34291233dd9f9c2b7d548b6c35135b65d06903fa |
| 評価実装commit / Path成功run | 2cd423e794408bd5818f6020ca6fe964f6bb5b21 / 35085113314 |
| Latest main（開始時確認） | b7801ce2c13772cbc3f5b51506819c119fe868ea |
| 固定期間 | 2024-09-17–2025-01-09、76 sessions |
| Session-list SHA256 | de4a4264a7d78446ff01f72c2f927cc29ec45b18126068ca2e9dc2cfe16c5483 |
| Dataset契約SHA256 | 4a1d3e4ec4229d32ee2a50678db8fe3f8739abb3530df521e3036d201e75b441 |
| 予測artifact SHA256 | a11313909248d2c8aa1c39bac807f8a5c476c19c0be75a0e15dde41690cdb8be |
| Path artifact SHA256（非圧縮） | 09ded9e302bf70027d90492c36e0d4b482368e6a7dcade6d9c64c1352bd2c015 |
| cadence | 09:30 /10:00 /10:30 /11:00 /11:30 /13:00 /13:30 /14:00 /14:30 /15:00 JST |
| Universe | Frozen PIT JPX domestic cash-equity Prime/Standard/Growth Top5、追加filterなし |
| Candidate | Score+Rankのみ、E[L] >=2.0、ENTER/SKIP_THIS_DECISION、同一symbol-session再Entryなし |

直接学習に未使用のB/C期間について、同品質で再構成できるFrozen Selector入力・strict path一式を確認できなかったため未測定。今回の76日をFreshに再分類しない。各sessionのDisclosureはsession-exposure-ledger.json、正確な日付・順序はdataset-contract.jsonに保存。

予測は全3,800 Selector eventsへ1回適用。未来labelabilityでENTERを制御しない。最初のlabel不能ENTERも再Entryを禁止する。モデルfit、scaler refit、OOF再生成、他threshold評価は0。

| Throughput | Selector-only | Candidate2.0 | CURRENT supporting |
|---|---:|---:|---:|
| Unique first-entry候補 / ENTER | 2743 | 277 | 96 |
| First-entry Coverage | 100% | 10.10% | 3.50% |
| ENTER/session | — | 3.64 | 1.26 |
| strict30m評価可能 | 1303 | 181 | 65 |
| strict30m評価不能 | 1440 | 96 | 31 |

Candidate SKIP_THIS_DECISION=3523（既ENTERの後続判断を含む）。CURRENTは保存済みFrozen first PASSを再利用し、native5分cadenceのまま。Candidateは10 decisions/dayであり、同一cadenceに統制された因果比較ではない。CURRENTモデルを再実行・調整していない。

| HIGH Quality | Selector first opportunity (n=1303) | Candidate actual ENTER (n=181) | CURRENT (n=65) |
|---|---:|---:|---:|
| +1% Precision | 66.00% | 86.19% (156/181) | 80.00% |
| +2% Precision | 42.75% | 72.93% (132/181) | 58.46% |
| +3% Precision | 27.63% | 52.49% (95/181) | 44.62% |
| +5% Precision | 12.05% | 30.94% (56/181) | 30.77% |

Precisionの分母は各actual reference時点でstrict30m pathが得られたsubset。全ENTERのprecision・実運用coverageではない。First-Selector-labelable共通母集団1,303 symbol-sessionsでも、Candidateは188 ENTER /178 labelable、Precision +1/+2/+3/+5 = 86.52/73.03/52.25/30.90%。このsubset Coverage14.43%を実運用Coverageと呼ばない。

| Opportunity | Selector winners | Candidate transfer | Preservation | Preserved/session | Original horizon内にENTER | WinnerかつEntry後もhit | CURRENT Preservation |
|---|---:|---:|---:|---:|---:|---:|---:|
| +1% | 860 | 153 | 17.79% | 2.01 | 139 | 147 | 6.28% |
| +2% | 557 | 131 | 23.52% | 1.72 | 119 | 123 | 6.82% |
| +3% | 360 | 98 | 27.22% | 1.29 | 88 | 88 | 8.61% |
| +5% | 157 | 58 | 36.94% | 0.76 | 53 | 53 | 14.01% |

Preservationはfirst Selectorのstrict30m HIGH winnerが後のCandidate ENTERへ移った割合。後続ENTER時点に元の上昇余地が残っている保証ではないため、元horizon終了前ENTERと、元winnerかつEntry後remaining hitを別記した。Entry-time remaining opportunityそのものはactual ENTER referenceから新しいstrict30mで測定し、+1/+2/+3/+5のhitは156/132/95/56（n=181）。元Selector winnersのtransfer件数とは異なる。

| Path / Risk（gross reference、strict30m） | Selector | Candidate | CURRENT supporting |
|---|---:|---:|---:|
| MAE mean | -1.72% | -2.56% | -2.90% |
| MAE median | -1.09% | -1.53% | -1.46% |
| MAE adverse 5th percentile | -5.60% | -10.26% | -11.08% |
| MAE worst | -35.29% | -35.29% | -35.29% |
| MFE mean | 2.49% | 4.86% | 5.05% |
| MFE median | 1.64% | 3.33% | 2.56% |
| MFE 95th percentile | 8.12% | 14.29% | 14.29% |

MAE = min(0,100×(strict horizon内minimum LOW / Entry reference−1))。MFE = max(0,100×(maximum HIGH / reference−1))。同一reference、同一30分、6つの連続completed5m barsを使用。昼休み跨ぎ・session終了跨ぎはlabel不能、auctionは除外。Session MAEで代用していない。costはgross reference-price diagnosticのみ、実約定・broker-realized P&Lではない。

最悪の観測値は2024-12-25、57590の09:30 ENTERでMAE−35.29%、MFE0%。同銘柄12-27はMAE−20.00%。結果が悪いsession・銘柄を除外せず全固定範囲へ残した。下方tailは損失の実現値ではないが、無条件GOを支える状態でもない。

| Completed CLOSE supporting | Selector | Candidate | CURRENT |
|---|---:|---:|---:|
| +1% | 53.11% | 70.17% | 58.46% |
| +2% | 32.39% | 51.93% | 41.54% |
| +3% | 21.03% | 39.78% | 38.46% |
| +5% | 9.59% | 25.97% | 27.69% |

CLOSEは同一strict path内completed5m CLOSEの最大値であり、30分endpointだけのcloseではない。HIGHと合成していない。

First Selector→ENTER latency: median 0.00分、mean 12.78分、p95 96.00分、max300分。Consumed return: median0 bps、mean -82.98 bps、range −1318.68～343.07 bps。負値は価格が下がってからENTERしたことを示す。同じdecision内のCandidate判定時刻差はhistorical convention上0分で、実際の計算時間・約定遅延を測ったものではない。

Session stability: 75/76 sessionsでENTERあり、ENTER/day中央値3、range0–11。上位5sessionsのENTER比率15.16%、+1/+2/+3/+5 hit比率16.03/15.91/15.79/21.43%。少数sessionだけで全体が成立しているとは見えない。session別ENTER・Precision・Preserved Opportunityをsession-summary.csvとmeasurement.jsonへ保存。

| Labelability | 全Selector events | Actual ENTER |
|---|---:|---:|
| Total | 3800 | 277 |
| Labelable | 1828 (48.11%) | 181 (65.34%) |
| Unlabelable | 1972 | 96 |
| PROVIDER_GAP | 1424 | 51 |
| LUNCH_BREAK | 380 | 25 |
| SESSION_END | 168 | 20 |

UnlabelableをClass0に置換していない。Missingを埋めない。Frozen provider normalizerは観測されたminute tradesを5分へ集約する仕様で、各5分に常に5つのminute rowsがあるわけではない。Sparse-minute barを含むpathはCandidate labelable181件中97件、Selector first-labelable1303件中848件。無観測minuteを補間せず、今回のtrue MAEは保存provider path上のstrict-horizon LOWの最小値として解釈する。未観測取引を保証しない。

Development OOF Threshold2.0 reference（再計算なし、直接比較不可）: Coverage13.01%、ENTER/session2.38、Precision88.81/74.13/53.15/32.87%、Preservation16.85/21.88/25.00/31.61%。OOFは60評価sessions・旧labelable cohort、今回はfinal model・76 training sessions・全events causal replayである。改善/劣化の独立推定に使用しない。

| Integrity / safety | 結果 |
|---|---|
| Frozen Candidate / model / scaler / Global Budget / Fit / Development / Selector | SHA一致、frozen-artifact-verification.json参照 |
| strict HIGH/CLOSE再構成 | 保存labelable1828 rowsすべて一致 |
| 保存checkpoint | L1 run34926225832、C+D run34936002178、V2 run34964031692、8 encrypted artifacts |
| Raw source | 76 Development日、31,968,247 minute rows →11,665,575 provider5m bars。Invalid/rejected0、duplicate0。raw/normalized/page SHAはpath-diagnostics.json.gzに全日保存 |
| Provider requests | Yahoo0 / J-Quants0 / Other0。GitHubの既存artifact downloadのみ |
| OOS / EXIT outcome access / SHORT evaluation | すべて0 |
| Forward-fill / interpolation / future substitution | すべて0 |
| Fit / scaler refit / OOF更新 / threshold search | すべて0 |
| Fresh budget consumption | 0、Global195とFuture20保護を維持 |
| executionAllowed / brokerWriteAllowed / excelOrderWriteAllowed / rssOrderFunctionAllowed / liveTradingAllowed / paperTradingAllowed / automaticPromotionAllowed / productionUpdateAllowed / transmitted | 全false |
| Offline regression | Predict2702 / Discovery26 / Foundation39 / Python ordinal-evaluation30 / RSS89 PASS。新規causal/artifact7 + strict-path6 PASS |

最初のpath jobはUTC/JSTの文字列表記差で停止した。等価なinstantへ正規化する実装修正後、同じ固定session/path契約でPASS。予測前の入力検証でも同じ表記差を検出し、修正後のみmodelPredictionCalls=1を実行。Rawデータ・Candidate・threshold・期間は変更なし。RSSは最初のPython環境にpytestがなかったため既存test venvを使用しPASS。これらの経緯をreceipt/regressionへ残した。

**次の正確な作業:** ここでSTOP。別のArchitecture Decisionで、このpath/risk懸念を踏まえてEntry2.0を変更せずLONG EXIT研究へ進めるか判断する。今回はEXITを実行せず、Entryを作り直さず、正式Fresh確認はPENDINGのまま維持する。

このEvidenceで述べられるのは「再利用した学習期間上でQuality・Preservation・Throughputを確認し、path/risk懸念も観測した」こと。未見データの性能証明ではない。

GitHub CI: prediction Evidence commit0be75a32623c02f6a6a0381f06d00173d0a4b561でPredict、Foundation、Daily Dry-Run、Historical Re-Measurement IntegrityがPASS。最終report commitのCIはPR #587のChecksで別途確認する。mainへmergeしない。
