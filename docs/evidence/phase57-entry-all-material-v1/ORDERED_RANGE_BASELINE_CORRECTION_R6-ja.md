# Entry評価の分類名訂正と本来のLow→Later High値幅別結果 R6

2026-09-25 JST / Developmentのみ。旧Evidenceは上書きしない。

## 重要な訂正

従来の `BASELINE_BUCKETS_R1.md` と会話で「Low→High値幅別」と説明していた6帯の数値は、実際にはcanonical evaluatorの `futureSelectorMfeBuckets`、すなわち `selectorOutcome.mfeEnd` による分類だった。Selector価格基準の将来上昇幅と、ordered Low→strictly later Highの値幅は同じではない。計算自体を変更したのではなく、説明の誤りを明示して別パネルを追加した。

以前の「≥5%、408件、ONE_MINUTE平均EntryPosition27.66%」はSelector MFE≥5%群の結果である。本来のLow→Later High≥5%群は666件で、ONE_MINUTE平均45.9989%、Immediate平均44.3575%である。27.66%をLow→High値幅≥5%の成績として使用してはならない。

## 固定定義

- EntryPosition=(EntryPrice−orderedOracle.low)/(orderedOracle.high−orderedOracle.low)。旧計算のまま、clipしない。
- 本パネルの値幅=100×(orderedOracle.high/orderedOracle.low−1)。価格の基準はLow。
- 既存oracleは同日観測範囲内の最大ordered riseを選ぶ。単純に時刻順を無視した日中最安値/最高値の組ではない。Highの時刻はLowより厳密に後。
- fullSessionEvaluableかつ正の有効ordered rangeで分類。2,053件が分類可能、102件がNOT_EVALUABLE。未約定と分類不能を母集団から消さない。
- EntryPositionの平均・中央値・閾値率は約定かつEP有効例が分母。下のNは機会数なので混同しない。
- 未来値幅は評価専用であり、Entry、ABSTAIN、特徴量選別には渡さない。

## 排他的Low→High値幅帯

| Low→High値幅 | 機会N | Immediate Fill/EP有効N | Immediate平均EP% | Immediate中央値% | ONE_MINUTE Fill/EP有効N | ONE_MINUTE平均EP% | ONE_MINUTE中央値% |
|---|---:|---:|---:|---:|---:|---:|---:|
| <1% | 158 | 117 | 111.8292 | 74.4500 | 76 | 106.7744 | 81.6495 |
| 1–2% | 391 | 350 | 87.8244 | 69.3917 | 299 | 93.6131 | 74.2500 |
| 2–3% | 361 | 346 | 72.1710 | 52.2357 | 317 | 78.7387 | 55.0956 |
| 3–4% | 289 | 279 | 65.9719 | 43.1285 | 250 | 71.1704 | 54.6612 |
| 4–5% | 188 | 183 | 54.5770 | 34.6000 | 175 | 57.9894 | 41.0300 |
| ≥5% | 666 | 656 | 44.3575 | 27.1733 | 634 | 45.9989 | 32.0882 |
| NOT_EVALUABLE | 102 | 32 fills / 0 EP | — | — | 13 fills / 0 EP | — | — |
| 合計 | 2,155 | 1,963 fills / 1,931 EP | 65.3993 | 42.2600 | 1,764 fills / 1,751 EP | 67.4868 | 49.6029 |

## 累積Low→High閾値

累積群なので≥5%の666件は≥1/2/3/4%にも含まれる。

| Low→High | 機会N | Immediate平均EP% | ONE_MINUTE平均EP% |
|---|---:|---:|---:|
| ≥1% | 1,895 | 62.4046 | 65.7042 |
| ≥2% | 1,504 | 56.3275 | 59.6397 |
| ≥3% | 1,143 | 51.4242 | 53.9226 |
| ≥4% | 854 | 46.5866 | 48.5926 |
| ≥5% | 666 | 44.3575 | 45.9989 |

## 再現根拠

追加evaluator: `scripts/phase57_entry_ordered_range_scorecard_v1.py`。
Dedicated workflow: `phase57-entry-ordered-range-scorecard-v1.yml`。
Producing run: 36096675175 / source HEAD b1226d4053d824f54aac1c35fbad2e1c2abb398b。
Artifact: 10847194724。ZIP SHA256: 481a5bf77e156b7e395243ea32fc4e4ddc72da0bbf4b39b14d53c392bcc191bf。

4本のbaseline（Immediate、Entry v1、original State v3、ONE_MINUTE）を同じ既存canonical evaluatorで再評価し、新パネルを追加。legacy output全キー一致、2回のscorecard一致、母集団2,155の保持をassert。新しいEntry学習・閾値調整はこの訂正には含まない。

この時点でAll-Material R1の新性能を本表に代入しない。R1正式結果は別Evidenceに保存する。旧値の訂正をEntry性能改善と呼ばない。
