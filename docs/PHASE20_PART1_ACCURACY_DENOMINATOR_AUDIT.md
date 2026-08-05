# Phase20 Part1 — Accuracy Denominator Audit

## Goal

Accuracyを上げる前に、現在表示されているAccuracyの分子・分母が正しいかを監査し、未確定・非取引・欠損データによる汚染を止める。

## Finding

旧`predict/analysis/accuracy-metrics.js`には次の問題があった。

- 全入力行をAccuracyの分母にしていた
- 損益がない行を`0`へ変換していた
- 明示的な正誤がない場合、`profit > 0`だけで正誤を推測していた
- PENDING、NO_TRADE、HOLD、CANCELLED、UNKNOWNを分母から分離していなかった
- 取引勝率・Profit Factor・Drawdownにも非取引行や未確定行が混ざる余地があった

この状態では、未確定予測が不正解に見え、Accuracyが実力より低く表示される可能性がある。

## Canonical denominator policy

### Directional prediction accuracy

分母へ入れるのは次をすべて満たす行だけ。

- action / signalが`BUY`または`SELL`
- 結果が確定済み
- 正誤が明示または検証可能

除外するもの。

- `PENDING`
- `CANCELLED`
- `NO_TRADE`
- `HOLD`
- `UNKNOWN`
- 結果欠損

### Trade performance

Win Rate、Profit Factor、Expectancy、Drawdownへ入れるのは次をすべて満たす行だけ。

- `BUY`または`SELL`
- 結果が確定済み
- 有限の損益値が存在する

欠損損益を`0`へ変換しない。

## Output changes

`calculateAccuracyMetrics()`は次を追加する。

- `sourceTotal`: 元データ件数
- `total`: Accuracy分母件数
- `denominatorPolicy`: 分母定義
- `excluded.pending`
- `excluded.noTrade`
- `excluded.hold`
- `excluded.unknown`
- `excluded.missingCorrectness`
- `excluded.missingProfit`
- `trades.total`: 取引成績の分母

Accuracy Dashboard composerも、Risk-adjusted metrics、Confidence calibration、Period performanceへ対象となる確定済みサンプルだけを渡す。

## OpenAI role in Phase20

OpenAI APIはAccuracyの採点器にはしない。数値の正誤判定、リターン計算、ラベル確定は決定論的コードが担当する。

OpenAIを使う予定の領域は次。

1. 失敗ケースのクラスタリング
2. ニュース・決算・市場文脈の構造化特徴抽出
3. 指標重み・閾値のCandidate案生成
4. Driftと弱点の説明
5. 改善仮説の優先順位付け

OpenAIが提案したCandidateは直接Productionへ反映しない。

```text
OpenAI proposal
  -> Candidate configuration
  -> walk-forward validation
  -> out-of-sample comparison
  -> risk gates
  -> human approval
  -> optional promotion
```

既存のContinuous Learning Orchestratorが持つCandidate、walk-forward、future-leak check、human approval、rollbackの境界を維持する。

## Safety

- OpenAIは実注文を作成・送信しない
- OpenAIはProductionモデルを直接変更しない
- OpenAIの提案だけで自動昇格しない
- 実口座はREAD ONLYのまま
- Phase19 broker write lockを変更しない

## Completion criteria

- PENDINGがAccuracy分母に入らない
- NO_TRADEとHOLDが方向予測Accuracyに入らない
- 欠損損益が0へ変換されない
- AccuracyとTrade Win Rateの分母を別々に表示できる
- 回帰テストがCIで成功する
