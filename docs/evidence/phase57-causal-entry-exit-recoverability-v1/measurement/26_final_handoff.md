# Final handoff — STOP

# Frozen Selector → Causal Entry / EXIT Recoverability

**Final Decision: F_INCONCLUSIVE**

既存76 Developmentのみ。FIT38 (2024-09-17〜11-12)、QUALIFY19 (11-13〜12-09)、REPORT19 (12-10〜2025-01-09)。すでに結果露出済みでSelectorの過去fitも含むため、独立した未知性能ではない。
PIT入力は確定済みOHLCと固定スコア/順位。15/20/25分の状態から次OPEN参照。全日Low/High・future MFE/MAE・winnerラベルはdecisionに渡さない。出来高/RVOL/VWAPは未保存で不使用。
各1仕様のridge、alpha1、予測値>0だけ。資格判定後の再fit/threshold/horizon選び直しはなし。判断後OPENとcanonical5bpsは比較用referenceで、実約定・spread/impact込み利益を保証しない。

| diagnostic | phase | states | sessions | economic target rankIC | simultaneous CI | separation gate |
|---|---|---:|---:|---:|---|---|
| Entry | QUALIFY | 1487 | 19 | 0.1040 | [0.02591518540974312, 0.17538080559458313] | True |
| Entry | REPORT | 1454 | 19 | 0.1363 | [0.08791978700526155, 0.18216948361145033] | True |
| EXIT | QUALIFY | 1487 | 19 | 0.0981 | [0.020679486985796025, 0.16824546728028578] | True |
| EXIT | REPORT | 1454 | 19 | 0.1361 | [0.08564434565570297, 0.18311725517349156] | True |

REPORTの分離診断が良くても、QUALIFYで失敗した候補を復活させない。

Entry候補: False。EXIT候補: False。候補がない場合はNOT_APPLICABLE理由を保存。

| comparison | phase | paired opportunities | sessions | candidate mean net/trade % | baseline mean net/trade % | opportunity paired delta pp | simultaneous CI |
|---|---|---:|---:|---:|---:|---:|---|
| Entry | QUALIFY | 491 | 19 | 0.1123 | 0.1019 | 0.1640 | [-0.08758173545801841, 0.5901556308472153] |
| EXIT | QUALIFY | 491 | 19 | 0.1053 | 0.1019 | 0.0139 | [-0.14006077282348994, 0.16683806444489754] |

Entry qualification gate: {"pass": false, "checks": {"sampleSessions": true, "samplePaired": true, "enteredTrades": true, "coverage": true, "pairedEconomicDelta": false, "p05NotWorse": true, "absoluteNetPositive": false, "PF": true}, "status": "ECONOMIC_GATE_NOT_PASSED"}
EXIT qualification gate: {"pass": false, "checks": {"sampleSessions": true, "samplePaired": true, "enteredTrades": true, "coverage": true, "pairedEconomicDelta": false, "p05NotWorse": true, "PFNotWorse": true}, "status": "ECONOMIC_GATE_NOT_PASSED"}

REPORT Immediate baseline: 482 entered / 482 common observed / 950 original opportunities。mean net 0.0713%、median -0.0500%、PF 1.0863。

Primaryは同じselection+30終点、原IDペア、完全0〜30経路に条件付けた比較。データ欠測はnull、PIT判断による意図的ABSTAINだけopportunity return0。約定tradeと全opportunity分母を別保存。欠測による全原母集団の収益は未同定。

Four-cell: NOT_APPLICABLE。両候補がQUALIFY Gateを通過していないため統合候補を捏造しない。

既存Frozen EXIT(+3/+1)は未変更の関数で、元のFixed12/カレンダーcapと別比較。n=379、Fixed12 mean 0.1205% → Frozen EXIT 0.1454%。これはprimary30モデル候補の成績ではない。

## 解釈と次工程

今回の固定仕様では、採用できる因果的な利益改善を確認できなかった。oracleの値幅の存在から、その底/天井をPIT識別できるとは結論しない。
失敗は「あらゆるEntry/EXITが不可能」や「Selector再設計が必ず有効」を意味しない。時系列分割でも既知Development、欠測、繰り返し銘柄、実約定可能性は未解決。CIはsession単位、5-session block感度・tail・集中度も保存。
Review the failed/passing gate and PIT-observability report to decide one next Development protocol; no automatic extra search, sealed-data opening or promotion.

17〜19番はsession・symbol・cluster、21〜23番はtests/regression/CI。Safety9項目false、DEV TEST/Fresh/OOS sealed、新規provider0。Selector/Capital未変更、既存Frozen Entry/EXIT未変更、候補の正式freeze/promotionなし、main mergeなし。ここでSTOP。


Protocol precommit: `afb32cb7f17d8f9abdfe516e156ba0bf9c677ed5`. Producing HEAD / CI recorded in23_ci.json. No next research task, protected-data opening or candidate freeze/promotion was executed.
