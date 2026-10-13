# 寄り前MA4 Selector — 2026-10-13再開結果

**未完成。実市場fit・較正・Report・旧Frozen比較は未実施。**
開始HEAD: f9430c4d2ab024f5cc6bbe914f1198daf4c51956。Open/Draft PR #593、base 10c94c92c4bd2a59a22744667fd0210252602df4を維持する。
最新コードはGitHubプラグインから58ファイルを取得し、全Git blob SHA/bytesを照合した。開始時にローカルcheckoutはなく、古いコードZIPを代用していない。

| 今回実施したこと | 実施量と意味 |
| --- | --- |
| private復元 | 27,298,507 bytes、SHA256 07309ffd12e6c672da2f6be5b41c1ce6d38fb99fb97c03da1722924c9717ee88。161 payloadのCRC/hash、SQLite quick_check、49 completed descriptor一致 |
| 原本・source | E53原本を保持、そのうち49原本の既存SQLite185,728行を再使用。新しい原本取得0、再ingest0。普通株eligible銘柄日数ではない |
| MA4とschema | 日足MAは5/15/25/75、前日分足MAは5/15/30/60、週/月MAなし。全寄り前schemaはMA4直後1,092列から554列へ。指標ごとの固定パラメータ、Williams-Rの重複と16個の財務/valuation直接別名を整理。必須source familyを転送都合で削除していない |
| 実source feature canary | FIT予定日2024-11-14のD-1、許可済み30日source履歴を使用。全4,392 raw-source銘柄を確認、4,202 source-feature行、138列中100列に実観測値。190件は前日無約定/比較可能履歴不足。普通株・price gate・正式snapshotの認証ではない |
| 最終codeのcanary資源 | 11.599秒、process peak RSS144,216KiB（直前の検証processからの起動条件を含む）、出力26,289,953bytes。全Tick/full-native/市場fitの資源認証ではない |
| 同じ実装者の別経路検算 | f64 matrix有限値計数とJSONL行数から4,202/100/190を確認。市場bucketの独立再計数や第三者盲検ではない |
| 工学試験 | 最終codeで32+88=120 testsと人工model E2E PASS。Report labelを物理的に隠したpredict・別process reloadを含む。最終Git HEADのCIはPR Checksとprivate最終receiptで照合する |
| 市場実行 | candidate0、base head fit0、較正fit0、model0、watchlist0、Report評価0。固定30/10/7日とcandidate budget1は変更なし |

554はbuilderの登録schema数、138/100は限定source-canaryの計算列数/観測列数、fit使用列数は0。full-nativeの列別FIT/較正/Report観測率は未測定。日足75日線・傾きに不足する履歴はNoneのまま。週/月regimeの12-bucket騰落には13個の既知bucketが必要であり、全指標を75日だけで計算できるとはしない。参照履歴はFIT教師日数と別である。

旧precommitは保持し、MA4_EFFECTIVE_PRECOMMIT_20261013_V2.jsonをfit前の追加契約とした。HGB設定、10 heads、logistic-logit較正→累積MIN envelope、順位式、K15、08:50、前日終値>75は変更なし。定数/全欠測の列判断はFITのみ。特徴量・columnar cache・model・exportはpolicy/schemaをbindし、cacheはcode/input/calendar/basis hashもbindする。旧V1 cache/modelをそのまま消費しない。

所有者の2026-10-12 23:38 JST更新申告は同じ研究の継続として適用し、元workId・時刻・hashを保持した。provider独立確認や契約期限の証明ではない。24時間は工学上の鮮度guardである。47日のsplit hash e18a181197927bed31b22fb376c42eb35fd0ed42dcabbbb88f7ffcc0b7208325とexact ledger hash c89f75b30d19038cdc7de8d4d785ce9ce50af1c633c0ad1c6dc55ab2e1eaf6e1は維持。参照履歴のseal照合は残る。Fresh/OOS credit0。

## 実証した障害と残工程

