# ARK No.1.1 — 休止日・切断復帰の運用簡略化（2026-11-04）

## 目的
売買しない日や一時通信断を理由に、429/4,328件の過去原本を毎回再取得したり、PowerShellで都度原本認証修復を要求したりしない。**検証済み証拠を再利用**し、証拠が足りない領域だけ取得・照合する。

> 完了の境界: このPRは日付を跨ぐ最新データの補充とLIVE自動再開の「安全な判定基盤」。実際の欠損RSS捕捉と注文ありセッションの再開操作はまだ未接続で、実機検証前のDraft。成功を装わない。

## 休止日と夜間データ
- 夜間UPDATEはその時点で実在する株価・D100/G1・Chart50・前日1Mだけを収集する。将来の株価を先取りして生成できない。
- 完了した翌日handoffと出典のSHA256はそのまま不変保管。現在の暦日に付け替えない。
- `no11_return_after_skip.py` は最後の正常終了した指標/hand-offを見つけ、現在日付と照合して `CURRENT_DAY_HANDOFF_VERIFIED`, `CATCHUP_REQUIRED`, `BLOCKED_SOURCE_INTEGRITY` などを返す。**TRADEを許可しない、RSS取得もしない**。
- 休止後は最新の現物営業日を対象に、元のRSS関数 `RssChart(D,100)`、G1/Chart50、前日1Mを**新たに取得して必要分のみ補完**する必要がある。すでに保存された429件の過去原本は復元しない。朝の一括自動捕捉・handoff生成は別実装である。
- 既存の `Run-No11WeeklyCandidateRefreshReadOnly.ps1 -CatchUpAsOf` は前営業日の日足を取り直す経路を持つ。ただし指定できる曜日・時間・Weekly元データに制限があり、月曜の金曜欠損などは別途対応が必要。万能な欠損回復とは扱わない。
- `Register-No11NightlySchedulePreserveWhite.ps1 -Apply` は、**ローカルで導入済みの白いOneClickを置き換えず**、現在ある `-Mode ScheduledNightly` を平日18:10に起動するタスクを**初回のみ**作成する。夜間RSS実行のデータ/注文安全ゲートは元のまま。
- このタスクは対話Windowsユーザーがログイン中で、ExcelとMarket Speed IIが起動・ログイン済み、RSSが接続された環境のみ対象。PC電源OFF/スリープの間の実行を保証できず、データがなければFail Closed。実注文はスケジュールしない。

## 日中RSS/Chart50切断・手動確認
- 一時的なExcel COM busy/read shapeは既存の最大12回bounded retryを優先。安全な収集再試行と、注文の再送は分離。
- 注文/保有が非ゼロでも、読取専用の楽天口座注文・約定・保有表と元のSQLite台帳を**1回のbroker観測**で照合する。 `no11_manual_reconnect_review.py` はこの照合を行う。
- 照合の必要条件: 同一営業日・90秒以内の観測、完全表・同一時点ダブル読取、ARK帰属注文番号/RSS発注ID/側/数量/累積約定数量の整合、ARK帰属保有数量の実証券口座一致、受渡/取引区分確認、未照合dispatch無し、手動注文混同無し。
- 一致を確認できた場合のみ `COLLECTOR_RESTART_REVIEW_ELIGIBLE` の判定候補になる。**これは自動再開・BUY許可ではない**。読取専用判定の結果は `REVIEW STOPPED SESSION` で元のbroker snapshotから再利用する。
- 不明な新規/取消注文、二重注文のおそれ、証券会社の最新状態不明、未解決注文、保有数量の食い違いは**新規BUY停止**。既存保有のEXIT監視は継続・復旧を最優先にする。
- 実LIVEのCollector再起動監督・安全に残ったExcel一時ワークブックの扱い・同runのEXIT復旧・停止記録の監査済み解除は未実装。元の `RunRecovery.history` が確認できるクローズ証跡なしに復旧扱いにしない。
- 当日の明示取引承認は維持する。**同一日にすでに有効な承認を得ている場合に不要な追加承認を何度も要求する設計は避ける**。ただし手動証券画面の目視だけで、注文結果未確定の自動再発注を許可しない。

## 実装ファイル
- `no11_return_after_skip.py`: immutable handoff履歴の検証と「取り直すべきデータ」の切り分け
- `no11_manual_reconnect_review.py`: 注文・保有ありを含むbroker/台帳一致のread-only判定
- `Review-No11RecoveryReadOnly.ps1`: 元の1回broker照合結果を再利用する非ゼロ復旧審査経路
- `Register-No11NightlySchedulePreserveWhite.ps1`: 白いUI不変の平日夜間タスク追加
- `test_no11_skipday_and_reconnect.py`: Linux/Windowsの合成データ試験

## 本番適用前に残る受入条件
1. 元のOneClick UIに変更がないこと、夜間タスクは現在の正常な夜間更新と競合しないこと。
2. 取引のない休止日・夜間更新なし日・金曜更新なしでの翌営業日catch-upと欠損表示。
3. LIVE切断、注文なし、未約定あり、約定あり、ARK保有あり、手動保有あり、約定/注文応答不明の証券口座読み取り照合。
4. 既存のLIVEと同一runでのcollector再起動およびEXIT継続、重複BUYゼロを実機で確認。
5. 未検証手動注文/保有が混入した場合は確実にFail Closed。
