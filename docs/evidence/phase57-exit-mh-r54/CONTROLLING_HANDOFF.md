# Phase57 R54 Multi-Horizon EXIT — Controlling Handoff

Saved JST: 2026-09-28 19:39  
Basis HEAD before this handoff: `96586e78cfe793c0ec4bc9f1630a07ae9486f356`  
Repo: `Iam-2squared/ark-terminal`  
Branch: `research/phase57-long-only-cash-equity`  
Draft PR: #587

## 🧭 結論

R54 `CYCLE2_CORRECTED_D_TEACHER` は、有限学習・OOF・全予定Replay・費用stress・独立D再fit・R34 Layer A会計補正監査まで完了した。

**R54 Cycle2は研究cycleとしてCLOSED。採用候補は0。**
最終状態は次のとおり。

| status | result |
|---|---|
| integrity_status | **PASS** |
| measurement_status | **MEASUREMENT_BLOCKED** |
| forecast_status | **FAIL_D_INCREMENTAL_SKILL** |
| winner_status | **FAIL** |
| economic_status | **FULL_PERIOD_UNMEASURABLE** |
| utilization_target_status | **FULL_PERIOD_UNMEASURABLE** |
| selection | **MEASUREMENT_BLOCKED / selected=null** |
| productionReady | **false** |

これは「R54が赤字だった」という一文には縮約しない。
24日Final Equityは候補経路で認証不能だった。一方、測定可能な同一数量Winner比較とD予測skillは明確にGate未達だった。

## 🔒 固定Upstream

- Selector: Frozen
- Entry: `IMMEDIATE` / `ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF`
- Entry Dual Freeze: `4878a1cc53430e816261dea0fb16aeb53b3c238d`
- Capital: `SAVED_CAPITAL_V3_B_CI_RANK_AND_R37_SIZING_ONE_SHOT_ENTRY`
- Initial cash: ¥1,000,000
- Lot: 100株
- MAX3
- 現物LONG / CASH-only
- Control EXIT: `R50_A_LIFECYCLE`

R54内でSelector / Entry / Capital / candidate count / threshold / model familyを性能後に変更していない。

## 🧬 Lineage / budget

| item | value |
|---|---|
| Corrected Teacher SHA256 | `a017a10b5b0b6dc0a023ba070a60b0e991d3d98d62a800d36fe743b85c2c759b` |
| Protocol SHA256 | `5c9576eee5f7a7d3a9447f3395afcc9eeee95d09998a6754fe2a3539c0e517b3` |
| Finite run | `36382668368` |
| Execution HEAD | `2166772f719bcd947382fa242ec63231c3f91fbe` |
| Real estimator fits | **176 / 176** |
| Integrated Replay invocations | **44 / 44** |
| Provider requests | **0** |
| Protected opens | **0** |
| Forecast artifact | `10962884880` |
| Replay artifact | `10964100200` |
| R34 accounting audit run | `36410273844` |
| R34 audit artifact | `10964250835` |

OOF independent D refit max prediction delta = **0.0**。
14 configsのsame-saved-forecast Replayはすべて一致。Independent D refit replayも一致した。

## 🔮 Forecast

### A — 将来参照価格の平均絶対誤差

| horizon | IM MAE % | IM MAE ¥ | R1 MAE % | R1 MAE ¥ |
|---:|---:|---:|---:|---:|
| 1m | 0.3642% | ¥4.63 | 0.3619% | ¥4.62 |
| 5m | 0.6710% | ¥8.67 | 0.6627% | ¥8.55 |
| 15m | 1.0949% | ¥14.28 | 1.0873% | ¥14.10 |
| 30m | 1.5123% | ¥19.67 | 1.5073% | ¥19.48 |
| 60m | 2.0743% | ¥26.82 | 2.0461% | ¥26.18 |
| EOD | 2.7457% | ¥36.37 | 2.7013% | ¥35.76 |

MAEが小さく見えても、AのMSEは据え置き価格相当のzero comparatorに主要短期horizonで勝っていない。
fold勝ちはIM/R1ともh1=0/4, h5=0/4, h15=0/4。h30/60/EODでも各1/4。

### D — 「今売る vs 待つ」予測

Controllerが実際に使うのはD。

| Arm | h | R54 pooled MSE | D=0 MSE | fold wins |
|---|---:|---:|---:|---:|
| IM | 1 | 0.412386 | 0.319593 | 0/4 |
| IM | 5 | 1.411612 | 1.330006 | 0/4 |
| IM | 15 | 3.684462 | 3.555809 | 0/4 |
| IM | 30 | 6.870997 | 6.656254 | 1/4 |
| IM | 60 | 12.327310 | 11.931424 | 1/4 |
| IM | EOD | 25.374156 | 24.681710 | 1/4 |
| R1 | 1 | 0.431842 | 0.319521 | 0/4 |
| R1 | 5 | 1.420300 | 1.316484 | 0/4 |
| R1 | 15 | 3.727369 | 3.542776 | 0/4 |
| R1 | 30 | 6.990043 | 6.683286 | 0/4 |
| R1 | 60 | 12.394177 | 11.960650 | 1/4 |
| R1 | EOD | 24.790549 | 24.532508 | 1/4 |

