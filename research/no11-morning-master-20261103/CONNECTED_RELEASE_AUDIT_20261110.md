# ARK No.1.1 接続監査 — 2026-11-10

## 結論

「全て問題なく動く」とはまだ判定しない。DATA側の少数欠損自動除外、保存済み取得ログ再利用、翌日handoff生成、中断からの復帰は、今回追加した接続試験まで通過した。一方、ユーザーPCのLIVE設定と固定.xlsx参照の不一致、実証券会社への接続、実BUY/約定/EXITの通し運転は未解決・未検証として残る。

この監査で元の選定・ENTRY・EXIT・配分ルールを変更していない。既存の「少数の不良1Mは新規ENTRY候補から自動除外し継続」という方針も維持する。個別銘柄の理由を毎回AIへ貼る運用に戻さない。

## 検証対象と外部境界

新しい接続試験は、実際と同じschemaの合成RSS原本47件を作り、元の `no11_previous_archive_context.stage_archive` で46件利用可能・1件欠損を生成する。自動除外の本体、実Node Chart50 validator、元のmorning_master、scope_morning_master、日付別pointer公開、selection_status、Trade準備bridge.resolve_daily_bindingまで実際のコードを接続した。

保存済みCAPTURING checkpointを使う試験では、実際の `native()` と `Pipeline.run()` を実行。RSS収集を呼んだら試験を失敗させる。既存成功ログから公開だけを再開し、再実行しても再取得しないことを確認する。

外部のJPX HTTP資料取得、時計/スケジュールCLI、Excelのプロセス検出は境界fixtureとして置き換えている。したがって実Excel/RSS・その時点のJPXページ・実発注・実約定・実EXITを成功させた証明ではない。HTTP fixtureも合成資料と明記し、実際に取得した資料として報告しない。

## 再現して直した不具合

| 不具合 | 再現と修正 |
|---|---|
| 引継ぎ失敗でも導入コマンドが成功終了 | publisherが非ゼロ終了してもinstallerが例外にしなかった。失敗を呼び出し元へ返し、INSTALLEDと引継ぎ成功を混同しない |
| 保存ログの複製直後に中断すると再開不能 | clone作成後・CAPTURED checkpoint前のpower-cutを再現。完全に同じ複製が既存なら再利用し、異なる内容は拒否。採用処理にも同一DATA排他を使用 |
| 派生1Mファイルを書き換えると原本も変わる | sourceへのhardlinkを作っていた。独立した同一bytesのcopyを原子的に公開する方式へ変更。派生copyへの書込み後も原本bytesが不変な試験を追加 |
| 適用済み判定で配置済みモジュールの改変を見落とす | COMPLETE journalがあっても実packageの全ファイルをハッシュ照合する |
| 遠い祖先PIDの再利用で無関係なプロセスまで停止条件になる | 子より後に作られたPIDは祖先として除外せず、祖先探索をそこで終了。以後は通常の別ワーカー検索対象に残す |
| Windows CRLFで旧worker領域の正確な一致に失敗 | namespace抽出前にCRLF/BOMを正規化。変換後ソースの改行は従来どおり保持 |

初回追加試験の失敗を握りつぶしていない。初回run `42648093292` で問題を再現し、修正後に同じ失敗条件を含む試験を再実行した。途中のWindows導入試験run `42649425047` はCRLF不具合で失敗し、最終版で修正した。

## 最終検証

検証HEAD: `b057807dff35f890a8a5038373a34af1602cf043`

- 接続監査: https://github.com/Iam-2squared/ark-terminal/actions/runs/42650464767 — Windows/Linux Python、Windows/Linux Nodeの **4/4ジョブ成功**。
- Windows Python: 26群、207回のテスト実行、失敗0、skip0。既存installer試験5件が接続試験へのimportにより重複実行されるので、207種類の固有ケースとは数えない。
- Windows Node: No11既存109ファイル、534件成功、失敗0、skip0。注文/約定/保有/EXIT等の既存模擬回帰を含む。
- Ubuntu Python/Nodeも成功。OS専用skipは各artifactの内訳で区別し、実行成功へ水増ししない。
- 配布専用監査: https://github.com/Iam-2squared/ark-terminal/actions/runs/42650464913 — Windows/Linux **2/2成功**。固定commitの7ファイルGit blob、Windows PowerShell 5.1のbootstrap自己試験も成功。

証跡はActionsの `audit-python.json` / `audit-logs/` / `audit-node.json` / `audit-node.log`。`realExcel=false`, `realRss=false`, `realOrders=false`, `realExit=false` を明記。

## 配布版

入口: `Bootstrap-No11AutoMinutes.ps1`

- bootstrap固定commit: `b057807dff35f890a8a5038373a34af1602cf043`
- bootstrap Git blob: `5a7b2fcc85fef5e3fbbeaee8e96574a3ae044733`
- payload固定commit: `9bfccb93e27f2e3b9d3894eb57a930641c1991d3`
- リリース表示: `NO11_AUTO_MINUTE_RELEASE_VERSION=2`

前回のV1コマンドの代わりにこのV2を使用する。V2の導入journalはV1と分離し、元モジュール・元checkpoint・元ログを保持。白UIを閉じ、既存の.xlsx/.xlsb実ブックを保存し直したり削除したりしない。

導入後は、対象日・engine pins・原本の一致を確認できた保存済み取得だけから、欠損除外と翌日handoffを再開する。導入処理からRSS全市場再取得へフォールバックしない。

`ARK_AUTO_BAD_MINUTE_EXCLUSION=INSTALLED` は導入状態だけ。今回の保存済みデータの公開完了は `NO11_AUTO_MINUTE_SAVED_STAGE=PASS` と `NO11_DAILY_CYCLE_STATUS=NEXT_SESSION_HANDOFF_READY` 等の実行結果で区別する。未採用/失敗を成功と報告しない。

## 残るLIVE経路の問題

ユーザーは3冊とも `(version 1).xlsb` を開いている。DATA専用registryへの登録は実機PASS済みだが、登録時は意図的にLIVEのsettings.json、broker/transport受信台帳を変更していない。

`windows/Start-No11UnifiedLauncher.ps1::CheckExcel` は依然として旧settingsの絶対パスを比較し、Account/Marketは `Workbooks.Item('Ark_No11_MSII_RSS.xlsx')` / `Workbooks.Item('Ark_No11_MARKET_RSS.xlsx')` で参照する。この登録と固定参照が今のxlsb構成に一致したことは証明されていない。このV2もLIVEブック登録を変更しない。

したがって「DATA更新から翌日handoffまでの合成接続試験が成功」と「ユーザー実機のTradeが発注・約定・EXITまで運転可能」は別の状態。全体正常とは表示しない。mainへmergeせず、Draft PR #612内の修正として管理する。
