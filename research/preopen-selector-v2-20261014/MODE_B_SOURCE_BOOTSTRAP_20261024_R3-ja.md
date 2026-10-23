# V2研究用途の登録と実行環境調査 — 2026-10-24 JST

実市場データの数値読取は0日。MODE Bは未実施、G1/G2平均通過数・G2内clean +3/+5残存数はNOT_MEASURED。市場candidate / fit / calibrationは0 / 0 / 0。VALIDATION / FINAL教師は未開封。

今回保存したのは、原本復元の検証、用途別登録、実行環境調査、原本転送・metadata検査ツールと試験結果。市場測定結果ではない。

## 所有者指示と固定仕様

開始HEADは`ff11de79863595ac0dd02273ac77e28c079896f3`。PR #594はOpen/Draftを維持する。
今回ユーザーが送った作業指示URLの完全な文字列bytesと、参照文書のblob/SHA256をroot管理記録へ結合した。
このメッセージの正確な送信日時は取得できないためnullとし、登録時刻とは区別した。Personal Contextで取得できた過去の許可発言は抜粋としてprivate保存し、完全な原文や所有者署名とは呼ばない。

`OWNER_PURPOSE_REUSE_OVERLAY_20261024_R3.json`は固定150/120/20/20/40営業日、公式calendar hash、実採用config/CORE95/quality hash、MODE B fit0とMODE B PASS後の一候補委任を結ぶ。
parameters_adopted=trueはこの固定設定の採用記録。元のPROPOSALや旧未承認時点のpackageは変更していない。数値gate・教師・95列・モデル・順位・品質目標・分割の変更は0。

旧protectedHoldout台帳は変更せず、V2の指定用途に限るreuse overlayを追加した。研究200日・先行45日の保護履歴を保存し、REPORT19の正確な対応および他研究露出はUNKNOWN_EXPOSURE、freshOosCredit=0と記録した。
現在の所有者研究利用指示と2026-10-06のprovider receiptを区別し、provider独立確認、新しい有効期限、旧V1限定申告の転用は主張しない。
登録は市場Authorityそのものではなく、`owner-channel.json`の実行grantは未設置。

## 保存原本と転送障害

添付のpart002〜005は直接受領できなかったが、16個の再送chunk ZIPから復元できた。chunk ZIP、chunk、復元part、全体archiveのSHA256と56entryのCRCを検査した。
全体は2,403,054,972bytes、SHA256 `7f1e0a7f4a98bcd613286de5acfa370963ea106ac845502b763de61e526e390f`。
中身は既存MA4用の2023〜2024年原本であり、今回の固定V2期間の原本ではない。価格・教師の数値化は0、期間のfallbackは0、再アップロードは不要。

既存MODE B scopeの24原本・51,429,816bytesについて、J-quants-Eの完全なcanonical Git treeを取得し、保存blob・byte数・metadata manifestを照合した。
logical object keyにはない`raw/`を含む実保存pathを、blob identityから解決した。初期のlogical pathの404を原本欠如の証拠にはしていない。

正しいpathと保存commitでのbase64 fetchはblob identityが一致する一方、contentが空だった。blob取得はUnicodeDecodeError、汎用blob endpointもUTF8限定でbinaryを拒否した。
private Git cloneは認証なしで失敗し、ローカルGH_TOKEN/GITHUB_TOKEN/ghも利用できなかった。保存run 37425728394のartifact一覧は0件。
したがって対象原本のpayload取得・再hash・header/date/単位/basis検査は未実施。24件のmetadata照合を24件の原本検証と読み替えない。

追加した`tools/restore_mode_b_sources.py`は、固定root登録から選んだ保存blobだけを復元する。既存認証は転送だけに使い、利用権の自己申告には使わない。
圧縮bytesのsize/SHA256/Git blob SHA1を照合し、既存原本を上書きしない。metadata検査はDateを先に照合し、許可日以外のCodeや価格を変換しない。価格・教師・売買代金の数値変換、source profile採用、学習grantの生成は行わない。

## OSで実際に成功・失敗した操作

通常の管理コマンドを実行した。

```text
useradd --system --no-create-home --shell /usr/sbin/nologin ark-v2-worker
exit_code=1
Cannot open audit interface - aborting.
```

専用workerは存在せず、別の既存UID、passwd直接編集、rootでの市場CLI実行、試験grantでの代替は行っていない。
root所有の指示原文・用途別overlay・source inspection登録・固定コードsnapshotを設置した。source/output/journalは別directoryでsymlinkなし。
root登録の読取と24原本の存在検査は成功し、対象payloadは0/24件だった。復元ツールは認証付きprivate binary転送未設定として停止した。
非root worker権限検証、独立producer pin、再起動後のjournal永続性は未検証であり、完了とはしていない。

## 再開に必要な具体的作業

1. 所有者の認証済みGitHub CLI/SDKまたはprivate mountで、登録された既存24blobを配置する。providerからの新規取得や同じZIPの再送は不要。
2. 通常のOSアカウント管理が使えるowner hostで専用非root workerを設置し、root固定コード・設定と独立永続journalの権限・再起動後の照合を確認する。
3. 登録済み用途のmetadata検査を行い、実header、dated identity、lot、RAW suffix、単位、knownAtを確認する。capture時刻とSCHEDULE_ASSUMEDの過去利用可能時刻を混同しない。
4. 確認したprofile/hashとMODE B precommitを実行Authorityへ結合し、FIT120/CAL20・rolling HISTORY289日のcensusをfit0で実施する。B PASS時だけ、同じ指示に基づくMODE Cの1candidate/2fit/2calへ進む。

新しい利用意思の再質問を再開条件にはしていない。実source意味契約の確認は原本転送後の工程であり、未確認値で埋めたprofileは作っていない。
private checkpointは環境の復元資料であり、別hostでそれだけを信頼した実行Authorityに昇格させない。

## 検証と状態

原本復元、OSの実操作、source存在検査は実行記録を保存した。追加5試験はDate-first・価格poison非変換、hash先行、解凍上限/重複、FINAL用途拒否、symlink/path拒否を確認する。
最新HEAD専用CIのrun/job・decoded logはPR本文へ結合する。過去HEADのCIを今回の受入結果にはしない。

ENGINEERING_PASSは人工経路・工学検証に限定。MARKET_MEASUREMENT_COMPLETE=false、POINT_TARGETS_MET/ PREDICTIVE_QUALITY=NOT_MEASURED、STATISTICAL_SUPPORT_ESTABLISHED=false、LIVE_READINESS=NOT_CERTIFIED。
全11執行flag=false。実注文、paper、provider新規取得、main merge、force push、Ready化、V1/Frozen/State9/既存Entry・EXIT・Capital/PR591への変更は0。
