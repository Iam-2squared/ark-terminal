# Frozen 30m Selector Universe → 5m PIT WATCH — First Validation

**FIRST_RAW_SELECTOR_DIRECT_ENTRY_MEASUREMENT_COMPLETE_HARD_FAIL**

Selectorは変更していない。各30分Top5 snapshotのscore/rank/Decision Priceをwindow内で固定し、5分PIT価格stateだけを更新した。
09:35等のSelector値は生成・補間していない。TRAINのみ1 fit、VALIDATION初回測定後の調整なし。

## Result

| Metric | Result |
| --- | ---: |
| Validation symbol-session episodes | 710 |
| Common60 complete | 259 |
| Entry coverage | 100.000% |
| WATCH episodes / delayed Entries | 0 / 0 |
| Mean Entry price improvement | 0.0000 pp |
| Strict30 MAE median improvement | 0.0000 pp |
| Remaining MFE ratio | 100.000% |
| Candidate A mean net delta | 0.0000 pp |
| Final classification | **HARD_FAIL** |

WATCH対象として訪問したstateは514件。price/loss/riskの3条件を同時に満たしたstateは0件だったため、全件BUY_NOWとなった。

## Integrity

- model digest: `f8e1dcbda5252037423a1dc3363da31af21f86ba2076b9fcbeda05aeb1ab93d2`
- TRAIN fit states: 956; effective episodes: 478
- DEV TEST未開封、Fresh/OOS未開封、新規provider取得0、Selector/EXIT/Candidate A変更0。
- Safety 9項目は全false。LONG-only / cash equity only。
- この初回結果に対するthreshold・feature・model・WATCH時間・routingの修正は行っていない。

Evidenceの詳細数値は `summary.json`、全decisionは `validation-ledger.json.gz`、経済比較は `economic-ledger.json.gz` に固定。
