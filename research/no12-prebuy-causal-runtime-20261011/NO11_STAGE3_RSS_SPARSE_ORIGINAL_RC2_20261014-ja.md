# No.1.1 Stage3: 欠損RSSを維持した元Frozen State9 RC2の再検証（2026-10-14）

## 実測先頭950銘柄の再集計

ユーザーPCから受領した `no11-2026-original-rc2-technical-2e79d4f530ed492b.json`
SHA256 `2e79d4f530ed492bf8c82a1df63b641ba1b3ab5c6ab4608c6a9b9c3adefbd5bc` によると、原取得順の950銘柄では、前営業日・当営業日各327本（含む区間特殊足）の完全ペアは4件のみ。元Frozen RC2の両エンジンは4件全て一致し、合計1,308受理tick・1,279有効Current Primary観測・不一致0件。946件はソース不足（前日完全でない888、当日完全でない6、ソースUnavailable52）で、元State9が失敗した銘柄ではない。

## Stage3の目的

前日あるいは当日の1分足が部分観測である銘柄で、**欠けた足を補完せず**元Frozen2エンジンがどの程度一致するかを確認する研究用機構のみ追加する。**前日327本を満たさないからと言って勝手に値段を作らない。**

`tools/no11_2026_rc2_sparse_missing_research.py` は元の2026年3回取得保存アーカイブと全4,327銘柄のハッシュ付索引を再照合し、元 `research/state9-structural-exit-v2-20261003/FROZEN_SOURCE/` のオリジナル Python `normalize80.py`、`normalize120.py`、`candidate/api.py`、`independent/api.py` を呼び出す。元のFrozenコードファイル自体は全く変更しない。

### 入口の厳密な条件

- 検証対象の銘柄選択は**取得リスト先頭950銘柄固定**。利益や後から得た状態で選別しない。
- 前営業日：09:00 / 12:30 / 15:30の基準足が原本にあり、通常取引時間内の**連続した**1分足リターンペアが30件以上。
- 当営業日：観測された元の1分足が15本以上。
- 技術リプレイは完全ペアも含め **原取得順の最初の合格40ペアまで**。残りは「上限により未再生」と記録し、PASSに含めない。
- 前日観測足をそのまま元Frozen 80/120正規化器に渡し、UとP_ref、座標が一致することを確認。元のRC2両エンジンは元の現物足だけで動かす。
- 当日全327予定tickを順に評価し、原本に存在しない1分足は両エンジンへ `step(t, None)` を渡す。前値持ち越しによる入力価格捏造は禁止。元エンジンが内部に保持する「観測されていない状態」を、観測ありとは数えない。
- 前日・当日が両方完全なサンプルはStage2の完全リプレイ結果と同一件数・同一Primary分布になることを再照合。

この運用上の30ペア/15足基準は**研究用の容量・品質下限**であり、元のFrozen SelectorやState9の合否条件ではない。結果の分母を明示し、数値を都合よく上げ下げしない。

### 検証・出力

保存原本への読み取りのみで、出力は `no11-2026-rc2-sparse-research-<SHA prefix>.json`（小さなprivate集計）一つ。銘柄別値段・予測・順位・個人口座情報は書かない。

監査は「ソース不足の分類」「全銘柄の観測可否」「技術実行ペアと元エンジンの一致tick」「元State9で有効と判定されたPrimary分布」を分離。元エンジンの不一致時は全体をBLOCKする。合格した場合でも `actualBrokerFirstSeenTimeCertified=false`、`stateLabelsEligibleForLiveSelectorOrEntry=false`、`originalFrozenFilesMutated=false`、`productionReady=false`、`orderTransmission=false`。

実行は `python -B tools/no11_2026_rc2_sparse_missing_research.py` の必要な私有レポートパス付きコマンドで行い、必ずStep2実測950件のSHA証明に一致した場合のみ進める。

## できないこと

MarketSpeed IIの `RssChart` 過去ログは、現物のExcel受信時刻や元J-Quantsのdecimal数字列を証明しない。架空の `known_at=t` は「RSS分足ラベルが開始時刻で、その1分後に使用可能」という技術仮定にすぎない。

元Frozen Selectorには前日調整済み日足・市場区分・分足売買代金Va・セクターなどが別に必要。Stage3のRC2元エンジン一致から、正式Selector・First Entry・H2/H3/H5 R0・Capital実口座・Structural EXITへ**自動的につなげない**。

これらの入力証明が揃わない状態では、Stage1合成統合が稼働していてもNative E2Eの証明にはしない。

**Frozen原本、旧24モデル、main、個人Excelブック、口座および発注許可の変更なし。**
