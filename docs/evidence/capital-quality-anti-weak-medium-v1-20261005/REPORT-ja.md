# Capital Quality Intelligence v1 — Final Report

作成: 2026-10-05T08:05:45.904184+09:00 / branch: `capital-quality-vnext-20261005`

**QUALITY_CONTRACT_FAIL。Q12で固定停止。**

固定base: `def427ab1b8fdf464e675d0c8f299059902ff028`。
Main Allocationのv8/v8R1研究内容は参照していない。

## A. Executive

| Head | Control | New fits | delta / CI | status |
|---|---|---:|---|---|
| MOVE_U2 | saved CORE_H2 p2 | 8 | 未実施 | CONTRACT_STOP |
| MOVE_U3 | saved CORE_H3 p3 | 8 | 未実施 | CONTRACT_STOP |

16 fitsは各1回で完了、ConvergenceWarningは0。Quality評価の開始時にQ4 baselineのhash不一致とJSON欠損を検出し、成功判定を停止した。Q5 claimがQ4 hashとの一致とJSON完全性を確認していなかったため、不完全なbaselineの現hashをclaimへ固定してしまった。元baselineを完全hashまで復元できず、救済はしていない。

## B. Fixed Budget Quality

共通supported OOF: 1,028件。母集団はWeak<2:596、Low2–<3:135、Medium3–<5:127、Big5–<10:103、Mega>=10:67。
Top20/30/40のselected構成・<2/<3・Medium・U5/U10・captureは**NOT_RUN_CONTRACT_STOP**。母集団件数を選択後の成果と扱わない。

## C. Anti-Weak

MOVE_U2の8 fitsを保存。WeakはU2 complement、別Weak modelは0。
A1–A7の成果判定は未実施、A8 integrityはFAIL。STRONG/PROMISING/有効性の主張は0。

## D. Medium+

MOVE_U3の8 fitsを保存。M1–M7の成果判定は未実施、M8 integrityはFAIL。
realized loser/positive teacher、追加teacher、別C・family・feature・thresholdは0。

## E. pP Conditional Incremental

pPは各supported test blockのoutcome-free equal-count decileへ固定済み。
新headのconditional discriminationとsession bootstrap deltaは未実施。追加情報ありという主張は0。

## F. Same-Session

新headのsame-session pairwise、same-session/decile conditional、bootstrapは未実施。
pairsを独立sample Nとして使用した解析は0。

## G. 5-Bucket Ordinal

上記5 bucketの件数とteacher整合性は監査済み。新headのmean/median percentile、Top20/30 density、NDCGは未実施。結果後blendは0。

## H. Big/Mega Guard

MOVE_U2/U3のTop30 U5/U10 capture診断は未実施。既存pPはそのままFreeze。BIG_WINNER_PRESERVINGという判定は行わない。

## I. Prior No-Repeat

GitHub metadata検索12語は該当0。固定baseの既存head/manifestを確認し、同一Movement U2/U3完成artifactを確認できなかったため最大16 fitsをclaimした。
CORE H2/H3/H5、pP/MOVE_P5、MOVE_R、HF1/HL0、LSAFE/Q1–Q8、PRR566の再fitは0。今回完了した16 fitsも再実行しない。

## J. Firewall / Integrity / Fits / Safety

独立監査はtrainer/evaluator/metrics import0、audit refit0。
labels/mask/split/preprocessing/係数・intercept保存snapshot/OOF再構成mismatch0。
最大float差: `1.6653345369377348e-16`、許容`1e-12`以下。
係数は独立optimizer再fitではなく、別保存したfitted-stateとの比較で検証した。

**baseline integrity root failure1、final mismatch1。mismatch0の最終監査PASSではない。**
Canary31項目: PASS29、FAIL1(hash)、NOT_RUN1(bootstrap)。全項目PASSという主張はしない。

v8研究read0、v8R1研究read0、Main B1/B2 outcome imported0、Quality途中結果のMainへの差し込み0。
Safetyは全false。orders/main merge/force push/provider/Claude/Capital replay/MAX3 replay/allocator変更/Fresh openはすべて0。

```text
selectedBigWinnerRank = EXISTING_MOVE_P5
selectedAuxiliaryHeads = []
qualityStatus = QUALITY_CONTRACT_FAIL
CapitalReplay = 0
MAX3Replay = 0
fresh_OOS_claim = false
productionReady = false
NEXT_POLICY = "Wait until independent Main Allocation Work is closed; integrate only in a new precommitted cycle."
```

Q12後のfit・model/teacher/gate変更・combined score・threshold・MAX3/Capital・Fresh・main merge・ordersは実行しない。
