# Phase57 R53 — EXIT-only finite integration / controlling handoff

Saved JST: 2026-09-28. Branch: research/phase57-long-only-cash-equity. Draft PR #587. Preperformance protocol commit: `3022bcb039077be5d3c84f1d7d7ca19a3cb90c3c`; tested zero-fit SHA: `531fcede83dae543eafff922e1307a8e6a755fa5`; exact finite execution SHA: `482c2ee4d90a361db5181177148af267fca3f8bd`. The enclosing commit of this handoff should be read from latest GitHub; do not infer its SHA from this document.

## 判定

**NO_SELECTION_STOP / INTEGRITY_PASS / FULL-PERIOD_MEASUREMENT_BLOCKED.** 今回の1候補は追加fit 0で保存済みR52-Bのtemporal OOF予測を使った別のEXIT policy trial。65テストのzero-fit CIはrun 36332343505 PASS、有限run 36332644609もSUCCESS、独立audit PASS。しかし大Winnerを保持できず、実際にfundされた1銘柄の約定・時価証拠も欠け、IM 24日のFinal Equityを認証できない。利益化完成・新Final EXIT SELECT・production合格のいずれも主張しない。

R50-A、R52 A/Bは旧NO_SELECTIONのまま。Frozen Selector、IM/R1 Entry、Dual Freeze `4878a1cc53430e816261dea0fb16aeb53b3c238d`、保存済みCAPITAL_V3_B CI score、R37 sizing、100株、MAX3、初期¥1,000,000、現物現金のみは変更0。

## IM: 同一Capital・24取引session

| 指標 | R50-A対照 | R53単一候補 |
|---|---:|---:|
| 購入 / 確定売却 | 79 / 79 | 44 / 43 |
| Initial / Replacement | 72 / 7 | 13 / 31 |
| 購入/日 平均・中央値・最大 | 3.29・3・4 | 1.83・0・11 |
| Funded ≥5% / ≥10% | 27 / 15 | 10 / 5 |
| ≥5% reach | 27/158 = 17.09% | 10/158 = 6.33% |
| Replacement ≥5% / median上値 | 0/7 / 1.787% | 4/31 / 1.787% |
| Replacement確定PnL | −¥123,935.66 | −¥31,226.93 |
| 価格評価可能時間の稼働率 | 76.84% | 71.07% |
| 80%以上稼働した有効時間割合 | 58.29% | 52.87% |
| 有効mark時間 / 全7,800分 | 7,779 / 7,800 | 1,604 / 7,800 |
| 認証EOD / 欠損EOD | 24 / 0 | 4 / 20 |
| 確定取引PnL | −¥112,868.99 | −¥32,311.65（未決済を含まない） |
| 確定取引PF / 勝率 | 0.814 / 44.30% | 0.728 / 46.51% |
| Final Equity / 24日Return | ¥887,131.01 / −11.2869% | **null / null** |
| EOD MaxDD | −16.12% | null |
| 日次 算術・中央値・幾何 | −0.3938%・−1.2299%・−0.4978% | null・null・null |

候補の最終cash ¥651,530.35は**最終資産ではない**。2025-07-28の `245A0`、Frozen Entry `2025-07-28|245A0|814` が15:30に確定売却不能となり未決済で残る。途中で正当なSELL_INTENTが無く、後から利用可能だったかもしれない過去OPENへ戻せない。原本のterminal auction minute930と翌日以降の認可済みmark/企業行動・保有数量連続性が不足。旧R52の `2025-07-23|62650|883` を今回はfundしなかったが、別の欠損銘柄を買った。20日分の欠損EODを0%化せず、資金稼働80%達成も**UNVERIFIED**とした。

## 同一Entry・同一数量: 旧79件の売却判断診断

