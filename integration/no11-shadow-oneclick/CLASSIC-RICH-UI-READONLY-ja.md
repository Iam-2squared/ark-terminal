# 旧Ark Terminal UI復元 + 新No.1.1 Frozen Shadow（読み取り専用）

## 要望と完成範囲

以前の「Ark Terminal No.1.1 READ ONLY」で使われていた多画面UI（Home / Selector / Positions / Orders / Performance / System）を、新しい独立Shadowアプリで表示する。元の凍結済みNo.1.1ランチャーやモデルを変更しない。**UIを復元したことと、実RSSおよび本番日付の統合Shadowが実運転したことは別**。

構成：
- **UI原本**：`integration/no1-1-msii/ui/public/index.html` と `ark-readonly-overlay.js` をバイト単位で複写、shaを保持。実口座未接続なら旧Reactデモを表示しない。
- **単一バックエンド**：既存 `ui/ark_shadow_ui.py` の実口座READ ONLY・元Frozen Shadow模擬SQLite読取だけを利用し、`ui/ark_shadow_classic.py` が旧UIのRead Model契約に安全に投影する。`127.0.0.1:8769` の同一オリジンに `/api/status`、`/api/ui-read-model` とUI資産を配置。旧8767サーバーを同時に自動起動しない。
- **Shadowオーバーレイ**：`ui/classic/ark-shadow-classic-bridge.js` が同一オリジンの実RSS口座・模擬台帳を読み取り、元UI画面に「統合Shadow・模擬総資産・買/売履歴・実口座約定」を追加。ブラウザー上で売買や設定変更を許可しない。実口座の総資産は根拠がなければ欠損として表示する。
- **新ランチャーのみ**：`windows/Start-ArkShadowClassicReadOnly.ps1`、`Ark-Shadow-CLASSIC-READ-ONLY.cmd` を追加する。モデル・RSS元2冊・既存ファイルを上書きせず、ステージ名/HRESULTを安全な診断コードとして表示する。別ポート・別private rootを使い旧アプリとの競合を減らす。
- **インストーラー**：`install/Install-ArkShadowClassicReadOnly.ps1` は既存新Shadowの3つの元ファイルと新たな6ファイルをGit blob SHAで検証。新規ファイルだけコピーし、自己テストを通した後、**新Shadowショートカット**だけをバックアップ＋原子的に新起動先に切り替える。元の `C:\ArkTerminal\no11-launcher\...` は変更しない。切り替えない場合は `-NoShortcutSwitch`。

## 最初の起動

元の新Shadowインストーラーで新ショートカットが導入済みであることが前提。下記Classicインストーラーを**Git commitとGit blob SHAを検証してから**実行。インストール後、`Ark Terminal Shadow READ ONLY` のデスクトップショートカットがClassicになり、`http://127.0.0.1:8769/` に元UIの見た目＋新Shadow欄が開く。

- MarketSpeed II・Excelが未起動でも安全。起動コードがMarketSpeedの一意のショートカットを起動（見つからなければ手動）、Excel元2冊を開く。ログインそのものはユーザーが実行。
- Excel元ブック（デフォルトはDesktop上 `Ark_No11_MSII_RSS.xlsx` と `Ark_No11_MARKET_RSS.xlsx`）が存在しなければ、サーバーは無理に別ファイルを作らない。実パスを `-AccountWorkbookPath` と `-MarketWorkbookPath` で指定して起動。
- Excelの第三ブック・複数EXCEL.EXE・危険なRSS発注数式・ブック/シート同一性の不一致なら安全停止。**実行時に全4,328銘柄G1は再取得しない。**
- アプリがエラー停止した場合は `ARK_SHADOW_FAILURE_STAGE`、`ARK_SHADOW_FAILURE_KIND`、`ARK_SHADOW_FAILURE_HRESULT` のみを共有。口座番号・保有内容・ログの全文は送らない。

## Shadowに進むためのゲート

G1: 2026-10-26の全4,328銘柄処理完了、観測G1 PASS429。2026-10-26の1分足は47対象中46が一次利用可能（5029.Tは前日分足不足）。元Frozen P1/H235/Capital/EXITのコード・原本読込は検査済みだが、**2026-10-27のdatedMaster、企業行動/価格基準の独立レビュー、前日Context確定、初回Preflight合格はまだ未証明**。本Classic UIの導入だけではSelectorやShadow模擬取引を起動できない。確認済み当日設定が無い場合、UI・読み取り専用口座観測だけを開始し `Shadow=未起動` と表示する。

設定パスは旧新ランチャーの `shadow-oneclick` と区別して `%LOCALAPPDATA%\ArkTerminal\No12\shadow-oneclick-classic\launcher-settings.json`。スキーマ・許可項目は元 `ARK_SHADOW_ONECLICK_SETTINGS_V1` と同じ。未確認の `EXTERNALLY_REVIEWED` 値は作らない。

READ ONLY、取引注文ゼロ、元Frozenモデル重み変更なし。前の新UIサーバーは `http://127.0.0.1:8768/`、Classic UIは `http://127.0.0.1:8769/`。同じExcelへの複数監視起動は競合するため、原則Classicだけを利用する。