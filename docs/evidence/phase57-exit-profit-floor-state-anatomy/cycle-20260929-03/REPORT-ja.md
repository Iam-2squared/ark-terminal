# Phase57 Path Anatomy Recovery v3 — invalid main, bounded observations

JST: 2026-09-29T21:32:40.191651+09:00  |  basis HEAD: `1e328c7b47acf6dc9341e784808f691cdbd75f18`  |  cycle: `cycle-20260929-03`

**最終status: `PATH_ANATOMY_INCOMPLETE_MAIN_INVALID`。** PreflightはPASS、実Entry主計算1回と独立照合1回（照合範囲内 mismatch 0）を実施。ただしCloseベースgivebackに負の不可能値38行があり、Main Sanityの初回PASSも誤りだった。`MAIN_SANITY_CORRECTION.json`が優先する。完全なPath Anatomy/EXITの採否判定には使用しない。旧2つのINVALID cycleは維持。

## A. Entry Opportunity

| world | ALL N | path-known | price-known | state-known | UNKNOWN | High mean% | High median% | High ≥1/2/3/5/10 N | Close ≥1/2/3/5/10 N |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| IM | 819 | 102 | 819 | 0 | 717 | 2.54 | 1.36 | 63/39/25/15/5 | 56/32/24/13/5 |
| R1 | 795 | 127 | 795 | 0 | 668 | 2.30 | 1.02 | 64/43/29/18/6 | 60/38/28/17/5 |

Highは観測最大値で約定利益ではない。Closeは確定した連続1分足のみ。IM/R1は別世界、FUNDEDはALLに内包（IM 4/79、R1 2/32 path-known）。完全path条件は全予定1分足＋正確な15:30 single-price auction。よって観測可能母集団に強い偏りがあり、ALL Entryへの率の外挿は禁止。

## B. Entry直後の下落と後のWinner（High、完全pathのみ）

| world | 後のWinner | N | 厳密に先行する −0.5/−1/−2 cross N | 先行minimum median / p10 / worst % |
|---|---:|---:|---|---|
| IM | +3% | 25 | 19/13/10 | -1.52 / -5.20 / -11.39 |
| IM | +5% | 15 | 14/10/7 | -1.93 / -7.95 / -11.39 |
| IM | +10% | 5 | 5/3/3 | -3.79 / -7.92 / -9.77 |
| R1 | +3% | 29 | 14/10/9 | -0.48 / -4.56 / -7.10 |
| R1 | +5% | 18 | 9/8/7 | -0.59 / -5.74 / -7.10 |
| R1 | +10% | 6 | 4/4/3 | -2.04 / -6.13 / -7.09 |

先行はWinner到達barより**前のbar**に限定。同一barでHigh到達とLow下落が重なった場合は順序不明として別集計（詳細JSON）。−2%は分布記述のみでstop候補ではない。IM +10 Winner 5/5、R1 +10 Winner 4/6が先に−0.5%を踏むため、完全path観測分は「Entryが概ね底を捉えた」という仮説を支持しない。ただしUNKNOWNが大きく一般化できない。

## C. Initial Weakness

| world | 先に下落 | Low到達 N | +1 Highより前 N | 後の +1/+2/+3/+5/+7/+10 N |
|---|---:|---:|---:|---|
| IM | -0.5% | 88 | 63 | 28/18/12/8/3/2 |
| IM | -1% | 75 | 47 | 14/10/7/4/2/1 |
| R1 | -0.5% | 87 | 75 | 26/18/11/7/5/2 |
| R1 | -1% | 67 | 50 | 14/11/7/5/4/2 |

厳密に前のbarで−0.5/−1へ下落したものだけを復活件数へ算入。同一bar曖昧は別欄。後のWinnerを捨てる潜在件数でありstopの成績ではない。回復active minute、MAE分位点、session/symbol集中は `INITIAL_WEAKNESS_ANATOMY.json`。

## D. Milestone後の押し（High）

| world | anchor→later | 後に到達 N | 押し測定 N | minimum-return median / p10 / worst % | max giveback pp median / p90 / worst |
|---|---|---:|---:|---|---|
| IM | +3→+5 | 15 | 14 | 2.71 / 0.95 / -9.77 | 1.34 / 2.59 / 13.05 |
| IM | +3→+10 | 5 | 5 | 2.45 / -5.82 / -9.77 | 4.37 / 10.01 / 13.05 |
| IM | +5→+10 | 5 | 5 | 2.85 / 1.03 / 0.09 | 2.44 / 5.01 / 5.44 |
| R1 | +3→+5 | 16 | 14 | 2.24 / 1.64 / -0.67 | 1.60 / 2.71 / 4.37 |
| R1 | +3→+10 | 6 | 5 | 2.34 / 1.96 / 1.71 | 2.93 / 5.29 / 5.56 |
| R1 | +5→+10 | 5 | 5 | 3.78 / 2.54 / 2.33 | 2.93 / 5.29 / 5.56 |

