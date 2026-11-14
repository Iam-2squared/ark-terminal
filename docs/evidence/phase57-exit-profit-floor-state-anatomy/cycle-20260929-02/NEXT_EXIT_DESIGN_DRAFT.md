# Ascending Profit Floor + Causal Path State EXIT — DESIGN_ONLY

保存対象: Outcome-exposed Development、Frozen Selector / IM・R1 Entry / Capital lineage。売買仕様としての採用、Replay、利益判定はしていない。

## 状態と境界

`INITIAL → ADVANCING → PULLBACK → RECOVERING → ADVANCING`、または `PULLBACK → BREAKDOWN → SELL_DECIDED → EXIT_PENDING → FLAT / OUTCOME_UNKNOWN`。保有中のどの状態からも、正確なsession終了なら `SELL_DECIDED`。不足データは `UNKNOWN` であり、補完による判定をしない。

- 上方進捗の継続中はHOLD。確定済み1分足のみを判断情報とし、未来Highをruntimeへ渡さない。
- 利益Floorの更新は上方のみ。一度設定したFloorは緩めない。候補の `+1→0`、`+2→+1.5`、`+3→+2.5` はOperator仮説の診断点で、採用値ではない。+5以上は未定。
- Floorは売却**判断**のライン。次の正確な連続時間OPEN、または既存terminal/auction契約に従う。gapと欠測により実現利益の保証にはならない。
- Floorより上に余裕がある押しの局面にだけ、Causal Path Stateによるearly SELLの追加価値を検討する。State規則・閾値・weight・UNKNOWN時の挙動は次の有限仕様で固定するまで未定。
- 上方進捗前の−0.5%／−1%は初期失敗の診断候補であり、stopに採用していない。
- 同じ足のHigh→Low順序は未知。High milestoneとClose milestoneの数え方、exact OPENの約定、15:30 auctionを別の契約として扱う。

## このcycleの状態

主計算は後処理エラーでINVALID。Anatomy数値と独立照合が保存されていないため、FloorやStateの可否を判断できない。修正済みコードは再実行の提案材料であり、新規EXIT候補の実装ではない。次の有限承認があるまで実行しない。
