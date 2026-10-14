# 新Selector V2 — 市場再開前の接続実装・承認パッケージ

対象branchは research/preopen-selector-v2-engineering-20261014-r1、Draft PR #594。開始時live HEADは57c7d7f03a44ae7d668e0c973d399ddd773e6071で指定基準と一致。Open/Draft・base V2設計branchを維持する。最終対象HEAD・専用CI run/job/event/headとdecoded log証跡はPR本文へ結合する。

実装状態：旧人工matrix経路を維持し、別のnormalized native経路へ census → train → calibrate → predict → evaluate → restore-verify を接続した。自己宣言JSONは権限にならない。owner原文・承認全体・親承認・precommit・manifest・用途別日付・code/config/schema・budget・artifact producer pinを独立Authorityで照合する。既定CLIはownerチャネルなしでrequest／原本／教師／モデルopen前に拒否する。

**市場実行準備完了とは報告しない。** 実在庫の月次CSV.gz正規化adapter、owner管理チャネル実配備、別process間の独立artifact pin永続化、optional44列実sourceは未接続。ORCHESTRATION-ja.mdに工程ごとの接続・未接続範囲とhost interfaceを記録した。

| 検証 | 対象経路 | 今回ローカル結果 |
|---|---|---|
| 必須72＋既存追加25 | 従来の純粋関数／契約／fail-closed | 97 PASS |
| 新規test_n01～test_n34 | 実native RAW/master → gates → CORE95 → teacher → 2HGB → 2温度 → artifact → watchlist → evaluation → restore、承認偽装・用途・保護・未来毒化・予算・fit spy | 34 PASS |
| V2合計 | 上記全試験 | 131 PASS |
| V1 read-only回帰 | 元tests／preopen_testsの今回実行 | 32＋125 PASS |
| type / syntax | V2 srcとtools | mypy28 files PASS / compile PASS |
| 人工matrix smoke | 従来のfactory専用・別process | 2fit／2cal、1080 trees、復元予測差0 |
| 人工native CLI E2E | 新オーケストレーション全工程 | 720 FIT／360 CAL、1予約／2fit／2cal、1080 trees、復元予測差0 |
| native人工VALIDATION／FINAL | 元点目標を変更しない停止経路 | VALIDATION FAIL、FINAL未開封。試験自体はPASS |
| 保護diff | V2領域＋専用workflow以外・V1 hash・旧設計bytes | PASS、保護source差分0 |

NATIVE_ROUTE_TEST_MATRIX.jsonで試験名と対象経路を対応付けた。SYNTHETIC_TEST_LOG.txt、LOCAL_VERIFICATION_RECEIPT.json、NATIVE_ROUTE_ENGINEERING_RECEIPT.jsonに結果を記録した。開発途中の失敗と修正はVERIFICATION_HISTORY_R2.jsonに残した。実市場再試行は0。

metadata監査：添付archiveのdirectory、元ファイルmanifest／転送receiptだけを読み、26元ファイルのsource identity・SHA256・bytesを承認パッケージへ結合した。価格payloadの展開・数値parseは0。高水準在庫はDAILY／MASTERが2021-10以後とされるが、正確なrecord日付coverage・calendar object hash／全営業日リストを証明していない。添付masterは2024-10～12の3か月で、この部分集合だけでは200営業日を満たせない。これを全保存原本の欠落とは扱わない。

最新在庫端点2026-10-05は既存protectedHoldout（2025-10-01～2026-10-05）内。REPORT19の未解放、V1 30/10/7日のhuman exposureも別区分で残した。保護日を飛ばした200日や、勝手な古い代替windowを作らない。原本再送は要求しない。

次の承認は二段階：

1. **MODE B**：不足metadataを結合したexact FIT120／CAL20／先行reference、用途別allowlist、source hash、V2利用根拠・seal・露出を提示して別途owner承認。G1/G2候補数、FIT clean3/5 oracle上限、教師support、95列観測／欠測を確認する。fit0、VALIDATION/FINAL教師未開封。
2. **MODE C**：MODE BがPASSした後、同一の数値案／教師／CORE95／順位／全split／source route／品質目標とcode/config/schema／census／precommit hashを固定して、別のowner原文承認。上限1 candidate／2fit／2温度。MODE B承認だけでは実行できない。

完了報告の固定値：

- parameters_adopted：false。
- V2用途データ許可：未成立、exact approved teacher/history日付0。
- ゲート実測日数／教師support：NOT_MEASURED（上の720/360は隔離人工試験だけ）。
- 市場candidate／estimator fit／calibration：0／0／0。
- 市場VALIDATION／FINAL：未開封。
- 市場raw/clean1/3/5・Low3/5：NOT_MEASURED。
- ENGINEERING_PASS：ローカルPASS。専用CIは最終HEADのrun/job/decoded logをPR本文で確認。
- MARKET_MEASUREMENT_COMPLETE：false。
- POINT_TARGETS_MET：NOT_MEASURED。
- STATISTICAL_SUPPORT_ESTABLISHED：false。
- PREDICTIVE_QUALITY：NOT_MEASURED。
- LIVE_READINESS：NOT_CERTIFIED。
- 全11安全flag：false。
- orders／paper／provider requests／main merge／force push：すべて0。

今回の未解決事項は、MARKET_APPROVAL_PACKAGE_DRAFT.jsonの6つの不足metadata、実原本adapter／ownerチャネル配備、V2用途MODE B承認、census後の別MODE C承認。承認ファイルだけで市場経路完成・性能完成とはしない。
