# 実source採用の検証表

実source profileは未採用。月次CSV adapterの人工PASSと実原本の意味確認を分ける。
V1コードをimportせず、読取参照だけを行った。

| 検証対象 | 既存根拠 | MODE B前後に必要な確認 |
|---|---|---|
| RAW日足 | V1 preopen_native_source.py blob 6d41961c1093362a6f25e048dad628f38a39c63e がO/H/L/C/Vo/Vaを使用 | 実42原本のexact header、null、単位/factor、価格basis。Adj値へのfallback禁止 |
| dated普通株 | V1 preopen_source_contracts.py blob a83cd02215e9709fe996b7ee35bb12be7db31b3f | Date+ProdCat+Mkt+Codeを組合せ、当時版を確認。末尾単独判定禁止 |
| alpha code/lot | 同上の分類version、2018-10-01以後の100株統一根拠 | dated identity対応、除外種別・特殊code、100株lotの適用範囲をownerが固定 |
| 株式分割 | RAW suffix契約は実装済み | 各identityの比較可能suffixと境界証拠が未確定。未来調整係数を使用せず、不足はUNKNOWN |
| knownAt | V1のavailabilityContractはschedule仮定を扱う | event/published/available/capturedを別記。保存時刻を過去公表時刻に戻さない |
| 月次境界 | Date-first slice、hash/bytes検査、解凍上限は人工試験済み | object-key期間と実record coverageの相違を承認済み日付だけで検査 |
| optional44列 | SOURCE_NOT_JOINED→Noneの固定route | 未接続を0へ変更しない。新source joinは今回実施しない |

42原本の価格payloadをMODE Aで開かず、exact headerや実record観測済みとはしない。
source profileのheader/identity/suffixを先に必要とする現行admissionにはbootstrap依存がある。
owner管理の既存source-contract/dated identity/CA metadataがあれば、そのhashを採用する。
なければ、同じMODE B用途内で、指定日付のmaster・CA・header metadataを確認する
owner承認と証拠作成を先に行い、生成profileをownerが独立pinしてからcensusを開始する。
現CLIに任意rawを無承認で探索するbootstrap bypassはない。未確認profileを仮採用して
censusを始めない。この依存は承認パッケージにも残す。

利用根拠は2026-10-06のprovider receipt、V1継続根拠はV1用途のもの。
現在のV2権利・protectedHoldoutの用途別開放・REPORT19照合・他研究露出を別に確認する。
Fresh認証は付与しない。現行権利の確認に新provider取得や原本再送は必要ない。
