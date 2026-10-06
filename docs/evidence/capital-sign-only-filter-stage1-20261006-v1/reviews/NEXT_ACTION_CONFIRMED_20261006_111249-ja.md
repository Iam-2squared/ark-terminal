# 🧭 次の作業確認 — 符号専用第1審査を実行する

確認実時計JST: `2026-10-06T11:12:49+09:00`
確認basis HEAD: `76dbfdde9dc51ee381ab2513d102cc27863cdeb8`
研究branch: `capital-main-reallocation-20261005`
現在地: `SIGN_ONLY_STAGE1_DESIGN_READY_NOT_EXECUTED`
今回の依頼: 「次どうする？」への方針確認。新実験の実行報告ではない。

## 1. 今回確認した原本

GitHub refと同HEADの `docs/evidence/capital-sign-only-filter-stage1-20261006-v1/CURRENT_STATE.json` をactual GET。現在地は `DESIGN_READY_NOT_EXECUTED`。未実行項目はA/B/Cの実列binding・score lineage確認、新学習、符号専用評価。別環境の未保存実行有無まではこの読取りから断定しない。

使用する指示書は既存 `WORK_REQUEST.md`（document_id `ARK_CAPITAL_SIGN_ONLY_FILTER_STAGE1_V1_20261006`、SHA256 `79029edf214607e9389ae4429af45a8b16036f4f05184e55477201512991aeee`）。設計仕様は既存 `DESIGN_CONFIG.json`。新しい指示書、別候補、追加Gateは作らない。

## 2. 次の作業順

1. 受領済み旧RNEG ZIPと保存入力・モデル・初回OOFを再利用し、A価格/出来高、B State/Path、C既存causal score、D事前固定統合の列と購入前as-of依存を確定する。同じ入力・教師・前処理・学習条件なら再fitしない。
2. 既存設計の固定構成だけを時間順に測定する。未知期間の予測を保存してから正負ラベルで採点。見送り閾値は、そのblockより前の成熟した初回OOFと符号だけで選ぶ。旧HL0/D1/D2の保存予測も同じ符号専用手続きで比較できる範囲を明示する。
3. 実際のプラス/マイナス × 通過/見送りの混同行列、プラス保存率、マイナス除去率、通過後マイナス率、prediction coverage、block別安定性を報告する。元の主判定SF_D_UNION・alpha=0.10を変更しない。0.05/0.20は固定された補助比較で、結果後に主判定へ昇格させない。
4. 符号専用第1審査の結果と残課題を保存して終了する。第2審査、大中Winner選別、Capital接続、Replacement研究、RESET20へ自動進行しない。

## 3. 評価・凍結境界

教師は固定Entry→固定EXIT/EODの既存費用後結果の符号だけ。正の大小、負の深さ、利益額、U5/U10、R帯、数量、最終資産を学習重み・閾値・合否へ入れない。exact zeroとunknownは分離する。全EntryとはFrozen Entryが発した候補を意味し、全市場銘柄の再選別でも全件購入でもない。

Selector/Entry/EXITは完全Freeze。旧Defense不採用とV5保持は維持する。旧D1/D2も正負教師だったので、呼称変更や金額Gate削除だけで識別性能向上を主張しない。今回の研究期間は反復使用済みDevelopmentのままであり、Fresh/OOS認証ではない。

既存予算: 最大4構成・最大32新fit、等価な旧fitの再実行0、新特徴量生成0、Capital Replay0、第2審査fit0。原本不足で一部が成立しない場合は不足を明示し、既存指示書の分岐に従う。未測定の性能向上を約束しない。

## 4. 今回の実施量

この確認turnの新fit0、新threshold選定0、新Replay0、upstream変更0、Claude0、provider価格取得0、注文0、main merge0。今回の変更はこのappend-only方針記録のみ。

次の実行対象は既存符号専用Work。設計し直すことではなく、承認済みの範囲を重複なく実測して正負分類の結果を得ること。
