これをそのままWorkに送って。今回は構造を明確に\*\*`Raw ¥75 Selector Stream → Actual Entry → EXIT`\*\*へ戻す指示です。

```text
Ark Terminal Phase57 — LONG-only
RAW SELECTOR STREAM → ACTUAL LONG ENTRY
Architecture Reset / Direct Entry Research

Date: 2026-09-19 JST
Repo: Iam-2squared/ark-terminal
Branch: research/phase57-long-only-cash-equity
PR: #587

==================================================
■ 最重要：Entry Architectureを整理し直す
==================================================

これまでのEntry研究で、
Frozen NEW Entry v1 / Opportunity Generatorの役割が
Actual Entryと混同されていた。

今後の本命構造を以下へ整理する。

JPX
↓
FROZEN_LONG_SELECTOR_WITH_MIN_PRICE_75
↓
RAW 5-MIN SELECTOR STREAM
↓
ACTUAL LONG ENTRY INTELLIGENCE
↓
Position
↓
LONG EXIT
↓
Capital / Portfolio

役割:

Selector
= WHAT TO BUY

Actual Entry
= WHEN / WHERE TO BUY

EXIT
= WHEN TO SELL

今回研究するのは
Raw Selector Stream → Actual Entry
のみ。

==================================================
■ 開始時
==================================================

必ずGitHub Repo / PR #587 latest stateを直接確認。

直近確認HEAD:
727277a2e726805ee58c4a21603ee7604ed2cefc

ただし決め打ち禁止。
GitHub latest stateを正とする。

確認:

- PR #587 Open / Draft / unmerged
- FROZEN_LONG_SELECTOR_WITH_MIN_PRICE_75
- Selector raw ledger
- Selector Decision Price semantics
- Selector score / rank
- Frozen NEW Entry v1
- Comprehensive Entry v1/v2/v3
- Integrated Entry v1
- Candidate A EXIT
- Development split
- Safety
- Fresh/OOS未開封

既存Evidenceを削除・上書きしない。

==================================================
■ Selectorは絶対変更しない
==================================================

FROZEN_LONG_SELECTOR_WITH_MIN_PRICE_75
は今回完全固定。

禁止:

- retrain
- feature変更
- target変更
- Ridge変更
- score変更
- rank変更
- Top-K変更
- ¥75変更
- Decision Price semantics変更

今回Selector性能を改善する研究ではない。

==================================================
■ Raw Selector Streamの現在Evidence
==================================================

既存Evidenceでは:

76 Development sessions
760 Frozen Selector decision timestamps

Selectorが選択した銘柄数 / decision:

mean = 3.7382
median = 4
max = 5

分布:

0 = 1 timestamp
1 = 17
2 = 99
3 = 180
4 = 229
5 = 234

つまりSelectorは
5分decisionごとに
概ね3〜5銘柄を既に選定している。

このRaw Selector Outputを
新Actual Entryの直接入力母集団とする。

==================================================
■ Frozen NEW Entry v1の扱い
==================================================

既存Frozen NEW Entry v1は削除しない。

既存Evidence / historical baselineとして完全保持。

そのcontract:

INITIAL_ENTRY_OPPORTUNITY

および、

最初のcompleted 5m CLOSEが
Selector Decision Priceを下回った場合の

DIP_REPRICE_OPPORTUNITY

を発行する。

ただし今回、

Frozen NEW Entry v1を
新Actual Entryの必須前処理にはしない。

つまり:

Raw Selector
→ Frozen NEW Entry
→ Actual Entry

を前提にしない。

今回の本命は直接:

Raw Selector
→ Actual Entry

とする。

==================================================
■ 重要：過去研究を無効化しない
==================================================

Frozen NEW Entry v1
Comprehensive Entry v1
Comprehensive Entry v2
Comprehensive Entry v3
Integrated Entry v1

のEvidenceはすべて保存。

過去研究が間違いだったと書き換えない。

ただしそれらは主に
INITIAL / DIP Opportunityを起点としたEntry研究だった。

今回は研究母集団 / architectureを変更し、

Selector raw streamを直接利用する。

別lineageとして扱う。

==================================================
■ 今回の核心
==================================================

Selectorがある銘柄を09:30に選択し、

09:35
09:40
09:45
09:50

でも選択し続けるなら、

Entry AIはその連続状態を直接観測できるようにする。

例:

09:30 rank 2 / score X / price 100
09:35 rank 3 / score X2 / price 98
09:40 rank 1 / score X3 / price 96
09:45 rank 1 / score X4 / price 97

このsequence全体をEntry判断に利用可能にする。

INITIAL / DIPという2 eventへ
先に圧縮しない。

==================================================
■ Actual Entryの目的
==================================================

Selectorが既に選んだ銘柄について、

BUY NOW

または

WATCH

を判断する。

必要なら明確なinvalid stateのみ
DROP / EXPIRE可能。

ただし主目的は
銘柄をさらに大量に絞ることではない。

主目的:

より良いEntry Timing / Location。

==================================================
■ Preservation-first
==================================================

これまでのEntry研究では、

Entry Locationを改善しようとすると
winnerを大量に失う問題が繰り返された。

そのため今回は、

Selector Opportunity Preservation

を最優先する。

基本思想:

Selectorで選ばれた銘柄は
原則としてEntry候補として保持。

Actual Entryは、

「買うか捨てるか」

より、

「今買うか、短く待ってより良い場所で買うか」

を中心に判断する。

==================================================
■ Raw Selector Episode
==================================================

symbol-session単位で
Selector streamをepisode化する。

最低限記録:

- first selected timestamp
- last selected timestamp
- consecutive selection count
- selection gaps
- current rank
- rank history
- current score
- score history
- Decision Price
- price path while selected
- elapsed time since first selection
- selected / dropped / reselected state

同一symbolが複数timestampでTop5になることを
独立tradeとして乱数的に重複計上しない。

Episode semanticsを測定前に固定する。

==================================================
■ Reselection
==================================================

Selectorから一度外れ、
後に再度Top5へ入った場合の扱いを
事前Contractする。

結果を見て都合よくepisodeを分割しない。

最低限:

continuous episode
reselection episode

を区別可能にする。

==================================================
■ PIT Context
==================================================

各5分decision時点で利用可能な
PIT Contextを使用。

既存feature inventoryを最大限再利用。

最低限family:

1 Selector state
- score
- rank
- score change
- rank change
- persistence
- reselection
- candidate breadth

2 Price
- current price
- return from first selection
- recent momentum
- acceleration
- recent high/low distance
- range location

3 Pullback / Path
- drawdown from selection
- pullback depth
- pullback duration
- adverse acceleration/deceleration
- bounce
- failed bounce
- path efficiency

4 Trend / Reversal
- HH/HL/LH/LL
- higher low
- higher close
- reclaim
- reversal
- continuation

5 VWAP / Range
PITで既存利用可能なもの。

6 Volatility
- realized volatility
- range
- normalized displacement
- expansion/contraction

7 Volume / Liquidity
既存PITで利用可能なもの。

8 Market / Relative
既存PIT sourceが存在するものだけ。

9 Time
- minutes since open
- elapsed since first selection
- number of Selector decisions observed

==================================================
■ Future情報禁止
==================================================

runtime Entry featureへ絶対に入れない:

- future HIGH
- future LOW
- future CLOSE
- future MFE
- future MAE
- terminal return
- future +1/+2/+3/+5
- future Selector state
- future rank
- future score

これらはEvaluatorのみ。

==================================================
■ Entry Decision
==================================================

まずシンプルに:

BUY_NOW
WATCH

を中心にする。

DROP / EXPIREは:

- Selector episode終了
- session boundary
- missing critical data
- precommitted invalidation

等に限定する方向を優先。

Integrated Entry v1のように
大半をSKIPして見かけのriskを改善する設計を避ける。

==================================================
■ WATCH
==================================================

WATCHは5分ごとに再評価。

ただし無限WAIT禁止。

最大WATCH時間 / episode end semanticsを
TRAIN結果を見る前にProtocol固定。

WATCH中もRaw Selector stateを更新する。

Selectorから外れた場合の処理も事前固定。

==================================================
■ Entry Timingの研究対象
==================================================

知りたいのは:

A.
first selection時に即Entryした方が良い銘柄

B.
Selectorが選び続けている間に
価格が改善し、
後からEntryした方が良い銘柄

C.
短いpullback後にEntryした方が良い銘柄

D.
Selector confidenceが維持/上昇しているのに
priceだけ下がっている銘柄

E.
Selectorから外れ、
Entryしない方がよい銘柄

のPIT分離可能性。

==================================================
■ 特に重要な仮説
==================================================

例えば:

Selector score / rankが維持
+
priceは下落

なら、

「上昇Opportunity評価は残っているが
Entry priceだけ改善した」

可能性がある。

これが本当に成立するかを
Raw Stream上で測る。

結果を見てrule化するのではなく、
まずEvidence化。

==================================================
■ Baseline
==================================================

B0:

FIRST_SELECTOR_ENTRY

各Selector episodeの
first selected timestampで
最初のcausally executable priceへEntry。

これを主Baselineとする。

==================================================
■ Secondary Historical Baseline
==================================================

既存Frozen NEW Entry v1の

INITIAL
DIP_REPRICE

も比較可能ならsecondary baselineとして使う。

ただし今回のActual Entryを
INITIAL/DIP母集団へ制限しない。

==================================================
■ Data Split
==================================================

既存Development:

TRAIN38
VALIDATION19
DEV TEST19

を維持。

今回まず:

TRAIN
→ architecture設計 / fit

VALIDATION
→ 初回Raw Selector Direct Entry測定

まで。

DEV TESTは開かない。

Fresh/OOSも開かない。

==================================================
■ Architecture
==================================================

今回はRaw Selector Stream Direct Entryを
一本だけ作る。

大量Candidate探索禁止。

既存研究の失敗を踏まえ、

Preservation-first
+
Timing/Location improvement

を目的とした
低〜中容量architectureを一つ選ぶ。

Architecture / features / WATCH semanticsは
Validationを見る前にprecommit。

==================================================
■ 今回も結果後修正しない
==================================================

初回Validation結果後:

- threshold変更なし
- feature追加なし
- model変更なし
- WATCH時間変更なし
- routing変更なし
- objective変更なし
- retrainなし

まず素の結果だけを見る。

==================================================
■ Main Evaluation
==================================================

FIRST_SELECTOR_ENTRY baselineと比較して:

Coverage:
- Selector episodes
- Actual Entries
- Entry coverage

Preservation:
- +1
- +2
- +3
- +5

Timing:
- Entry delay

Location:
- Entry price improvement

Risk:
- MAE
- p05
- <=-3
- <=-5
- <=-10

Upside:
- remaining MFE

Winner:
- Immediate Winner
- Fast Winner
- Pullback Winner

を測る。

==================================================
■ Selector Persistence分析
==================================================

特に:

selected once
selected 2 consecutive
selected 3+
selected 5+

等で、

- future +3/+5
- Entry Location
- MAE
- MFE

を診断。

ただし結果を見て
persistence thresholdを追加しない。

==================================================
■ Rank / Score Evolution
==================================================

Entry時点までの:

score level
score change
rank level
rank change

と、

Entry Timing Qualityの関係を診断。

特に:

score stable/up
+
price down

のケースを重点確認。

==================================================
■ Candidate Count
==================================================

Selectorのraw outputは既存Evidence上:

mean 3.7382
median 4
max 5

これをEntry母集団として保持。

候補数削減自体を
今回の目的にしない。

==================================================
■ Economic Comparison
==================================================

Direct Entry Candidateができたら、

B0 FIRST_SELECTOR_ENTRY
→ exact Candidate A

vs

Raw Selector Direct Entry
→ exact Candidate A

をcounterfactual比較。

Candidate A変更禁止。

Capital/Portfolio評価ではない。

==================================================
■ Successの意味
==================================================

良いDirect Entryは:

Selector winnerを高率保持
+
Entry price改善
+
MAE改善
+
remaining MFE保持
+
economic改善

を同時に示す。

単にSKIPしてMAEを改善するだけでは不十分。

==================================================
■ Historical Opportunity Generatorとの比較
==================================================

最後に記述的に:

Raw Selector Direct Entry

vs

Frozen NEW Entry v1
(INITIAL/DIP)

を比較。

最低限:

- population
- timing
- coverage
- price location
- +3/+5 preservation
- MAE
- remaining MFE

を出す。

これにより、

Opportunity Generatorが
Entry前処理として本当に必要だったのか

を判断できるEvidenceを作る。

ただし今回、
Frozen NEW Entry v1を削除しない。

==================================================
■ Safety
==================================================

全9項目false維持:

executionAllowed=false
brokerWriteAllowed=false
excelOrderWriteAllowed=false
rssOrderFunctionAllowed=false
liveTradingAllowed=false
paperTradingAllowed=false
automaticPromotionAllowed=false
productionUpdateAllowed=false
transmitted=false

LONG-only / cash equity only。

SHORT / Margin / Leverage禁止。

==================================================
■ 禁止
==================================================

- Selector変更
- ¥75変更
- Selector retrain
- Top-K変更
- future leakage
- oracle Entry
- Validation後retune
- unlimited Candidate
- DEV TEST
- Fresh/OOS
- new provider
- 1m
- Candidate A変更
- EXIT変更
- Capital tuning
- Portfolio
- main merge
- paper/live
- broker/RSS/Excel write
- promotion
- Evidence上書き

==================================================
■ Tests / CI
==================================================

最低限:

- Selector raw identity
- 760 decision timestamps
- episode construction
- reselection semantics
- PIT causality
- score/rank history causality
- price-path causality
- no future Selector state
- WATCH state
- execution ordering
- session boundary
- missing handling
- deterministic fit/inference
- ledger
- Candidate A unchanged
- Safety

を確認。

Targeted tests
→ dataset
→ train
→ Validation
→ comparison
→ evidence audit
→ regression
→ CI

まで進める。

==================================================
■ 最終報告
==================================================

Git:
- exact HEAD
- PR state

Selector:
- identity
- 760 timestamps
- raw candidate count distribution

Episodes:
- total
- continuous
- reselection
- persistence distribution

Direct Entry:
- architecture
- features
- model digest
- WATCH semantics

Coverage:
- Entry count/rate
- delay

Preservation:
- +1/+2/+3/+5
- Immediate/Fast/Pullback Winner

Location:
- price improvement

Risk:
- MAE
- p05
- <=-3/-5/-10

Upside:
- remaining MFE

Selector State:
- persistence
- rank evolution
- score evolution
- score-stable + price-down diagnostic

Economic:
FIRST_SELECTOR_ENTRY + Candidate A
vs
Direct Entry + Candidate A

Historical comparison:
Raw Direct Entry
vs
Frozen NEW Entry v1 INITIAL/DIP

Integrity:
- causal
- leakage
- deterministic
- ledger
- tests
- regression
- CI
- Safety

DEV TEST未開封。
Fresh/OOS未開封。

==================================================
■ 最終STOP
==================================================

今回は:

RAW SELECTOR STREAM
→ ACTUAL LONG ENTRY

の初回Validation測定まで。

結果が良くても悪くても
その場で修正しない。

Evidence固定後STOP。

==================================================
■ 最終命令
==================================================

本来のPhase57 LONG-only構造へ戻す。

Selector:
WHAT TO BUY

Entry:
WHEN / WHERE TO BUY

EXIT:
WHEN TO SELL

Frozen ¥75 Selectorは絶対変更しない。

これまでのFrozen NEW Entry v1 /
INITIAL / DIP Opportunity Generatorは
Evidenceとして保持するが、

新Actual Entryの必須前処理から外す。

Selectorが5分ごとに出す
Raw Top5 Streamを直接Entryへ渡す。

その連続した

score
rank
persistence
price path
momentum
pullback
trend
volatility
volume/liquidity
market/relative context
time

等のPIT情報を使い、

Selectorが見つけたwinnerをなるべく捨てずに、
より良いEntry Timing / Locationを作れるか測る。

初回Validation後は修正しない。

DEV TEST / Fresh/OOS / Capital / Portfolio / EXIT変更へ進まない。

全Evidenceとexact HEADを報告してSTOP。
```