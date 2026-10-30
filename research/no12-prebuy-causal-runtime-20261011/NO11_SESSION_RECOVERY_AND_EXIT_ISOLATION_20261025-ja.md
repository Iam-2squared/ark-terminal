# No.1.1：同じrunへの復帰と、Entry障害時のEXIT継続

2026-10-25 / PR #592 / 既存統合Shadowのみ。モデル・元Selector・State9・Capital・Structural EXITの計算式は変更せず、新規学習・実注文・別branch更新は行わない。

## 1. 修正した運用上の問題

以前の一括起動は実行ごとにUUID付きの別runを作っていた。同じprivateRootでコマンドを再実行しても、同一のP1・保有・未約定台帳を復元する経路ではなかった。また、Entry推論や入力取得の例外でconsumer全体が終了し、Shadow保有のEXIT時刻確認も終了していた。

今回、既存ランチャーの既定入口を `no11_received_session_controller.py` に変更した。元bootstrapの入力準備・モデル事前確認・collector起動引数・Excel一時book閉鎖処理をそのまま呼び出し、runの同一性と再開を管理する。

## 2. 新規起動と復帰

新規起動の引数はこれまでと同じ。privateRoot内へ当日のactive-runポインタとrun-contractを保存する。同じ営業日のrunが登録済みなら、空台帳でのもう一度の新規起動を拒否する。

復帰時だけ、既存 `Run-No11ReceivedSessionReadOnly.ps1` に `-ResumeRun` を追加する。指定先は初回の `NO11_BOOTSTRAP_PRIVATE_RUN=` が指す同一フォルダ。設定・準備済みplan/mask/master/previous・Shadow資金設定のハッシュを照合し、**同じinferenceディレクトリ**のP1 SQLite・portfolio SQLite・pipeline checkpointを再使用する。原本の読み直しで企業行動認証を作ったり、資金や保有を初期化したりしない。

旧版で作ったrunはこのrun-contractを持たないため、自動で推測して移行しない。旧runの台帳・collector証拠がある場合も、新規空runでの上書き復旧は拒否する。旧bootstrap Pythonファイルは互換のため残しているが、一括起動は更新後のWindowsランチャーを使う。

collector再開時は別の一時book・ready/stop通知を使うが、推論先は変えない。過去と今回のsnapshotを `capture-view` へ**元バイト列のまま一度ずつ**コピーし、既存consumerへ渡す。ファイル名SHA256、対象日、計画、選定銘柄、注文OFF、受信時刻を確認する。原本の削除・改変やコピー先の改変を勝手に修復しない。停止中のバーやVaは生成せず、元の遅延拒否・実行済みSelector時刻の重複防止を維持する。

再開可否は、所有するcollectorプロセスの終了と、一時bookを閉じた通知の両方を確認する。spawn要求とPID記録の間で落ちた場合も不明状態のまま止める。既存 `bootstrap-recovery-required.json` は自動削除しない。元Excel全体のkill/終了は行わない。

## 3. Entry障害とEXITの分離

常駐serviceは `no11_received_failure_isolation.py` の薄いラッパーを使う。元H235/R0、元Capital、元EXITとその入力検査を置き換えない。

Entry推論失敗、既知の入力不備、受信停止・古い入力を検出したら、既存portfolioのSQLiteトランザクションとイベント列へ `entryPipelineHalt=true` と理由を保存する。この停止はプロセス再起動では解除されない。

停止後は新規推論・Capitalの新規配分を行わず、確認済みの未約定BUYへローカル模擬取消を要求する。UNKNOWN注文はUNKNOWNのままで、資金予約や照合待ちを消さない。以後のfeedが正常なら、元の保有State9・EXIT・模擬SELL処理のみ継続する。改変・未来・未受信の価格からEXITやfillを生成しない。

市場入力まで不正・停止している場合は、価格依存の構造判断や模擬fillは進めず、serviceが稼働している間の時刻確認を残す。15:20以降のループで元EOD SELL_INTENTを生成するが、価格が来なければ売れたことにはしない。**プロセス停止・電源断・OS/Excel停止でも売却できる、あるいは15:20ちょうどのハードリアルタイム動作を保証するものではない。** 外部処理の実行時間と実PCでの負荷は別途確認する。

報告は正常完了と混同せず `DEGRADED_EXIT_ONLY`、`ENTRY_PIPELINE_HALTED`、`NO_VALID_FEED_CLOCK_ONLY` を明示する。台帳書込み自体が失敗した場合は、記録に成功したふりをせず停止する。Ctrl+Cは明示停止として保持する。

## 4. テスト範囲

復帰・relayは実ファイルとSQLite、模擬collectorプロセスで確認する。Entry障害テストは既存の実State9/Capital/EXITコードを呼び、価格・資金・スコアラーは合成とする。実機RSS・私有元モデル・本当の口座は使わない。Windowsランチャーはオフライン引数・構文検査を追加した。成功件数は該当commitのCIログを参照する。

重要な確認対象は、同runへの復帰で部分保有・予約・SELL後BUY停止が消えないこと、二重新規起動を止めること、入力の改変・削除を検出すること、Entry障害後も元EOD意図が出せること、UNKNOWNを取消完了へ偽装しないこと。

## 5. 今回では完了しないもの

当日master/企業行動・価格基準の実証、実PC上での不足分足取得、未反映の口座接続案、実口座残高/保有の管理、楽天RSS実発注/取消/約定IDとの対応付け・実口座の部分約定/通信断復旧は対象外。これらを「接続確認だけ残った」とは表記しない。

26日の実RSS Shadowと、27日の実売買開始は別の判定。今回のコード・合成テスト成功だけで実注文を有効化しない。全経路で `productionReady=false`、`orderTransmission=false` を維持する。
