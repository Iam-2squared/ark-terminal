# 🚀 Ark Terminal — Capital Full R-Spectrum Anatomy Work

文書ID: `ARK_CAPITAL_FULL_R_SPECTRUM_ANATOMY_V1_20261006`  
作成時刻: `2026-10-06T06:57+09:00`  
Repo: `Iam-2squared/ark-terminal`  
Branch: `capital-main-reallocation-20261005`  
開始基準HEAD: `5e6a3641d811c0fd3df9b222c4c5fc98f3bdd859`  
状態: `READY_TO_EXECUTE / DIAGNOSTIC_ONLY / NO_NEW_CAPITAL_POLICY_YET`

---

## 0. 🎯 このWorkの目的

今回の問いは1つだけ。

> **Frozen Entry → 現行Frozen EXIT/EODまでの実現net returnを、プラス側・マイナス側とも全域で解剖し、V5が「どの実現return帯へ何円・何株使い、どの良いreturn帯を何件/何株取り逃しているか」を確定する。**

R5/R10だけでは粗い。  
次のCapital変更を作る前に、**R1/R2/R3/R4/R5…R10以上、R0近辺、マイナス側も含む実現return分布全体**を確認する。

このWorkは **V5.2を実装・ReplayするWorkではない**。  
ただし、最後にEvidenceから「次に1個だけ攻めるべきCapital機構」を設計草案として1つまで提示してよい。

工程ごとの確認待ちは不要。既存Evidenceを最大限reuseし、同じ計算を名前だけ変えて再実行しない。

---

# 1. 🔒 絶対Freeze

以下は変更禁止。

- Selector
- Entry
- EXIT
- EOD execution contract
- U5/U10の既存定義
- MAX3
- 100株lot
- LONG / cash-only
- BUY/SELL cost semantics
- 既存pP / MOVE_U2 / MOVE_U3 / MRET等の学習済みscore
- 既存V5
- Reject済みV5.1
- 旧Reserve / Rank cutoff / Quality Pareto / MRET throttle等のclosed route

新fit・refit・calibration・threshold sweep・grid searchは禁止。

U5/U10は引き続き **Entry → future High** のOpportunity診断であり、R系へ改名しない。

---

# 2. 📚 Authority / 開始監査

開始時にGitHub latestをactual GETし、`5e6a3641...` より新しい有効Evidenceがあれば差分だけ確認する。

最低限読むもの:

- `docs/evidence/capital-v51-reset20-r5r10-20261006-v1/REPORT-ja.md`
- `R_LABEL_CONTRACT.json`
- `R_LABEL_CENSUS.json`
- `CAPITAL_DIAGNOSTIC.json`
- `FINAL_COMPARISON.json`
- `CURRENT_STATE.json`
- `INDEPENDENT_ACCOUNTING_AUDIT.json`
- `V5_RESET20_RESULT.json`
- `V51_RESET20_RESULT.json`
- V5 native decisions / trades / candidate stream / execution books
- 既存Expert score artifact
- private artifactの既存R label / entry identity / trade ledgers

既存R materializationは **1回済み**。  
R5/R10を作り直すために同じmarket/EXIT replayを再実行しない。

現在のR contractを権威とする:

```text
r = sell_credit / buy_debit - 1
BUY factor  = 1.0005
SELL factor = 0.9995
Capital EXIT = native frozen_execution if available before/at contract,
               otherwise inherited native EOD source
unknown = null
effective costの二重控除禁止
Structural EXIT returnは別列
```

既存 `R5 = r >= +5%`、`R10 = r >= +10%` の境界・意味を変更しない。

---

# 3. 🧮 R系の正式な全域定義

## 3.1 continuous原値

各known Entryについて、最重要列として

`realized_net_return_exact`

をFraction/Decimal原本で保持する。

丸めた表示値で分類しない。

---

## 3.2 正方向の累積R

既存R5/R10と同じ意味で、以下を機械的に追加する。

| 名前 | 条件 |
|---|---:|
| R0PLUS | r >= 0% |
| R1 | r >= +1% |
| R2 | r >= +2% |
| R3 | r >= +3% |
| R4 | r >= +4% |
| R5 | r >= +5% |
| R6 | r >= +6% |
| R7 | r >= +7% |
| R8 | r >= +8% |
| R9 | r >= +9% |
| R10 | r >= +10% |

境界はすべて成立側を含む。

known returnの最大が+10%を超える場合は、**結果を見て都合のよい閾値を選ばず**、+11,+12,…と1pp刻みで最大観測整数域まで機械的に延長してよい。これはdescriptive census専用。

---

## 3.3 負方向の累積R

マイナス側も対称に固定する。

