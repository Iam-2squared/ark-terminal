# XR00 — 新Ranking実資産研究（開始・保存）

**State:** SOURCE LEVEL AUDITED / ROW-LEVEL R-JOIN REQUIRED / NEW RANK NOT YET TRAINED. No.1研究基準は不変。

研究の唯一のPrimary判定は**100万円→20営業日最終資産→200万円までの距離**。AUC、S正答、DROP件数では採用しない。No.1 frozen source public `fee1458e...`, private `9276308...`、Capital V5 MAX3・SHARP_DROP EXIT・FIRST LAYER/Entry/P1現在状態・約定/費用は一切変更しない。旧RG01 `NO_INCREMENT` を維持。

## 既存原本から独立再会計した結果

固定9×RESET20におけるNo.1最終資産中央値 **¥1,216,396.70**。旧EXIT中央値 **¥1,245,688.10**。9窓の対応差合計 **−¥71,321.05**、paired差中央値−¥14,038.50、改善3/9、200万円到達0/9。9窓は大きく重複するDevelopment。

資産差の9窓会計分解：共通取引EXIT +¥67,966.00、同数量差−¥63,492.60、E_ONLY新規購入−¥56,729.60、C_ONLY差−¥19,064.85。費用後正PnL差−¥27,499.00・総実損増額¥43,822.05で差引−¥71,321.05。

Private原本の9窓E_ONLY account trade192件はPLUS84/MINUS108。PLUS gross+¥314,759.20、MINUS absolute ¥371,488.80、net−¥56,729.60。**新規購入を全部消して利益が増えるとはいえない**。E_ONLYでR>=+2も31件存在。9窓のunqiue purchased EntryはE152/C123、C/E一度でも共通119、Eだけ33、Cだけ4。unique countsと重複window trade countsを混同しない。

2026-10-05元Privateパックから V5 native 1039 candidates・38 Development sessions・583 symbolsを抽出してSHA一致検算。Numeric27, categorical7, liquidity13 source fields。PIT実受信時刻は全1039 UNKNOWN、厳密BUY_INTENT as-of認証0であり研究用入力に限定。

## 次工程

XR00 full: private RD01 exact R_NEW labels (known1016/unknown23) を同Entryでjoin、Exit理由、Winner損傷、E_ONLY追加購入、資金/slot因果時系列をevent levelで整理。
XR01: NEW Rankingを「No.1凍結EXITの費用後実現R/Economic contribution」を教師にして事前固定。未来State/MFE/MAE/Exit結果を特徴入力にしない。
XR02: 別系譜Rank fit・時系列forward OOF・same-K・amount mass・Winner preservation・asof独立検証。
XR03: 原No.1は変更せず、新Rank出力を**別No.2版adapter**で既存V5 APIへ接続。元V5 admission/reserve/caps/lot/MAX3と旧Frozen Exit/price/cash orderをコード変更せず同一RESET20比較。新Rankによる結果だけ差分。新Rankを従来ML/bandにどう変換するかは事前に署名し、後付け調整は禁止。

Fresh/OOS、original as-of、same-price capital resale, new rank wealth impactは未検証。研究sourceだけでは新Rank改善を認定しない。Order, broker write, paper/live, main merge, production changeは0。
