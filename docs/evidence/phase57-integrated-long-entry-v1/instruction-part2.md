もちろん。**前回の** **`TARGET / OBSERVED`** **の続きから最後まで**です。そのままWorkに追加して。

```text
==================================================
■ 最終報告（続き）
==================================================

各主要metricについて:

TARGET
OBSERVED
GAP
STATUS

を明示する。

STATUSは:

PASS
NEAR_MISS
FAIL
HARD_FAIL

のいずれか。

ただし今回のSTATUSは
次の修正を自動許可するものではない。

NEAR_MISSでも
その場でthreshold / feature / model / routeを変更しない。

==================================================
■ PASS / NEAR_MISS / FAIL / HARD_FAIL
==================================================

今回の統合版は、
単純なbinary PASS/FAILだけでなく、
Gateからの距離も保存する。

ただし事前Targetそのものは変更しない。

例:

Target:
+3 preservation >= 90%

Observed:
91%
→ PASS

Observed:
87%
→ NEAR_MISS候補

Observed:
70%
→ FAIL

Observed:
20%
→ HARD_FAIL

のように、

「どれだけ離れていたか」

をEvidence化する。

正確なNEAR_MISS bandは
Validation結果を見る前にProtocolへ固定すること。

結果を見て
都合の良いbandを作らない。

==================================================
■ 重要：Near-Missでも今回は修正しない
==================================================

例えば:

+3 preservation = 87%
+5 preservation = 88%
Entry price improvement = +0.35pp
MAE p05 = 大幅改善

という結果でも、

「あと少しだからthresholdを動かす」

ことは禁止。

今回やるのは、

FIRST INTEGRATED MEASUREMENT

だけ。

Near-Miss原因分析も、
必要なら記述的に

- Immediate Winner loss
- Pullback Winner loss
- DIP weakness
- WAIT delay
- route imbalance
- missingness
- concentration

等を報告してよいが、

その原因に対する修正実装はしない。

==================================================
■ Integrated Entryの評価思想
==================================================

今回の統合Entryで最も重要なのは、

「何か一つの数字が良い」

ことではない。

以下を同時に見る。

A. Opportunity Preservation

Selectorが見つけた
大きなupsideを壊していないか。

B. Entry Location

Immediateより
良い価格位置で入れているか。

C. Risk

Entry後MAE / deep tailが
本当に改善しているか。

D. Remaining Upside

待った結果、
上昇余地を使い切っていないか。

E. Coverage

良いtradeだけ少数選んで
見かけの数字を作っていないか。

F. Economic

Candidate A接続後の
trade-level outcomeが改善しているか。

この6つをまとめて評価する。

==================================================
■ 特に重要なTrade-off
==================================================

v1〜v3で確認した以下のTrade-offを
必ず再確認する。

1.
待ちすぎる
→ Entry価格は改善
→ winnerを逃す

2.
すぐ入る
→ winner preservation
→ Entry Location改善なし

3.
Pullbackで入る
→ Entry価格 / MAE改善
→ Continued Failureにも頻出

4.
反転確認を待つ
→ Failure separation改善の可能性
→ Entry価格悪化 / remaining upside低下

Integrated Entryが
このTrade-offを本当に改善できたかを評価する。

==================================================
■ Route A — Immediateの評価
==================================================

Route Aについて:

- total count
- INITIAL / DIP
- Immediate Winner count
- Fast Winner count
- +3 winner
- +5 winner
- MAE
- remaining MFE
- economic result

を出す。

Route Aが多すぎて
Integrated Entryが実質Immediate Baselineに戻っていないか確認。

==================================================
■ Route B — Pullbackの評価
==================================================

Route Bについて:

- total count
- Pullback Winner
- Deep Pullback Winner
- Continued Failure
- Entry price improvement
- MAE improvement
- remaining MFE
- +3/+5 preservation
- economic result

を出す。

特に、

GOOD PULLBACKとBAD PULLBACKを
どの程度分離できたか

を記述する。

==================================================
■ Route C — WAITの評価
==================================================

Route Cについて:

- WAIT開始数
- eventual BUY
- eventual SKIP / EXPIRE
- mean WAIT
- median WAIT
- max WAIT
- Entry price improvement
- winner loss
- remaining MFE

を出す。

v1のWAIT過多、
v2のWAIT=0

の中間として
実際に意味のあるWAITが成立したか確認。

==================================================
■ Route D — SKIP / EXPIREの評価
==================================================

Route Dについて:

- count
- Continued Failure
- +1 winner missed
- +2 winner missed
- +3 winner missed
- +5 winner missed
- Immediate Winner missed
- Pullback Winner missed

を出す。

SKIPが
本当にfailure avoidanceとして働いたのか、

単にwinnerも大量に捨てたのかを確認。

==================================================
■ Route Balance
==================================================

Integrated Entryが
一つのRouteへ極端にcollapseしていないか確認。

例:

Route A 98%
Route B 1%
Route C 0%
Route D 1%

なら、

multi-route architectureとして
実質機能していない可能性がある。

逆にRoute比率を均等にする必要もない。

目的は
各Routeが意味のある役割を持っているか。

==================================================
■ INITIAL / DIP
==================================================

必ず別々に報告。

INITIAL:

- n
- Entry coverage
- route distribution
- +3/+5 preservation
- Entry price improvement
- MAE
- remaining MFE
- economic

DIP:

同じ指標。

Overallが良くても
片方が大幅崩壊している場合は明記。

結果を見て
INITIAL/DIP別thresholdを追加しない。

==================================================
■ Candidate Breadth
==================================================

Opportunity発行時の候補数:

1
2
3
4
5

別にも確認。

Integrated Entryが

4〜5 candidates時だけ
極端にSKIPする

等の挙動がないか見る。

ただしbreadth別ruleは追加しない。

==================================================
■ Missingness
==================================================

Integrated modelで使用するfeatureについて:

- coverage
- missing rate
- missing indicators
- route別missingness
- Entry / Skip別missingness

を確認。

missingnessそのものを
future outcome proxyとして
不当に利用していないか監査。

==================================================
■ Concentration
==================================================

最低限:

- unique symbols
- symbol HHI
- top-frequency symbols
- top3-frequency-symbol exclusion

を確認。

性能が特定少数銘柄に依存していないか見る。

top3除外後に再fitしない。

診断のみ。

==================================================
■ Chronological Stability
==================================================

Validation19 sessionsを
事前固定したchronological blocksへ分け、

最低限:

- Entry coverage
- +3 preservation
- +5 preservation
- Entry price improvement
- MAE
- economic delta

を見る。

結果を見て悪いblockを除外しない。

==================================================
■ Economic結果の注意
==================================================

Candidate A自体は
Development上でmean<0 / PF<1だったことを忘れない。

したがってIntegrated Entry接続後に

Candidate A比で改善

しても、

Portfolio profitability
実運用profitability

を意味しない。

今回のEconomic比較は、

Entry Timingを変えることで
同じFrozen EXIT下のtrade-level outcomeが
改善したか

を見るためだけ。

==================================================
■ 今回のDecision Record
==================================================

最終Decisionは

FREEZE
KILL

ではなく、

FIRST_INTEGRATED_MEASUREMENT_COMPLETE

とする。

その中に:

OVERALL_STATUS:
PASS
NEAR_MISS
FAIL
HARD_FAIL

を記録。

今回新EntryをFreezeしない。

たとえPASSでも
まずユーザーへ結果を報告してSTOP。

==================================================
■ PASSでもFreezeしない
==================================================

重要。

今回の目的は
統合版初回測定。

Validation PASSでも、

自動Freeze禁止。

DEV TEST未開封のため、

DEVELOPMENT_FROZEN

とは呼ばない。

状態例:

INTEGRATED_LONG_ENTRY_V1_VALIDATION_PASS_NOT_FROZEN

または

INTEGRATED_LONG_ENTRY_V1_VALIDATION_NEAR_MISS

等、

実測に合ったstatusを使用。

==================================================
■ FAILでも即廃棄しない
==================================================

FAIL / HARD_FAILでも
今回その場でCandidateを修正しない。

しかし、

どの部分が良く、
どの部分が悪かったか

を分解して保存する。

特に:

- Immediate route
- Pullback route
- WAIT route
- SKIP route

それぞれの寄与を保存。

次の判断材料にする。

==================================================
■ Validation Exposure
==================================================

今回Validation19 sessionsを
統合版v1へ使用した時点で、

その結果はexposedとなる。

その事実をmanifestへ記録。

今後このValidationを
Fresh扱いしない。

DEV TEST19は未開封維持。

Fresh/OOSも未開封。

==================================================
■ Reproducibility
==================================================

最低限固定:

- Protocol SHA
- Feature manifest SHA
- Training dataset identity
- TRAIN split
- Validation split
- model type
- model hyperparameters
- random seed
- scaler / preprocessing
- model digest
- decision contract
- route contract
- output ledger hash

同一sourceから
deterministicに再生成可能にする。

==================================================
■ GitHub
==================================================

すべて:

research/phase57-long-only-cash-equity

PR #587

上で行う。

main merge禁止。

Protocolは
Validation結果を見る前にcommit。

その後:

implementation
training
Validation
Evidence
tests
CI

を行う。

==================================================
■ Workの実行スタイル
==================================================

途中で、

「Protocol作りました。続けますか？」

のようにユーザー確認で止まらない。

今回許可された範囲:

Protocol
→ Integrated Dataset
→ Architecture
→ Training
→ Validation
→ Economic comparison
→ Robustness
→ Tests
→ CI
→ Evidence freeze
→ Final Report

まで連続して進める。

ただしValidation結果を見た
修正・再学習はしない。

==================================================
■ Completion Gate
==================================================

以下すべて完了したらSTOP:

1.
Integrated Entry v1 Protocol precommit

2.
PIT Integrated Dataset構築

3.
Integrated Candidate 1本をfit

4.
Validation19 sessionsで初回測定

5.
Immediate Baseline比較

6.
Opportunity Preservation

7.
Entry Location

8.
Risk / MAE

9.
Remaining MFE

10.
Route attribution

11.
Candidate A economic comparison

12.
Robustness diagnostics

13.
Integrity audit

14.
Tests / regression

15.
CI

16.
FIRST_INTEGRATED_MEASUREMENT_COMPLETE Evidence固定

17.
Final Report

その後STOP。

==================================================
■ 最終STOP後に勝手にやらないこと
==================================================

- Near-Miss修正
- threshold変更
- feature変更
- model変更
- route変更
- retrain
- v2 Candidate作成
- DEV TEST
- Fresh Validation
- OOS
- Capital
- Max3
- Portfolio
- EXIT再研究
- main merge
- paper/live

全部ユーザーの次の指示待ち。

==================================================
■ 最終命令
==================================================

これまでのEntry研究を
さらに細かく分割しない。

v1〜v3で得たEvidenceと
現在利用可能なPIT Contextを統合し、

Ark Terminal Phase57 LONG-onlyの

COMPREHENSIVE INTEGRATED LONG ENTRY v1

を一本作る。

Immediate Winner
Pullback Winner
Good / Bad Pullback
Stabilization
Reclaim
Momentum
Trend
Volatility
Volume / Liquidity
Selector / Opportunity
Market / Relative Context
Time / Breadth

等、

PITで利用可能な情報を統合して、

BUY NOW
PULLBACK ENTRY
SHORT WAIT
SKIP / EXPIRE

を総合判断する。

ただしfuture informationは禁止。

今回の目的は
一発で完成品を宣言することではない。

まず、

「今までの研究を全部統合した本命Entryを
何も後付け修正せず測ると、
実際どこまで性能が出るのか」

を確認すること。

Validation結果が
PASSでも
NEAR_MISSでも
FAILでも
HARD_FAILでも、

その場で修正しない。

素の結果をEvidenceとして固定。

DEV TEST / Fresh/OOSは開かない。

Selector / Opportunity Generator /
Candidate A / Capitalは変更しない。

Safety全false維持。

最後にexact HEAD SHAと全結果を報告し、
FIRST_INTEGRATED_MEASUREMENT_COMPLETE
としてSTOP。
```