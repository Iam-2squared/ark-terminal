# ARK TERMINAL — 統合版 No.1 / 完全参照凍結

**ID:** `ARK_INTEGRATED_NO1_V5_SHARP_DROP_FREEZE_20261008`  
**正式名称:** ARK Integrated No.1 — Capital V5 MAX3 × SHARP_DROP EXIT  
**状態:** USER-SELECTED / RESEARCH REFERENCE FROZEN（2026-10-08 JST）

## 最初に読む順番
1. `INTEGRATED_NO1_FREEZE.json`: No.1の機械可読定義と変更禁止境界
2. `SOURCE_LOCK.json`: GitHub固定commit、原本path、Git blob、公開・非公開asset所在
3. `EVENT_AND_RANK_INTERFACE-ja.md`: 価格・State・SELL_INTENT・約定・資金解放と既存Rankingの接続
4. `BASELINE_RESET20_EVIDENCE-ja.md`: 成績・損失・Winner損傷を含む失敗記録
5. `CHANGE_CONTROL_AND_XR00-ja.md`: 変更禁止範囲と次Ranking研究の入口
6. `FREEZE_INHERITED_VERIFICATION.json`: 保存済み検算の継承範囲と今回実施した確認

## 統合版No.1の意味
No.1は**既存コード・既存モデル・既存データ・既存評価を改変せず、Capital V5とユーザー選択済みSHARP_DROP EXITを一意の研究基準として束ねたもの**。新しいEXIT条件、Capital配分、Ranking、ML学習、現在の実運用設定は作らない。

V5: `CAPITAL_MAX3_SLOT_RESERVE_V1`（MAX3・native H2/H3/H5→ML・slot reserve・100株lot・S/A/B cap）。  
EXIT: `SHARP_DROP_FIRST_OBSERVED_EXIT_V0`＋旧State9 Structural EXIT v3 Local Guard＋正規15:20 EOD。

基準のR0 RankingはNo.1の**既存アダプターとしてのみ保存**する。新Rankingは別系譜で最初から再設計してよいが、No.1のロジックへ差し戻さない。

## 決定の性格
旧EXITより資産成績が向上したと主張しない。保存済み同条件9×RESET20では新EXITが3窓改善・6窓悪化、paired中央値差 -14,038.50円。ユーザー選択の凍結であって性能ゲート合格ではない。

これは**オフライン研究用の完全参照凍結**であり、実運用用build・受信時刻証明・ブローカー接続・注文許可ではない。productionReady=false / Safety9全false。新しい研究での参照原本は必ずcommitとSHAを用い、branch先頭だけを引用しない。

旧コード・旧EXIT比較・失敗したRD01/RD02/RG01・既存FIRST LAYERの系譜も消さない。新研究はNo.1から差分を持つNo.2または研究用overlayとして進める。