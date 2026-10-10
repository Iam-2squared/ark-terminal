# 🚀 Ark Terminal No.1.1 — One-click READ ONLY 起動（2026-10-10）

**status: IMPLEMENTED_IN_DRAFT_INTEGRATION / WINDOWS_PHYSICAL_TEST_PENDING / LIVE_TRADING_NOT_READY**

## 今回実装したもの

- `integration/no1-1-msii/windows/Start-ArkTerminalNo11.ps1`：既存Freeze checkout・Private Ownership・専用xlsxの整合性を検査し、MarketSpeed IIの唯一のStart Menuショートカットを可能なら起動し、Excelで既存xlsxを開き、RSS4系統のREAD ONLY状態を待った後、既存UI2 Read-onlyランチャーを起動する。
- `integration/no1-1-msii/windows/Ark-Terminal-No11.cmd`：ダブルクリックで上記PowerShellを起動。
- `integration/no1-1-msii/windows/Install-ArkTerminalDesktopShortcut.ps1`：**ユーザーが一度だけ実行した場合のみ**、デスクトップ上に `Ark Terminal No.1.1 READ ONLY.lnk` を作る。既存リンクは上書きしない。

**MarketSpeed IIのログインは楽天証券側の本人操作が必要。** スクリプトはID/パスワード/PINを保持せず、認証を自動化しない。起動用Start Menuショートカットが一意に見つからなければ、MarketSpeed IIは手動起動し、同じArk起動ウィンドウは既存RSS4状態を待つ。ExcelアドインはExcel側で既に正規に有効化しておく。手動でアドイン登録を繰り返さず、ARKから`RegisterXLL`しない。

## 再利用するもの（再生成・上書きしない）

- Frozen No.1.1 source `C:\ArkTerminal\repo`、HEAD `10c94c92c4bd2a59a22744667fd0210252602df4`
- 既存ユーザーExcel `%USERPROFILE%\Desktop\Ark_No11_MSII_RSS.xlsx`、`ARK_ACCOUNT_READONLY`
- PRIVATE ownership `%LOCALAPPDATA%\ArkTerminal\No11\ownership-baseline.json`
- PIN済み `Ark-No11-CaptureReadOnly-v2.ps1` （既存`Start-No11DesktopReadOnly.ps1`がSHA256検証）
- 従来の `Start-No11DesktopUi.ps1` と UI2 Read Model、Capital v5 funding preview、Safety Ledger

## セーフティ

1. xlsxディスク原本はExcel起動前にZIPのWorkbookシート識別・VBA/binary・注文系RSS formulaを検査。不明・変更・危険を検出したら開始しない。
2. 既存Excel COMから **L1/N1/AA1/AL1のステータス文字列だけ** 読む。現金や個人株情報を表示しない。実到着時刻の認証ではない。
3. 起動の二重押しをnamed mutexで拒否し、UI port競合も拒否。
4. RSSが準備できない場合はtimeoutで停止。ダミーSnapshotや推定保有による救済なし。
5. 成功した場合でも `Start-No11DesktopUi.ps1` が別途Fresh Account/Ownership/CapitalのREAD ONLY検証を実施。注文関数呼び出し、Excel書込、RSS注文ON、実送信はすべて0。
6. **売買許可はExcel側RSS注文機能のみ**という最終方針は変えない。ただし現行はLIVE経路そのものが未完成のため、**Excel側の注文許可は必ずOFF** のままにする。

## Windowsで最初に1回だけ行うこと

まず最新Draft integration commitを **Frozen checkoutとは別のworktree** に配置し、既存ファイルを一切上書きしない。そのworktreeからPowerShellで一度だけ次を実行。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\integration\no1-1-msii\windows\Install-ArkTerminalDesktopShortcut.ps1"
```

その後デスクトップの **Ark Terminal No.1.1 READ ONLY** をダブルクリック。MarketSpeed IIのログインが必要なら本人がログインする。RSS4系統が整えばUIが `http://127.0.0.1:8767/` に起動する。新しいWorkbook作成、Ownership再分類、git操作、VS Code起動は日々不要。

### 期待される状態表示

```text
ARK_NO11_ONE_CLICK_STARTUP=READ_ONLY
EXCEL_RSS_ORDER_PERMISSION=KEEP_OFF
RSS_FOUR_STATUS_CELLS_OBSERVED=True
STARTING_ARK_UI2_READ_ONLY=True
NO11_UI2_DESKTOP_READ_ONLY_STARTING
ORDER_TRANSMISSION=False
```

