# No.1.1 RSSギャップ時刻・前営業日基準の範囲監査（2026-10-13）

前段の実機出力: 1M 295行、5M 99行、1M→5M開始/開始57/57一致。両足にそれぞれ観測ギャップ1件。実データは `%LOCALAPPDATA%\ArkTerminal\No12\chart-evidence-b919f2bac393428da53404871b42632c.json` にローカル保存済み。

今回の監査は**保存済み証跡のみ**を使用し、Excel/MarketSpeed IIを再起動せずに次を出す。
- `NO11_1M_DAY_RANGE`、`NO11_5M_DAY_RANGE`: 観測された営業日ごとの最初・最後の時刻ラベルと本数
- `NO11_1M_GAP`、`NO11_5M_GAP`: 前後時刻と暫定分類
- `EXPECTED_LUNCH_BREAK_BOUNDARY`: 前場終端と後場開始をまたぐ観測
- `UNEXPLAINED_OBSERVED_LABEL_GAP_REQUIRES_SOURCE_REVIEW`: 予定上の差を説明できない観測ラベルの飛び
- `CROSS_SESSION_ARCHIVE_BOUNDARY_NOT_MISSING_BAR`: 日付境界（当日内ギャップには含めない）
- UとP_refについては「過去日のバーが存在する」ことと「原本定義に基づく基準値が認証された」ことを厳密に分離する。両者とも認証False。

これは**日付・時刻ラベルの診断**であり、未取得の足が取引所で存在しなかったこと、前営業日全セッションの完全性、取引所の確定足、State9の入力準備完了を証明しない。前営業日U/P_refを近似値や当日値から作成しない。

実行:
```powershell
$repo="C:\ArkTerminal\no12-launcher"
$research="$repo\research\no12-prebuy-causal-runtime-20261011"
$file="$env:LOCALAPPDATA\ArkTerminal\No12\chart-evidence-b919f2bac393428da53404871b42632c.json"
node "$research\tools\no11_state9_rss_input_boundary_check.mjs" --evidence $file
```

既存Frozen原本変更なし。発注機能なし。No.1.1はresearch-only、productionReady=false。