**Primary h1/5/15でD=0に一度もfold勝ちせず、pooledでも全て悪化。Frozen D forecast GateはFAIL。**

HIGH/LOW extrema側はzero comparatorより改善したが、初版ControllerはHIGH/LOWを売買入力にしないため、D failureを救済するselection authorityはない。

## 🔨 Controller

Full modelの2候補は最終的に同じ挙動になった。

| Arm | Policy | Entries | Model Exit | Forced Terminal | Grace used |
|---|---|---:|---:|---:|---:|
| IM | MH_WAIT15 | 819 | 542 | 277 | **0** |
| IM | MH_WAIT5 | 819 | 542 | 277 | **0** |
| R1 | MH_WAIT15 | 795 | 509 | 286 | **0** |
| R1 | MH_WAIT5 | 795 | 509 | 286 | **0** |

full WAIT15/WAIT5のledger/bucket/daily/equityは各arm内でbyte-identical。

**long_supportが実売買で一度もgraceを発火させなかったため、5分/15分という設計差が消失した。**
結果後に3つ目のControllerやthresholdを追加して救済しない。

## 🏆 Winner保持 — R34会計補正後

Layer Aはperformance閲覧前に発見済みだったR34売却費用basis差を、保存済み価格・同一数量だけからappend-only補正した。
追加fit=0、追加integrated replay=0、候補/threshold変更=0。
監査run `36410273844` はSUCCESS。

### IM — 同じ旧79 Entry / 同じ数量

| cohort | R50 control Mean Net | R54 Mean Net | R50 PnL | R54 PnL | delta |
|---|---:|---:|---:|---:|---:|
| ≥5% N=27 | **4.8960%** | **1.8850%** | ¥329,595.75 | ¥142,895.75 | **−¥186,700** |
| ≥10% N=15 | **7.4675%** | **2.6691%** | ¥269,377.29 | ¥114,677.29 | **−¥154,700** |
| 3–5% N=17 | −1.0889% | **+1.1649%** | — | — | **+¥105,000** |
| <1% N=20 | −4.6600% | **−1.6986%** | — | — | **+¥165,900** |
| 全79 | −0.3042% | **約+0.1951%** | −¥112,868.99 | +¥35,381.01 | **+¥148,250** |

R54は小値幅・3–5%群を大きく改善した一方、**>=5% / >=10% Winnerの利益を大幅に失った**。

Frozen minimum:
- >=5% Mean Net >= 3.8960% → **FAIL**
- >=5% same-quantity PnL >= ¥296,636.175 → **FAIL**
- >=10% Mean Net >= 6.468% → **FAIL**

### R1

| cohort | R50 Mean Net | R54 Mean Net | PnL delta |
|---|---:|---:|---:|
| ≥5% N=12 | 7.1148% | **0.9413%** | **−¥209,700** |
| ≥10% N=8 | 9.5169% | **0.1308%** | **−¥215,200** |

Winner保持FAILはIMだけの現象ではない。

## 💴 Capital / Integrated Replay

### IM Full R54

| metric | R54 Full | R50 Control |
|---|---:|---:|
| funded | **31** | 79 |
| confirmed exits | 30 | 79 |
| end open | **1** | 0 |
| realized closed PnL | **+¥18,988.62** | −¥112,868.99 |
| Final Equity | **null** | ¥887,131.01 |
| 24日Return | **null** | −11.2869% |
| certified sessions | **1/24** | 24/24 |
| valid mark minutes | **650/7,800** | 7,779/7,800 |
| valid-only utilization | 51.21% | 76.84% |
| ≥80% valid-time share | 26.00% | 58.29% |
| ≥5% funded / available | **7/158 = 4.43%** | 27/158 = 17.09% |
| ≥10% funded | **3** | 15 |
| Replacement N / ≥5 | 25 / 4 | 7 / 0 |
| Replacement upside median | 1.9517% | 1.7866% |
| top-session notional share | **55.21%** | 5.63% |

IMは `2025-07-23|62650|883` のterminal auction参照不足で未解決positionが残り、その後の>=5% Opportunity **146件**が `UNRESOLVED_CASH_LOCK` へ流れた。

closed PnLが+18,988円でも、未決済を無視した値なので100万円→101.9万円とは呼ばない。

