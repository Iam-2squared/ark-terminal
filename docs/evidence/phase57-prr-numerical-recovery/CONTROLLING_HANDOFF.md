# Phase57 PRR Numerical Recovery — CONTROLLING_HANDOFF

2026-09-29 JST。`research/phase57-long-only-cash-equity`、Draft PR #587。新cycleの機械可読Precommitは `CYCLE_PRECOMMIT.json`、SHA-256 `e57cd148f20b93633504994c67eeb28c4c97ac1f1334f54e7d10793e4442feb9`。直前PRRのPrecommitと `RANK_REPRODUCTION_FAIL` closureは変更していない。

## 結論

**NO_SELECTION**。新canonical環境のOOFとtrain-median AND routeは独立2 passで完全一致し、Rank SignalとRoute FeasibilityはPASSした。Primary funded 111のGateもPASSした。しかし全Entry standaloneでR1 WinnerとDefensive route valueが事前Hard GateをFAILしたため、Capital、0.20pp stress、24-session equityは実行しない。`adaptiveDevelopmentOnly=true`、`productionReady=false`。

| Gate | Result |
|---|---|
| Source lineage | PASS、frozen 566 features SHA `54bf771f6a090eb3e8035f7ee433ca1fbd617c165d77955ab71054b4e259a3fe` |
| Old OOF exact reproduction | FAIL、以前の1e-10 Gateは不変 |
| Canonical route stability | PASS、pass A/B byte identical、route不一致 0/1,614 |
| Rank Signal | PASS、両head、両arm、3 fold |
| Route support/direction/separation | PASS、4比較のsession bootstrap upper <0 |
| Primary Layer A | Measurement/Winner/Defensive Value/low-upside/overallすべてPASS |
| All-entry Winner | **ALL_ENTRY_WINNER_REGRESSION** |
| All-entry Defensive | **ALL_ENTRY_DEFENSIVE_VALUE_FAIL** |
| Integrated/Stress | NOT_RUN_INELIGIBLE、Replay 0/16 |
| Month-2x | ARK_MONTH_2X_UNMEASURABLE |

## 数値再現と環境

旧OOFを作ったpackage/BLAS/thread環境はimmutable evidenceから一意に特定できなかった。事前Case Bに従い、最初の診断環境を `CANONICAL_ENVIRONMENT_V2` として固定した。Linux x86_64、Python 3.12.14、numpy 2.3.5、scipy 1.18.1、scikit-learn 1.8.0、OpenBLAS single-thread。環境receipt SHA-256 `a4ec6736731e434a8b8f829f1254013364e4060cf8c59c7c3393ed2f2af7232d`。

fold 3の最初の>=5 mismatchはEntry `2025-07-22|14310|860`（R1）。saved probability `0.5539045764810699`、rerun `0.5538313748180916`、差 `0.0000732016629783061`、saved implied logit `0.2164595440789956`、rerun score `0.21616329889828756`。全1,614×2 headsのmismatch行を `MISMATCH_ROWS.jsonl.gz` に保存した。

| Old OOF comparison | >=5 | >=10 |
|---|---:|---:|
| N | 1,614 | 1,614 |
| 最大abs probability差 | 0.0012632426 | 0.0008606454 |
| 平均abs差 | 0.0000492860 | 0.0000029069 |
| AUC差（rerun−saved） | +0.0000025303 | 0 |
| fold内順位反転率 | 0.0000906658 | 0.0000192089 |

新canonicalの2 passはfold 3/4/5×2 headsの6 fitずつ。前段診断2 fitと合計**14/14 fit attempts**。preprocessing、係数、intercept、train/test score、train median、fold内順位、routeが一致した。新OOF SHA `ae460660a45ef9c20138a0cd2481a82f20f8192bbde5ecb6154ed8e01e5929f2`、route SHA `071ad1039edc886fa1d56084178ac57d8121e37d8a3a333e4621f6bb7a7845b8`。経済結果閲覧前にcommit `8dd25842384ca3c6ec0589181e8638ba3b775268`で固定した。

| Fold | >=5 TRAIN score median | >=10 TRAIN score median |
|---:|---:|---:|
| 3 | −4.412506639787202 | −8.917232926973014 |
| 4 | −3.383551659565806 | −8.361180653735431 |
| 5 | −3.006669990854336 | −7.431227466371281 |

## Rankと固定route

| Head | Canonical AUC | Session 95% CI | IM AUC | R1 AUC | Status |
|---|---:|---:|---:|---:|---|
| >=5 | 0.720353 | 0.675940–0.759413 | 0.701067 | 0.739972 | RANK_SIGNAL_PASS |
| >=10 | 0.692546 | 0.630440–0.748257 | 0.668880 | 0.716417 | RANK_SIGNAL_PASS |