大容量UTF8 metadataは専用blob toolで回収できたが、同toolのdated-master gzipはUnicodeDecodeErrorとなった。large Contentsの空本文、generic blobのUTF8-only拒否、Release binary tool未提供は前回証拠と整合する。新たなprivate Git CLI probeはusername要求で失敗し、認証済みCLIは実在しなかった。原本0byte/消失や全metadataアクセス不可とは記録しない。ブラウザ認証、新規provider取得、Secrets/権限変更、A〜Eへの書込みは行っていない。

必要な未マウント原本26件/2,403,000,958bytesは、canonical actual path/commit/blob、Release asset名/ID、SHA/bytesをprivate REQUIRED_ORIGINALS_MA4_PRIVATE.csvへ固定した。Aの2024-10/11/12 Tick、C同月分足、E dated master/valuation、最小参照履歴とReport用sourceの入口である。24GB全量取得は要求しない。この必要bytes照合は元データの全privateコピーやnumeric admissionを意味しない。

普通株class/100株lotの独立dated根拠、公開時点・単位・RAW basis、財務/決算予定の版管理、正式State/Dictionary上流fit lineage、full native resource、毎朝のcache更新/RSS parityが未完。011だけで普通株と断定せず、未確認なら停止する。決算予定は公開時点で知られた最新の銘柄/四半期版を使い、変更・未定を古い予定へ戻さない。missing familyを0や学習済みとして偽装しない。

生成matrixと行台帳2ファイルに保存後の欠損を発見した。原因は確定していない。破損派生ファイルを隔離し、既存の同一source canaryの期待SHA/bytesに一致するコピーからoperative cacheを復旧。原本161 payloadとSQLiteの全hash/quick_checkを再照合しPASS。保存の懸念を受け、writer終了を待つ同期実行で120 tests/E2Eを再確認した。市場結果閲覧・fitは前後とも0で、モデル探索ではない。修復receiptと旧証跡をprivateに保持する。

人工fit/較正は今回local各100、最終CIはunit+smokeで各20の予定。実施数は最終private Git/CI receiptで確定する。canary4回の計算試行16,808行に対しunique source-feature行は4,202、各回source record処理131,558件。code/policy修正後の機械的再検証であり、原本/SQLiteの重複ingestや別candidate市場探索ではない。

主6bucket、exact0、UNKNOWN、累積>=1〜5、Low/Close、up×down、日別/順位/市場/業種/流動性、後半余地、day bootstrapは全てNOT_MEASURED/null。新/同条件売買代金TopK/厳密ランダム/旧Frozenのいずれも市場件数0と報告しない。旧日中Top5×10時刻のfuture Highと、旧集合へ日通しOpen→Highを付ける事後記述は別表である。親FITの正確な重複は元manifest再確認前に断定しない。

再開順は、private bytes/hash/CRCと参照許可を照合→欠けたfamily/PIT/class/lineage結合→full schema/resource QA→1candidate FIT30・較正10→model/全Report watchlist固定→Report7評価→旧比較/別経路再計数。checkpoint内のsource-canary出力は正式native bundleへ昇格させない。保存済みrequestの旧絶対パスや旧policyをそのまま走らせない。

ENGINEERINGは部分PASS、MARKET_MEASUREMENT_COMPLETE=false、LEGACY_COMPARISON_COMPLETE=false、RESEARCH_QUALITY=NOT_MEASURED、LIVE_READINESS=NOT_CERTIFIED。全11安全flags false、main_merge=0、force_push=0、provider_new_acquisition_requests=0。No.1/No.1.1、main、旧Freeze、#591、Entry/EXIT/Capital、口座/Excel原本は変更していない。外部市場job0。

財務期間のEPS/BPS/ROEを日次valuationと同じ値として重複削除しない。財務native値を残し、日次valuationは別出典・計算basisとして保持した。最終canaryは同期実行を終了まで待ち、matrix/行台帳の期待hashとbytesが直接一致した。旧破損派生ファイルはquarantineとrepair receiptを保存し、operative入力へ戻していない。

専用CI run38332799944は25eb432fのworkflow重複envキーでjob起動前に失敗（人工fit0）。重複を除去してstrict YAML全mapping検査PASS。Selector Python bytes、554 schema、市場設定は変更なし。最終HEADのrun/job/120tests/E2EはPR Checksとprivate最終receiptで確定する。
