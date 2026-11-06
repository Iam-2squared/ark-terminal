# Ark Terminal Phase57 — EXIT Path Anatomy 有限診断結果

**判定: `PATH_ANATOMY_INCOMPLETE_MAIN_INVALID`。利益PASS、正式EXIT選定、productionReadyではない。**

保存日時・source hash・実行量は `START_AUDIT.json`、`SOURCE_MANIFEST.json`、`RUN_INVALID_POSTPROCESS.json`、`EXPOSURE_CORRECTION.json` を参照。Basis HEAD `9a0b6749b8e1835fb553c0a593a88c7044ff9648`。母集団はIM 819、R1 795、funded内数はIM 79、R1 32。24 sessions。これらは保存済み契約の件数で、新しいPath結果ではない。

## A. Entry Opportunity

| arm/world | all N | known path N | UNKNOWN | Entry→High mean | median | ≥1 | ≥2 | ≥3 | ≥5 | ≥10 |
|---|---:|---|---|---|---|---|---|---|---|---|
| IM / ALL | 819 | 未保存 | 未算定 | 未算定 | 未算定 | 未算定 | 未算定 | 未算定 | 未算定 | 未算定 |
| IM / funded（ALLの内数） | 79 | 未保存 | 未算定 | 未算定 | 未算定 | 未算定 | 未算定 | 未算定 | 未算定 | 未算定 |
| R1 / ALL | 795 | 未保存 | 未算定 | 未算定 | 未算定 | 未算定 | 未算定 | 未算定 | 未算定 | 未算定 |
| R1 / funded（ALLの内数） | 32 | 未保存 | 未算定 | 未算定 | 未算定 | 未算定 | 未算定 | 未算定 | 未算定 | 未算定 |

## B. Initial Weakness

−0.5／−1到達後のlater +1/+2/+3/+5/+10復活件数は未算定。0件とは解釈しない。

## C. Winner Pullback

+1/+2/+3/+5/+7 milestone後のgiveback、minimum return、later higher milestone件数と分位点は未保存。

## D. Operator Floor仮説

`+1→0`、`+2→+1.5`、`+3→+2.5` のWinner前crossは未算定。採用・最適化なし。

## E. Path State

Raw closed 1m OHLCから記述可能なprimitiveを事前指定したが、回復群と非回復群の集計は未保存。既存State/Signalのexact snapshotとknownAtは利用可能と認定していない。`STATE_INCREMENT_NOT_DEMONSTRATED` は本cycleの実証不足であり、State一般の無価値を意味しない。

## F. Data / execution blockers

- Main後処理失敗でPath-known / price-known / UNKNOWN N、6図、independent照合が存在しない。空グラフ・推測値は生成していない。
- 元データのhistorical bar-endはpublication knownAtの証明ではない。missing 1mのNO_TRADE / HALT / data missingは未分離。
- Floor crossは約定や利益を意味しない。正確な次OPEN欠測、R1 auction等の前cycle blockerも維持。
- Raw schema probeのallowlist外decodeをExposureへ記録。別封印partitionの新規ファイル閲覧なし。

## 実行枠・停止

Path Anatomy主計算1（INVALID）、独立再計算0。new estimator fit / calibration / new policy Replay / integrated Capital Replay / new EXIT candidate implementation / threshold optimization / provider / orders / main merge = 0。次の数値計算には新しい有限仕様・承認が必要。`RECOVERY_SPEC_DRAFT.md` は未承認。
