# No.1.1：既存RSS取得形式から前日contextへの接続

2026-10-25 / PR #592、既存No.1.1 Shadowのみ。モデル・ランキング・原本EXIT・Capital・口座接続には変更を加えない。

## 解消する接続切れ

既存 `Capture-No11RssTrainingBatchReadOnly.ps1` は `ARK_NO11_RSS_TRAINING_SYMBOL_ARCHIVE_V1` を出す。一括起動側は `ARK_NO11_RSS_P1_PREVIOUS_CONTEXT_V1`、または別形式のChart50 snapshotしか受け付けていなかった。今回はこの形式間の変換と、取得対象を選定済み銘柄だけに絞る起動手順を追加する。ファイル名のTrainingは既存名であり、今回学習は行わない。

## 新しい入口

`windows/Prepare-No11PreviousArchiveReadOnly.ps1`

既存の日足G1・Chart50計画をそのまま使い、`selectorInputSymbols`だけの取得リストを生成する。通常は約47銘柄、上限50。全4,328銘柄を再取得しない。既存取得器の20銘柄ずつ・1分足3,000本の設定を使用する。実際に得られる本数・銘柄はRSS次第であり、取得成功は別途実機で確認する。

既存の日足runと検証済みPython環境がPCに残っていれば、次の入口を使用できる。

```powershell
& powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011\windows\Prepare-No11PreviousArchiveReadOnly.ps1 `
  -SessionDate 2026-10-26
```

既定の日足runは、会話で確認した `%LOCALAPPDATA%\ArkTerminal\No12\daily-trend-capture\daily-2026-10-23-3de08f7ea26ae46d`。別の場所は `-RunDir` で指定する。出力は `%LOCALAPPDATA%\ArkTerminal\No12\previous-source\2026-10-26`。Pythonが見つからなければ停止し、インストールしない。`-PythonExecutable`で既存のPythonを指定できる。

元のExcel2冊とRSS接続が必要。元Workbookを編集・保存しない既存取得器を再利用する。場中の常駐収集と同時起動せず、起動前の準備として実行する。

## 前日にできることと、当日に確定すること

マスタを指定せず実行すると、取得原本のSHA256・チェックポイント・前営業日の日時を確認し、前日OHLCVだけの中間ファイルを作る。10月25日に10月23日の原本を取得しても、受信時刻を10月23日や26日に書き換えない。前日Vaも生成しない。元State9が使う前日価格基準の品質・企業行動が、この取得だけで確認済みになるわけではない。

`-CaptureDir`にすでに保存したRSS archiveのディレクトリを指定すれば**再取得を省略**する。10月26日には、実在する当日マスタを `-DatedMaster` で指定して再実行すると、既存マスタ検査と元State9の正規化を通した `previous-context-*.json` を生成する。

元bootstrap設定を `-BootstrapConfig` でも指定した場合は、元ファイルを変更せず、`previousContext`を新しい変換結果へ差し替えた設定コピーを出す。他のモデル・資金・入力設定はそのまま保持する。出力行 `NO11_PREVIOUS_BOOTSTRAP_CONFIG=` の設定ファイルを既存一括ランチャーへ渡す。自動で常駐推論や注文は開始しない。

## 不足・異常時

前営業日以外の足は前日contextに混ぜない。5分足を1分足として使わない。元progressのSHA256と実ファイルが違えば停止。原本自体が不正・欠損の銘柄は理由付きで除外し、2本未満の前日足を補間しない。全銘柄が使えなければcontextを出さない。部分的な前日データを終日網羅と認証しない。元コードによる正常化が通ることと、前日の完全な再現は別である。

当日マスタの `corporateActionsCleared`、`priceBasisVerified` は既存検査をそのまま要求する。保存済み日足のfalseをtrueへ変更しない。マスタ取得・企業行動確認は**未解決の別作業**として残る。

## テストと未検証範囲

合成入力による原本形式の変換、元JS計画検査、元State9正規化、Windowsランチャーの引数検査、別日・重複・不正価格・ハッシュ不一致・未確認マスタの拒否をCIで確認する。実行結果はcommitごとのCIを参照する。テスト追加だけで実RSS取得済みと主張しない。

この変更では実RSS、実PC、非公開の元モデルを実行していない。口座連携の未反映変更、実発注・取消・約定照合も対象外。常に `productionReady=false`、`orderTransmission=false`。
