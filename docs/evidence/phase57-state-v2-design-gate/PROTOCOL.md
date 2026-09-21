# Phase57 — State Definition v2 Design Gate / Completion Gate Precommit

記録日時: **2026-09-21 22:18 JST**
開始HEAD: `7bed00dc37a7d24b2af6a4abdc0e676437b012a8`
ユーザー承認: 「進めて」

## 目的

Future-assisted 5分State正確表をより正確・詳細に表現するため、State Definition v2の**設計**へ進む。
ただし、v2実装・正確表v2生成の前にCompletion Gateと残り診断を固定する。

本Gateで許可するのは:
1. Completion Gateの固定
2. Claude最終レビューで要求された残り3診断
3. そのEvidenceだけに基づくState Definition v2仕様案の設計

**v2 code実装 / 正確表v2生成 / Causal Recognition / Signal / BUY-WAITは開始しない。**

## 固定 Completion Gate

### G1 — 保存・母集団
- 2,155 Opportunities / 77,214 checkpointsを1:1保持。
- 重複key 0、削除0、Opportunity再filter 0。
- v1→v2 transition matrixと変更理由を全行で保存。

### G2 — 再現
- source SHA lock。
- 固定入力二重replayでbyte/hash一致。
- 実行時定義・ScaleSpec・schema hashを保存。

### G3 — NOW/FUTURE因果分離
- NOW schemaはbars <= tだけで再計算できること。
- **truncation invariance = 100%** を必須。
- NOW artifact/schemaにfuture/PnL/return outcome fieldを禁止。
- Future resolutionは別artifact / 別schema / 別hash。
- G1〜G3のどれか失敗なら生成物は無効。

### G4 — Status/Reason完全性
各軸は値とは別に共通statusを持つ:
- DEFINED
- INSUFFICIENT(reason)
- AMBIGUOUS(reason)
- NOT_APPLICABLE(reason)
- NOT_EVALUATED(reason)

reasonなしNULL/UNKNOWN = 0。
成功指標は「理由付き明示」であり、UNKNOWN率低下やStructure識別率をGateにしない。

### G5 — 非強制・v1保全
- v1 label/artifactを上書きしない。
- 同一入力・同一定義で保持すべきv1 fieldはdrift 0。
- v2で新規記述する場合、根拠primitive/evidence fieldを必須化。
- Opportunity削除やforced classificationは禁止。

### G6 — 層別報告
evaluable/defined/insufficient等を最低限:
- Observation density
- Scale status / ScaleSpec
- time band
- session
- pivot count
で報告。
単一UNKNOWN率をheadlineにしない。数値目標は置かない。

### G7 — Chart review
- fixed seed stratified sample。
- PnL/future return非表示。
- pivot / S / lookback / 30m rangeを重畳。
- as-of viewとfuture resolution viewを分離。
- Vocabulary追加候補は一文の機械定義があり、別session群でも再現するときだけ次版候補にする。
- v2生成後のfreeze前に2者独立reviewを要求する。

### G8 — Scale
- 各rowにversioned ScaleSpec ID / scaleSource / provenanceを保持。
- v2.0設計では現行previous-session Sを基準として明示し、代替Scaleを無断混在させない。
- Scale変更版は別tag/version。事前登録Scale protocolを通過した場合のみ採用候補。

## Freeze前の残り3診断

### R1 — B固定horizon再集計
対象:
`latest5 COMPLETE && scale AVAILABLE && pivotN<4 && Structure UNIDENTIFIED`

**固定H = 10 active minutes**。
理由: adopted mechanical-v1の既存 `ORACLE_HORIZON=10` を流用し、新しい自由パラメータを増やさない。

各B checkpointについて:
- RESOLVED_WITHIN_H(type, activeMinutes)
- NOT_RESOLVED_WITHIN_H
- SESSION_CENSORED_BEFORE_H
- OBSERVATION_CENSORED_BEFORE_H

を分離。

pivotN 0/1/2/3 × observation density絶対binでcross-tab:
- D0: [0, 0.50)
- D1: [0.50, 0.80)
- D2: [0.80, 0.95)
- D3: [0.95, 1.00]

density binは標本分位で作らない。

### R2 — 36 chart固定rubric review
既存fixed-seed 36 checkpoints / 36 Opportunities / 29 sessionsをそのまま使い、再samplingしない。

各chartを次の**重複可** rubricで判定:
1. EXISTING_AXES_SUFFICIENT
2. BOUNDARY_OR_TOLERANCE_SUSPECTED
3. DATA_OR_OBSERVATION_ARTIFACT_SUSPECTED
4. VOCABULARY_GAP_CANDIDATE
5. INDETERMINATE

必ず短い根拠を残す。
PnL/future returnは見ない。
pivot / fixed S / as-of latest30 active window / missing intervalを表示する。

### R3 — Observation multi-flag cross-tab
優先順位1reasonを廃止せず、**追加診断として重複flag**を保存する。

checkpoint-level:
- currentBarObserved
- latest5ObservedK / 5
- latest5Complete
- density5 / density15 / density30 / densityToday
- lastObservedAgeActiveMinutes
- consecutiveMissingRun
- scaleStatus
- previousComplete5mBlockN
- scaleSource / provenance

hard missing reasonを付けるのはcalendarで決まるSESSION_BOUNDARY/OUTSIDE_SESSION等のみ。
原因不明の未観測は `NOT_OBSERVED_CAUSE_UNKNOWN`。
no-trade / halt / provider lossを推測しない。

## State v2設計原則（診断前に固定する境界）

- Layer 0 = Observation Quality / evaluation eligibility。
- State軸 = Direction / Structure / Phase / Attributes / Events / Context。
- pivotSignatureはStructure classではなくdescriptor。
- StructureはState全体の必須軸ではない。
- pivotN<4は `INSUFFICIENT_PIVOTS(k)`。PRE_STRUCTURE / FORMING_UP/DOWNへ昇格させない。
- NOWとFuture resolutionを完全分離。
- ScaleはState vocabularyから分離したversioned ScaleSpec。
- PnL / Entry outcome / future returnで設計・選択しない。

## STOP

R1〜R3のEvidenceとState Definition v2**仕様案**を保存したらSTOP。
v2 implementation / 正確表v2 generationには進まない。

Safety9 all false。
