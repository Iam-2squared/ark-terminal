# V5 Anchor Slot3 R1 — 固定結果

V5を超えていない。D・DRともNO_EFFECT。

activeCapitalChampion=V5 / selectedResearchCandidate=null / selectedCapitalCandidate=null / championUpdated=false。状態: `V5_ANCHOR_NO_EFFECT`。

## 100万円 → 20 sessions

同じ連結38-session系列から切り出した19窓の正規化値。各窓を100万円・保有0へresetしたReplayではない。

|Profile|Min ¥|Mean ¥|Median ¥|Max ¥|2x|
|---|---:|---:|---:|---:|---:|
|V5|1,082,366|1,190,646|1,199,154|1,297,031|0/19|
|D|1,082,366|1,190,646|1,199,154|1,297,031|0/19|
|DR|1,082,366|1,190,646|1,199,154|1,297,031|0/19|

## Paired19 noninferiority

|Profile|better|equal|worse|最悪差 ¥|19/19|
|---|---:|---:|---:|---:|---|
|D|0|19|0|0|PASS|
|DR|0|19|0|0|PASS|

## Drawdown

|Profile|全38 minute-MTM MaxDD|各対応20-window MaxDD|
|---|---:|---|
|V5|10.225325%|基準|
|D|10.225325%|PASS|
|DR|10.225325%|PASS|

各窓の開始前EOD資産を初期peakとし、窓内の全有効minute-MTM点で再計算した。明細はPAIRED_WINDOW_MAXDD.json。

|20-session窓|V5 MaxDD|D MaxDD|DR MaxDD|
|---|---:|---:|---:|
|2025-06-27–2025-07-29|10.225325%|10.225325%|10.225325%|
|2025-06-30–2025-07-30|8.043720%|8.043720%|8.043720%|
|2025-07-01–2025-07-31|8.043720%|8.043720%|8.043720%|
|2025-07-02–2025-08-01|8.043720%|8.043720%|8.043720%|
|2025-07-03–2025-08-04|8.043720%|8.043720%|8.043720%|
|2025-07-04–2025-08-05|8.043720%|8.043720%|8.043720%|
|2025-07-07–2025-08-06|8.043720%|8.043720%|8.043720%|
|2025-07-08–2025-08-07|8.043720%|8.043720%|8.043720%|
|2025-07-09–2025-08-08|8.043720%|8.043720%|8.043720%|
|2025-07-10–2025-08-12|8.043720%|8.043720%|8.043720%|
|2025-07-15–2025-08-13|8.043720%|8.043720%|8.043720%|
|2025-07-16–2025-08-14|8.043720%|8.043720%|8.043720%|
|2025-07-17–2025-08-15|5.807349%|5.807349%|5.807349%|
|2025-07-18–2025-08-18|5.807349%|5.807349%|5.807349%|
|2025-07-22–2025-08-19|9.476170%|9.476170%|9.476170%|
|2025-07-23–2025-08-20|9.476170%|9.476170%|9.476170%|
|2025-07-24–2025-08-21|9.476170%|9.476170%|9.476170%|
|2025-07-25–2025-08-22|9.476170%|9.476170%|9.476170%|
|2025-07-28–2025-08-25|9.476170%|9.476170%|9.476170%|

## Quality

|Profile|N|Loser ≤0|Positive >0|Weak <2|<3|Medium 3–<5|U5|U10|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|V5|150|82|68|58|73|27|50|26|
|D|150|82|68|58|73|27|50|26|
|DR|150|82|68|58|73|27|50|26|

率の分母はfunded BUY unique identity N。Potential Weakと実現Loserは別指標。gross profit / gross loss / net / profit factor / 平均positive PnL / 平均strict negative PnL / 平均nonpositive PnLはLOSS_AMOUNT_AND_TAIL_DIAGNOSTICS.jsonにexact値を保存した。

|Profile|Loser率|strict negative|exact zero|gross loss ¥|negative sessions|worst daily return|
|---|---:|---:|---:|---:|---:|---:|
|V5|54.666667%|82|0|564,509|15|-6.445785%|
|D|54.666667%|82|0|564,509|15|-6.445785%|
|DR|54.666667%|82|0|564,509|15|-6.445785%|

## Slot1/2 protection

元V5の41+59=100 unique identitiesは評価後のみjoin。全identity fundedと元Slot1/Slot2各group aggregate actual PnL非劣化を要求する。個別identityの数量/PnL下限は追加しない。
- D: PASS
- DR: PASS

|Profile|元Slot|funded/required|V5 PnL ¥|candidate PnL ¥|差 ¥|
|---|---:|---:|---:|---:|---:|
|D|1|41/41|253,569|253,569|0|
|D|2|59/59|251,494|251,494|0|
|DR|1|41/41|253,569|253,569|0|
|DR|2|59/59|251,494|251,494|0|

## Slot3

実際に成功したcausal BUYだけをrecoveredとして数える。veto後のFrozen outcome joinは評価専用で、実際の回避損益とは呼ばない。未完走armの観測値はprefix diagnosticであり、公式全期間指標ではない。

|Profile|scope|native planned3|veto|veto Frozen loser/positive/unknown|rescued|rescued U5/U10/Medium/Weak|closed Slot3 PnL ¥|
|---|---|---:|---:|---|---:|---|---:|
|D|COMPLETE_ARM|50|0|0/0/0|0|0/0/0/0|-27,627|
|DR|COMPLETE_ARM|50|0|0/0/0|0|0/0/0/0|-27,627|