| 名前 | 条件 |
|---|---:|
| RNEG | r < 0% |
| RN1 | r <= -1% |
| RN2 | r <= -2% |
| RN3 | r <= -3% |
| RN4 | r <= -4% |
| RN5 | r <= -5% |
| RN6 | r <= -6% |
| RN7 | r <= -7% |
| RN8 | r <= -8% |
| RN9 | r <= -9% |
| RN10 | r <= -10% |

known returnの最小が-10%未満なら、-11,-12,…を1pp刻みで最小観測整数域まで機械的に延長してよい。

既存 `Loser = credit <= debit` はそのまま保持し、`RNEG = r < 0` と完全に同一だと決め打ちしない。exact 0%を別扱いできるようにする。

---

## 3.4 排他的1pp bucket

累積Rだけだと重複するため、分布を見るための排他的bucketも必須。

```text
[..., -6%〜<-5%, -5%〜<-4%, ... , -1%〜<0%,
 0%〜<1%, 1%〜<2%, ... , 9%〜<10%, 10%〜<11%, ...]
```

ルール:

- lower inclusive / upper exclusive
- known returnの実観測最小〜最大まで1pp刻み
- 境界は事前の整数gridで機械生成
- outcomeを見てbucket幅を変えない
- tailを一部だけまとめて都合よく見せない
- 表が長くなる場合、本文は主要域を表示し、JSON/CSVには全bucketを保存

---

# 4. 🧭 母集団を混ぜない

最低でも次のpopulationを別々に出す。

1. `ALL_FROZEN_ENTRY`
2. `EXECUTION_ELIGIBLE`
3. `RANK_PASS_EXECUTION_ELIGIBLE`
4. `V5_FUNDED`
5. `V5_NOT_FUNDED`
6. `V5_RESERVE_REJECT`
7. `V5_MAX3_FULL`
8. `V5_CASH_OR_LOT`
9. その他native reason別

現在の既存censusとの整合をまず確認する。

参考の既存値:
- 全Frozen Entry: 1,039
- R known: 1,016
- R unknown: 23
- 実行適格: 1,028
- rank-pass・実行適格: 494
- rank-pass known: 492
- R5: 34
- R10: 16
- V5旧chain capture: R5 19/34, R10 11/16

これらは**開始整合確認用**であり、合わない場合に新結果へ黙って置換しない。

---

# 5. 🔥 U5/U10 → R全域クロス

ここが必須。

U5/U10はEntry→High Opportunityの既存定義のまま。

少なくとも以下を別表にする。

- ALL known U5
- U5かつ非U10
- U10
- non-U5
- U unknown

各群について、Rの排他的1pp bucket分布と累積Rを出す。

最低限、次に答える。

1. U5のうちR1/R2/R3/R4/R5/R10へ何件到達したか。
2. U5のうちR0〜1%付近で終わったものは何件か。
3. U5なのにRNEG / RN1 / RN2 / RN3 / RN5以下へ終わったものは何件か。
4. U10でも同じ分解。
5. U5/U10の「future High Opportunity」とFrozen EXIT後の実現利益の乖離はどこに集中しているか。

**U5/U10をRの予測精度と呼ばない。**
これはOpportunity→Realization anatomy。

---

# 6. 💴 V5が各R帯へ何をしているか

## 6.1 unique Entry census

R bucketごとに最低限:

- candidate N
- eligible N
- rank-pass N
- V5 funded N
- funded rate
- missed N
- miss reason別N
- distinct sessions
- distinct symbols

unique Entryを単位とし、reset20の重複windowをここへ混ぜない。

---

## 6.2 実funded Capital flow

V5が実際に買ったEntryについて、各R bucket別に:

- shares
- BUY debit
- realized PnL
- net return
- holding minutes
- debit × holding minutes
- funded slot 1/2/3
- entry time帯
- recycle cash使用量
- concurrent occupancy

を出す。

特に以下を金額で明示する。

```text
R positive側へ投じた総資金
R0〜+1%帯へ投じた総資金
RNEGへ投じた総資金
RN1 / RN2 / RN3 / RN5 / RN10へ投じた総資金
各帯の実現損益
```

---

## 6.3 missed positive R

R1+ / R2+ / R3+ / R4+ / R5+ / R10+をV5がfundしなかった理由を、

- Reserve
- MAX3
- cash/lot
- cutoff
- rank/admission
- same-symbol
- その他native reason

に分解する。

ただし未funded R+のstandalone利益を単純合算して、

> 「これだけ回収可能だった」

とは言わない。

同時刻競合・MAX3・cash・後続状態があるため、これは **missed standalone opportunity anatomy** であってcounterfactual portfolio wealthではない。

---

# 7. 🧠 既存causal score × R全域

新モデルは作らない。

既存scoreだけを使用:

- pP / MOVE_P5
- MOVE_U2
- MOVE_U3
- MRET
- V5 native rank / S-A-B-C 等、既存contractで正式に存在するもの

