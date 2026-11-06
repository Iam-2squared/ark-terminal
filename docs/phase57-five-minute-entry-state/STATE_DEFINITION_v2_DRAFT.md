# Phase57 — 5-minute State Definition v2 DESIGN DRAFT

Status: **DESIGN_ONLY / NOT_IMPLEMENTED / NOT_GROUND_TRUTH_V2**

## 目的

Future-assisted 5分State正確表を作り直す前に、5分時点tで観測できるNOWと、未来で後から解決した事実を完全分離する。
Structureを必須にせず、各軸が未定義なら「なぜ」を機械的status/reasonで残す。
UNKNOWN率低下は成功条件にしない。

## Layer 0 — ObservationQuality

他軸と並列のStateではなく、各軸の評価可否を決めるメタ層。

必須field:
- currentBarObserved
- latest5ObservedK / latest5Complete
- density5 / density15 / density30 / densityToday
- lastObservedAgeActiveMinutes
- consecutiveMissingRun
- missingFlags[]
- evidenceSource
- causal=true

calendarで確定できない未観測原因は `NOT_OBSERVED_CAUSE_UNKNOWN`。no-trade/halt/provider lossを推測しない。

## ScaleSpec — State vocabulary外

v2.0:
`PREVIOUS_SESSION_COMPLETE_5M_TR_MEDIAN_V1`

mechanical-v1の現行Sを変更せずparameterize:
- actual previous session
- complete non-overlapping 5m blocks
- TR median
- minimum 6 blocks
- same raw price basis
- current day fixed
- fallbackなし

rowごとに scaleStatus / scaleValue / scaleSourceDay / previousComplete5mBlockN / scaleSpecId / provenance を保持。
代替Scaleはv2.0へ混在させず別version。

## 共通Axis Status

値とstatus/reasonを分離。

status enum:
- DEFINED
- INSUFFICIENT
- AMBIGUOUS
- NOT_APPLICABLE
- NOT_EVALUATED

reasonなしNULL/UNKNOWN = 0 をCompletion Gateにする。

## NOW axes

### Direction
latest five scheduled active 1mがcomplete:
- DEFINED(UP|DOWN|UNCHANGED)

不完全:
- NOT_EVALUATED(LATEST5_INCOMPLETE)

Scale不要。

### Structure
State全体の必須軸ではない。v2.0ではUP/DOWN/RANGE判定を結果に合わせて緩めない。

- active UP/DOWN/RANGE → DEFINED(value)
- current/必要観測不足 → NOT_EVALUATED(observation reason)
- Scale unavailable → NOT_EVALUATED(SCALE_UNAVAILABLE:<status>)
- active Structureなし + pivot<4 + Rangeなし → INSUFFICIENT(INSUFFICIENT_PIVOTS(k))
- pivot>=4だがactive Structureなし → NOT_APPLICABLE(NO_ACTIVE_STRUCTURE_UNDER_FIXED_RULES)

PRE_STRUCTURE / FORMING_UP / FORMING_DOWNは導入しない。

### Phase
bars<=t + Scale/pivots/recovery/restructuring factsのみ。
- phase setあり → DEFINED([phase...])
- 評価可能だがphaseなし → NOT_APPLICABLE(NO_ACTIVE_PHASE)
- Scale/観測不足 → NOT_EVALUATED(reason)

StructureとPhaseは別軸だがprimitiveを共有するため統計的独立とは呼ばない。

### pivotSignature
Structure classではないdescriptor。
pivot>=4でlatest two HIGH / LOWのexact relationを9-cell codeで保存。
pivot<4 → INSUFFICIENT(INSUFFICIENT_PIVOTS(k))
v2.0で新toleranceを導入せずEQはexact equality。

### Attributes
各familyに個別status/value/evidence:
- choppiness（Scale依存）
- range expansion/compression
- volume expansion/compression
- trading value expansion/compression

1 familyの評価不能で他familyを潰さない。

### Events
typed fixed-level events と moving VWAP relation events を別familyで保持。
各familyにstatus/reason/provenance。

### Context
D-5..D-1 Daily / previous observed session / Today Open→tを別objectで保持。
partial/missingを個別lag・primitiveで明示。

## Primitive dependency

| Axis | bars<=t | latest5 | Scale | pivots | previous day | levels | volume/value |
|---|---|---|---|---|---|---|---|
| ObservationQuality | yes | yes | no | no | optional | no | no |
| Direction | yes | complete | no | no | no | no | no |
| Structure | yes | current obs | yes | trendでyes | S経由 | no | no |
| Phase | yes | current obs | yes | yes | S経由 | no | no |
| pivotSignature | yes | no | yes | >=4 | S経由 | no | no |
| CHOP | yes | latest5 | yes | no | S経由 | no | no |
| range/volume/value attrs | yes | current+prior5 | CHOP以外は原則不要 | no | no | no | activityはyes |
| Level Events | yes | no | optional | optional | optional | yes | no |
| VWAP Events | yes | no | no | no | no | no | yes |

## Future Resolution — 別artifact

NOW schemaへFutureを入れない。
別artifact `future_resolution_v2` に固定Hと:
- RESOLVED_WITHIN_H(type, activeMinutes)
- NOT_RESOLVED_WITHIN_H
- SESSION_CENSORED_BEFORE_H
- OBSERVATION_CENSORED_BEFORE_H

を保存。

## Truncation invariance

全77,214 rowでbars<=tだけにtruncateしてNOWを再計算し、保存NOW rowと**100%一致必須**。
1件でも不一致なら正確表v2生成物は無効。

## v1→v2 transition

v1を上書きしない。
全rowでv1 key/value/status、v2 value/status、changeReasonCodes[]を保存。

期待する変更は新Stateへのforced assignmentではなく:
- Observation/Scale multi-flag
- status/reason明示
- StructureなしをINSUFFICIENT/NOT_APPLICABLEへ分離
- pivotSignature descriptor追加
- NOW/FUTURE分離強化

## Scale問題

SCALE_INSUFFICIENT 1,105 Opportunitiesの相対活性化偏りは確認済み。
ただしv2.0 vocabularyの結果に合わせてSを変えない。
代替ScaleはCausal Recognition前の別Gateで、候補/session split/基準を事前登録し、PnL/UNKNOWN率/Structure識別率で選ばない。

## Completion Gate

正本は `docs/evidence/phase57-state-v2-design-gate/PROTOCOL.md` のG1〜G8。
G1〜G3はhard invalidation。

## Disposition

- v2 implementation: NOT STARTED
- Ground Truth v2 generation: NOT STARTED
- Scale alternative selection: NOT STARTED
- Causal Recognition / Signal / BUY-WAIT: BLOCKED

次は本仕様案の人間/Claude設計レビュー。承認前に実装へ進まない。
