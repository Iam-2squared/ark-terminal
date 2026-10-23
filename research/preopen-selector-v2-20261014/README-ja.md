# 新Selector V2 — MODE A

詳細契約はV2_DESIGN_DETAIL-ja.md、95列はFEATURE_REGISTRY.json。
市場数値読取・市場fit・実行は許可されていない。

最新のMODE B準備: MODE_B_PREPARATION_COMPLETION-ja.md。
用途別24原本scopeはMODE_B_SOURCE_SCOPE_DRAFT.json、実source採用条件は
REAL_SOURCE_ADMISSION-ja.md、owner環境手順はOWNER_CHANNEL_DEPLOYMENT-ja.md。
統合比較はINTEGRATION_ADAPTER_PROPOSAL-ja.mdの独立案に限定する。

Python3.12、requirements-engineering.lockの5依存版を使用する。
人工E2Eは外部ファイルを入力せず、自作fixtureのみから2モデル/2温度を実行し、
別processで信頼済み自作artifactをrestore、候補固定後に別processで評価する。
失敗成果も保持するので同じoutput名を再使用しない。

```powershell
$env:OMP_NUM_THREADS = "1"
$env:OPENBLAS_NUM_THREADS = "1"
$env:MKL_NUM_THREADS = "1"
$env:PYTHONDONTWRITEBYTECODE = "1"
$v2 = "research/preopen-selector-v2-20261014"
$out = Join-Path $env:LOCALAPPDATA ("ArkTerminal/V2Synthetic/" + (Get-Date -Format "yyyyMMdd-HHmmss-fff"))
py -3.12 "$v2/tools/v2_cli.py" synthetic-test --output $out
if ($LASTEXITCODE -ne 0) { throw "V2_SYNTHETIC_FAILED" }
py -3.12 -m unittest discover -s "$v2/tests" -p "test_*.py" -v
if ($LASTEXITCODE -ne 0) { throw "V2_TESTS_FAILED" }
py -3.12 "$v2/tools/v2_cli.py" public-audit
if ($LASTEXITCODE -ne 0) { throw "V2_PROTECTED_SCOPE_FAILED" }
```

census/train/calibrate/predict/evaluate/restore-verifyはMODE Aでrequestを開く前に停止する。
--unsafe/--force-fit/--ignore-hash/--auto-retry等は存在しない。
再開にはV2固有の正確な期間・用途別許可、source/権利/露出manifest、
数値/95列/品質/予算を束ねたowner原文承認が必要。
V1の47日や旧4日履歴例外は転用しない。添付原本の再送は不要。


## 承認接続・native経路の追加

[MODE_A_CONNECTION_COMPLETION-ja.md](MODE_A_CONNECTION_COMPLETION-ja.md)、[ORCHESTRATION-ja.md](ORCHESTRATION-ja.md)、[MARKET_APPROVAL_PACKAGE_DRAFT.json](MARKET_APPROVAL_PACKAGE_DRAFT.json)を参照。normalized nativeに加え、承認profile付き月次CSV.gz adapterと、POSIX/Linux向け固定ownerチャネル・別process間の独立producer pin journalを実装した。実source profileの採用とOS owner設定の設置は未完了。optional44列の実source joinも未検証で、SOURCE_NOT_JOINEDとしてNoneを保持する。

POSIX/Linuxの人工月次E2Eは、repository外の未使用outputに対し `python tools/v2_cli.py monthly-host-test --output /tmp/ark-v2-unique-run` を実行する。固定factoryを独立再生成し、通常6工程を6つの別processで検証する。test用Authorityでは市場承認が成立せず、任意の実rowも受け付けない。試験対応は[CONNECTION_TEST_MATRIX.json](CONNECTION_TEST_MATRIX.json)。

[INVENTORY_WINDOW_METADATA.json](INVENTORY_WINDOW_METADATA.json)に先行150日とFIT120/CAL20/VALIDATION20/FINAL40の在庫案、42原本のhashを結合した。研究200日全てと参照45日が既存保護範囲内。利用承認済み日数0、市場candidate/fit/calibration=0/0/0。MODE BとMODE Cは別承認であり、今回はどちらにも移行しない。