存在しない特徴は追加しない。

## 正方向

R1〜R10+について:

- pooled AUROC
- support N / positive N
- inherited block/session別率
- 既存の固定rank bucket / S-A-B-C別 event rate
- rank-pass内でのevent rate
- V5 funded内でのprecision

を出す。

**test outcomeから新しいquantileを作らない。**
既存training由来rank/bucketだけ使う。

## 負方向

RN1〜RN10+についても同じ。

元scoreの方向は勝手に反転して「skillあり」と救済しない。

少なくとも:

- raw score directionでのRN event AUROC
- score bucket別RN率
- low-score側にRNが増えるかの記述

を示す。

もし `-score` を補助表示するなら、全score・全RN thresholdについて機械的に同じ処理を行い、**promotion evidenceではなく方向確認用**と明記する。良かったheadだけ抜き出さない。

MRETは既存通りrelative diagnosticのみ。過去のabsolute-loss defense INCONCLUSIVEを上書きしない。

---

# 8. 📊 「本当に次へ使えるR帯」を調べる

単にAUC最大のR thresholdを選ばない。

次の3条件を同時に見る。

### A. Economic relevance
そのR帯へ資金を寄せた場合に、実現利益として意味のある幅か。

### B. Support
候補数・rank-pass数・funded/missed数が極端に小さくないか。

### C. Causal separability
購入時点で既に存在するscore/rankだけで、ある程度順位差があるか。

結果を見て、

- 「R5が一番きれいだからR5だけ」
- 「R3なら件数が多いからR3だけ」
- 「RN4だけAUCが良いからRN4 cutoff」

のような単一threshold cherry-pickをしない。

**全R曲線を見て、どの領域からどの領域へCapitalを移す問題なのか**を判断する。

---

# 9. 🔁 RESET20との接続

今回の主目的はEntry-level R anatomy。

既存RESET20は再実行不要。

既存9 complete windowについて、保存済みV5 account flowを使って可能なら:

- windowごとのR bucket別BUY debit
- R bucket別実現PnL
- RNEG debit share
- R3+/R5+/R10+ debit share
- Final cash

を結合する。

「R5比率が高いwindowほどfinal cashが高い」等は記述相関に留める。9窓は重複市場期間で独立標本ではないため、有意差・一般化性能を主張しない。

7/11・7/14 coverageをこのWorkの主題にしない。既存sourceで新しいreceiptが即見つかる場合だけ記録し、同じ探索を繰り返してR anatomyを止めない。

---

# 10. 📈 必須図表

数値はJSON/CSVを正本とし、REPORTには見やすい表と図を付ける。

最低限:

1. **全R 1pp histogram**
   - positive / zero近辺 / negativeを全表示
2. **U5/U10 → R bucket分布**
   - U5、U10の実現return着地
3. **R bucket別 V5 funded / missed**
   - 件数とfunded率
4. **R bucket別 BUY debit / realized PnL**
   - 「どこへ金を使っているか」
5. **主要score × R threshold curve**
   - R1…R10、RN1…RN10のsupportとAUROCを同時表示
6. **miss reason × positive R**
   - R3+/R5+/R10+がReserve/MAX3/cash等で何件消えたか

図は空データで作らない。

---

# 11. 🚫 禁止事項

- Selector / Entry / EXIT変更
- U5/U10定義変更
- R contract変更
- 新fit / refit / calibration
- threshold sweep
- 新Capital policy実装
- V5.2 Replay
- V5.1救済
- closed Reserve再開
- outcomeをruntime decisionへ入力
- future High / R labelをCapital scoreに直接入力
- future exit source availabilityを現在candidate除外へ使用
- unknownをfalse / Loser扱い
- R5/R10の既存結果を都合よく再materialize
- overlapping reset windowを独立月次標本と呼ぶ
- missed R+ standalone利益をそのまま「回収可能利益」と合算
- 良かったR thresholdだけを抜き出して新Gateを承認
- protected / Fresh / OOS / Prospective開封
- provider価格取得
- 注文
- main merge
- force push

---

# 12. ⚡ 実施量上限

```text
new model fits/refits/calibration = 0
new Capital candidates = 0
new Capital replays = 0
R market/EXIT rematerialization = 0
existing R rowsからのmechanical derived labels = 1 batchまで
new provider requests = 0
protected partition openings = 0
orders = 0
main merge = 0
Claude = 原則0
```

R1〜RN系は既存continuous R原値からの**機械的派生**として作る。新しいmarket replayではない。

---

# 13. 📦 必須成果物

新Evidence directory例:

`docs/evidence/capital-full-r-spectrum-20261006-v1/`

最低限:

