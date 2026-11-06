# Phase57 9-State Entry Audit — PROGRESS R6

2026-09-23 JST / PR #587 / branch `research/phase57-long-only-cash-equity`

## 今回の結論

REBOUND prefix-only blind semantic reviewを、sealed mapを開く前に34/34ケース完了・固定した。`REBOUND_BLIND_REVIEW_R1.csv` を commit `54b445127b0e0c1aa14479e79f1f0e9a7cba3aea` でappend-only保存済み。全ケース `chartInspected=YES`。

reviewはGitHub Actions run `35850371390` のmasked terminal chart + public `cases.json` prefix-only witnessだけを使用した。Future/Outcome/Fill/Oracle Low/High/MFE/MAE/Capture、Opportunity identity、sealed baseline Stateはreview固定前には開いていない。

## Prefix transport / CI

- witness+chart transport head: `d9a090fda673c898abdf4a6006646bf6cd122af0`
- run: `35850371390`
- job: `107146354502`
- conclusion: SUCCESS
- focused blind-packet tests: 3/3 PASS
- approved substrate hash check: PASS
- packet build: PASS
- identity/outcome leakage guard: PASS
- masked prefix witness log: PASS
- masked terminal chart log: PASS
- public packet artifact: `10745153728`, ZIP digest `816be397ce23d85f8f57094514e6815f643bbabf1d2e959a9c6ec8de1929a030`
- sealed map artifact: `10745366281`, ZIP digest `fea084ca27e0e7890eebc19437bb30504a90ad5ef43943938fd91f95d4bc6bce`
- public `cases.json` SHA256 remains `249aaeb58965207c32aafa56466aa87bd1e6bc99d0d4625f5b53f102f066c6bf`
- future/outcome sources opened by packet build: 0
- entry/fill sources opened by packet build: 0
- provider requests: 0
- protected data opened: 0

## Blind review fixed result — sealed map未照合

Reviewer State count:
- REBOUND: 24
- RISE: 10
- other 7 States: 0

これはsealed mappingとのaccuracy結果ではない。現時点ではreviewer judgementだけを固定した状態。

Visual annotation:
- CLEAR_REBOUND: 4
- CLEAR_RISE: 2
- WEAK_REBOUND: 14
- BOUNDARY_AMBIGUOUS: 5
- AMBIGUOUS_CHOPPY_RISE: 4
- AMBIGUOUS_SPIKE_RETRACE: 1
- AMBIGUOUS_REVERSAL: 1
- AMBIGUOUS_REBOUND: 1
- AMBIGUOUS_SPIKE_RISE: 1
- AMBIGUOUS_SPARSE_REBOUND: 1

Ambiguity reason annotation:
- DATA_QUALITY: 14
- WEAK_SHAPE: 8
- BOUNDARY_FLOAT: 5
- SMALL_PRIOR_MOVE: 4
- CHOPPY_PATH: 1
- NONE: 2

Packet quality witness:
- dataQuality=OK: 6
- dataQuality=DEGRADED: 28

Samplingはboundary/quality/time stress + fixed-seed general coverageを意図的に含むため、28/34 DEGRADEDや各visual比率を192件母集団の率へ外挿してはならない。

## 重要なblind finding

1. REBOUND候補には、prior down legに対するrecovery fractionが視覚的にかなり小さい `WEAK_REBOUND` が複数存在する。State名としての反発と「十分な反転確認」は同義ではない可能性がある。
2. `RBV1-013/014/026/027/033` は recovery ratio が実質1.0で、RISE/REBOUND equality境界をfloating-pointの極小差で跨ぐ `BOUNDARY_FLOAT` として固定した。これは将来Outcomeとは無関係なprefix-only implementation/contract境界の診断事項。
3. 一部RISE判定はprior down leg自体が小さく、recent/prior ratioが大きくなる `SMALL_PRIOR_MOVE` ケース。ratioが大きいこととfull-prefix chart全体が明瞭な上昇形状であることは必ずしも同義ではない。
4. 上記はまだEntry性能問題の証明ではない。Low/High anatomyやCaptureを見ていないため、現時点でT0 BUYを変更しない。

## sealed scoring

blind review固定後にだけsealed mapを開く専用workflow `.github/workflows/phase57-nine-state-rebound-score-v1.yml` を追加した。review fileのGit blob SHA `afb66ff0ee9dedc824f558e15d587da1f2390682`、34 rows、34 `chartInspected=YES` をassertしてからartifact `10745366281` を開き、identityを出力せずcaseId×baselineStateだけでscoreする。

- scoring workflow commit: `2188704faf42bb6a67e94a13dfbe3ee87727bd65`
- run: `35850842830`
- 本書作成時点: QUEUED
- 完走前なのでclassifier match/accuracyをまだ主張しない。

## REBOUND現在地

- T0 population: 192
- blind review: 34/34 DONE + FROZEN
- sealed mapping opened for scoring: pending dedicated score run
- classifier semantic score: pending
- Low/High Entry anatomy join: NOT STARTED
- performance hypothesis used: 0/1
- classifier change: 0
- Entry policy change: 0

## 次工程

1. run `35850842830` 完走を確認し、blind review vs sealed baseline Stateをscoreする。
2. exact implementation matchとvisual semantic ambiguityを分離して結論化する。34/34一致しても「視覚的に明瞭なStateが34/34」という意味にはしない。
3. その後、固定T0 REBOUND 192件に対して既存Evaluator-only future dataを結合し、N/Fill/Low→Entry/Entry→Later High/Position <=10/25/50/+3/+5 Capture/30m・60m MFE/MAEを集計する。
4. classifierの実装問題か、Contract意味問題か、T0即BUY Timing問題かを切り分けた後にだけREBOUNDの1仮説を検討する。

## 境界

Fresh/OOS/Common Holdout/REPORT19/Validation/Prospective開封0。provider新規取得0。EXIT/Capital/Portfolio/main merge/productionへ進んでいない。Entry policy/classifier/9 Pattern definitionは変更0。Safety/write/trading flagsは変更0。