D token action counts: `{}`。terminal reasons: `{}`。


DR token action counts: `{}`。terminal reasons: `{}`。


## Winner miss

U5 rank-pass113/U10 rank-pass47のterminal reasonsをconservationする。

|Profile|Potential|分母|funded|Reserve|MAX3|cash/lot|D veto|other|conserved|
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
|V5|U5|113|50|30|28|5|0|0|True|
|V5|U10|47|26|10|9|2|0|0|True|
|D|U5|113|50|30|28|5|0|0|True|
|D|U10|47|26|10|9|2|0|0|True|
|DR|U5|113|50|30|28|5|0|0|True|
|DR|U10|47|26|10|9|2|0|0|True|

|Profile|relation|IDs|U5|U10|Medium|Weak|positive|Loser|
|---|---|---:|---:|---:|---:|---:|---:|---:|
|D|V5_ONLY|0|0|0|0|0|0|0|
|D|CANDIDATE_ONLY|0|0|0|0|0|0|0|
|DR|V5_ONLY|0|0|0|0|0|0|0|
|DR|CANDIDATE_ONLY|0|0|0|0|0|0|0|

D: COMMON=150、数量差あり=0、COMMON PnL差=¥0。全38session対称LOOは保存trade差分集中度診断で、削除後Replay/rolling20ではない。


D reason changes: `{"new_MAX3_miss": 0, "new_cash_miss": 0, "new_reserve_miss": 0, "reserve_recovery": 0}`（観測ledger join）。


DR: COMMON=150、数量差あり=0、COMMON PnL差=¥0。全38session対称LOOは保存trade差分集中度診断で、削除後Replay/rolling20ではない。


DR reason changes: `{"new_MAX3_miss": 0, "new_cash_miss": 0, "new_reserve_miss": 0, "reserve_recovery": 0}`（観測ledger join）。


## Intelligence

pP/U2/U3/MRETはcompleted-past referenceのstrict-less rank。exact rank=1/2はHIGH。未来outcomeは評価専用、結果後threshold調整0。

|Profile|cohort|head|N|min rank|mean rank|max rank|
|---|---|---|---:|---:|---:|---:|
|D|veto|—|0 observed|—|—|—|
|D|rescued|—|0 observed|—|—|—|
|DR|veto|—|0 observed|—|—|—|
|DR|rescued|—|0 observed|—|—|—|

## Independent audit

- D: PASS
- DR: PASS

|Gate|D|DR|
|---|---|---|
|E0|PASS|PASS|
|E1|PASS|PASS|
|E2|FAIL|FAIL|
|E3|FAIL|FAIL|
|E4|PASS|PASS|
|E5|PASS|PASS|
|E6|PASS|PASS|
|E7|PASS|PASS|
|Q1|PASS|PASS|
|Q2|PASS|PASS|
|Q3|PASS|PASS|
|Q4|PASS|PASS|
|Q5|PASS|PASS|
|Q6|FAIL|FAIL|
|Q7|PASS|PASS|
|Q8|PASS|PASS|
|Q9|PASS|PASS|
|Q10|PASS|PASS|
|Q11|PASS|PASS|

## Fixed STOP / next bottleneck

このcycle終了時もV5を保持。全E0–E7/Q1–Q11 PASSでも研究候補の提示まで。追加arm/fit/threshold retune/注文/main merge/Champion切替0。

Exposure=ITERATIVE_DEVELOPMENT_EVIDENCE。Fresh/OOS評価ではない。19窓は重複し、将来の非劣化・無損失・productionReadyを保証しない。

保存された終了理由:

- D/DRはV5と同じ全19窓・全minute-MTM DD・150 funded identities・数量・PnL。E1非劣化PASS、strict median E2/strict mean E3/strict Loser改善Q6はFAIL。V5を超えていない。
- 次bottleneck: native quantity>=100かつactual planned Slot3の50件全て4-axis intelligence available。個別LOW件数はrP=3、r2=7、r3=4、rM=35だが4LOW intersection=0。従ってveto0→token0→rescue0。これはcausal trigger診断で、未来PnL joinによる閾値選択ではない。
- このcycleのthreshold救済・D2/DR2・追加fit/replayは0。V5を保持しR12 CLOSURE_FIXED_STOP。
- Primary causal checks62 PASS、Independent A3 mandatory49+2=51 PASS。Independent ownloop D/DR各38 COMPLETE、action/token/quantity/money/MTM/postmain比較mismatch0、schema-only exact metrics各218 checks mismatch0。

実行回数: `{"controlVerificationReplays": 1, "DPrimaryReplays": 1, "DRPrimaryReplays": 1, "DIndependentReconstructionReplays": 1, "DRIndependentReconstructionReplays": 1, "candidatePrimaryReplays": 2, "independentReconstructionReplays": 2, "newFits": 0, "providerRequests": 0, "orders": 0, "mainMerge": 0, "forcePush": 0, "candidateExecutionClaimActualGET_HEAD": "4650212cb92234e3386d4ce9d0f37a9664a13de7", "precommitActualGET_HEAD": "6aaa325aa339f8f75083af47d0d0566621cd3118", "additionalReplaysForEvaluationOrReporting": 0}`。

## Secondary appendix

V5全38-session末EOD資産: ¥1,477,436。20-session Primaryとは別。
