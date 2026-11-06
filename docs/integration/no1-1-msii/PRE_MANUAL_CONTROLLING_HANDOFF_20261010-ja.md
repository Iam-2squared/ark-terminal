# Ark Terminal No.1.1 — 手動Windowsチェック直前の controlling handoff

作成：2026-10-10 JST / repo `Iam-2squared/ark-terminal` / Draft PR [#591](https://github.com/Iam-2squared/ark-terminal/pull/591)

**結論：GitHub側の単一Workbook・Capital入力・UI2 READ ONLY経路はオフラインCI成功。Windows PCによる現行版の6画面E2Eは未実施。実注文を使える段階ではない。**

## 1. 研究原本と変更禁止

| 対象 | 確認済みの状態 |
|---|---|
| Immutable Integrated No.1.1 research Freeze | `10c94c92c4bd2a59a22744667fd0210252602df4` |
| Integration branch | `integration/no1-1-msii-cash-locked-v1` / Draft PR #591 |
| 直近の実装・安全テスト最終HEAD | `15565e0ceb9e8735a1ed0a6b08ef5a427df9144e` |
| UI2 Git blob | original HTML `ec79214fcc8ad9f200d7899ee562ed11b917b686` / overlay `b0f27e1ad0e62b24052ce839c9eac29f934a677f` |
| Capital V5研究原本 | byte-exact verified **synthetic-only** adapter; V5 S/A/B, Slot Reserve, MAX3, 100株の変更なし |
| main / actual broker trades | main mergeなし、実発注なし |
| Production | `productionReady=false`, nine Safety flags false |

No.1.1のEntry側で `PULLBACK` / `SHARP_DROP` を除外し、**当日最初の合法SELL fillの後は当日新規BUYを全面停止**（SELL_INTENTではない）。本人のEXTERNAL保有はARK枠・資産・EXIT対象に含めず、同銘柄ARK BUYも拒否する。現物LONGのみ・100株・MAX3・信用/SHORT/レバレッジ禁止。

## 2. いまのPCで再利用する原本（**ユーザーが既に確認**）

- Frozen checkout: `C:\ArkTerminal\repo`（HEADは上記Freeze）
- Workbook: `%USERPROFILE%\Desktop\Ark_No11_MSII_RSS.xlsx` / sheet `ARK_ACCOUNT_READONLY`（**これ1冊を再利用**）
- RSS four feed status: Capacity `完了`, Orders/Executions/Positions `配信中` は過去の実機記録
- 現在の保有1件を本人が `EXTERNAL` と選択済み。private baseline: `%LOCALAPPDATA%\ArkTerminal\No11\ownership-baseline.json`
- Windows実機で成功した非変更Captureスクリプト：`%USERPROFILE%\Downloads\Ark-No11-CaptureReadOnly-v2.ps1`; SHA-256 `0EAB3CA3081B2E0CB323D8438719F2B820B69FC02F373AD843B5907315838E2C`
- Private `snapshot.json`, `source-health.json`, `desktop-capital-readonly.json`, `private-safety-ledger.json`, `ui-read-model.json` は `%LOCALAPPDATA%\ArkTerminal\No11\` 以下。GitHub・チャットへ原本を出さない。

**古い `C:\Ark\Ark_No11_RSS_DefaultHeaders_v2.xlsx` の生成手順、旧read-only worktreeの作り直し、既存Excel・Ownershipの上書きは行わない。**

## 3. 既存コードを再利用して今期修正した内容

| Commit | 狙い | オフラインCI |
|---|---|---|
| `f7a2addb58a35230ecbdb05d58926d5824f99b81` | 失敗時のSafety Ledger永続ラッチ、同一Workbook二重COM読取排他、UI refresh直後BLOCK・30秒鮮度、子プロセスエラー非開示 | 38057703728：2/2 PASS |
| `d4ae9c6b5f8b8240f2c871abfe9a58b8971dd3b9` | localhost HTTP E2E、PowerShell 5.1 named mutex実行テスト、古い手順の誘導修正 | 38057940516：2/2 PASS |
| `15565e0ceb9e8735a1ed0a6b08ef5a427df9144e` | ループバック Host/Origin gate（DNS rebinding対策）、個人パスのHTTPエラー漏洩防止、403/405 HTTPテスト | 38058096244：2/2 PASS |

CIはGitHub hosted runnerのオフライン検証であり、ユーザーPCのWindows COM実機PASSを証明しない。CIは実注文、RSS order function、Excel注文書込を実行していない。

## 4. 手動Windows機能試験の「入口」までできている

- `integration/no1-1-msii/windows/Start-No11DesktopReadOnly.ps1`
  - pin済み読取CaptureをSHA照合
  - 既存単一WorkbookからFresh RSS account snapshot取得
  - 現在のOwnership Baselineと口座一致の確認
  - `cash = RSS現物買付可能額`, `exposure = ARK管理株の時価`, `equity = cash + exposure` をprivate Previewへ
  - 個人株の時価を資産へ加えない・買付可能額から個人株を二重控除しない
  - 失敗を即BLOCKし、持続Safety Ledgerへlatch／同時pollは拒否
- `integration/no1-1-msii/windows/Start-No11DesktopUi.ps1`
  - 同じprivate Previewを使い、READ ONLY UI 2.0を `http://127.0.0.1:8767/` で起動。30秒自動更新。
  - stale/invalid/refresh failureはBLOCK。HTTP mutation不可。Host/Originをlocalhostに限定。
  - 6ページ：HOME / SELECTOR / POSITIONS / ORDERS / PERFORMANCE / SYSTEM（値がないものはUNAVAILABLE）。
- どちらも**実口座発注を行う機能は持たない**。UIは許可スイッチではない。読取に失敗したら古いSnapshotで続行しない。

将来のWindows PCゲートでは、最新のintegration worktreeを**Frozen checkoutとは別に**用意し、MarketSpeed IIログインとExcel RSSアドインの手動有効化を維持した状態で上記UI READ ONLY起動のみを行う。実機結果は4 RSS状態、UI各画面のREAD ONLY/Blocked、Mutation false、エラー名のみ報告する。現物買付可能額・保有コード・数量・Ownershipの実データは投稿しない。

## 5. 本番での唯一の手動許可／現状では決してONにしない

ユーザーが操作する**取引許可**は将来的に **Excel側MarketSpeed II RSS注文利用ON/OFFの一つだけ**。Ark側に独立した本番昇格・手動Safety解除ボタンを追加しない。ただし自動の資金・保有・鮮度・重複・約定・Frozen契約監査は必須。

**現状はExcel注文利用OFFのまま。** UIやPreviewがGREENでも実売買可能を意味しない。

## 6. Windows以外では完了できない／権威ソースのないブロッカー

1. No.1.1 Research Freezeは政策・原本参照の固定であり、実運用の**native live Selector/State9/Entry/EXIT Decision Event publisher**を提供しない。古い研究score・synthetic envelopeを昇格させない。データ/モデル/受信方法とPITを別途回収・認証する必要がある。
2. `source-health.json`のRSS `observedAt` は観測時刻で、真の取引所/証券会社データ到着時刻とは別。`actualFeedTimestampCertified=false`を維持。
3. `RssOrderIDList`→固有order ID→order/execution/partial fills→ARK ownership/資金枠更新は注文なしでは物理E2Eを認証できない。現行ドラフトは20引数の**TEXT ONLY/trigger=0**。
4. 持続Safety/SELL-fill同一意図の証明、Brokerの注文中資金拘束、相場停止/COM fault後の回復はWindows実機が必要。すでに存在する暫定 `explicitSafetyReset` は将来唯一手動許可ポリシーに合わせ、**正に検証できる自動復旧だけ**にする。受信時刻の根拠なしに解除しない。
5. 新UI2 6画面、昼休み、EOD、継続監視、切断/復旧の現在版Windows E2Eは未取得。

## 7. 再開手順・STOP契約

1. GitHub PR #591のHEAD、base Freeze、Actionsを最新照合。上のcommitsから先行作業があれば再実装しない。
2. 既存設計を保持し、READ ONLY desktop UIを**ユーザーPCで一度だけ**検証。専用Workbook・Ownershipを新規生成しない。
3. 上記の本質的な未実装（native live events、真のfeed timestamps、broker order/execution reconciliation）は、実運用認証に必要な一次資料・実機観測の範囲で設計。手元にない証明を合成データで代替しない。
4. 発注禁止・個人保有保護・1許可方針は継続。Freezeとmainに触らない。
5. 証拠のない箇所は `BLOCKED` / `NOT_CERTIFIED` として残す。実運用許可は出さない。

**Status: OFFLINE_READ_ONLY_INTEGRATION_GATE_READY / WINDOWS_PHYSICAL_CHECK_PENDING / LIVE_TRADING_NOT_READY.**
