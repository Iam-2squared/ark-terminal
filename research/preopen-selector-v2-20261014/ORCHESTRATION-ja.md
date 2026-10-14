# 新Selector V2：承認接続とnative経路（MODE A）

旧matrix smokeは人工専用のまま維持した。新経路は `authority.py` → `native.py` → `orchestration.py`。承認JSONのtrueやCLI引数だけで市場利用できない。今回、市場承認は成立しておらず、市場candidate / fit / calibrationは0 / 0 / 0。

## 接続した範囲と残る接続

| 項目 | 状態 |
|---|---|
| 旧固定人工行列・別process smoke | 人工専用guard維持。市場入力を受け付けない |
| session別RAW／dated master native形式 → G0/G1/G2 → CORE95 → RAW教師 | 新しい同一経路で接続。人工native fixtureで検証 |
| census → train → calibrate → predict → evaluate → restore-verify | 独立したstageとして接続。各stageが承認を再照合し、前工程の自己生成artifactを独立pinで検証 |
| owner原文と承認・precommit・manifest・用途日付・親承認・予算 | hostが保持する独立Authorityとの完全一致を要求。既定はAuthorityなし |
| owner管理チャネルの実配備・別process間の信頼pin永続化 | **未設定／未接続**。requestや環境変数で代用する入口はない |
| 既存在庫の月次J-Quants CSV.gz → session別native正規化 | **未接続**。本経路はNATIVE_RAW_SESSION_V1／NATIVE_DATED_MASTER_V1のみ。元source契約・分類ルール・時点lineage未確認のため推測adapterを作らない |
| optional44列の実source接続 | **未接続**。固定95列内でSOURCE_NOT_JOINED / None。自動代替なし |
| 実市場実行・市場性能・live認証 | 未実施／未認証 |

したがって、承認ファイルの用意だけで現存在庫を市場実行できる状態ではない。normalized native入力に対するオーケストレーションと、実在庫adapter／ownerチャネルの配備を分けて扱う。将来のhost配備は認証済みownerチャネルから `Authority` を渡して `dispatch(...)` または `v2_cli.main(..., authority=...)` を起動する。Authorityの原文・承認全体・precommit・親承認・manifest・自己生成artifact pinは、実行requestとは独立に永続化する必要がある。

## 承認の照合順序

既定CLIはrequestを開く前にAuthority不在で停止する。独立Authorityがある場合も、request schema、owner原文SHA256と参照・日時、承認全体pin、candidate ID、MODE B/C、precommit pin、code/config/schema、manifest全体pin、用途別exact allowlist、連続calendar／split、教師成熟時点、source route、resource上限を確認してから原本を開く。

元ファイルidentity、hash、bytes、record date、用途、利用根拠もnative manifestへ結合する。native sourceと元原本を同一と捏造しない。人工権限はfactory生成root・各byte hash・SYNTHETIC provenanceだけに限定し、市場descriptorや変更byteを拒否する。人工短縮split／support緩和はtest_only Authority内部だけ。実市場は150 reference + 120/20/20/40と元のsupport基準を要求する。

## 工程と入力

| stage | 入力・境界 | 主出力 |
|---|---|---|
| census / MODE B | FIT/CALとその150-close参照だけ。全descriptorを最初のpayload open前に検査。VALIDATION/FINAL教師を許可allowlistへ含めない | G0～G2日別数、FIT oracle clean3/5上限、Risk3／R0-B6 support、95列観測・欠測、CAL support shift、RAM preflight。fit0 |
| train / MODE C | 別のMODE C owner承認＋MODE B親承認＋PASS census hash。FIT/CAL preflight再現一致後に候補予約。FITだけをfit | 独立2HGB、FIT別used-columns、共通日重み、base model |
| calibrate / MODE C | 自己生成base model pin、CAL入力とCAL教師だけ | 2温度、optimizer回数、固定model。追加estimator.fitなし |
| predict / MODE C | 固定modelと当該区分featureだけ。教師を開かない | 各日0～15件watchlist、全区分watchlist seal、全G2予測／feature hash |
| evaluate / MODE C | 全当該区分watchlist固定・hash照合後だけ教師open | UNKNOWN下限／最悪上限、raw/clean供給、捕捉／除外、raw・較正確率診断、固定bootstrap、不確実性と点目標を分離 |
| restore-verify / MODE C | 自己生成モデルの独立pin、固定feature、元予測 | 再fitなしの再読込と予測差検証 |

START、候補予約、各fit／calibration START/FINISH、MODEL_SEALED、WATCHLISTS_SEALED、LABEL_OPENEDをexclusive作成する。stage全体を排他的lockで保持し、途中失敗もSTART／failure receiptを残す。同じstageや候補を再試行して予算を回復できない。出力はgit外のprivate root。自己生成receiptファイル内のhashだけではpickleをloadしない。再起動後も独立host pinがなければ停止する。

VALIDATIONがFAILならFINALは未開封で停止する。人工fixtureにも点目標変更・成功overrideを設けていない。人工VALIDATIONのFAILは市場品質のFAILではなく、固定条件での停止経路試験である。

## MODE BとMODE Cの次の承認

MODE Bの正確なFIT120/CAL20/参照日付・元source hash・用途・利用根拠・seal／露出を、MARKET_APPROVAL_PACKAGE_DRAFT.jsonの不足metadata解決後に提示する。MODE Bはfit0、VALIDATION/FINAL教師開封0。

MODE Bのsupport・oracle・観測率・時点・RAM検査がPASSした後、同一の数値案／教師／CORE95／順位・全split・source route・品質目標・code/config/schema・census receipt hashを固定した別MODE C承認を求める。MODE C上限は1 candidate / 2 fit / 2温度。今回の指示・添付在庫・人工test grantは、いずれの承認にもならない。

今回metadataで確認した26元ファイルhashと在庫範囲、保護範囲、未確定項目をパッケージへ記録した。CALENDAR objectは在庫summaryに1件あるが、添付archiveにcalendarはなく、exact営業日リスト・hashは未結合。最新在庫端点2026-10-05は既存protectedHoldout内。保護日を飛ばす／古い期間へ勝手にfallbackする処理はない。原本再送は不要。

次工程は前工程FINISHとMODEL_SEALED／当該WATCHLISTS_SEALEDの独立pinも必須とする。モデルbytesだけ残った途中失敗から評価へ進まない。評価の全教師UNKNOWNでは確率診断をNOT_MEASURED_NO_KNOWN_TEACHERとし、0確率や成功に変換しない。

人工native E2Eは通常6 subcommandのv2_cli.mainを隔離host権限で起動する。CLI failureの0 reads/fit表示はauthority不在／test-only時に限る。将来の実市場承認下での失敗はSTART/access receiptによる確認を要求し、失敗時に0を捏造しない。
