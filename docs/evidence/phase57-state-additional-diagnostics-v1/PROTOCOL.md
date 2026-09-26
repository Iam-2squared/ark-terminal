# Phase57 — State Ground Truth Additional Diagnostics v1 Protocol

記録日時: **2026-09-21 20:08 JST**
開始HEAD: `e936b422e80288990f498f1a34c874b7e98aa669`
ユーザー承認: 「次進もう」

## Gateの目的

State Definition v2へ進む前に、Claudeのチャートレビューで残った5つの問いだけを、既存G measurementで追加診断する。
State Definition / threshold / Selector / Entry / EXIT / Capitalは変更しない。PnL・future return・保護データは使わない。

## 固定入力

- `docs/evidence/phase57-five-minute-reference-g-v1/measurement/`
- 2,155 Opportunities / 77,214 checkpoints
- adopted `five-minute-state-mechanical-v1`
- Deep Audit v1は比較用Evidenceのみ。今回の分類定義を後付けで変えない。
- 新規market provider request = 0
- Holdout / Fresh / OOS / Prospective = 未開封

## 診断1 — 真の未記述集合

対象はDeep Audit D:
`latest5 COMPLETE && scale AVAILABLE && pivotN>=4 && Structure UNIDENTIFIED`。

各行で以下を独立に確認:
- Direction
- Phase
- CHOPPINESS
- other Attributes
- typed Level event
- VWAP event

**strict residual** = 上記がすべて空。
Daily contextはこの判定に含めない。
「Phaseなし+CHOPなし」を真の未記述と同一視しない。

## 診断2 — 層別チャート再抽出

Dを `pivotSignature × timeBand × session` で層化。
timeBand:
- OPEN_0900_1000
- AM_1000_1130
- PM_EARLY_1230_1400
- PM_LATE_1400_CLOSE

同一Opportunityの連続checkpoint自己相関を抑えるため、**1 Opportunityにつき最大1 checkpoint**。
各pivotSignatureについて、可能な限り複数session/timeBandへ分散させる。
利益・return・Entry outcomeは抽出条件に使わない。

Deterministic seed string:
`phase57-state-additional-diagnostics-v1-seed-20260921`

候補順位:
`SHA256(seed + "|" + opportunity + "|" + asOf)` 昇順。
上限: 各pivotSignature 6例、全体54例以内。
出力図には:
- actual observed 1m OHLC
- confirmed pivots（effectiveAt / confirmedAt）
- fixed scale S
- checkpoint時点のlatest30 active-minute range window
- current checkpoint
を表示。
欠測区間は補完しない。

## 診断3 — B time-to-next-Structure

対象B:
`latest5 COMPLETE && scale AVAILABLE && pivotN<4 && Structure UNIDENTIFIED`。

同じOpportunity・同日・既存5分checkpoint列の中で、次にStructureが識別されるcheckpointまでのactive minutesを測る。
次がない場合はsame-session right-censored。

層:
- pivotN = 0 / 1 / 2 / 3
- observation density quartile

Observation densityはcheckpointまでの当日regular 1m実観測本数 / 同時点までに予定されるregular active minutes。
PnL・future returnは使わない。

報告:
resolved率、right-censored率、resolvedのみのmedian/P25/P75 time-to-next-Structure。

## 診断4 — SCALE_INSUFFICIENT vs AVAILABLE

Opportunity単位で比較。
結果に依存しない以下だけを使う:
- previous-day observed regular 1m count
- today observed regular 1m count
- selector時点までのtoday observed regular 1m count
- opening 30m trading value
- previous-day regular trading value
- opening30 value / previous-day regular value ratio（denominator>0のみ）
- opening30 trading value > previous full-day regular value の割合

`SCALE_INSUFFICIENT` と `AVAILABLE` を比較し、「前日薄い→今日活発」の系統性候補を記述する。
因果・provider欠損・selection biasを断定しない。

## 診断5 — pivotSignature 3×3実測

identified Structure行もD行も、pivotN>=4のlast-4 confirmed pivotsから
High relation {UP,EQ,DOWN} × Low relation {UP,EQ,DOWN}
の9セルを機械記録する。

- 新Structure名へ昇格しない。
- broadening/contracting等の意味ラベルを付けない。
- identified Structure別とUNIDENTIFIED D別の分布を報告。
- exact equalityだけをEQとし、新しいtoleranceを導入しない。

## STOP条件

診断1〜5の数値・chart・再現性を保存したらSTOP。
**State Definition v2 / State正確表v2 / Causal Recognition / Signal / BUY-WAITには進まない。**

Safety9 all false。