確認すべき画面：HOME / SELECTOR / POSITIONS / ORDERS / PERFORMANCE / SYSTEM。欠測・未認証情報は`BLOCKED`/ `UNAVAILABLE`と表示する。メンテナンス対象があればログイン以外に設定操作が必要となる場合もあり、一発起動だけで健全性を保証しない。

## 火曜日のライブに向けて未完了の絶対条件

- native No.1.1リアルタイムSelector/State9/Entry/EXITシグナルの正規推論、knownAt/因果境界の認証
- Broker相当の真のデータ到着時刻（単なるExcel観測時刻ではない）と市場時間境界
- Broker固有Order ID / 注文・部分約定・現金拘束・ARK持分/個人保有/初回SELL-fill latch /復旧の実運用連動
- Windows実PCでの起動・RSS/Excel/COM回復・6画面・終日READ ONLY E2E
- 発注機能そのものは現行Draftになく、ユーザーがRSS注文ONにしてもArkはまだ発注しない

CIはオフラインでソースを検証するに過ぎず、現在の株価や本番実行環境を認証したものではない。**ユーザーの火曜日実売買希望は目標として保持し、未認証のまま実注文を解禁しない。**

## 2026-10-10 PM: RSS formula-echo STARTUP regression repaired

**Observed on user PC:** RSS status cells were rendered as formula plus state, e.g. `=@RssCapacityList(L2:L2) => 完了`, while one-click preflight required raw `Value2 === 完了` / `配信中`. This caused `ARK_RSS_STATUS_NOT_READY_TIMEOUT` even with visible RSS output. A startup-only strict parser now checks **both the exact approved formula and one of the exact approved status representations**. It is aligned with the already audited `Get-No11ReadOnlySnapshot.ps1` parser, and the existing offline Windows PowerShell test tests all three implementations on valid and malformed states. No Excel formula change, workbook regeneration, order function, account write, or loosened signal checks.

**IMPORTANT:** This corrects the launcher *readiness heuristic only*. It does NOT independently certify underlying RSS delivery timestamps, live data, broker fill, strategy inference or live trade readiness. Keep Excel RSS order feature OFF. After pulling the new branch version, the pinned old launcher will still fail until the versioned worktree is updated safely.

## 2026-10-11: RSS timeout diagnostic (no private data)

A second `ARK_RSS_STATUS_NOT_READY_TIMEOUT` occurred with the fixed parser, so the launcher now exposes **categorical reasons only**, never raw RSS cell contents or any amount/symbol/account path.

After pulling the updated integration commit, run the existing launcher script with `-DiagnosticOnly` to inspect the already-open Excel **without opening Excel, MarketSpeed II, refreshing data, writing a cell, or placing orders**:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\ArkTerminal\no11-launcher\integration\no1-1-msii\windows\Start-ArkTerminalNo11.ps1" -DiagnosticOnly
```

Permitted report fields: `NO11_RSS_DIAG_WORKBOOK`, `NO11_RSS_DIAG_SHEET`, `NO11_RSS_DIAG_L1/N1/AA1/AL1`, `NO11_RSS_DIAG_READY`; all are coded enums, not raw account values. If a future regular startup times out, the same report is printed. The code still demands exact original formula + acceptable RSS echo. A screenshot of an Excel cell is not adequate proof of broker delivery freshness.

## 2026-10-11: whole-account 18-header reference acceptance (strict)

Live diagnostic (user PC): Workbook MATCHED, Sheet FOUND; L1/N1/AA1 PASS, AL1 FORMULA_MISMATCH. Read-only structural inspection: AL1 has one argument (header range), no symbol filter, no account filter; formula length 29. A formula with Excel absolute coordinates, `=RssPositionList($AL$2:$BC$2)`, has that length, but the actual header address is **not yet independently certified** by these observations.

The one-click startup whitelist now additionally permits **only** the relative or absolute `AL2:BC2` 18-header form, provided all 18 provider headers are byte-exact in the expected columns and the returned feed state is exactly `配信中`. `RssPositionList()` remains supported. A 10-header range, any filtered account/symbol variant, wrong header order/labels, malformed formula or invalid feed state remains BLOCKED. This checks only startup RSS observation: downstream pinned private capture/Ownership/Fresh Snapshot must still pass separately. No workbook edits, manual order switch or production promotion.
