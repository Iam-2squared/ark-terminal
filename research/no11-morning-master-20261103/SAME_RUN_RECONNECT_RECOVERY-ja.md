# ARK Terminal No.1.1 — 日中切断の同一run復帰（2026-11-05）

## 目的
一時的なExcel/RSS/Chart50切断後、既存の資金・注文ID・売買台帳・保有・EXITの状態を消さずに、同じrunから再開する。旧注文コマンドは再送しない。休止日・欠損データの追補はこのPRの対象外。

## 使用する既存基盤
- `Run-No11ReceivedSessionOperatorLive.ps1 -ResumeRun`: 当日の元のLIVE起動パス
- `RunRecovery.restore/history`: 旧runの原本・prepared-inputs・元のCaptureRelay・ブローカー設定ハッシュを検証
- `no11_broker_execution_ledger.BrokerExecutionLedger`: 元SQLiteのイベント連鎖と注文・保有状態を復元し検証
- `Observe-No11AccountReadOnly.ps1`: Excel上の元口座情報と注文ID・約定・保有を1回の独立した二重読取で観測
- `no11_manual_reconnect_review.assess`: 非ゼロの元ARK注文／保有を含む実brokerとの厳格な突合せ

## 同一run復帰の手順
1. ユーザーは楽天Market Speed IIで注文・約定・保有を確認する。白いOneClickの**既存** `REVIEW STOPPED SESSION` を押す。YESは同一run復帰、NOは読み取り専用診断、CANCELは操作なし。既存の当日取引承認は別に保存済みである。
2. 元LIVEが完全に停止していることを確認する。旧TRADE起動マーカー、原本、売買台帳は削除しない。
3. 失敗したChart50収集器が残した未保存Excelブックがある場合、ready receiptの`temporaryWorkbook`から、正規の3冊と別の唯一の未保存ブック・全シート名・`ARK_NO11_C50_TEMP_*` G1トークン・収集PID不在を確定してから**その一時ブックだけ**Close(false)する。
4. 元の`collector-ready.json.closed.json`は書換えず、新しい `collector-postmortem-cleanup.json` に署名付き証跡を保存する。旧attemptはバックアップ後、閉鎖済みと記録する。理由`COLLECTOR_CLEANUP_NOT_CONFIRMED`の原停止マーカーは**削除せず保持**し、PIDと新証跡が一致する場合だけcontrollerが再開を認める。
5. 楽天RSSの同日ブローカー情報を1回収集して、元SQLite注文・RSS ID・注文番号・約定数・ARK帰属保有を一致照合。過去の元キャッシュにない未解決指示、更新された注文結果、曖昧な手動注文・保有はブロック。
6. 元sessionの復旧回数（最大3）とhalt理由を確認。収集器起因の許容理由だけに限定し、署名付き監査checkpointを追記。BUY再開は元の条件が全て満たされた場合だけ。既にSELL約定している場合はBUY停止を維持しEXIT-only。
7. 元の`Run-No11ReceivedSessionOperatorLive.ps1 -ResumeRun`を**元のrunRootで1回だけ**起動。元のインスタンス、新しいrun、旧注文の再送は作成しない。ログでCOLLECTOR_CONNECTEDと実broker照合結果を確認する。

## 失敗時の挙動
- 注文応答が不明 / broker tableの最終時刻が古い / 元台帳と数量が違う / 未解決コマンドや手動同一銘柄保有がある → BUY停止・自動再送なし。
- 唯一の元一時Excelブックを証明できない / PIDが稼働中 / 旧run復元SHAが違う → 失敗記録を維持して停止。
- 停止理由が取引・資金・構造EXIT等なら、Chart50復旧経路では解除しない。
- 実際のMARKETSPEED IIのスナップショット、LIVE BUY / SELL / EXITを検証できていないため、実機の初回試験が終わるまでDraft・未承認運用。GitHub ActionsのオフラインPASSは実注文の正常動作を証明しない。

## 配布
`Apply-No11SameRunRecovery.ps1` を検証済みの単一GitコミットからPowerShellで取得し、Git Blob SHA1一致を確認して実行する。コードは元の白いOneClickの `$review.Add_Click` 部分と、既存の運用復旧コードの2箇所だけ差分変更し、保護された色/サイズ/配置・Frozen戦略・モデル・注文モジュール・元CSV/JSON原本には触れない。

## 実機受入条件
- 失敗するChart50ブックだけClose(false)、元Excel3冊は存続
- 元の復旧必須マーカーおよび閉鎖失敗receiptの元ハッシュが不変
- 旧注文あり・ARK保有あり・EXIT中の復旧が同一SQLite/同一runで成立
- 古いTRADEマーカーは不変、注文の再送0、新規注文は元の同日承認とソース・資金・MAX3条件に従う
- 不明注文・手動保有混入時は確実に停止し、EXIT管理可能性を明示
- 複数の連続営業日・切断・復旧シナリオで実機安定性検証

**結論**：GitHubに必要なコード経路を実装したことと、Windows実機で問題なくLIVE注文が完走したことは異なる。後者はユーザーPCで検証するまで未完了。
