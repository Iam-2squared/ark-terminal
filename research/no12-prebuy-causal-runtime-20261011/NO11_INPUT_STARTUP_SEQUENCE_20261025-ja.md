# 既存Shadow入力準備：原本確認から収集・起動まで同じ入口で実行

2026-10-25 / PR #592。No.1.1 Frozen計算・係数・選定時刻・別モデルbranchは変更しない。実注文はOFF。

## 今回変更した動作

既存の `windows/Prepare-No11ReceivedInputsReadOnly.ps1` を、次の順序で動くように変更した。

1. 既存の日足runからPASS maskとChart50計画を出す。選定対象は既存の最大50銘柄で、新しい選定は行わない。
2. `tools/no11_input_prerequisites.py` が、指定済みの外部確認証跡と根拠bytes、元P1、指定された元H235 24モデル、Shadow口座設定と元Arrival Table・EXITコードを検査する。これが失敗したらExcel取得を始めない。
3. `-PreviousCaptureDir` があれば、その保存済み原本を再利用する。省略した場合だけ、既存 `Capture-No11RssTrainingBatchReadOnly.ps1` を同じ選定済み銘柄に対して実行する。前日archiveの実出力ディレクトリを受け取り、後続へ自動で渡す。
4. 取得処理が終了して一時Workbookを片付けた後、既存の当日RSS基準値取得を実行する。
5. 既存 `no11_prepare_received_inputs.py` が当日master・前日context・bootstrap設定コピーを作る。
6. 既存 `Run-No11ReceivedSessionReadOnly.ps1` を生成済み設定で起動する。既定はPreflightOnly。`-StartShadow` を明示した場合のみ注文OFF Shadowを起動する。

以前のように前日取得を別コマンドで走らせ、保存先をコピーして次の準備コマンドへ渡し直す必要をなくした。全銘柄の再取得や元モデルの再学習はない。

## 前日の確認と当日の実行

`-CheckOnly` は、対象営業日以前に実行できる原本・依存環境の確認。Excel・口座の実読取・収集・推論は始めない。翌日の日付を付けた市場観測やmasterを生成しない。`-CheckOnly` と `-StartShadow` の同時指定は拒否する。

通常の準備・起動は実際の対象営業日に限定する。必要引数は既存の `-ConfigFile`、`-SecurityEvidence`、`-EvidenceDocuments`、`-OutputRoot`、固定依存環境の `-PythonExecutable`。任意の `-AccountWorkbookPath` は既存ランチャーへ渡す。

`-PreviousCaptureDir` は任意になった。存在しないディレクトリを明示した場合は失敗とし、別のデータへ勝手に切り替えない。省略時の前日取得は既定 `-BatchSize 20 -WaitSeconds 25 -Bars 3000 -Period 1M`。BatchSizeとWaitSecondsは既存収集処理の範囲内で指定できる。

`-StartShadow` の場合は元H235の保存先とShadow口座設定も原本確認段階で必須にする。P1だけ起動して統合Shadowが完了したことにはしない。既存の同一run復帰は従来のランチャーの `-ResumeRun` を使い、この入力準備を再実行して台帳の代わりにはしない。

主な出力は `NO11_INPUTS_PREREQUISITES_REPORT`、`NO11_INPUTS_PREVIOUS_CAPTURE_DIR`、`NO11_INPUTS_PREPARED_CONFIG`。口座残高・個別モデル係数は出力しない。原本検査のprivateレポートにも `shadowReady=false`、`actualRssVerified=false`、`modelsScored=false` を明示する。

## 起動前に必要な実物は引き続き必要

確認済みの銘柄属性・価格基準・企業行動の証跡を作成済みとは主張しない。`SecurityEvidence` と根拠ファイルは既存契約どおり実物が必要。未確認のフラグをtrueに埋めず、不足はExcel取得前に止める。hash一致は出所・内容の正しさの独立認証ではない。

PC側の元モデル・RSS接続・当日の日付データ・前日分足をここで取得済みにしたわけではない。`-CheckOnly` の成功も実市場の合格ではない。CIでは外部入出力や私有モデルを模擬し、原本のscope・archive検証コードと実PowerShell関数の順序・停止条件を実行する。

今回の変更に実発注・取消transport、実約定価格・現金・実保有への反映、未反映の `ae037a3` は含まれない。27日の実売買を許可するものではなく、これらと実機通し検証は依然未完了。
