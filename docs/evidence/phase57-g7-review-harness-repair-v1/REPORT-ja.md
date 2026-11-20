# Phase57 — G7表示器修正・旧36例の回帰検証

記録: 2026-09-22T10:58:05+09:00  
開始HEAD: fdcdde9c099dd6b0f59a313f596118083e0de1eb  
事前登録commit: 4f474a2077df7bc5a6655e23317752817a162379

## 結論

**表示器の時刻ずれを修正し、旧36 ACTUALケースで回帰検証PASS。旧G7はFAILのまま、State v2は未Freeze。新しい独立レビューは未実施。**

分類や数値閾値は変更せず、tまでに確定した入力の読み取り、NOW再計算、表示根拠の引き渡しを修正した。これはレビュー用display adapterであって、完全なState v2 schema/77,214-row生成器ではない。

## 修正

- raw STARTをEND=start+1へ正規化し、END<=tだけを採用。knownAtが明示される場合も<=tを要求。tから始まる次の足は描かない。
- 前回の監査portではなく、GitHubから回収した**採用元reference.pyの完全一致バイト**を利用。SHA-256 e57d41b1a9472fb0ed254895d956623a438557f540443c0bee14a6db8f2d8d3d、Git blob 5c5ae2511be02ffb7e38616ec04d80a4c9d17451をローカルで一致確認した。
- そのままのsnapshotを使用。reference_at呼出しを実行時sentinelで禁止し、古いoracle出力をNOWとして流用しない。前日Scaleも同じ元関数で再計算。
- 先にcausal JSON sidecarを確定し、それだけからHTML/PNGを生成。全日archive hashは監査receiptに分離し、未来suffixのhashをState値や図に持ち込まない。
- 最新5本O/H/L/CとEND時刻、Directionの式、構造の成立/確認時刻・保護水準・4本の起点pivot、Rangeの誕生window/固定上下限/接触blockを表示。
- 昼休み/欠測を線で接続しない。観測なしwindowは価格0を作らず明示。正しく表示された入力欠損と、表示の矛盾を区別するRULE_BRIEFを同梱。

## 実行結果

| 検査 | 結果 |
|---|---:|
| 元measurementファイルのSHA照合 | 179/179一致 |
| 表示器・ガードの合成テスト | 49/49 PASS |
| 旧36例のDirection・観測可否・Scale | 36/36一致 |
| 元コードのfresh-prefix Stateと前回のcausal裁定 | 36/36一致 |
| post-t価格変更: JSON/HTML/PNGの不変性 | 36/36 PASS |
| post-t価格削除: JSON/HTML/PNGの不変性 | 36/36 PASS |
| 逆順再実行: ケースファイル | 144/144バイトハッシュ一致 |
| 逆順再実行: receipt | バイト一致 |
| 生成したprimaryグラフ | 72枚（prefix/最新5分を別図） |
| 新しい独立ケース・レビュー | 0 |

144ファイル=36 JSON +36 HTML +72 PNG。2種類のfuture mutationはケースごとに再計算・再描画した。逆順runでも両mutationを再実行した。数値は既存36例のソフトウェア検証であり、予測精度・Entry収益・G7 PASSではない。

### 時刻ずれの修正例

| Case | t | 旧図の末尾 | 修正後の終値 | 最新5分先頭O | Direction |
|---|---|---:|---:|---:|---|
| G7-023 | 10:05 | 1173 | 1179 | 1179 | UNCHANGED |
| G7-030 | 10:45 | 1240 | 1230 | 1229 | UP |
| G7-039 | 09:30 | 98 | 96 | 96 | UNCHANGED |

旧図の末尾はt+1に確定する足の終値だった。修正版は全例で正規化済みEND<=tを使う。ここでの旧値は前回裁定済みの比較用数値であり、NOW sidecar/モデル入力へ混ぜていない。

## 見る場所・再現

`regression_final/index.html`から36例すべてを確認できる。各caseは数値表と2図、exact JSON sidecarを持つ。RULE_BRIEF.mdとコードを同梱し、private GitHubへアクセスできないreviewerにもルール本文が渡る構成。

GitHubにはレポート・検証receipt・source/添付ハッシュを保存する。検証したcausal_card.py/run_regression.py/test_causal_card.pyの実体は、会話添付SOURCE_CODE.zipと全体ZIPに保存する。source ZIP自体をGit管理したという意味ではない。依存する元reference.pyは既存の採用元を参照し、全体ZIPにはその完全一致コピーも同梱する。価格データの元archiveやadmin keyは再配布ZIPへ重複保存しない。

code SHA、環境、入力archive SHA、実行receipt SHAはREPAIR_RECEIPT.jsonへ。再現コマンドはREADME.md。既存出力ディレクトリへの上書きは拒否する。

## 修正中の失敗と範囲

最初のsmokeでraw時刻のintegral floatを厳密intと誤って拒否した。既存G adapterが受け入れる整数値floatに合わせ、分類閾値を変更せず修正。その後の最終49テストと全36例の2runはPASS。出力ファイル所有権とPythonの任意spreadsheet warmupには環境側の調整・警告があったが、研究結果のfail/PASSとは混同しない。

## 残る事項

- G7 v1のFAIL、元A/B回答、元画像を保持。本回の回帰PASSでG7を上書きしない。
- 修正review protocolはDRAFT。binary issueの意味、target-specific control検出、NOW/Future evaluatorの分離、近似重複の回避、二段階blindingを明記した。新しいblind runはまだ開始していない。
- 新レビューの対象・protocol承認後、旧36例を独立分母から除いた既存Developmentで実施する。希少cell不足があれば明示し、黙って旧例をfreshと扱わない。
- 外部差分レビューと有効なG7確認なしにState v2をFreezeしない。実装・学習へは自動進行しない。
- historical receivedAt、企業行動のPIT、provider timestamp規約の外部独立監査は未解決。今回の時間修正は保存済みGの時刻契約との内部整合性であり、clean PIT/Prospective parityの証明ではない。

## Safetyと停止

売買/書込Safety9=false、provider新規0、保護データ開封0、数値閾値変更0、Selector変更0、Entry/EXIT/Capital/main変更0。

**REVIEW_HARNESS_REPAIRED / OLD36_REGRESSION_PASS / NEW_G7_NOT_RUN / STATE_V2_NOT_FROZEN。**