| 旧funded群 | R50-A Mean Net | R53 Mean Net | R50-A PnL | R53 PnL |
|---|---:|---:|---:|---:|
| ≥5%上値（27） | +4.896% | +1.506% | +¥329,595.75 | +¥106,540.60 |
| ≥10%上値（15、上行の内数） | +7.468% | +1.914% | +¥269,377.29 | +¥76,138.20 |
| 3–5%上値（17） | −1.089% | +0.391% | −¥48,156.91 | +¥13,735.00 |
| <1%上値（20） | −4.660% | −1.211% | −¥272,430.61 | −¥71,896.05 |

≥5%群は同一数量で **−¥223,055.15**、3–5%群は +¥61,891.91。≥10%は≥5%の内数なので利益差を二重加算しない。旧79件全体の同一数量PnLはR50-A −¥112,868.99、R53 +¥16,517.25だが、これは購入競合を無視したLayer A。後者をR53 Portfolio Returnと呼ばない。最初のR52誤売却では旧IM Winner 27件のうちCORE 19件、PREFIX 16件で予測継続価値が負、固定教師の実現継続価値が正だった。今回の3連続条件でもWinner保護に失敗した。早売り原因の完全識別は未証明。

## 資金循環の実際と円単位の限界

IMでは対照と比べて27 IDを新たに購入（うち≥5% 3、≥10% 0）、62 IDを購入しなくなった（≥5% 20、≥10% 10）。追加IDの**確定済み**PnL −¥6,322.76（27件のうち1件は未決済）。共通IDの確定PnL差 −¥10,200、対照だけが保有したIDのPnL控除 +¥97,080.09、確定取引差額 +¥80,557.34。未決済 `245A0` の時価を認証できないため、+¥80,557をFinal Equity改善と扱わない。IM ≥5% missの `UNRESOLVED_CASH_LOCK` は131件で、miss理由の変更はreach改善ではない。各positionの全bucket、Initial/Replacement/Combinedと資金shareは RESULT の4つの buckets JSON。

## R1 / 資料の復元

R1候補は103購入・102確定売却（Initial20 / Replacement83）、≥5% 25・≥10% 10。対照は32/31、≥5% 12・≥10% 8。ただしR1候補は `2025-08-01|35600|751` のauction/跨日mark未解決で、認証EOD 8/24、Final Equity・全期間Return・日次率はnull。対照も別の `2025-08-04|36700|602` により9/24のみ認証。R1の売買件数だけで成功を主張しない。

GitHub上の [PRECOMMIT.json](PRECOMMIT.json) / [READINESS_AUDIT.json](READINESS_AUDIT.json) / [POST_ACTION_CLOSURE_AUDIT.json](POST_ACTION_CLOSURE_AUDIT.json) / [FINAL_CLOSURE.json](FINAL_CLOSURE.json) / RESULT 以下の32ファイルだけで評価を復元できる。結果には4台帳、paired Layer A、各armのasset curve PNG・equity CSV/JSON・daily CSV、bucket、scorecard、独立audit、exact receipt、全hashを保存。元OOF予測・fold・modelはR52 cycle2の既存GitHub分割ArtifactをSHAで固定して参照。有限Action 36332644609 / job 108657409718 / GitHub artifact 10936206149、zip SHA256 `a99f9aacd595480da736f2adff2224424ad6b3580fa093f76af01fe9955af3b1`。CI receiptのtested SHAは `531fcede`、Actionは `482c2ee4` の同一政策ソースに65 testsを再実行。saved predictionからの再Replayはbyte-identical、独立再fitのprediction byte一致は未試験であり主張しない。

次工程は未解決positionの合法なterminal価格、または実際の別時刻fillと跨日mark・企業行動の許可を、銘柄・日付・knownAt付きで別途検討すること。provider新規取得・Protected/Fresh/OOS新規開封・仕様後付け修正なし。新候補や新学習には別のpreperformance契約が必要。Safety9全false、broker/Excel/RSS書込・live/paper・production・main merge・force pushなし。過去R49/v0のallowlist外decode履歴は消していない。