### R1 Full R54

| metric | R54 Full | R50 Control |
|---|---:|---:|
| funded | **90** | 32 |
| confirmed exits | 89 | 31 |
| end open | **1** | 1 |
| realized closed PnL | **−¥36,440.72** | +¥149,573.94 |
| Final Equity | **null** | null |
| certified sessions | **9/24** | 9/24 |
| valid mark minutes | **3,233/7,800** | 3,232/7,800 |
| valid-only utilization | 63.93% | 70.33% |
| ≥80% valid-time share | 39.38% | 66.40% |
| ≥5% funded / available | **23/143 = 16.08%** | 12/143 = 8.39% |
| ≥10% funded | **13** | 8 |
| Replacement N / ≥5 | 67 / 14 | 2 / 1 |
| Replacement upside median | 2.2079% | 7.7391% |
| top-session notional share | 15.19% | 13.07% |

R1はOpportunity reachを増やしたが、closed PnLは悪化し、`2025-08-04|36700|602` の未解決auction/markによりfull-periodはnull。

## 🧪 0.20pp stress

| Arm / Policy | certified days | closed PnL | Final Equity |
|---|---:|---:|---:|
| IM R54 Full | **1/24** | +¥5,964.81 | **null** |
| IM Control | 24/24 | −¥144,828.40 | ¥855,171.60 |
| R1 R54 Full | **9/24** | −¥60,682.91 | **null** |
| R1 Control | 9/24 | +¥135,290.70 | **null** |

Frozen stress GateはFAIL。

## 📊 Month-2x North Star

ArkのNorth Starは一般市場の「普通」ではなく、Ark自身のOpportunity Evidenceを基準にする。

目標:
**1か月でPortfolio約2倍 — ¥1,000,000 → ¥2,000,000**
24 sessionsなら必要な幾何平均日次returnは約 **+2.93%/日**。

R54では24日Final Equity / geometric daily returnがnullのため、このNorth Starとの差を正当には計算できない。
closed-only PnLやcashを代わりに使わない。

ただし、North Starが測定不能であることとは別に、
- D予測skill FAIL
- >=5% Winner保持 FAIL
- >=10% Winner保持 FAIL
- >=5% reach FAIL
が測定済み。

したがって、欠測だけを埋めればR54が採用になる状態ではない。

## 🧩 何が分かったか

R54のfailure anatomyは4点。

1. **D forecastにincremental skillがない。**  
   Controllerが使うh1/5/15でD=0より悪い。

2. **設計した長期graceが発火しなかった。**  
   MH_WAIT5とMH_WAIT15が完全に同一挙動になった。

3. **Loser / 3–5%改善と引き換えに大Winnerを早売りした。**  
   全79の同数量PnLは改善したが、>=5/10%の利益を大きく毀損。Arkの目的には不足。

4. **Capitalの全期間測定も既知のauction/mark不足で止まった。**  
   IMは1/24、R1は9/24しか連続EOD認証できない。nullを赤字にも0にも変換しない。

## ✅ Frozen Gate disposition

PASS:
- Integrity
- IM 3–5% Mean Net >= 0
- IM <1% floor
- Replacement support + >=5件
- Replacement upside median

FAIL:
- D forecast skill
- >=5% Winner Mean Net
- >=5% Winner currency PnL
- >=10% Winner Mean Net
- >=5% reach
- IM top-session concentration
- IM 24/24 EOD
- positive Final Equity and above control
- EOD MaxDD full-period certification
- 0.20pp stress

**Final: R54_CYCLE2_CLOSED_NO_SELECTION_MEASUREMENT_BLOCKED**

## 🔒 Safety / Exposure

- real fits: 176, 追加0
- integrated Replays: 44, 追加0
- provider新規取得: 0
- Protected/Fresh/OOS新規開封: 0
- main merge: 0
- executionAllowed=false
- brokerWriteAllowed=false
- excelOrderWriteAllowed=false
- rssOrderFunctionAllowed=false
- liveTradingAllowed=false
- paperTradingAllowed=false
- automaticPromotionAllowed=false
- productionUpdateAllowed=false
- transmitted=false

## ▶ 次の境界

このR54 cycle内で、
- 閾値を緩める
- WAIT値を追加する
- P/S ablationをbest-of-failingで採用する
- Capitalを結果後に変更する
- Protected/Fresh/OOSへ逃げる

ことは禁止。

R54から次へ進む場合は、**このfailure anatomyを入力にした新しいpre-performance EXIT architecture cycle**として開始する。
新cycleはR54のGateを遡って書き換えず、今回の「D skill不足 / grace不発 / Winner早売り / measurement不足」を明示的に解く問いをperformance前に固定する。

R54 Cycle2そのものはここで完了。
