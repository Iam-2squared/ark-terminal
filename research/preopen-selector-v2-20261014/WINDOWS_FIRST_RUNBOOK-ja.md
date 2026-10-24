# Ark Selector V2 — Windowsのみで再開する手順

2026-10-24。**Linux・useradd・/etc・/srv・POSIX workerは不要。Windows 10/11 + PowerShell + Python 3.12 + GitHub CLI**が対象。No.1/No.1.1 Frozen・V1・mainには変更しない。

この手順は、従来の R3 Linux host bootstrap が止まった2点（24個のprivate gzip取得、worker環境）をWindows向けに置換する。過去に確定した150 HISTORY /120 FIT/20 CAL/20 VALIDATION/40 FINALの期間は変えない。MODE BでFIT/CALの数値を扱う前に実source契約を検証する。VALIDATION/FINALの教師はその段階まで封印し、結果を見た探索をしない。

## 1. Windowsの通常PowerShell（管理者として実行しない）

GitHubへのログインには、ユーザーの既存GitHubアカウントを使う。**トークンをチャット・引数・ファイルへ貼らない。** GitHub CLIがない場合だけ一度インストール。

```powershell
winget install --id GitHub.cli -e
gh auth login --hostname github.com --web --git-protocol https
gh auth status
```

すでに `gh auth status` が成功する場合、再ログインしない。

V2研究ブランチの作業コピーで以下を実行。プライベート元原本はリポジトリ内へ書かない。

```powershell
cd C:\Users\Owner\Desktop\ark-terminal
git fetch origin research/preopen-selector-v2-engineering-20261014-r1
git switch research/preopen-selector-v2-engineering-20261014-r1
$v2 = "research/preopen-selector-v2-20261014"
$restore = Join-Path $v2 "tools/windows_restore_mode_b_sources.py"
$src = Join-Path $env:LOCALAPPDATA "ArkTerminal\SelectorV2\Sources"
py -3.12 $restore plan --destination $src
py -3.12 $restore restore --destination $src
if ($LASTEXITCODE -ne 0) { throw "WIN_V2_SOURCE_RESTORE_FAILED" }
py -3.12 $restore verify --destination $src
if ($LASTEXITCODE -ne 0) { throw "WIN_V2_SOURCE_HASH_FAILED" }
py -3.12 $restore inspect-metadata --destination $src
if ($LASTEXITCODE -ne 0) { throw "WIN_V2_METADATA_SCAN_FAILED" }
```

`C:\Users\Owner\Desktop\ark-terminal` は**例**。実際のcheckoutを指定する。2026-10-24時点の原本24個・51,429,816 bytesを既存GitHub private J-quants-Eから**保存blob identityで取得**する。新provider契約は不要。

コードは保存済み `MODE_B_SOURCE_SCOPE_DRAFT.json` のGit blob hashを最初に検証し、各原本の**compressed byte count・SHA256・Git blob SHA1**を照合する。部分成功後の再開では既存の正しい原本を再利用し、改変済みファイルは上書きせず拒否する。

**この復元は転送だけ。** 数値価格parse 0、学習0、保護期間の教師open0、実行grant作成0。元原本や認証情報をGitHub public研究ディレクトリへpushしない。

## 2. Windowsの既存アカウントをworkerとして使用

`useradd` は使わない。専用Linuxアカウントも不要。**既存Windowsログインを通常権限で使い、所有者管理用の設定だけNTFS ACLで保護する。**

一度だけ **管理者として起動したPowerShell** から、同じアカウントのWindows環境を整備する。

```powershell
$v2 = "C:\Users\Owner\Desktop\ark-terminal\research\preopen-selector-v2-20261014"
$src = Join-Path $env:LOCALAPPDATA "ArkTerminal\SelectorV2\Sources"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$v2\tools\Install-ArkV2Windows.ps1" -DownloadedSources "$src"
```

これで、保存原本は `C:\ProgramData\ArkTerminal\SelectorV2\Sources` に**検証後だけ**配置する。controller/sourceはAdministrators・SYSTEMが書込可能、ユーザーは読み取りのみ。outputとpin journalはユーザープロファイル内の分離したフォルダー。ACLは明示的に検証する。Windowsサービス、WSL、Docker、Linuxユーザーは不要。

**実市場CLIは管理者PowerShellで動かさない。** 実行は既存Windowsユーザーの通常PowerShellで行う。現在の未設置owner-channelは、実際の元データ意味契約・元権利・用途別の信頼済み記録が揃い、ownerが確認した内容を管理者が取り込む場合だけ `-OwnerConfigFile` で別途設置する。単なる生成JSONのtrueやテストfixtureでは市場を解放しない。既に伝えられた分割と研究利用意思を再質問する必要はない。

## 3. 取得後、Workが自動で進める作業

1. 実24原本のheader/date/RAW units/調整前basis/企業行動/dated普通株/lot/knownAtの契約を、許可済みscope内で確認する。PROTECTEDの旧sealと他研究露出を削除せず、V2専用reuse overlayへ用途を対応付ける。
2. source profileとmanifestをhash固定し、Windows controllerへBだけの承認をインストール。Bは**FIT120/CAL20＋rolling HISTORYのみ、学習0**。
3. MODE B censusで日別G0/G1/G2通過数、raw/clean+1/+3/+5、Low−3/−5、教師support、95列欠測、FIT oracleを測る。Validation/Final教師を見ない。
4. BがPASSの場合、固定の市場1candidate、Risk+Opportunity各1 fit、2温度較正へ進む。既に設定採用済みなら同じ設定を再質問しない。結果が未達なら失敗を記録し、報告の数値を改ざんしない。
5. VALIDATION20日がPASSした場合だけ、同一モデルのFINAL40日を開く。その後、既存Entry/EXIT/Capitalとの**独立**比較候補を準備する。Frozenへ統合・本番売買は禁止。

## 4. 検査と停止条件

- `tools/windows_restore_mode_b_sources.py` : Windows環境でのみrestore/verify。固定scope以外・パス逸脱・junction/symlink・既存上書き・hash不一致・GitHub認証不足は拒否。
- `src/ark_selector_v2/windows_security.py`: Windowsの管理者所有controllerとDACL、通常権限worker、private journal、再解析ポイントをfail closedで検査。
- `tools/Install-ArkV2Windows.ps1`: Windows標準の `icacls` で制御。アカウント作成なし、モデル/承認の捏造なし。
- `tests/test_windows_bootstrap.py`: 転送・Windows ACLの人工境界試験。Windows runnerの専用CIと、既存Ubuntu側のV2/V1全回帰で検証する。
- 現実のWindowsアカウントでのインストール・実原本24件の認証転送は、**実際にそのPCで実行して検証するまで成功とは報告しない**。

## 固定安全条件

`executionAllowed=false`、`brokerWriteAllowed=false`、`excelOrderWriteAllowed=false`、
`rssOrderFunctionAllowed=false`、`liveTradingAllowed=false`、`paperTradingAllowed=false`、
`automaticPromotionAllowed=false`、`productionUpdateAllowed=false`、`transmitted=false`、
`productionReady=false`、`entryAllowed=false`。

V1、No.1.1 Frozen、State9原本、既存Entry/EXIT/Capital、main、PR #591には変更0。
