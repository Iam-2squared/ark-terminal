# No11：実 `.xlsb` 3冊のDATA登録 — 2026-11-09

## 実機で確認された不一致

開いているのは次の3冊。各1シート、Date1904=False、保存済みパスあり。

| 役割 | 実際のブック名 | シート |
|---|---|---|
| Account | Ark_No11_MSII_RSS (version 1).xlsb | ARK_ACCOUNT_READONLY |
| Market | Ark_No11_MARKET_RSS (version 1).xlsb | ARK_MARKET_READONLY |
| OrderIds | Ark_No11_BROKER_READONLY (version 1).xlsb | ARK_ORDER_IDS_READONLY |

settings.jsonの注文ID指定はArk_No11_BROKER_READONLY.xlsxであり、ORDER_BOOK_MATCH_COUNT=0。さらにD100・候補更新・1Mの収集器はAccount/Marketを固定の.xlsx名で取得していた。注文IDのパスだけ直しても次の固定名参照で失敗する構造だった。

直前の実報告は11/6基準、capturedSymbols=0 / requestedSymbols=4328。取得完了と扱わない。

## 今回の修正

`Bootstrap-No11DataWorkbookRegistration.ps1`が固定コミットの5ファイルをGit blob検証して導入する。標準は監査、`-Apply`で適用。

1. 既存ExcelのEXCEL7から、選んだPIDに接続する。新しいExcelは起動しない。
2. ブックのFullName・名前・シート名・日付方式だけを読み、Account/Market/OrderIdsを一意に登録する。セル値、口座番号、注文内容を読み出さない。ブックを開く・保存する・変換する・閉じる処理はない。
3. データ更新専用の `data-workbooks.json` をローカルの不変パッケージに保存する。次回以降は登録済み絶対パスとシートを照合する。各実行で適当に似た名前を探す方式ではない。
4. 全市場D100、日次候補D100、前日1Mの3収集器から `.xlsx` 固定参照と旧設定依存の第三ブック確認を共通resolverへ置換する。参照されているClean別名があればその実ファイルも対象にする。
5. チャート関数の既存占有数は3冊すべてを数える。最大バッチ47・上限50・予約3は維持する。一時ブックCloseのCOM拒否後確認は元の冊数3を使用し、誤って2冊と決めつけない。
6. ファイル置換前に元bytesと更新bytesをチェックサム付きjournalへ保存。新パッケージを先に配置、bindingを最後に原子的更新。途中停止は同じ入口で再開できる。
7. 新しいDATA checkpoint領域を用い、以前の0件失敗ログやcheckpointは削除しない。

## 変更しないもの

- Excelの実ブックとその内容、ファイル名、保存形式。
- 白いOneClickの外観・ボタン構成、Frozen売買ルール、注文/約定台帳。
- `settings.json` のLIVE用ブックパス、既存取引handoff、broker/transport登録先。

**これはDATA経路の `.xlsb` 対応。LIVE側の旧 `.xlsx` 登録をこの操作だけで新しい注文送信先に自動移行しない。データ取得成功と実売買の接続成立は別である。**

## 検証

- Windows/Linux Python：実際の導入済みソースを構成して変換し、冪等性、CRLF/BOM、Clean参照、旧設定不変更、中断からの再適用を検証する。
- Windows PowerShell 5.1：ユーザーから提示された `(version 1).xlsb` 名の3冊を持つ模擬COMオブジェクトで、登録→対応付けを実行。並び順変更、旧xlsxパス、4冊目、重複役割、Date1904、未保存、余分なシートを区別する。
- 実収集器候補とhelperのPowerShell構文、固定配布ソースhash、bootstrap自己テストを検証する。
- 実Excel/RSSはCI環境にないため、実4,328銘柄取得・実BUY/約定/EXITの成功は主張しない。

## PCでの使用

白いOneClickを閉じる。上記3冊の `.xlsb` とMarket Speed IIは開いたまま。固定bootstrapに `-OfflineSelfTest`、次いで `-Apply` を渡す。

成功表示：

```
NO11_DATA_BOOK_DISCOVERED=Account|Ark_No11_MSII_RSS (version 1).xlsb
NO11_DATA_BOOK_DISCOVERED=Market|Ark_No11_MARKET_RSS (version 1).xlsb
NO11_DATA_BOOK_DISCOVERED=OrderIds|Ark_No11_BROKER_READONLY (version 1).xlsb
NO11_DATA_BOOK_REGISTRATION_INSTALL=PASS
ARK_DATA_WORKBOOK_REGISTRATION=PASS
```

導入だけではデータも売買も開始しない。通常の `UPDATE NEXT SESSION DATA` から再実行する。

実処理で確認する表示：

```
NO11_DATA_WORKBOOK_REGISTRY=EXACT_THREE_PATHS_AND_SHEETS_MATCHED
NO11_DAILY_EFFECTIVE_RSS_CONCURRENCY=...
NO11_DAILY_PROGRESS=.../4328
```

`PASS`は適用結果と取得完了を区別する。通常 `OPEN LOGS` の `DataUpdate-...log` が実行状況の確認先。
