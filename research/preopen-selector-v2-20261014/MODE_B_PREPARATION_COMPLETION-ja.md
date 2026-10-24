# MODE B準備の完了記録

開始HEADは6eb002f33e338d876c23088655de5504645c07a0。live HEADは一致、PR #594は
Open/Draft、追加owner承認は未確認。MODE Aの範囲を維持した。

実装を追加したのはcensusのprivate診断と失敗時receipt。数値案・G1/G2・教師・
95列・重み・モデル・較正・順位・品質目標・固定期間は変更していない。
各層のraw/clean Winner1/3/5、Low3/5、UNKNOWN、master/price/G0別の取りこぼし率、
95列の観測/欠測率・理由、Risk/R0 Opportunityのclass別行/日/銘柄数、
FIT oracle上限を出す。CALのoracle最適化は行わない。
support不足時も直前までの診断と検証完了accessをprivateに残し、fit0で停止する。
失敗receiptは未完了open試行まで網羅する完全なアクセスログとは呼ばない。

42原本は最新TRANSFER_MANIFEST（blob d0999ab…）のhash/bytes/保存commit/blobと
全件一致。価格payloadの再hash/数値parseではなくmetadata照合である。
保存済み営業日リストは変更せず、MODE Bの24原本を用途別に限定した。

| 用途 | 日数 | 承認状態 |
|---|---:|---|
| FIT教師 | 120 | 未承認 |
| CAL教師 | 20 | 未承認 |
| rolling HISTORY | 289 | 未承認 |
| master FIT_FEATURE / CAL_FEATURE | 120 / 20 | 未承認 |

rolling HISTORY289日は独立先行150日と、各FIT/CAL判定より前の参照日に分かれる。
固定した研究200日すべて、先行HISTORY45日がprotectedHoldout内。
MODE B対象の日付重複を除く保護日数は185。用途別開放は0。
VALIDATION/FINAL教師はMODE B scopeに入れない。

REPORT19Released=false、正確な台帳hashは既存summaryにあるが、日付対応は
今回取得できたmetadataにない。他研究露出の完全な日付/用途台帳も未確認。
既存添付のZIP central directory56entryもmetadata名だけ点検したが、
ledger/exposure/REPORT19/approval名のentryはなかった。価格payloadは展開していない。
V1の4日例外・利用継続根拠をV2へ移さず、Fresh認証もしない。

実source契約の採用表、owner環境設置手順、Frozen source-lockの実コード3件の
読取監査と独立adapter案を追加した。OS設定の実設置、dated identity/CA/knownAt/
exact headerの採用は未完了。raw探索の無承認bootstrap機能は作っていない。

検証: MODE_B_PREPARATION_TEST_MATRIX.jsonが追加8試験を対応付ける。
ローカル162件PASS（保護tree試験1件はsparse mirrorのため専用CIで実施）、
mypy34files PASS。最初の試験中にコード編集が重なったhash drift停止を記録し、
固定したコードで再実行した。最新HEADの163件・V1 read-only32+125・保護差分・
人工3経路・decoded job logはPR本文のrun/job/HEADへ結合する。
過去HEADのCIを今回の合格証拠として転用しない。

対象HEAD / branch / Draft PR: CURRENT_PR_HEAD / research/preopen-selector-v2-engineering-20261014-r1 / #594 Open/Draft。
実装状態: 人工接続経路完成、MODE B診断追加。実市場の契約採用・環境配置は未完了。
専用CI run/job/head / テスト数 / PASS・FAIL: 最新HEADの実行結果をPR本文に記録。
V1/Frozen保護差分: 全tree専用CIで検査。本作業の保護対象write0。
parameters_adopted: false。
V2用途データ許可: B/CともNOT_GRANTED。
ゲート実測日数 / 教師support: NOT_MEASURED。
市場candidate / estimator fit / calibration: 0 / 0 / 0。
VALIDATION / FINAL: UNOPENED / UNOPENED。
上昇raw/clean1/3/5・Low3/5: NOT_MEASURED。
ENGINEERING_PASS: 最新HEADの人工試験・専用CIに限定。
MARKET_MEASUREMENT_COMPLETE: false。
POINT_TARGETS_MET: NOT_MEASURED。
STATISTICAL_SUPPORT_ESTABLISHED: false。
PREDICTIVE_QUALITY: NOT_MEASURED。
LIVE_READINESS: NOT_CERTIFIED。
orders / paper / provider requests / main merge / force push: 全て0。
全11安全flag: false。

残る障害は次の3組に限定する。
1. 現在のV2利用根拠、用途別保護解決、REPORT19正確対応、他研究露出台帳を
   ownerが確定する。既存原本の再送は不要。
2. owner管理metadataを使って実source profileを採用し、なければ指定範囲の
   metadata検査を明示承認して先に行い、独立pinしてcensusのbootstrap依存を解消する。
3. ownerが専用非root workerとroot固定設定・永続独立journalを設置し、
   固定FIT/CAL/reference censusだけをMODE Bとして承認する。

MODE Bが成立してPASSした場合のみ、census hashと親承認を結合したMODE Cを
別途提示する。今回MODE Cへ進んでおらず、実市場学習は実行していない。
