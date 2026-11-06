# No.1.1 clean rebuild — 2026-11-03

前回のOperational ZIP・EXIT ZIPを読み込まず、固定Git本体から新規生成する修正版です。
元モデル、重み、Selector、Capital V5、Structural EXITシグナル、通常MAX3、100株ルール、現金確認、発注許可は変更しません。

## 含まれる修正

- 既知の日本語RSS関数名を英語関数名へ対応付け。未知表示は拒否。
- 正しい注文数式エコーだけを除去。注文ID/発注IDを照合。先頭の `=@` だけを正規化。
- `発注済み` は照合待ちで、受付・約定・取消完了とは区別。
- 当日参照を行単位で取得し、観測保存には型を限定したJSONシリアライザーを使用。
- 明示的な `feeCourse: ZERO` に対して `orderTerms.sor: true` を要求。既存設定を勝手に変更しない。
- SELL直前にobserverを再読込みし、ARK注文・ARK残数量・現在保有・外部除外を再確認。
- 手動売却後、個人購入、同銘柄混在、保有数量不一致、不明な帰属では自動SELLを保留。
- CANCELは保有ゼロでも妨げない。BUY、UNKNOWNの再送禁止、送信済み注文の扱いは従来どおり。
- 同一対象週の静的銘柄情報と、当日の独立した変更情報・RSS参照を分離して既存入力生成へ接続。

## 生成元と対象

基準commit: `24b906e19a2623e45701311ca3fbb20dafe11c80`。
`rebuild.py` はこのcommitのGit objectを直接読みます。旧配布物は不要です。
生成対象は既存7ファイル＋新規3モジュール。マニフェストに変更前Git blob、変更後SHA256とGit blobを記録します。
Windows PowerShell 5.1用の日本語スクリプトはUTF-8 BOMを保持します。

## PCでの扱い

`Stage-No11CleanRebuild.ps1` の既定は監査だけです。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Stage-No11CleanRebuild.ps1 -SourceRoot 'C:\ArkTerminal\no11-unified-2026-10-30'
```

`-Stage` を追加すると、検証済みpayloadだけを新しい個人用フォルダーへ書き出します。
**これは実行可能なエンジン一式ではなく、実行先へのインストール・ランチャー切替ではありません。**
現在のworktree、ローカルの週次/RSS/UI修正、Excel、口座、台帳、発注許可を変更しません。
既存ファイルが想定と異なる場合や、適用が混在する場合は拒否します。既存の出力先も上書きしません。

## 週次入力の新しい内部契約

`ARK_NO11_CLEAN_WEEKLY_SECURITY_V1`:
`weekStart` (月曜)、`weekEnd` (同週金曜)、`acquiredAtJst`、`knownAtJst`、
`reviewStatus=EXTERNALLY_REVIEWED`、`productionReady=false`、`orderTransmission=false`、
`dailyGuardDirectory` (個人用絶対パス)、`rows`。
各rowには `symbol`, `commonEquity`, `domesticEquity`, `listed`, `lotShares`, `segment`, `sector`, `sourceDocumentSha256` が必要。

日次入力は上記directoryの実セッション日 `YYYY-MM-DD.json`。
`ARK_NO11_CLEAN_SESSION_GUARD_V1` に `sessionDate`, `previousSession`, `knownAtJst`,
`reviewStatus=EXTERNALLY_REVIEWED`, `weeklyFileSha256`, `referenceFileSha256`, `chartPlanSha256`,
`productionReady=false`, `orderTransmission=false`, `rows` を指定。
各rowは `symbol`, `reviewStatus=CLEAR`, `changesReviewed=true`, `tradingSuspended=false`,
`corporateActionsCleared=true`, `priceBasisVerified=true`, `reviewedPreviousClose`, `sourceDocumentSha256` を必要とします。
これらの値は実資料に基づく独立確認から供給するもので、サンプル値をそのまま本番へ使ってはいけません。

未確認をCLEARにせず、日付・価格・元資料hashが合わなければ停止します。
選定済みChart50を黙って縮小せず、欠けた銘柄は再計画を要求するエラーになります。
週次・日次双方の `.source` 文書bytesを既存の検証処理で照合し、組み立てた当日証拠を別ファイルに保存します。

## 完成したとは扱わないもの

この修正版だけで全自動運用は完成しません。以下は別の統合作業です。

- 実資料・企業行動情報の自動取得と独立レビュー。
- 適格Chart50の再生成と前日Contextの整合。
- 銀行未連携RSS余力を開始予算・実refresh証拠へ接続する処理。
- 当日bootstrap・物理book設定の自動生成、起動先への反映。
- Windows Excel COM、実RSS、実注文番号・実約定・資金・保有の統合確認。

送信直前の再読込みも証券会社との原子的同期ではありません。
未観測の手動操作、確認直後の競合、送信済み注文の自動取消までは解決しません。
手動操作時は証券側の未約定・残数量の確認が必要です。

## CI

専用workflowはWindows/Linuxの隔離した基準commitへ生成物を配置してテストします。
新規Pythonテスト、元のFrozen/P1関連テスト、Nodeテスト、PowerShellの構文・純粋モック試験を実行します。
WindowsではPowerShell 5.1を使用。各OSで同一payloadが生成されたことを最終jobで照合します。
**CI成功は本番発注成功ではありません。実機適用や実注文は実行しません。**

公開物には合成テストだけを含め、個人の市場データ・口座・原本PRIVATEモデルを含めません。
