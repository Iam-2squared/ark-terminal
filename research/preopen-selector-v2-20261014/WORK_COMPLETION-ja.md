# 新Selector V2 — MODE A 接続実装完了記録

最新の継続作業（開始HEAD 6eb002f…）は **MODE_B_PREPARATION_COMPLETION-ja.md**。
以下は37eb703…を開始点とした前回接続実装の記録であり、155件/33files等は当時の値。
最新のテスト数・run/job/HEADは新しい完了記録とPR #594本文を参照する。

今回の継続開始HEADは `37eb703065dc1698757dd320e40629dab2e40448`。live PR #594はOpen/Draft、baseはV2設計branchで一致した。以前の57c7d7f…からの工学履歴を保持し、V2専用directoryと専用workflowだけを更新する。最終対象HEAD・専用CI run/job/event/head・decoded logはPR本文へ結合する。

対象HEAD / branch / Draft PR: CURRENT_PR_HEAD / research/preopen-selector-v2-engineering-20261014-r1 / #594 Open/Draft。
実装状態: normalized nativeに加え、承認profile付き月次CSV.gz slice、固定OS ownerチャネル、独立host journalを実装。通常6工程を別processで試験。実source profileは未採用、OS設定は未設置。
専用CI run/job/head / テスト数 / PASS・FAIL: CURRENT_PR_HEADの専用runとdecoded job logをPR本文へ記録。V2予定155（既存133＋追加22）、V1 read-only32＋125、mypy33 source files。過去のrunを今回の受入へ流用しない。
V1/Frozen保護差分: 本作業のwrite0。専用CIで全tree差分・V1 computation hash・旧V2設計byteを検査する。
parameters_adopted: false。
V2用途データ許可: MODE B / MODE CともNOT_GRANTED。利用承認済み日数0。
ゲート実測日数 / 教師support: NOT_MEASURED。
市場candidate / estimator fit / calibration: 0 / 0 / 0。
VALIDATION / FINAL: 市場区分ともUNOPENED。
上昇raw/clean1/3/5・Low3/5: NOT_MEASURED。
ENGINEERING_PASS: 接続・人工経路の試験と最新専用CIに限定。
MARKET_MEASUREMENT_COMPLETE: false。
POINT_TARGETS_MET: NOT_MEASURED。
STATISTICAL_SUPPORT_ESTABLISHED: false。
PREDICTIVE_QUALITY: NOT_MEASURED。
LIVE_READINESS: NOT_CERTIFIED。
orders / paper / provider requests / main merge / force push: 0 / 0 / 0 / 0 / 0。
全11安全flag: false。

## 接続・検証

`CONNECTION_TEST_MATRIX.json` が追加22試験と月次6process E2Eの対象・期待結果を結ぶ。前日RAW → G0/G1/G2 → 95列 → 別teacher → Risk/Opportunity fit → 較正 → 保存 → 予測 → 評価 → 復元を同じstage実装で通す。test hostは固定factoryを独立再生成してreal row混入を拒否する。

月次CSVは対象date/purposeを確認してから数値parseする。他日付のpoison価格は数値化0、元ordinalを保持する。独立journalからproducer pinを再読込し、未知pickle、source/outputとの重複、権限不正、symlink、再試行・上書きを拒否する。人工VALIDATIONの目標未達とFINAL未開封は成功経路へ書き換えない。

ローカルはconnectorから復元したsparse snapshotで、全repoのgit treeとV1実体を備えない。そのため保護全tree試験1本はローカルでは実行不能、full checkoutを備えた専用CIで実行する。これをローカルPASSとして数えない。新しいCIが155全件・保護差分・V1回帰を検証する。

## 承認パッケージと残件

`MARKET_APPROVAL_PACKAGE_DRAFT.json` と `INVENTORY_WINDOW_METADATA.json` に、保存済みcalendar identity/hash、全350営業日、42原本のhash/bytes/commit/blobと用途別日付案を結合した。前の26添付原本metadataも監査履歴として維持する。calendar以外の市場原本は数値parse0、原本再送は不要。

在庫案: 先行参照2025-04-28〜12-05の150日、FIT2025-12-08〜2026-06-08の120日、CAL2026-06-09〜07-06の20日、VALIDATION2026-07-07〜08-04の20日、FINAL2026-08-05〜10-05の40日。最新在庫に依存した一案で、成績を使って選んでいない。

具体的な未解決事項:
- 研究200日全てと先行参照45日が既存保護範囲内。解除・代用はしていない。
- 原本各日の実record coverage、当時版/knownAt、RAW suffix、dated普通株/lot分類と実source profileは未確認・未採用。
- V2用途別利用根拠・owner原文・exact allowlist、REPORT19/その他seal、他研究の人間/モデル露出対応が必要。
- owner管理OS設定と専用非root workerの実配置が必要。実source44 optional joinは未検証で、初期routeはSOURCE_NOT_JOINEDのNoneを固定。

次のMODE Bは、上記を解決したexact FIT120/CAL20/referenceの調査だけを別承認し、fit0のままgate供給・FIT clean3/5上限・teacher support・95列観測を確認する。MODE CはB PASS後に別承認し、親承認・全条件・全split・全hashを固定して1 candidate / 2 fit / 2較正に限る。現在の完了状態はENGINEERING_READY / AWAITING_MARKET_APPROVAL。
