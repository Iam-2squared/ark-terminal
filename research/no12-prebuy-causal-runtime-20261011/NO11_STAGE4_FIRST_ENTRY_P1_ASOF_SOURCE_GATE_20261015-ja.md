# No.1.1 — Stage 3実測とStage 4 First Entry接続ゲート（2026-10-15）

## Stage 3 実測（ユーザーPC原本）

受領した `no11-2026-rc2-sparse-research-d30f81c94b3f5313.json` のSHA256は
`d30f81c94b3f5313dcd1c2543cc393bca4c095c3e73e22336994c9b686b405ca`。

| 項目 | 実測 |
|---|---:|
| 原取得順の調査銘柄 | 950 |
| 前日基準足・連続ペア・当日足の研究用条件を満たす | 244 |
| Stage 3で実行済み | 40 |
| 未実行（40の実行上限） | 204 |
| 元Frozen RC2 2エンジンの技術的一致 | 13,080/13,080予定tick |
| 受理した原本1M | 7,693 |
| `step(t,None)` に渡した欠損tick | 5,387 |
| 現物のPrimary観測 | 3,965 |
| 元RC2技術エラー | 0 |
| 完全な前日・当日ペアのStage3内再照合 | 0（最初の40に含まれず） |

**注意:** 100%一致は実行済み40銘柄の元2エンジン比較に限る。元ベンダーの時刻ラベル・実受信knownAt、J-Quantsとの数値同一性、本番売買適格性は未認証。

## Stage 3 追加実装

`tools/no11_2026_rc2_sparse_missing_research.py` は固定先頭950銘柄の合格244ペアまで（`--max-replayed 244`）再実行可能。欠損足を補完しない。エラー発生時はBLOCKし、完走時には前段で未照合だった完全ペアも元の2エンジンで照合する。

`--export-asof` は元State9が返した**その時刻の技術的状態**だけを、privateでSHAアドレス付きJSONL.gzに保存する。各銘柄327予定tickを順序どおりに保持し、欠損tickでは `formalPrimary=null`、`numericStatus=NOT_AVAILABLE`、`sourceLabel=null` とする。先読み教師値・High/Low・モデルscore・BUY intentは一切出力しない。

**as-ofは歴史的な実受信時刻の証明ではない。** `researchAssumedBarEnd` はラベル+1分という研究仮定のみ。ファイルの `eligibleForNativeSelectorOrFirstEntry=false` を解除しない。

## Stage 4 — 元Frozen First Entry P1_Q70の入力検証

`runtime/no11_first_entry_p1_asof_gate.mjs` / `tools/no11_2026_first_entry_p1_source_gate.mjs` は次を監査する：

1. 元Frozen P1_Q70契約（Git blob `62f10b9f12fc968daa2a9393737f2323cdd99307`）が不変。P0 numeric 110、P1 numeric 148、P1 categorical 15、最初のscore>=threshold、同一session|symbolのWatchなどの仕様。
2. Stage3の保存監査レポートの原本SHA・244件の合格分母・2エンジン一致件数・発注OFF・既知時刻未認証。
3. private State9 as-ofファイルのSHA、原4,327銘柄取得順、各銘柄327tick、受理/欠損/Primaryの件数、欠損時に状態を捏造していないこと。
4. 元P1が必要とする**Va分足売買代金/VWAP、Frozen SelectorのWatchイベント、モデル本体と前処理/閾値、全148+15特徴量、実受信knownAt** が未認証であることを明示。

Stage4が `PASS_SOURCE_AUDIT_NATIVE_BLOCKED` と出ても、**正式First Entry推論は0行、BUY intentも0件**。現段階の「元State9技術的再現→First Entry入力境界」は接続できるが、元First Entryモデル推論の接続完了とは呼ばない。

## 次の実行と統合優先度

ユーザーPCの既存RSS原本でStage3の固定244ペアを再生し、同時にprivate as-ofストリームを生成する。Stage4で元Frozen P1の入力監査を行い、小さな結果JSONのみ受領する。**新たなRSS取得・再学習は不要**。

次のボトルネックはState9エンジンの不一致ではなく、元SelectorのL0日足・マスタと元P1のVa/Watch/前処理・本番時刻の証跡。既存原本から確認できるものだけを接続し、未取得項目を合成して正式モデルへ渡さない。

Frozen原本、旧24モデル、main、Excel口座・注文機能は変更なし。研究用Shadowのみ。実注文はOFF。
