# No.1.1 Stage 2 — 2026 RSS保存足 → Frozen RC2 State9 技術リプレイ

**2026-10-14 / 仮学習完了、統合作業のみ / 注文OFF。**

## 追加した接続

`tools/no11_2026_rss_original_rc2_dual_technical.py` は、既存のユーザーPCに保存済みの2026年RssChart 1Mアーカイブを、SHA256による元の3回取得監査／チェックポイント／銘柄インデックス順序へ照合して読み込みます。

- 過去の実受信時刻（knownAt）を新たに取得したり、元の保存足から遡って復元したりはしません。
- 前営業日＋当営業日の双方が**厳密に327ラベル**（09:00..11:30 / 12:30..15:24 / 15:30）を持つ銘柄に限って処理。欠けた1分足を0出来高の足にしたり補間したりしない。
- 元Frozen `normalize80.py` / `normalize120.py` でU・P_ref・座標を照合。元Frozen `candidate.api.Engine` / `independent.api.Engine` をどちらも実際に呼び出し、Primary・Basis・State9観測可用性などを照合。
- 元Frozen RC2 Python、元のState9意味論、学習済みH2/H3/H5、元Capital V5、main、口座、Excelを一切変更しない。
- 日付は保存済み8営業日の**隣接ペア**だけ。作業対象は元取得順の先頭N銘柄のみ。利益・上昇・結果で銘柄を後から選別しない。
- 送信するのは件数・状態数・不一致コードのみを含む**private小レポート**で、行単位の価格や個人口座情報は出力しない。

## 正直な認証境界

`known_at=t` は「1分足ラベルが区間開始であり、終了時刻までに利用可能だった」という**仮定**で、実際のExcel受信時刻ではない。Excel `Value2` → JSONの数値は元のJ-Quants丸め前decimal tokenとは同一と主張できない。

したがって、**2エンジンの技術的State9一致がPASSしても、そのPrimaryを過去時点に本当に入手できたとは証明できない。** 本番Selector/First Entryの確定候補、H2/H3/H5 R0スコア、原本Structural EXITおよび実発注に接続する許可はない。技術レポートは `nativeLiveState9Connected=false`、`productionReady=false`、`orderTransmission=false` を常に保持する。

## 検証済み範囲

`tests/no11_2026_rss_original_rc2_dual_technical.test.mjs` は合成の完全な327×2営業日で**元の**normalizerと**元の**候補／独立2エンジンを実行。欠損1分足は完全性検査で拒否。

`tests/no11_2026_rss_original_rc2_capture_integration.test.mjs` は3回取得形式の合成チェックポイント・全4,327銘柄索引から最初の3銘柄を監査し、完全ペア1銘柄のみを2エンジンへ通し、不完全前日とSOURCE_UNAVAILABLEを分離、再実行の同一レポートと改ざん拒否を検証。

CIの合成PASSは、**ユーザーPCの全4,327銘柄での技術的State9一致を意味しない**。次にPC内の元データを読取専用で実行し、結果JSONの件数を確認する必要がある。

## 次の開発ゲート

1. 実RSS価格原本の技術的State92エンジン一致数と除外理由を取得。
2. 保存原本のL0日足・マスタ・元L1分足売買代金Vaの有無を照合。存在しないものを合成してFrozen Selectorの正式スコアとは呼ばない。
3. Frozen Selector/First Entryを正しく再現できるsourceが揃う場合のみ、実受信時刻付きの将来Shadowへ接続。満たせない場合は研究アダプターで明示的に代替し、元Frozenモデルの自動昇格禁止を維持。
4. 元Capital V5合成S/A/B接続は前段階で既に検証済み。正式な候補証跡と口座整合ゲートを通るまで売買へ進めない。

**注文送信、mainマージ、Frozen原本変更、新学習、RSS再取得はすべてゼロ。**
