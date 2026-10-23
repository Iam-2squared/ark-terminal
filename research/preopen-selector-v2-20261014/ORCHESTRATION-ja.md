# 新Selector V2：承認接続とnative経路（MODE A）

市場candidate / fit / calibrationは0 / 0 / 0。最新の詳細・停止理由は [MODE_A_CONNECTION_COMPLETION-ja.md](MODE_A_CONNECTION_COMPLETION-ja.md)、工程別試験対応は [CONNECTION_TEST_MATRIX.json](CONNECTION_TEST_MATRIX.json)。

| 接続 | 実装状態 | 今回の検証 |
|---|---|---|
| 元の固定人工matrix | 人工専用guardを保持 | 既存smoke |
| session別RAW / dated master → gates → CORE95 → teacher | normalized native reader | 既存36経路試験 |
| 月次CSV.gz → 承認済み日別slice | exact header・単位係数・dated identity・RAW suffixをpin | 追加22試験と生成月次原本 |
| census → train → calibrate → predict → evaluate → restore-verify | 通常6 CLIへ接続 | 6つの独立process、人工2fit/2cal、復元予測差0 |
| owner原文・承認・precommit・manifest・用途・hash・予算 | 独立OS owner設定と照合 | 既定拒否、偽承認・権限・symlink・用途外入力の拒否 |
| artifact producer pin | source/outputとは別の0700 journalへexclusive保存 | process間再読込、sidecarだけでのpickle拒否 |
| optional44列 | 固定SOURCE_NOT_JOINEDルートのNone | 95列を保ち、FIT全欠測/定数除外を記録 |

市場で使用する具体的source profileは未採用、OS ownerチャネルは未設置。実sourceの44列joinも未検証である。実在原本のheader / units / dated普通株type / lot / RAW corporate-action suffix / knownAtを推測して埋めない。必要な意味契約が欠ければ、原本open前に停止する。

## 各工程の入力境界

censusはMODE Bのみで、FIT/CAL feature・teacherと必要なhistoryを使う。fit0、VALIDATION/FINAL teacher descriptorを渡さない。gate後のknown/unknown、Risk3 / R0内B6、FIT供給上限、95列観測とCAL support shiftをfit前に調べる。

trainはMODE Cと親MODE B、PASS census receiptを必要とする。FIT全knownをRiskへ、同じ日weightを継承したR0だけをOpportunityへ渡す。CALはsupport確認までで、推定器fitは2回だけ。失敗時もSTARTと予約を残す。

calibrateは同じbase modelとCALだけを使う。温度は各head1個、追加estimator fit0。失敗をT=1で成功扱いしない。MODEL_SEALED後に予測へ進む。

predictは全対象日のlabel-free featureだけを使い、全watchlistを固定する。evaluateは対応する全watchlist sealを検査してから、その区分の教師を開く。VALIDATIONの目標未達ならFINALを開かない。restore-verifyは独立producer pinに結合した自作modelをloadし、保存featureへの再予測差を検査する。load失敗を再fitで修復しない。

## production入口

固定パス `/etc/ark-selector-v2/owner-channel.json` をrootがowner管理下で設置し、専用の非root workerへ読み取りだけ許す。親directory、owner、permission、symlink、code hashを検査する。request JSONやCLI引数・環境変数ではtrust rootを選択できない。OS設定がなければ、request / 原本 / 教師 / modelをopenする前に拒否する。

owner設定はsource_root、output_root、別のjournal_root、worker UID、owner原文と参照・日時、approval / precommit / manifestの独立pinを結合する。artifact journalは信頼した専用workerが自身で生成したpinを保存する領域であり、同一OS accountやrootを侵害した攻撃まで防ぐ契約ではない。

## 日付・sourceの承認パッケージ

保存済みcalendarのhashとDate/HolDiv metadataを確認し、最新の連続350営業日を列挙した。`INVENTORY_WINDOW_METADATA.json` が42原本の保存hash・bytes・commit・blobと全日付を結ぶ。月次object-key coverageは実record coverageではない。

先行参照2025-04-28〜12-05の150日、FIT2025-12-08〜2026-06-08の120日、CAL2026-06-09〜07-06の20日、VALIDATION2026-07-07〜08-04の20日、FINAL2026-08-05〜10-05の40日が在庫候補。研究200日すべてと先行参照45日が既存protectedHoldout内で、利用承認済み日数は0。古い期間への自動fallbackや保護日を飛ばす代用は行わない。

MODE Bはexact FIT/CAL/reference、原本利用根拠、保護・REPORT19・他研究露出、実source意味契約の解決後に別承認。MODE CはB PASS後に全条件とhashを固定する別承認で、上限1candidate/2fit/2cal。現時点はENGINEERING_READY / AWAITING_MARKET_APPROVAL。
