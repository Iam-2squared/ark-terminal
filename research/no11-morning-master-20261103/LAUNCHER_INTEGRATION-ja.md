# 自動入力処理を既存Tradeへ接続

## 追加した実行経路

既存 `Start-No11UnifiedLauncher.ps1` の `RunTrade` に、明示的な当日承認と既存の市場時間チェックの後、元のLIVE設定確認の前に自動入力処理を追加する。

`Trade → 保存済み当日handoff → automatic_morning → 当日マスター → 保存済み前日Context → bootstrap-ready-inputs → 既存の同日RSS LIVE設定と結合 → 元のTrade処理`。

人手の価格入力・security-evidence指定・毎日のZIP提出・銘柄別承認は追加しない。全市場再調査、前日の日足/1分足再収集、戦略変更、資金方式変更、シャドウ試験、限定注文は行わない。

今回のhandoffは2026-11-04に紐付いている。11月5日以降のhandoffを自動生成する夜間処理まで完成したことを意味しない。古いhandoffや発注設定の日付を書き換えて流用しない。

## インストール

`automatic_launcher_install.py`、`launcher_automatic_bridge.py`、固定版 `automatic_morning.py` を専用privateディレクトリーに置く。

```powershell
& $python -B -X utf8 $installer --runner $existingMorningRunner --handoff $scopedHandoff
```

既存ランチャーと当日RSS参照collectorをバックアップし、必要な部分だけを変更する。ローカルのUI2修正、COM対策、RSS資金パッチ、他のファイルは保持する。Windows PowerShell構文解析と元スクリプトのオフライン自己診断を実行する。実口座、Excel、注文にはアクセスしない。

`automatic-inputs.json` を既存 `unified-launcher/settings.json` の隣へ保存する。元のsettingsスキーマは変更しない。初期導入時はbootstrapパス・口座設定・売買承認も変更しない。

## 3冊目の発注用ブック

自動参照取得は、元の2ブックに加え、既存settingsに明示された発注用xlsxが3冊目として開いている場合も許容する。名前だけでなくFullNameと `ARK_ORDER_IDS_READONLY` シート構成を照合する。未知のブックや4冊以上を許可する変更ではない。ブックを開く・閉じる・保存する・注文トリガーを書く処理は追加しない。

## 実発注接続との境界

今回のbridgeは **既に設定済み・当日承認済みのRSS broker configを引き継ぐ**。実際のExcel PID/HWND、アドイン、セッションキー、発注用セル設定、元の到達確率テーブルを新規に生成するものではない。

`bootstrapConfigFile` が空、broker設定がない、古い日付、異なる41銘柄の計画、違うモデル/口座/資金方式の場合は停止する。入力生成の成功と実発注準備の完了は分けて表示する。`NO11_AUTOSTART_INITIAL_BROKER_CONNECTION_NOT_CONFIGURED` は初回の物理発注接続が未設定という意味で、日々の証拠提出や価格入力を求めるものではない。

既存同日brokerが利用可能な場合も、既存privateRoot/台帳を保持する。稼働中セッションの再接続、既存注文の再送、初期台帳へのリセットはしない。発注許可のtrue化、承認の自動生成はしない。実注文は戻り先の従来Trade経路と全既存条件に従う。

## 成功表示の範囲

- `AUTOMATIC_LAUNCHER_INSTALL=PASS`: ローカル差分適用と自己診断の成功。
- `AUTOMATIC_INPUTS=COMPLETE_NOT_LIVE_STARTED`: マスター/前日Context/入力設定の生成。
- `AUTOSTART_INPUT_CHAIN=CONNECTED_TO_EXISTING_TRADE`: 同日LIVE設定への接続。まだ約定や発注成功ではない。

Windows/Linuxのテストは元のスクリプトへの差分適用、ローカル修正の保持、同日broker再利用条件、並行起動防止とファイル更新を検証する。Windowsでは元PowerShellのオフライン自己診断も実行する。実ExcelのRSS受信、非公開モデル、実注文が成功した証拠ではない。
