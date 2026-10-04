# 🔧 Mechanics reuse scope

JST: 2026-10-04T12:05:56+09:00; basis: f65d3ed2bfe92e4a71285925f0fad23c8144eb40。

前回の12/16=75%は候補互換性のcomponent countで、コード行再利用率でも性能実証率でもない。今回はそのmechanicsをcurrent cash LONG contractへ適合させたが、完全Portfolio監査完了armは0/6。旧scorer/数値の直接採用は0。Python実装を旧JS implementationと同一コードとは主張しない。

| Component | This cycle | Boundary |
|---|---|---|
| causal queue / exit release before same-time entry | implemented + synthetic audit | cashはreference-backdateしない; observed prefixのsellイベント0 |
| deterministic causal score ordering | implemented | Frozen P1 score + identity tie-break |
| 100株floor | implemented / independent match | cash and all caps before rounding |
| cash vs MTM equity | implemented | exact missing funded markでBLOCK/null |
| cash LONG debit/credit | implemented | effective price内のfriction一回、commission0 |
| no symbol double-open | implemented / canary | same symbol current position guard |
| concurrent MAX-N | implemented / cap tests | N is NOT adaptive budget divisor |
| causal score weighting | implemented | new finite 0.5+s; old4feature合成なし |
| utilization / reserve mechanism | implemented | newly precommitted finite curve、旧valuesなし |
| candidate equity cap | implemented | newly precommitted .20+.20s、旧SABCcapなし |
| confirmed capital recycling | implemented + synthetic | actual prefixclose0、full recycling成績未測定 |
| append-only decisions/outcome allowlist | implemented | 9600 decision rows、future evidenceはevaluation bookのみ |
| old4 scorer features | NOT adopted | 同義field0; P1 scoreをprobability/confidenceへ読み替えない |
| old calibrated thresholds/weights/caps | NOT adopted | no direct parameter transfer or sweep |
| SHORT/collateral accounting | DISABLED | current LONG現物ONLY |
| old reported realized PnL | NOT adopted | legacy double-entry-fee reporting bug原本保持 |

