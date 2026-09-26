# Phase57 — State v2 Design Gate 残り3診断 R1〜R3

記録日時: **2026-09-21 22:41 JST**
入力: 保存済みG measurementのみ。
State Definition変更0 / threshold探索0 / PnL・future return使用0 / provider request 0 / protected data 0。

## R1 — B固定Horizon H=10 active minutes

対象は `latest5 COMPLETE && scale AVAILABLE && pivotN<4 && Structure UNIDENTIFIED` の11,326 checkpoint。
H=10は採用mechanical-v1の既存 `ORACLE_HORIZON=10` をそのまま流用。

- RESOLVED_WITHIN_H: **998**
- NOT_RESOLVED_WITHIN_H: **4,735**
- OBSERVATION_CENSORED_BEFORE_H: **4,750**
- SESSION_CENSORED_BEFORE_H: **843**
- Hを完全評価できた行: **5,733**
- evaluable内10分以内Structure成立: **998/5,733 = 17.41%**
- 全B行を分母: **8.81%**

pivot別（censor除外のevaluable分母）:
- pivot0: **10.07%**
- pivot1: **10.29%**
- pivot2: **18.03%**
- pivot3: **41.21%**

絶対density bin別のevaluable成立率:
- D0 [0,.50): 15.91%（n=44で小さい）
- D1 [.50,.80): 17.18%
- D2 [.80,.95): 14.24%
- D3 [.95,1.00]: 19.42%

旧same-session終端までの39.37%より固定Horizonでは低い。旧Q1 18.11% vs Q4 69.08%の差も固定Horizon+censor分離後は小さく、同日残存時間・pivot数・観測欠測の交絡が大きかった。因果効果の主張ではない。

**Disposition:** pivot<4をPRE_STRUCTURE/FORMINGへ昇格しない。v2案は `INSUFFICIENT_PIVOTS(k)` を維持。

## R2 — fixed-seed 36 chart rubric review

既存36 checkpoints / 36 Opportunities / 29 sessionsを再samplingせず、9 pivotSignature ×4を単一reviewerで確認。
PnL/future return非表示。actual 1m / pivots / fixed S / as-of latest30 window / gap表示を使用。

重複可rubric:
- EXISTING_AXES_SUFFICIENT: **36/36**
- DATA_OR_OBSERVATION_ARTIFACT_SUSPECTED: **1/36**（chart 16にoverlay）
- BOUNDARY_OR_TOLERANCE_SUSPECTED: **0**
- VOCABULARY_GAP_CANDIDATE: **0**
- INDETERMINATE: **0**

このsampleでは新Structure名を要求する明確な例は見つからなかった。ただし単一reviewerの定性的監査であり、全母集団のsemantic correctnessを証明しない。Completion Gate G7のv2 freeze時2者独立reviewは未実施。

## R3 — Observation multi-flag cross-tab

77,214 checkpointすべてに重複可能flagを生成。

主要flag:
- current bar未観測: **30,986**
- latest5不完全: **48,740**
- Scale AVAILABLE以外: **37,932**

重複:
- current bar未観測 ∩ latest5不完全: **30,986**
- current bar未観測 ∩ Scale unavailable: **23,116**
- latest5不完全 ∩ Scale unavailable: **31,747**
- 3つすべて: **23,116**

代表combination:
- latest5 complete + Scale AVAILABLE: **22,289**
- current bar未観測 + latest5不完全 + SCALE_INSUFFICIENT: **22,679**
- current観測 + latest5不完全 + Scale AVAILABLE: **9,123**
- latest5 complete + SCALE_INSUFFICIENT: **5,116**

旧primary reasonは原因の排他分解ではなく順序依存表示だった。v2ではbarCoverage / density5/15/30/today / lastObservedAge / consecutiveMissingRun / Scale status / previous blockN / provenanceを同時保持する。
原因不明未観測は `NOT_OBSERVED_CAUSE_UNKNOWN` とし、no-trade/halt/provider lossを推測しない。

## Replay

R1/R3を固定入力で独立2回実行しhash一致。
- summary SHA256: `f9f1b03122db3bb66c0df19046c8c3ccfdb2d6ae7fcdc7b49de664c1822cd553`
- R1 CSV.GZ SHA256: `9a1a507b7231879883f57d49d2cb83c51c12a2c20df4a781b0d4b5b8a2aae9e2`
- R3 CSV.GZ SHA256: `d38658e348077f6bc1196012a0da2c5944cd11cadd9309c08639218773efa607`

会話添付 `phase57_state_v2_design_gate_20260921.zip` SHA256
`c26a3194226c9f9c4186e4bb71ee50c3067eb7353095539267e963e19572d5f2` に詳細CSV、rubric、report、replay producer、v2 design draftを保存。

## STOP境界

R1〜R3はState Definition v2設計Evidence。
State v2 implementation / 正確表v2 generation / Scale代替選定 / Causal Recognition / Signal / BUY-WAITは未開始。
