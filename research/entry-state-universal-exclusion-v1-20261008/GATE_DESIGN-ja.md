# 新研究版：Entry State除外ゲート（初回・全空き枠共通）

**ユーザー決定：2026-10-08 / 研究仕様V1 / 実売買・本線昇格ではない。**

## 固定するルール
新研究版では、凍結Entry候補の正式な購入前State9 Primaryが有効かつ `PULLBACK` または `SHARP_DROP` なら、**無条件でそのEntry IDを購入候補から除外**する。新たなランキングやEXITの条件変更ではない。

- 初回の空Slot1、最初から空いているSlot2/3、先行SELLが**合法約定して**空いた枠、資金再利用時、同時刻batchの各候補に、**同じ関数を必ず適用**する。Slotの空き方・資金由来・元MLの強さに例外は作らない。
- `SELL_INTENT` だけでは枠/現金を解放しない。合法fill→現金credit/Slot release→新しいEntry batch候補のState判定→**残った候補**を凍結V5の元優先順位、MAX3、Slot Reserve、S/A/B cap、100株allocationへ渡す。EXITもNo.1をそのまま使う。
- 一度除外したEntry IDは、その後にStateがRISEへ戻っても、枠が空いても再提示・復活させない。同じIDの再び現れたイベントも一律SKIP。別の新規Frozen Entryを自動生成しない。
- 残った候補がなければ空き枠は空きのまま。既存V5がreserve/cash/lotで見送った候補を後から強制購入しない。無理なbackfill・slot予約緩和・Rank改善の抱き合わせは禁止。
- State未観測/正式利用不可の行は、新しいStateを補完せず、前回研究の`KEEP_STATE_UNAVAILABLE`相当として**別件数**に記録。欠けた実データ・ID違い・未来のState参照・同時刻の処理順不明は`BLOCKED`。現実の受信時刻未認証のため、過去研究の再現を実運用許可としない。

## 何が変わらないか
凍結No.1原本のFIRST LAYER、旧P1のOFF状態、既存Frozen Entry、既存R0 ranking/H2/H3/H5 PAVA/ML、V5 MAX3・slot reserve・配分・EOD/費用、購入後のSHARP_DROP EXIT、全過去のEvidence・No.1の20日成績を**変更しない**。新しい条件は`EXCLUDE_PULLBACK_SHARP_DROP_EVERY_ENTRY_OPPORTUNITY_V1`として別研究版だけに実装する。元No.1にこっそり重ねず、新研究の比較相手として残す。

## 研究判断の現状
既存Developmentの9×RESET20で両State除外は中央値 ¥1,221,394.30、元No.1 ¥1,216,396.70。両者とも2倍0/9。これは同一条件研究の参考であり、Fresh/OOS性能認証でも新最適版の証明でもない。今後の研究は**この両State除外を固定した上で**、空いた枠にどんな購入を通すか（または空けておくか）を分析し、20営業日で100万円が200万円にどこまで近づいたかだけで評価する。

### このブランチの成果
`RESEARCH_POLICY_CONTRACT.json`、研究専用の`entry_state_gate.py`、合成fixtureテスト `test_entry_state_gate.py`。**原No.1本線のruntimeには接続していない**。
