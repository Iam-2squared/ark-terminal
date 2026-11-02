# No.1.1：保存済み入力の準備と、RSS収集＋常駐推論の一括起動

2026-10-25 JST / PR #592 / `research/no12-prebuy-causal-runtime-20261011` のみ。元Frozen、別モデルbranch、main、元Excel、発注許可は変更しない。

## 実装した範囲

`tools/no11_received_session_bootstrap.py` と `windows/Run-No11ReceivedSessionReadOnly.ps1` を追加した。

実在する既存原本を設定ファイルで指定すると、既存の日足exporterでG1 PASS maskとChart50計画を生成し、当日マスタの契約・受信時刻・対象銘柄を既存Node validatorで確認する。前日contextは元State9の正規化処理で実際に読み込み、使用可能件数と欠けている銘柄をprivate記録へ出す。元P1 F5と任意の元H235 24モデルの読み込みが通ってから、既存read-only collectorを起動する。

collectorが一時Excelを用意した時点で、保存先・プロセスID・計画ファイルSHA256をready通知へ書く。bootstrapはこの通知を確認して同じ保存先へ既存常駐consumerを接続する。収集終了まで保存先の出力を待つ必要はない。

`no11_received_pipeline_service.main` の任意のsupervisor callback以外、既存のモデル実行・受信時刻・重複判定・State9再生ルールは変更しない。単独のconsumer起動方法も引き続き使える。

## これは「必要な市場データをすべて新規取得した」という意味ではない

**当日マスタの新規取得、企業行動の新規認証、存在しない前日分足の新規取得は今回の実装範囲外。** 指定原本がなければ起動を止める。前日終値から分足を作ったり、`corporateActionsCleared`等を通過用にtrueへ変更したりしない。

前日データの入口は次のいずれか1つ。

- 既存の `ARK_NO11_RSS_P1_PREVIOUS_CONTEXT_V1` JSON。
- 前営業日に保存された `ARK_NO11_RSS_CHART50_1M_CAPTURE_V1` のSHA256名付きsnapshot（明示指定、最大8ファイル）。前営業日のOHLCVだけを集約して既存context形式へ変換する。矛盾する同時刻バーのある銘柄は除外する。Vaは生成しない。観測できた前日バーが部分的なら部分的なままとし、終日網羅を認証しない。

この2番目は**指定schemaの保存済みデータが実際にある場合だけ**使える。過去の別形式のtraining-batchを無条件に読んだり、ユーザーPCにそのファイルがあると推測したりしない。

当日masterも既存 `ARK_NO11_DATED_MASTER_RECEIPT_V1` が前提。`commonEquity`、`priceBasisVerified`、`corporateActionsCleared`等は元入力の確認結果を検査するだけで、新しく保証するものではない。

## 設定はprivate JSON 1つ

以下は構造の例であり、このパスのファイルがPCに存在すると主張するものではない。必要な原本の実際のパスを設定する。個別銘柄・株価・モデル係数をこの設定やGitHubに書く必要はない。

```json
{
  "schemaId": "ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1",
  "sessionDate": "2026-10-26",
  "dailyRun": "C:\\PRIVATE\\existing-daily-run",
  "datedMaster": "C:\\PRIVATE\\verified-dated-master.json",
  "previousContext": "C:\\PRIVATE\\verified-previous-context.json",
  "runtimeRoot": "C:\\PRIVATE\\verified-p1-runtime",
  "h235ModelRoot": "C:\\PRIVATE\\original-24-models",
  "privateRoot": "C:\\PRIVATE\\received-session-output",
  "samples": 4,
  "historyBars": 120,
  "warmupSeconds": 20,
  "productionReady": false,
  "orderTransmission": false
}
```

`previousCaptureFiles`配列は`previousContext`の代わりに指定する。併用しない。保有・既存Watch・未約定・他のChart枠を既存契約で固定する場合は`pinsFile`を追加する。口座状態を指定しないテストは実口座検証済みとはならない。`h235ModelRoot`を省略すると従来のP1までのread-only経路になる。

`privateRoot`は既存のリポジトリ外ディレクトリを指定する。既定samplesは390だが、短時間診断には例の4を使う。4回だけでは終日Selector10回の実行確認にならない。

## 起動

PowerShell側は、既存P1手順で用意したPython 3.12 / numpy 2.3.5 / scipy 1.17.0 / scikit-learn 1.8.0を探す。依存関係の新規インストールはしない。必要なら`-PythonExecutable`で検証済みpython.exeを指定する。

```powershell
& powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011\windows\Run-No11ReceivedSessionReadOnly.ps1 `
  -ConfigFile C:\PRIVATE\bootstrap-config.json
```

`-OfflineSelfTest`は曜日や市場状態に依存しない引数・スクリプト存在確認。モデル・原本・Excel・ネットワークへアクセスしない。

`-PreflightOnly`は**指定営業日に実在する入力とモデル**の検査・準備だけで、collectorは起動しない。翌日分の受信時刻を作り出して前日に合格させる機能ではない。マスタ・前日原本の受領が不足していれば停止する。

場中実行ではMarketSpeed II接続と元のExcel2冊が前提。Ark UI停止・RSS注文許可OFFを維持する。ChatGPTがユーザーPC上でこのコマンドを実行済み、または監視中、という意味ではない。

## 停止・異常時

- collectorとconsumerの起動順序・入力同一性を照合する。複数のbootstrapは既存file lockで拒否する。
- collectorが正常に終わると、consumerは最後の完全なsnapshotを一度処理して終わる。
- consumer異常やCtrl+Cでは、bootstrapがcollectorへstopファイルを出す。分境界待機中も最大500ms単位で停止確認する。
- collectorのfinallyは**自分が作った一時Workbookのみ**を保存せず閉じ、閉鎖確認を返す。元Workbookの保存・Excel全体の終了・プロセス強制終了は行わない。
- 停止が間に合わない、または一時Workbook閉鎖を確認できなければ`bootstrap-recovery-required.json`をprivateRootに残し、次の自動起動を拒否する。元Excelを強制終了して整合したふりをしない。これは注文系Safetyとは別の起動後片付け確認で、勝手なSafetyリセットはない。

保存物は準備済み入力、入力不足のprivate記録、collector log、ready/closed通知、既存の推論checkpoint・SQLite・集計レポート。JSONのmember順序を保ち、元のJS Chart50 plan hashを壊さずに渡す。

新たなbootstrapは独立したread-only収集runである。既存consumer単体のcheckpoint再起動機能は保持するが、この一括起動を本番の口座・注文状態復旧とみなさない。

## テスト・未完了部分

原本State9正規化、実Nodeマスタ・計画validator、前日snapshotのhash・日時・矛盾、モデル不備時の起動禁止、process-ready通知、停止・閉鎖確認・手動復旧ラッチ、Windows PowerShell parseと停止待機、既存consumerの停止通知を検査する。モデル・価格・口座のテスト入力は合成で、プロセス起動の結合テストもmockである。実Excel/実RSS/実口座の成功証拠ではない。

**未完了：当日マスタと不足分足の実取得経路、実RSSでの終日速度・入力精度確認、実P1/H235での連続稼働、Capitalの実口座連携、元EXIT、発注・約定・取消・部分約定・通信断復旧。** 本変更による本番許可、モデル再学習、別branch変更はない。常に`productionReady=false`、`orderTransmission=false`。