以前のabsolute probability skillは両headとも **POTENTIAL_SKILL_FAIL** のまま。routeは各foldのTRAIN decision-score medianに対しstrict lowerを両headで満たす場合だけ `DEFENSIVE_ELIGIBLE → CCMG_GUARD_V1`。それ以外は `CONTROL_DEFAULT → R50_A_LIFECYCLE`。Entry後に変更しない。

| Arm | Defensive | Default | Defensive sessions | >=5 rate D / Default | >=10 rate D / Default |
|---|---:|---:|---:|---:|---:|
| IM | 276 | 543 | 24 | 9.06% / 24.49% | 3.62% / 10.31% |
| R1 | 336 | 459 | 24 | 6.85% / 26.14% | 2.38% / 11.33% |

4つの差のsession cluster bootstrap 95% CI upperは順にIM >=5 `−0.1020`、IM >=10 `−0.0369`、R1 >=5 `−0.1450`、R1 >=10 `−0.0585`。いずれも0未満。Decile、quadrant、各sessionは `RANK_ANATOMY.json` と図に保存。結果後のthreshold変更はない。

## 同一Entry経済性

PrimaryはIM 79、R1 32のR50 funded Entry・frozen quantity・R34 exact paired accounting。Nullは補完していない。

| Arm | N | Defensive | Known paired | PRR−Control aggregate JPY | Primary Gates |
|---|---:|---:|---:|---:|---|
| IM | 79 | 8 | 78 | +24,497.60215 | PASS |
| R1 | 32 | 8 | 30 | +14,896.14155 | PASS |

| Primary Winner | Cohort N | Defensive誤route N | Known paired | PRR−Control JPY | Gate |
|---|---:|---:|---:|---:|---|
| IM >=5 | 27 | 3 | 27 | +24,497.60215 | PASS |
| IM >=10 | 15 | 3 | 15 | +24,497.60215 | PASS |
| R1 >=5 | 12 | 1 | 12 | +97.00070 | PASS |
| R1 >=10 | 8 | 0 | 8 | 0 | PASS |

Primary Defensive subsetはIM 7/8 known pairedで+¥24,497.60215、R1 7/8で+¥14,896.14155。<5 cohortはIM 0、R1 +¥14,799.14085。Primaryの良好な結果だけで採用しない。

全EntryはIM 819、R1 795の**100株standalone**。Portfolio PnLではない。

| Arm | Defensive | Known paired | Overall delta JPY | <5 delta JPY | Defensive subset delta JPY |
|---|---:|---:|---:|---:|---:|
| IM | 276 | 789/819 | +65,467.25 | +27,186.40 | +65,467.25 |
| R1 | 336 | 767/795 | −13,193.40 | +48,075.95 | **−13,193.40** |

| All-entry Winner | Cohort N | Known paired | PRR−Control JPY | Hard Gate |
|---|---:|---:|---:|---|
| IM >=5 | 158 | 157 | +38,280.85 | PASS |
| IM >=10 | 66 | 66 | +25,387.30 | PASS |
| R1 >=5 | 143 | 143 | **−61,269.35** | FAIL |
| R1 >=10 | 60 | 60 | **−19,790.10** | FAIL |

R1の負のexact deltaはNによる免除なし。これで `ALL_ENTRY_WINNER_REGRESSION`、かつR1 Defensive subsetの負で `ALL_ENTRY_DEFENSIVE_VALUE_FAIL`。session別deltaは `ALL_ENTRY_RESULT.json`。IM全体のプラスには2025-08-22の+¥80,059.95が寄与し、R1は2025-08-08の−¥41,179.40と2025-08-21の−¥35,582.20などが悪化。ここからhard concentration thresholdを後付けしない。

## Capital、監査、安全

All-entry Hard Gateの時点でIntegrated eligibilityなし。Capital configs、0.20pp stress、2回のReplay再現性は実行0/16。Final Equity、MaxDD、¥2M gapはnullで `ARK_MONTH_2X_UNMEASURABLE`。closed PnLをFinal Equityへ代入しない。`CAPITAL_ELIGIBILITY.json` に停止理由を固定した。

独立script `scripts/phase57_prr_v2_independent_audit.py` は、新route 1,614件、6 model hashとtrain medians、Primary/全EntryのR34 paired算術、Defensive subset、<5を別計算して照合PASS。既存focused tests 30/30 PASS、diagnostic Actions `36496358294` SUCCESS、canonical Actions `36497047637` SUCCESS。図19点は `figures/`、各hashは `FIGURE_MANIFEST.json`。

Provider 0、Protected/Fresh/Validation/OOS/Prospective開封0、orders 0、main merge 0。9 safety flagsはすべてfalse。R54 D、WPSD、CCMG component、Selector、Entry、Capitalの変更はない。

**次の境界**：本固定architectureはNO_SELECTIONでClose。新routeやcomponentを試す場合は別Precommitが必要。この結果は前cycleのAUC閲覧後に設計したadaptive Development evidenceであり、独立検証・Protected/OOS承認・production承認ではない。
