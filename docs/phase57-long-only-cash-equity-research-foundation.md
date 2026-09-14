# Phase57 LONG-only Cash Equity — Research Foundation

## 結論

このbranchは、日本株の現物買いだけでRemaining Upsideを発見する独立research laneである。既存LONG+SHORT版のSHORTをOFFにしたものではない。Lane Y、Frozen Minimal Hybrid、MSH Entry、EXIT、Capital Allocation、mainの実売買回路は変更しない。

| 項目 | 状態 |
|---|---|
| LONG-only Research Contract | 🟢 FOUNDATION PASS |
| L0実装 | 🟢 FOUNDATION PASS |
| Data Budget / Dataset Split | 🟢 DESIGN FROZEN |
| J-Quants新規取得 | 🔴 BLOCKED |
| Formal L0 | 🟡 INPUT BLOCKED |

取得前の詳細設計は`docs/phase57-long-only-data-budget-and-dataset-split.md`、Claudeへ送る独立レビュー文は`docs/phase57-long-only-claude-data-budget-review-request.md`を正本とする。

## Frozen LONG-only contract

| Capability | Contract |
|---|---|
| Cash-equity LONG | Allowed |
| Margin buy | Prohibited |
| Short sell / margin sell | Prohibited |
| SHORT Entry / position | Prohibited |
| Leverage | Prohibited |
| Quantity | Positive integer、default 100-share lot |
| Buying power | current available cash only |
| Cash lifecycle | Entryでlock、EXITでrelease、以後causal reuse |
| Order transmission | Prohibited during research |

## J-Quants実装に関する訂正

旧版の「J-Quants implementation on main = TDnet disclosures only」はmainについては正しいが、repository全体の説明としては不完全だった。全remote branch再監査により、過去research branchに次が存在すると確認した。

- `/v2/equities/bars/minute`取得とpagination
- `/v2/equities/bars/daily`取得
- `/v2/equities/master`によるdated point-in-time universe
- sparse 1m→5m aggregationとterminal-auction/timestamp contract
- source/session/hash/safety metadata

したがって取得基盤は再利用し、同じ処理を新造しない。ただし既存Selector仮説、SHORT logic、threshold、performance winnerはLONG-only researchへ流用しない。

## L0 contract

L0はDaily + dated Masterだけで成立する。minute requestは0とする。

| 項目 | 定義 |
|---|---|
| Unit | point-in-time eligible domestic common-equity symbol-session |
| Return | `100 × (adjustedClose_t / adjustedClose_t-1 − 1)` |
| Threshold | +3%、+5%、+10% |
| Output | countとeligible-universe rateのmean/median/P25/P75/min/max/session distribution |
| Segment | Prime / Standard / Growth point-in-time |
| Regime | prior-day causal definitionを先にfreezeした場合だけ追加 |

IPO/前日値なし、null OHLC、zero volume、suspension、limit-up、corporate actionは黙って落とさず、stratumまたはblocked reasonとして保存する。

## Dataset protection

Development A/B/C/D、Validation、Validation Confirmation、Untouched OOS、Final Confirmation、Freshは取得前に分離する。outer blockを見た後のfeature/model/threshold/horizon選択は禁止する。sealed blockはrelease hashなしにmountできない。

## Acquisition gate

現契約と保存条件の再attestation、Fresh exact dates、Claude review受領とcritical blocker解消、operator明示承認が未完了のため、J-Quants Historical取得は開始しない。committed codeやCIから自動取得できる経路も作らない。
