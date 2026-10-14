# 新Selector V2 — MODE A

詳細契約はV2_DESIGN_DETAIL-ja.md、95列はFEATURE_REGISTRY.json。
市場数値読取・市場fit・実行は許可されていない。

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