高値到達bar自身と次milestone到達barは押し幅の順序計算から除外し、同一barのHigh/Low順序を仮定しない。+1/+2/+3/+5/+7の全pair・p10/p25/median/p75/p90/worst、active duration、回復・前高値回復・新高値更新は `MILESTONE_PULLBACK_ANATOMY.json`。Close milestone到達NはA表でHighより少ないが、**Close押し幅38行は無効**のため `CLOSE_MILESTONE_PULLBACK_ANATOMY.json` を判断材料にしない。

## E. Operator Floor仮説（High、売却ではない）

| world | 仮Floor | 後の目標 | Winner N | Floor先行cross N | 同一bar曖昧 N |
|---|---|---:|---:|---:|---:|
| IM | +1→+0.00 | +3 | 24 | 11 | 0 |
| IM | +1→+0.00 | +5 | 15 | 8 | 0 |
| IM | +1→+0.00 | +10 | 5 | 3 | 0 |
| IM | +2→+1.50 | +3 | 24 | 12 | 0 |
| IM | +2→+1.50 | +5 | 15 | 7 | 0 |
| IM | +2→+1.50 | +10 | 5 | 3 | 0 |
| IM | +3→+2.50 | +5 | 15 | 5 | 1 |
| IM | +3→+2.50 | +7 | 9 | 6 | 0 |
| IM | +3→+2.50 | +10 | 5 | 3 | 0 |
| R1 | +1→+0.00 | +3 | 28 | 12 | 0 |
| R1 | +1→+0.00 | +5 | 18 | 10 | 0 |
| R1 | +1→+0.00 | +10 | 6 | 5 | 0 |
| R1 | +2→+1.50 | +3 | 22 | 8 | 0 |
| R1 | +2→+1.50 | +5 | 16 | 4 | 0 |
| R1 | +2→+1.50 | +10 | 6 | 0 | 0 |
| R1 | +3→+2.50 | +5 | 16 | 9 | 0 |
| R1 | +3→+2.50 | +7 | 10 | 6 | 0 |
| R1 | +3→+2.50 | +10 | 6 | 3 | 0 |

+1→0の+7、+2→+7など、前回Precommitにpairがない組み合わせは今回追加していない。Floor crossはSELL成立でも実現利益でもない。

## F. P4 Path State

| world | checkpoint | later +5 recovery | 後に+5なし | peak/current同bin重複 | 回復/非回復の down close 中央値 |
|---|---:|---:|---:|---:|---|
| IM | 49 | 7 | 42 | 4 bin / 38 rows | 1.00 / 2.00 |
| R1 | 42 | 12 | 30 | 4 bin / 36 rows | 1.00 / 1.50 |

候補primitiveの記述差はあるが、回復群が小さく、同程度のpeak/currentで安定した増分を証明していない。`STATE_INCREMENT_NOT_DEMONSTRATED`。既存State/Signalのexact knownAt snapshotは0でBLOCKED。classifier/重み/閾値はfit・選択していない。

## G. Input / UNKNOWN / Integrity

Input GateはPASS。原本337,151 barはすべて整数相当floatで、lossless normalize後の拒否0、0-bar Entry 0、exact 15:30 auction 1,594/1,614（世界重複計上）。不完全な連続1分足は1,385 Entry。欠測はno-trade/halt/data-missingへ推測分類しない。IM UNKNOWN上位sessionは2025-08-21(36)、2025-07-24(35)、2025-08-12(35)、R1は2025-08-07(34)、2025-08-21(34)、2025-08-19(33)。価格publication knownAt、State snapshot、exact next OPEN約定は今回未証明/未実施。

Main Sanity初回PASSは負のClose givebackを検査していなかった。Close pair 904行中38行（IM 9、R1 29）に負値があり、最小−2.64pp。このmetricは非負でなければならず、完成GateはFAIL。独立照合mismatch 0はEntry数、High milestone、initial weakness、pre-winner、Floor cross、主要High pullback分位点の範囲に限る。Close givebackは独立照合対象外だった。

## H. 実行量と次の境界

Input contract preflight 1、synthetic suite 1（コード拡張に伴う合成実行2 invocationを明記）、read-only real schema 1、主計算1、独立照合1。fit / EXIT Replay / Capital Replay / provider / protected・Holdout・Validation・OOS・Fresh・Prospective開封 / 発注 / main merge はすべて0。安全フラグはすべてfalse。

次回は新しい有限承認の下で、Close givebackを `max(0, peak−Close)` と定義し、負値拒否をsynthetic E2EとMain Sanityに追加した上で、正規Mainと独立照合を再実施する必要がある。今回の出力を正式EXIT判断・収益性PASS・productionReadyへ昇格しない。−0.5/−1 stop、3つのFloor、+5以上のFloor、P4閾値は未決定。

## 図（診断用・完成判定不可）

- [01_entry_high.png](figures/01_entry_high.png)
- [02_milestone_giveback.png](figures/02_milestone_giveback.png)
- [03_minimum_before_later_winner.png](figures/03_minimum_before_later_winner.png)
- [04_weakness_recovery.png](figures/04_weakness_recovery.png)
- [05_candidate_floor_cross.png](figures/05_candidate_floor_cross.png)
- [06_causal_state_paths.png](figures/06_causal_state_paths.png)