- `WORK_REQUEST.md`
- `START_AND_SOURCE_BINDING.json`
- `R_SPECTRUM_CONTRACT.json`
- `R_FULL_CENSUS.json`
- `R_FULL_CENSUS.csv`
- `U_R_CROSS.json`
- `U_R_CROSS.csv`
- `V5_R_CAPITAL_FLOW.json`
- `V5_R_MISS_REASONS.json`
- `SCORE_R_SPECTRUM.json`
- `RESET20_R_FLOW.json`（既存結果で作れる範囲）
- `INDEPENDENT_R_AUDIT.json`
- `NEXT_CAPITAL_DECISION.md`
- `CURRENT_STATE.json`
- `WORK_STATUS_LOG.jsonl`
- `MANIFEST.json`
- `REPORT-ja.md`
- 必要な図

private identity / symbol単位の生台帳をpublic GitHubへ漏らさない。

---

# 14. 🔍 Independent Audit

主処理と別経路で最低限:

1. raw debit / creditからcontinuous Rを再構成
2. R1/R2/.../R10、RN1/.../RN10境界を再判定
3. exclusive 1pp bucketがknown Nを過不足なくpartitionするか
4. cumulative Rが単調になるか
   - R1 N >= R2 N >= ... >= R10 N
   - RN1 N >= RN2 N >= ... >= RN10 N
5. U5/U10 crossのrow totals一致
6. V5 funded/trade joinのN・quantity・debit・PnL一致
7. unknown 23等のmaskが誤ってevent/non-eventへ入っていないか
8. R5/R10が既存認証値と一致

不一致を見つけた場合、既存Evidenceを上書きせずappend-only correction receipt。

---

# 15. 🧭 Work終了時に必ず答える質問

REPORTの冒頭で簡潔に答える。

1. **R1〜R10+は各何件か。**
2. **RN1〜RN10+は各何件か。**
3. **実現returnの中央値・平均・主要quantile・最悪/最高は何%か。**
4. **U5 170件はRのどこへ着地したか。U10 67件はどうか。**
5. **U5/U10なのにマイナスで終わる件数と、その深さはどれくらいか。**
6. **V5はR1+/R2+/R3+/R4+/R5+/R10+を何件・何株fundし、何件missしたか。**
7. **V5はRNEG/RN1/RN2/RN3/RN5/RN10へ何円投入したか。**
8. **R positive missの最大理由はReserve / MAX3 / cash / rankのどれか。**
9. **既存causal scoreはどのR領域で最も一貫した順位情報を持つか。単一thresholdではなく曲線として答える。**
10. **「どの悪いR帯から資金を抜き、どの良いR帯へ寄せる」のが次のCapital課題か。**
11. **次にV5.2を作る価値があるか。あるなら変更機構は1個だけ何か。**
12. **新fit / 新Replay / provider / protected open / order / merge が全て0か。**

---

# 16. ✅ 終了判定

次のいずれかで終了する。

### `R_SPECTRUM_ACTIONABLE`
R全域を確認し、既存causal情報とCapital flowから、次に攻める donor R帯 / receiver R帯 / Capital mechanism が具体化した。

### `R_SPECTRUM_INCONCLUSIVE`
分布は確認できたが、既存causal情報では次のallocation改善へ安全につなげる根拠が弱い。

### `R_SPECTRUM_BLOCKED_SOURCE`
continuous R / funded flow / maskの権威ある原本が不足し、全域監査を成立させられない。

どの結果でもV5.2をこのWork内で実行しない。

---

# 17. 💾 GitHub運用

開始、R contract固定、census完了、score/capital anatomy完了、finalの各重要checkpointで、

- 実時計JST
- basis HEAD/tree
- 現在地
- 完了
- 未実行
- blocker
- counts
- next
- source/hash

をappend-only保存。

保存後はactual GETで本文・blob/tree/HEADを確認。

旧V5/V5.1 Evidenceはread-only。  
force push / main merge禁止。

---

# 18. ▶ Workへの開始指示

この指示書に従って、**R系の全域監査を一気に完了してください。**

R5/R10だけで止めず、continuous realized returnを基準に、R1〜R10以上、0付近、RN1〜RN10以下、さらに観測tailまで1ppで機械的に分解してください。

U5/U10とのクロス、V5のfunded/missed、数量・BUY debit・PnL・拘束時間、miss reason、既存causal scoreとの関係までまとめてください。

既存Evidenceをreuseし、同じmarket/EXIT replay、新fit、新Capital Replayは行わないでください。

このWorkの出口は、**「100万円のCapitalが現在どの実現return帯へ流れ、どのreturn帯へ移す余地があるか」をEvidenceで確定し、次のCapital変更箇所を最大1個まで設計草案化すること**です。

Selector / Entry / EXITは完全Freeze。  
R/Uは評価専用。未来情報をruntime判断へ入れない。  
結果を見て閾値を救済しない。

END_OF_WORK_REQUEST
