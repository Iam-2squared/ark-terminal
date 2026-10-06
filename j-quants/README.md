# J-Quants 専用保存場所

更新実時計JST: 2026-10-06T13:33:23.954930+09:00  
repository: Iam-2squared/ark-terminal  
専用branch: data/jquants-raw-cache-20261006-v1

現在地は **CACHE_BLOCKED_AUTH_OR_STORAGE**。このRAW cache Workの公開可能な記録36件、現在の事前確認コード・workflow 3件、過去成功した取得経路の参考原本4件をここへ集約した。取得可能な全dataset／全期間のRAW保存は未開始で、全量保存済みではない。

| 場所 | 内容 |
|---|---|
| [CURRENT_STATE.json](./CURRENT_STATE.json) | 最新の現在地、実時計、取得量、残る前提、次方針 |
| [PUBLICATION_INDEX.json](./PUBLICATION_INDEX.json) | 集約43原本の元commit・blob・SHA256・bytes・取得元 |
| [evidence/20261006-v1/](./evidence/20261006-v1/) | registry、hash、coverage、取得状況、既存cache台帳、利用権、保存先、方針、Work原文、読戻し証跡の全36件 |
| [code/](./code/) | provider requestsを行わないpreflightと既存合成guard検証 |
| [history/acquisition/](./history/acquisition/) | 過去成功した直接API取得・checkpoint・復元・認証guardの参考コードとworkflow |
| [workflows/](./workflows/) | 既存metadata preflight workflowの参照用コピー。実際のActions入口はrepo直下の .github/workflows/jquants-raw-cache-preflight-v1.yml |
| [PRIVATE_STORE_BINDING.json](./PRIVATE_STORE_BINDING.json) | RAW用保存先のbinding。未成立のためpathはnull |
| [STORAGE_POLICY.json](./STORAGE_POLICY.json) | GitHubへ置くもの、RAWの保存条件、利用期限の扱い |
| [SAVE_CHECKPOINT.json](./SAVE_CHECKPOINT.json) | 今回の専用場所作成の実績と次方針 |

このrepositoryは現在 **public** で、フォルダごとのprivate設定はない。最初のWork指定および[公式利用条件](https://jpx-jquants.com/ja/help/usage)に従い、ここへ保存するのは公開可能なコード・台帳・hash・coverage・取得状況・方針・実時計。RAW本体、RAW archive、キー、署名URLを置かない。RAWは利用権が有効な間に本人専用の既存永続保存先へ保存し、その場所・hash・coverageをこの台帳から追跡する。

既存Actions secret JQUANTS_API_KEYの存在は確認済み。過去の[成功run 35447995157](https://github.com/Iam-2squared/ark-terminal/actions/runs/35447995157)と[取得・復元方法](./evidence/20261006-v1/ACQUISITION_METHOD-ja.md)も保存した。ブラウザーの403は、この直接API経路の認証失敗の証拠ではない。今日のAPI認証・現契約は未確認。

[全datasetの候補registry](./evidence/20261006-v1/DATASET_REGISTRY.json)は11候補。provider bulk/listは未実行で対象分母はnull、RAW取得・再利用検証・永続readbackは0。空のmanifestは取得対象0件や全量完了の意味ではない。source artifact metadataは原本の現bytes検証とは区別する。

本人専用の永続保存先、現契約のLight／アドオン別期限、全利用者の共有limiter、本線の固定snapshot readerを確認してから、bulk/listで全期間の分母を固定し、Light基礎・Minute・Tickの別queueで取得する。契約変更・追加課金・モデル学習・Capital Replayは行わない。

evidenceは元の時刻・内容を保つsnapshotで、過去のcheckpointの件数は当時の値。最新の現在地はこのfolder直下のCURRENT_STATE.json、全ファイル読戻しの結果はPUBLICATION_READBACK.jsonを参照。本線branchや既存snapshotへの書込み・job停止は0。
