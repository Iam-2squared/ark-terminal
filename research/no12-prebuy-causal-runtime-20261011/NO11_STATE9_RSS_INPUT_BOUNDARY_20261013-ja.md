# No.1.1 Frozen State9 ← MarketSpeed II RSS の入力境界（2026-10-13）

## 実機確定事実
- 7203.T、1M 295本、5M 99本、ローカルOHLCV検査不正0・重複0。
- 証跡SHA256 `f65aa90e2b2f11bb3995070164df0f57eb2d980303ac3a5ffa4411ae7d85ced6`。
- 保存証跡に対する1M→5M比較では開始/開始57/57一致。他の3解釈は0一致。比較不能42本。
- 上記は**ベンダー仕様の正式な開始時刻認証ではない**。

## Frozen State9原本から確認した入力契約
`research/state9-structural-exit-v2-20261003/FROZEN_SOURCE/input_gate.py` は `JQUANTS_V2_EQUITIES_BARS_MINUTE` の1分足、元ソースTimeを開始時刻として `bar_end=Time+1分` に変換。opening mixed minute、continuous、terminal auctionを分離し、予定分ordinalと既知時刻を処理する。

`FROZEN_SOURCE/RC2_CONTRACT.txt` は**確定済み1分OHLC**の逐次入力を要求し、CloseでDC/pivot/破壊、High/Lowで停止帯とRange、Openで整合性を確認。State kernelは円建ての価格を直接受けず、開始前に固定された `U/P_ref` で変換したexact normalized OHLCを受ける。RC2の数値契約ではfloatのままState判定することは禁止。

**重要：原本J-Quantsのバー時刻・競売区間とRSSの観測足を同一扱いにしない。** 今回の57/57はOHLCV集計整合性であって原本State9の再現ではない。

`runtime/no11_state9_rss_input_boundary.mjs` と `tools/no11_state9_rss_input_boundary_check.mjs` は保存済み市場証跡から、観測期間・欠測疑い・一致件数・未解決ブロッカーを監査するだけ。State9を実行・偽造しない。

## 実行
```powershell
$repo="C:\ArkTerminal\no12-launcher"
$research="$repo\research\no12-prebuy-causal-runtime-20261011"
$file="$env:LOCALAPPDATA\ArkTerminal\No12\chart-evidence-b919f2bac393428da53404871b42632c.json"
node "$research\tools\no11_state9_rss_input_boundary_check.mjs" --evidence $file
```

- `NO11_STATE9_INPUT_BOUNDARY=MARKET_DATA_AUDITED_NOT_CONNECTED` が正しい研究出力。
- ベンダー足ラベル/終値確定/auction、前営業日U、P_ref、exact変換、予定ordinal、known_at、Frozen kernel、数千銘柄Selectorが未認証。
- 既存Frozen/No.1.1の意味・閾値・モデルは変更0。発注0。productionReady=false。
