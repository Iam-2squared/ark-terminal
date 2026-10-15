# Ark Terminal No.1.1 — 仮学習完了 → Shadow統合 Stage 1

## 2026-10-14 利用者選択

H2/H3/H5は**2025年データによる研究モデル3本の学習を仮完成**として固定。2026年RSSを無理に教師付き学習に変えない。元Frozen No.1.1、元24 OOFモデル、main、PR #591、ブローカー口座・Excel原本は不変。実注文と自動昇格は禁止。

権限源は `NO11_H235_PROVISIONAL_TRAINING_COMPLETE_INTEGRATION_GATE_20261014.json`。2025年の研究モデルは発注候補へ使用しない。独立したfresh OOS検証は未達成。

## Stage 1: 実際に実装した接続

`runtime/no11_provisional_shadow_integration.mjs` は次の異なる経路を結ぶ：

1. **合成ASOF source frame → research candidate gate**：時刻逆行、post-fill/future教師値、外部の個人保有銘柄、PULLBACK/SHARP_DROPの新規Entryを拒否する。これはFrozen Selectorのスコア生成ではない。
2. **合成 First Entry score/threshold → synthetic eligibility**：元First Entryモデルの推論ではない。研究用スコア比を元H2/H3/H5 R0と混同しない。
3. **元Frozen Capital V5 `allocation.py` / `slot_policy.py`**：`runtime/no11_frozen_v5_synthetic_stage.mjs` から元 `integration/no1-1-msii/tools/no11_capital_v5_shadow.py` のPython処理を実行し、元S/A/B/Slot Reserve/100株/手数料を合成入力で通す。入力には合成rank/ML/scoreと合成到着統計を**明示的に要求**し、研究モデルの予測値を捏造して流用しない。
4. **No12 synthetic cash**：元Capital V5の合成出資数量と100株の整合を確認して、合成BUY intent→合成BUY fillへ進む。元Capitalのライブ注文ロジックではない。
5. **State9 SHARP_DROP合成checkpoint → synthetic EXIT proposal**：買い約定後に確認された架空のState9 Primaryを検査し、SHARP_DROPの場合のみ売りintentを提案する。元のState9/Path生成やStructural EXIT v3/15:20 EODを再現したわけではない。
6. **合成 SELL_FILL → 同日新規BUY待機**：同時刻はSELL_FILLをENTRY_SIGNALより前に処理、初回の合成売却約定で以後BUYを拒否。SELL_INTENTだけでは枠・現金を解放しない。

実行サンプル：`tools/no11_provisional_shadow_integration_demo.mjs`。**全データ合成。** 例えばSバンド・現金70万円・株価1,000円・300株に対して元Frozen Pythonが合成配分300,150円（税込）を計算し、同数をSyntheticCashに渡している。利益や予測性能を示す値ではない。

Windows GitのCRLF対応：`tools/no11_capital_v5_crlf_safe_synthetic.py` は元Frozenソースと元bridgeのGit blobをメモリ内LF正規化で完全照合し、**同じ元のPython関数**を呼び出す。元ソース・元bridgeを変更しない。

## 2026年の実RSSとの接続境界

`runtime/no11_saved_integration_preflight.mjs` と `tools/no11_saved_integration_preflight.mjs` はユーザーPCの監査済み小レポート4件（source audit / chronological index / 5M source gap / price-only outcome）をSHA256と行数で接続し、結果をprivate不変JSONへ保存する。**これは実RSSで戦略が走った証明ではなく、入力原本が追跡可能である証明。**

- RSS 1M: 3,705,797本 / 4,071銘柄（4,327リクエスト）。
- 5本揃った暫定5M: 337,023本。元Frozenの部分観測5M変換や業者ラベルの完全同一性は未認証。
- 8日×10時刻の価格参照: 59,712件。未来区間完全観測: 17,251件のみ。+5%未判定41,888件を負例へ変えない。
- 元Selector L0の調整済み日足、master市場区分・普通株区分、元L1の分足売買代金Vaとセクター等の情報がRSSアーカイブにない。最新のRssMarket値を歴史的Va・修正済み日足の代用品にしない。
- 本番時のブローカー実受信時刻、native Selector/First Entry/State9/モデルR0/Structural EXIT/Capital funded account状態は未認証。

## Stage 1 判定と残作業

| 部位 | Stage 1 | Frozen native運用 |
|---|---|---|
| 学習H2/H3/H5 | 2025研究モデル3本仮完成 / 個別offline scorer PASS | 旧24本への置換なし、採用未審査 |
| RSS原本 | 読取専用・SHA監査済み | 価格以外のL0/L1不足 |
| Selector/First Entry | 合成観測→synthetic eligibility接続 | **BLOCK** 実モデル推論・as-of未接続 |
| State9/Path | 合成状態を新規Entry/EXITで検査 | **BLOCK** 元State9生成・Pariy未接続 |
| Capital V5 | **元Frozen Python S/A/Bを合成入力で実行** | **BLOCK** native候補・リアル口座検証不足 |
| EXIT | 合成SHARP_DROP intent→SELL_FILL待機規則実行 | **BLOCK** 元Structural/EOD/実約定未接続 |
| 発注 | 機能OFF | **不可** |

Stage 1の次は、既存RSS＋保存原本のみで元Selectorの必須入力の正当な再現性を調べ、成立しないならネイティブ同一と偽らず別の研究用adapterとして区別する。First Entry/State9/H2H3H5 R0の順に接続、既存元Frozen Capital V5のブリッジとEXITへ合わせる。再現性を示せない入力を自動補完したり、モデルを自動昇格させたりしない。

**最後まで** `productionReady=false`、`orderTransmission=false`、main未マージ、Frozen原本未変更。
