# 🏁 State v2 Implementation — 正式Acceptance完了

記録: 2026-09-22T21:31:04.995161+09:00

**`STATE_V2_IMPLEMENTATION_ACCEPTED` — `HISTORICAL_CLOSED_RECONSTRUCTION_ONLY`**

A8・A9の証跡補完、修正後の全件再計算、GitHub CI完走、別環境の完全一致、A1〜A12の最終受入判定を完了。State定義・閾値・Scale・H10・Selector・Opportunity集合は変更していない。

## 📊 最終検証

| 項目 | 結果 |
|---|---:|
| 固定Opportunity | 2,155 |
| NOW全項目・別実装照合 | 77,214 / 77,214 一致 |
| Future全項目・別実装照合 | 77,214 / 77,214 一致 |
| NOW/Futureの数値計算照合 | 各77,214 / 77,214 一致 |
| 入力Context独立照合 | 2,155 / 2,155 一致 |
| Schema検証 | 154,428 / 154,428 PASS（CI・取得後再検証） |
| 正順4worker対CI逆順3worker | 232 / 232ストリーム、4 / 4全体ハッシュ完全一致 |
| Future suffix変更・削除・fresh再計算 | 各77,214 / 77,214 PASS |
| 基本テスト | 322 / 322 PASS（各環境） |
| 追加PIT canary / 最終監査器テスト | 8 / 8、15 / 15 PASS |
| 重複・脱落・無断refilter・説明不能残差 | すべて0 |

322件の内訳は既存158、新しい原本parser/admission45、別実装に再適用した既存数値/Golden119。119件を新規テスト設計や外部レビューとは扱わない。

## 🔎 A8の影響

| 単位 | 結果 |
|---|---:|
| 復元した日足銘柄×日付 | 9,987 |
| 元の日足との一致した参照 | 10,547 / 10,547 |
| 新たに利用不可としたOpportunity×Daily lag | 240 |
| 影響Opportunity / checkpoint | 123 / 4,380 |
| 各checkpoint内のDaily項目変更 | 8,604 |
| 新たなScale / D1の無効化 | 0 / 0 |
| A8によるコアState・イベント・Future教師値の変更 | 0 |

無効化は不足する日をまたぐ価格基準の根拠に限定した。Opportunity削除や欠測補間、都合のよい価格調整はしていない。古いローカル配布版とはsourceVintageId・A8 receiptキー/ハッシュ・qualification表現が異なるが、全77,214件のNOW/Futureについて意味・数値・status・reason・witness・因果境界は一致。差分全件の理由を保存した。

## ✅ A1〜A12

| Gate | 対象 | 最終判定 | 検証範囲 |
|---|---|---|---|
| A1 | Row conservation | **PASS** | 2,155 fixed Opportunities; 77,214 unique keys per NOW/Future. Exact v1 key-set match. Duplicate/drop/refilter=0. |
| A2 | Determinism | **PASS** | Independent fresh normal-order4/hashseed23 and CI reverse-order3/hashseed71 runs. All232 session streams and all4 canonical hashes identical. |
| A3 | Causal/PIT readers | **PASS** | Per-primitive reader enforcement, frozen synthetic canaries and8 extra cutoff/knownAt canaries; all77,214 NOW/Future metadata boundaries checked. Historical knownAt remains null. |
| A4 | Schema/status/value/reason legality | **PASS** | 154,428 complete JSON Schema validations in CI and after artifact retrieval; closed enums and reason precedence tested. No schema or legality waiver. |
| A5 | NOW/Future isolation | **PASS** | Separate modules/schemas; no Future import in NOW.77,214 future-price suffix mutations and77,214 suffix removals preserve NOW, including fresh recomputation. |
| A6 | Fresh prefix replay | **PASS** | Each checkpoint recomputed without previous output;77,214 fresh suffix-removal checks and77,214 exact cross-environment NOW/Future comparisons. |
| A7 | v1-to-v2 transition audit | **PASS** | All77,214 v1-to-v2 rows retained and explained.3,774 core semantic-change rows;188 inferred DEFINED-to-INSUFFICIENT rows disclosed. A8 changes no additional core State/event/Future value. |
| A8 | Timestamp/as-of/vintage | **PASS** | Historical effective-date factor-chain evidence regenerated exactly;10,547 raw Daily projections;240 unsupported lag primitives narrowly masked.704,991 timestamp projections plus6 predeclared raw witnesses; actual receipt latency not certified. |
| A9 | Golden vectors/second implementation | **PASS** | All26 Golden vectors;93 numerical assertions reused against independent code; all77,214 NOW/Future full-schema and numerical comparisons, plus2,155 full input Context checks. R2 lock and failed comparisons/R3 corrections preserved; not external-human review. |
| A10 | Coverage disclosure | **PASS** | All77,214 rows disclosed overall/by time/price/Scale/observation and each2,155 Opportunity. Future CENSORED56,273; no missing-row deletion or threshold retuning. |
| A11 | Explainability | **PASS** | v1 transition,5,660 persistence changes and240 A8 lag masks have explicit causes.77,214 NOW/Future baseline and older-delivery full-field comparisons explained; unexplained residual0. |
| A12 | Acceptance receipt | **PASS** | Explicit user-authorized final adjudication binds tested code/spec/input/vintage/output/environment/CI artifact and all supplemental audits. Acceptance limited to historical implementation; no downstream promotion. |

## ⚠️ Acceptedの範囲

これは過去データによるFrozenルール実装の受入。全77,214行のhistorical knownAtはnullのままで、当時の受信時刻や公表遅延、実市場でのリアルタイム同等性は証明していない。A9は同じassistantによる別実装照合で、比較前lock・不一致履歴・比較後R3修正を開示しており、外部人間/Claudeの承認ではない。

| Future resolution | 行数 |
|---|---:|
| RESOLVED_WITHIN_H | 7,525 |
| NOT_RESOLVED_WITHIN_H | 13,416 |
| CENSORED | 56,273 |

CENSOREDを確定教師として自動利用しない。実装一致率を予測精度・利益率・未知データ成績とは呼ばない。

## 🧾 GitHubとEvidence

- 試験対象コード: `b784e97ac6a5bd1b97a62af4923423596a1258c6`
- Frozen primary: `f9d4b0a764c91d06fac6d8e867198d3a90b1ec64`
- 完了CI: `35721458178` / job `106725082587`、2026-09-22 21:10:58 JST SUCCESS
- 完了artifact: `10692617487`、ZIP SHA256 `ef3e3a631d43702ac7072fb02885c199b92e65378105b651255aca56834db9c4`
- A12: `A12_ACCEPTANCE_RECEIPT.json`（コード/spec/input/output/environment/全監査ハッシュを固定）

古いBootstrap CIはsplit packageをsparse checkoutしていないためimport段階で失敗した履歴を保持。8つのpin自体は一致し、完全なpackageを復元したR3では互換6件もPASS。**専用Completion CIの成功であって、PR全体GREENやmain mergeを意味しない。**

## 🔒 完了後の停止境界

Safety9すべてfalse。providerRequests=0、protectedDataOpened=0。PR #587はOpen/Draft/未mergeを維持。Recognition・学習・Signal・BUY/WAIT・Entry/EXIT・Capital・売買を開始していない。

**次はCausal Recognitionの別途承認・事前固定。今回はState v2 Implementation AcceptedでSTOP。**
