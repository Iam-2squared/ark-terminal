# 📦 旧RNEG Defense ZIP受領確認 — 新しい符号専用第1審査とは分離

確認実時計JST: `2026-10-06T10:55:11+09:00`
確認basis HEAD: `d43d5d40eb2f4ba439be3404ac4edfe4baf1bec9`
確認basis tree: `1f81e2081d1017c22bb0b94e30c2b88f0967a77b`
現在地: `SIGN_ONLY_STAGE1_DESIGN_READY_NOT_EXECUTED`
今回の作業: 受領原本の同定・保存済み正負ラベルと旧actionの集計照合のみ。

## 1. 受領ファイル

`Ark_Capital_RNEG_Defense_20261006_PRIVATE.zip`、23,583,759 bytes。
SHA256: `a70abbbb2e4d9933d7a6479dff4e1081b07627ccaad5c3eeb2c3132e5312f47d`。
ZIP 307 membersのCRC検査はエラーなし。今回利用した下記3ファイルについて、manifestのbytesとSHA256一致を確認した。全memberのSHA256を再監査したとは主張しない。

PRIVATE_MANIFESTの日時は `2026-10-06T09:35:10+09:00`、GitHub_headは `6f3a09e4800a1cccbf359364c9acc9ba1f05e8dc`。同HEADの `docs/evidence/capital-rneg-defense-reuse-20261006-v1/REPORT-ja.md` は09:27:25の旧D1/D2結果、`DEFENSE_REJECTED`。

これは新しい `ARK_CAPITAL_SIGN_ONLY_FILTER_STAGE1_V1_20261006` の実行結果ではない。最新確認HEADの符号専用CURRENT_STATEは `DESIGN_READY_NOT_EXECUTED`。新旧実験を合算・再採用しない。

| 保存入力 | SHA256 |
|---|---|
| RNEG_TARGETS_EVALUATION_ONLY.jsonl.gz | `fe8053da6798adcf01b5f4c09236304f607113c541acfee35a8f4ea74c9b9293` |
| DEFENSE_ACTIONS.jsonl.gz | `0082efc6f8deb496309baea85a52991a5a62e7a2f54077117a55736aa5c83f94` |
| RUNTIME_FEATURES.jsonl.gz | `2ac6acd608385eedf61e5ad912b6ec5a4be5750622167c1f619b30dda323628d` |

## 2. 旧actionを正負件数で読み直した結果

対象はFrozen Entryが発したOOF候補。全市場を再選別した結果ではなく、Capitalによる購入後709件でもない。旧全8block、DEFENSE_OFFを含む。保存済みy_negとactionをEntry IDで1対1joinし、金額・Rの大きさによる再選択は0。

| 実際の固定Entry→EXIT/EODの符号 | R既知合計 | PASS_TO_V5 | VETO_THIS_ENTRY |
|---|---:|---:|---:|
| プラス | 462 | 436 | 26 |
| マイナス | 554 | 509 | 45 |
| 合計 | 1,016 | 945 | 71 |

全OOFは1,039件。R不明23件は別枠で全件PASS、正負分母に入れていない。実行適格1,028件ではR不明12件、正負既知の上表は同じ。

| 符号だけの指標 | 値 |
|---|---:|
| マイナス除去率 | 45/554 = 8.122744% |
| プラス保存率 | 436/462 = 94.372294% |
| 見送りprecision | 45/71 = 63.380282% |
| フィルター前マイナス率 | 554/1016 = 54.527559% |
| 通過後マイナス率 | 509/945 = 53.862434% |
| マイナス率変化 | -0.665125 percentage points |

Rank通過集合も分離: R既知492件は負273/正219。見送り負21/正15、通過負252/正204。通過後負率は252/456=55.263158%、元55.487805%から-0.224647pp。Rank不明R2件は別枠。

見送りprecisionは全Entryのプラマイ正解率ではない。PASSはプラス確定でもBUY指示でもない。この表は旧actionの記述集計であり、旧閾値に使った正利益金額・純価値条件まで符号専用になったことを意味しない。

## 3. 現在の方針を維持

現在の目的は、Capital側の第1審査として、Entry→固定EXIT/EODの正負を購入前情報で分けること。Selector／Entry／EXITは完全Freeze。今回の旧結果をEntry/EXIT変更の根拠にせず、Replacement研究へ主題を変更しない。

次の実行対象は既存の符号専用WORK_REQUEST／DESIGN_CONFIG。教師・学習・比較・閾値・合否には符号と件数だけを用いる。利益額、R1〜R10、RN tail、U5/U10、数量、最終資産を合否に混ぜない。A価格出来高／B State-Path／C既存causal score／D事前固定統合の既存設計を変更しない。

旧D1/D2の学習target自体も正負だった。目的の呼び方だけを変更して識別性能が新たに向上したとは主張しない。等価な入力・学習条件・初回OOFは再利用し、重複fitしない。

第1審査の結果が出るまで第2審査・Capital接続・RESET20 Replayへ進まない。この受領確認では新fit0、新閾値選定0、新Replay0、upstream変更0、Claude0、provider0、発注0、main merge0。旧不採用を維持、V5は保持。新しい実験を開始したとは報告しない。
