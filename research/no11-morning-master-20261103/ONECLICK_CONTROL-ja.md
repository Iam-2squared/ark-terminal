# ARK No.1.1 — OneClick Control Center（Draft）

## 目標

普段はデスクトップの **ARK Terminal OneClick** を開き、取引当日1回だけ明示承認を行う。
毎朝PowerShellを貼り直さなくても、既存のNo.1.1 LIVE経路を利用する。
Frozen Selector/State9/P1 F5/H235/Capital V5/Structural EXIT、一般口座・現物・通常MAX3・100株・RSS余力、既存の注文台帳は変更しない。

## 実装済み（PR #600）

1. **状態判定** — 当日ブートストラップと翌営業日用不変handoffを検証。起動マーカー・既存run・停止記録があれば新規Tradeボタンを無効にする。Excel/RSSやブローカーの承認を偽装しない。
2. **デスクトップGUI** — Trade、引け後RSS更新、状態更新、停止済みrunの読み取り専用照合、ログ表示。画面の表示だけでは注文許可しない。15秒間隔で状態表示を更新。
3. **取引起動** — Tradeボタン押下時に **明示Yes** を取って元の `Start-No11UnifiedLauncher.ps1 -Mode Trade` に処理を委譲。元ランチャーが独立して当日の営業時刻、Excel/RSS、資金、注文台帳の条件を再確認する。二重起動マーカーを上書きしない。
4. **夜間** — 元のWeekly/after-close処理をGUIから起動。任意でログオン中ユーザー限定の平日18:10タスクを登録し、実RSSから翌営業日handoffを準備する。注文開始はスケジュールしない。元の夜間データ更新は `install_daily_cycle.py` が適用済みである必要がある。
5. **障害** — Chart50は親PR #599の最大12回の有界再試行を継承。ライブ途中停止に対して、復旧ボタンは**独立したRSS口座読み取り＋監査のみ**を実行。自動で `ENTRY_HALTED`、起動マーカー、実行DB、注文や発注許可を消さない。破損/未確定注文を抱えたまま買付を再開しない。

## 一度だけのWindows導入

対象: 既存No.1.1が稼働せず、旧ランチャー・既存入力接続が配置済みのWindows。

このPRの `research/no11-morning-master-20261103/` フォルダーを利用し、PowerShellから次を一度だけ実行する。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Install-No11OneClick.ps1 -Apply
```

日次更新が既に導入されており、ログオン中のみ18:10に自動実行したい場合は、初回に限り `-EnableNightlyTask` を付加する。タスク登録は既存タスクを上書きしない。既存の手動トレードには影響しない。

インストーラーはローカルソースのGit Blob SHA-1を検証し、変更前をバックアップする。既存ランチャーや売買ソースを上書きしない。導入後、デスクトップの **ARK Terminal OneClick** ショートカットを使用する。

## 状態の読み方

- `PRELIMINARY_INPUTS_READY` — 当日の入力源は確認できたが、**Excel/RSS注文可・モデル実行・証券会社受付を認証した意味ではない**。
- `ALREADY_STARTED_TODAY` — 当日の一度限りの起動記録が存在。二重START禁止。
- `EXISTING_RUN_REQUIRES_REVIEW` — 既存run/停止・復旧が必要。復旧レビューボタンは読み取り専用で、解除・再注文しない。
- `TODAY_HANDOFF_MISSING`, `HANDOFF_HASH_CHANGED` — 日次・週次夜間処理の失敗やソース不一致。古いhandoffの翌日付け替えは禁止。
- `NEW_ENTRY_WINDOW_CLOSED` — No.1.1の新規買い締切（15:20）以降。ユーザー承認でも制限解除しない。

## 限界

- **実機未検証**: PCへのOneClick導入、個人ブック/Market Speed IIの継続接続、実BUY、ブローカー受付、実約定・Structural EXIT。
- **自動解除なし**: 永続的な `ENTRY_HALTED`、未確定注文、収集器の終了履歴の不一致では新規発注しない。
- **夜間タスクはログオン中のみ**: Excel/RSSが起動・ログイン済みでなければ正しい翌営業日handoffは生成できない。
- **Market Speed IIのログイン/発注可**は証券会社側の対話操作が残る場合がある。
- OSデスクトップショートカットの設置はWindows限定。Linuxは状態判定ユニットテストのみ。

これらを満たさない状態を「完全LIVE運用完成」とは表示しない。
