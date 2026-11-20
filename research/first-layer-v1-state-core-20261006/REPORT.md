# ARK FIRST LAYER V1 — Phase 0 checkpoint

最終statusは **BLOCKED_DATA_OR_LINEAGE**。停止地点はPhase 0であり、PRIMARY Dの性能は未評価です。今回のmodel fit／preprocessing fit／provider新規取得／CAL threshold探索／TEST開封はいずれも0です。

記録時計: UTC 2026-10-06T11:20:46.964035+00:00 / JST 2026-10-06T20:20:46.964035+09:00。Owner: Iam-2squared; recovery executed by Codex。
文書ID: ARK_FIRST_LAYER_V1_STATE_CORE_WORK_20261006。
新規branch: `research/first-layer-v1-state-core-20261006`。public基点は正式EXIT Freeze branch HEAD `1ecbcc43f75279fa302f19fd896add2aac15b537`、private基点は `ed8aa200525a62cf43de78297625357d90c1a2bd`。main変更・force pushは0です。旧Signを再開せず、新しいState-Core研究の停止checkpointを作成しました。

## 必須16項目

| # | 回答 |
|---|---|
| 1 Freeze pins | 下記とSOURCE_PIN.json。Entry P1_Q70／Frozen EXIT v3／State9 RC2／Path contractを維持。 |
| 2 使用RAW | A〜Eの保存inventoryとGit tree/Private Release metadataを照合。市場特徴に使用した原本は0 objects／0 bytes。必要C Minute 4件は下記。 |
| 3 provider | 新規request=0。必要原本は存在するためproviderによる代替取得を行っていない。 |
| 4 母集団・Exposure・split | 2025-05-30〜2025-08-25、58 sessions、1,600 Entry。PLUS706／MINUS854／UNKNOWN40／ZERO0。露出済みDevelopment。FIT/CAL/TEST境界は未設定、適用件数は各0。旧splitは継承しない。 |
| 5 表現 | CURRENT → 連続観測TRANSITION → 最大6 State runsのPATH → Stateに対応したprice/Volume/Value/timeの新規proposal。実matrixは未構築。 |
| 6 future／missing監査 | 未実行。RAW本文readbackも未合格。future suffix invarianceやmissing continuityをPASSとはしていない。 |
| 7 A/B/C/D/E | 各fit0、結果なし。DをPRIMARYとしてproposalに固定、A/B/C/Eは診断。 |
| 8 PRIMARY D CAL | PLUS retention／MINUS rejection／passed PLUS precision／coverageはいずれも未測定。0%や正解扱いに置き換えない。 |
| 9 CAL Gate | NOT_EVALUATED。最小MINUS rejection、整数miss budget、split等が未確定のため実行可能PRECOMMITを発行していない。 |
| 10 TEST | 開封0、適用0。TEST結果なし。 |
| 11 session／不確実性 | Session別class countのみ回収。頑健性・信頼区間は未評価。 |
| 12 独立監査 | Phase0 metadata/ledger限定: 1,891 checks、mismatch0。Phase5性能・未来漏洩の独立監査は未実行、mismatchはNA。 |
| 13 status | BLOCKED_DATA_OR_LINEAGE。研究のPASS/FAILを推測しない。 |
| 14 実行量 | 新規教師生成0、feature archive0、State engine0、EXIT replay0、fit0、preprocessing fit0、technical model retry0、provider0、threshold探索0、protected RAW開封0、Capital0、orders0。既存private original回収1、GitHub Actions artifact download1（metadataのみ利用）。 |
| 15 保存 | 新規public/private branchへcheckpointを保存。保存commit、各fileのblob/bytes/SHA256とactual GET・branch HEAD照合はREADBACK_RECEIPT.json、receipt保存後の最終HEAD照合はWork完了回答に記載。 |
| 16 次方針 | STOP。既存C Git objectの認証付きbinary取得とFreeze依存物の回収・QAを完了してからPhase0再開。PRECOMMIT保存・actual GET後にのみ特徴構築／fitへ進む。Second/Third Layer、Capital、productionへ進まない。 |

## 最新権威Freeze

| 対象 | authority commit / hash |
|---|---|
| Entry authority HEAD | `4a2d6f35946b16820a13449a9288a6685a5c283c` |
| Frozen Entry records | 452,854 bytes / `e7a6140b6b11d8d078a271fad76b75e68a5b2fda9e45c7db43d98ee2f282abeb` |
| Selector contract | blob `37abd9a4464d4d4064c088d6492100b4674418d4` / SHA256 `e75a49adb2a35497b6ac4d1afdd2942f87d9e139f04ae98e2478ca564ee874d8` |
| P1_Q70 Entry contract | SHA256 `a60f604cdcdfe5dc9d673fd502883dc17797cceb06b1c2680b1a7e41cb07a750` |
| EXIT official receipt HEAD | `1ecbcc43f75279fa302f19fd896add2aac15b537` |
| Frozen EXIT v3 final HEAD | `c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad` |
| EXIT contract | `ee573737833ca000beb543da617ce7c4d3815d92108d728a48baa725481381a3` |
| EXIT provenance manifest | `6becd10c04601c040ea329fa6fa569aa1036ab2aa79aa826d44e50e22f8501db` |
| State Path authority HEAD | `f4f00f32bae2491095a8ed29916b4f470f496fcf` |
| State9 RC2 contract | `45859122a62ccdc946b31bb5709f3fc080ea4a4f935958afd8f1ca895f75b6ff` |
| State Path contract | `fc3808cb7d3d161e85527d7ebf97f902df7f0c3463457beddf1a25d053cee268` |
| PATH_FROZEN.py expected pin | `ad59222fcc0f9dfed4698efb49a87d66ea4e01b90562cdcaa8b9bc028ffffbf8`（本文未回収） |

SOURCE_PIN.jsonにsource repo/commit/path/blob SHA、残りのsemantic pin、6 EXIT code hash、teacher identity/maturity/source hashの出典を保存しています。正式権威receiptをGitHubからactual GETし、契約とEXIT codeは保存hashに一致しました。添付handoffを最新Freezeの代用にしていません。

EXITは固定売値targetではありません。固定State9 EXIT_A/B/C policyとSESSION_CLOSE fallbackです。next eligible regular RAW Openのfill/cost、dated calendar・lunch規則は凍結コードのまま維持しています。このWorkではEXITを再実行していません。

## A〜E正式保存ソース

| Repo | originals | bytes | Git / Private Release | 今回RAW利用bytes |
|---|---:|---:|---|---:|
| A Iam-2squared/J-quants-A | 14 | 10,387,317,454 | 0 / 14 | 0 |
| B Iam-2squared/J-quants-B | 13 | 9,646,782,612 | 3 / 10 | 0 |
| C Iam-2squared/J-Quants-C | 13 | 1,136,175,906 | 13 / 0 | 0 |
| D Iam-2squared/J-quants-D | 14 | 1,076,069,715 | 11 / 3 | 0 |
| E Iam-2squared/J-quants-E | 1,664 | 1,856,768,532 | 1664 / 0 | 0 |

合計1,718 originals／24,103,114,219 bytes。保存receiptのunsaved=0・blocker=0・full_remote_SHA256_verified=trueを、今回のRAW本文SHA256 readbackやFresh/OOSと同一視していません。各CURRENT_STATE／ALLOCATION／transfer/provider receiptと全objectのstorage locationを確認し、Git blob sizeまたはPrivate Release asset digest/sizeを独立再照合しました。

Aのroot HASH_MANIFESTは旧public-safe Git inventoryです。B〜Eに同名ファイルがあるとは仮定せず、原本SHA256 inventoryは各ALL_NATIVE_STORAGE_STATE、E APIはAPI_RAW_STATEから回収しています。A/B/Dはdraft Private Releaseなのでtag endpointの404を原本欠落と判断せず、release list GETからasset metadataを確認しました。署名URL・secret・private raw bodyをpublicへ保存していません。

## 初回に必要なC Minute原本

| 月 | bytes | SHA256 | Git blob SHA |
|---|---:|---|---|
| 202505 | 86,185,623 | `a671695eb4c9ed37c10515e768d4278a9cc701dacd022af99a35d2615bcec965` | `34ddebe04e35cc1c9ab2cf2645e6956ec2809800` |
| 202506 | 86,117,134 | `58572650290f6a8268b9add5d3ca50a7f501758f9f1ef940ace46d98510ac011` | `d76eb3518e53a912e0cd7e0ec22944e0fcaa1834` |
| 202507 | 91,406,828 | `32d4c22fa3a69258f64527d0d8fe810a2c29fb3e7160e98876b30752dd8197ba` | `47996b5ef2d5d30254c351fd863659cb5cfa07ec` |
| 202508 | 90,574,217 | `14b0d3eb810fb2e3eb24f494b12814e79d4f1f16870c97f328a5857eb2092bbe` | `c1f3a3cff0fe53d88ecaa4587953038658b97bcb` |

4 objects合計354,283,802 bytes。C HEADは `09dcb8d8e1a2063e077006e44a456179e90a60b8`。May objectのGETはblob SHAを返しましたが本文は0 charactersでした。これは原本がないという証拠ではありません。後続月を未検証の代替sourceに置き換えず、特徴入力0 bytesで停止しています。Tick A/B、EのLight/API等は初回へ投入していません。

## 台帳と独立監査の限界

Private Gitの原ZIPは26,213,376 bytes、SHA256 `f44ac726082843064f93666dce9cdeaa3b70a6a7503934c32e9452b61fdeab4c`、blob `ef8bb7ab930ca1c81de01d45811c582d80f7fbf5`。既存原本を回収し、このGit blobと全体hashが一致しました。保存教師SIGN_TARGETS原本は78,284 bytes、SHA256 `37395d7567df741a74b1ff749a32118cec04ed988da101b81634c2c55ae9ae0d`。原本辞書を変更せずteacher ledgerへ保持しました。

EntryはFrozen Entry原本からBUY_INTENT identityだけを投影しています。score、旧threshold、fill、将来値や旧feature matrixを投影していません。teacherはfeature locatorと別fileです。原教師のnet符号・maturity/hashの整合は確認しましたが、全native EXIT rowの独立再構成は未完了であり、teacher production lineageの完全な再監査をPASSとはしていません。

旧保存アクセスログのunionは1,589 Entry。今回は全1,600 Entryの教師台帳を読み、全58 sessionsを露出済みDevelopmentとして登録しています。未露出と認定したEntryは0。commonHoldout 244 datesは区分metadataだけを確認し、RAW・教師を開いていません。追加期間のFrozen Entry producerは最新source auditで9 inference assets/routing未認証です。これは追加期間/Fresh利用の制約であり、既存58-session DevelopmentをFreshと呼ぶ根拠にはなりません。

古いviewのPOSITIVE/NEGATIVEと現教師のPLUS/MINUSには1,560件の文字列差があります。identity、maturity、source hash、y_plus/y_negの符号意味は一致しました。原本とpinを変更せず、schemaの対応として記録しています。初回のliteral比較receiptもprivateで保持しました。また2件のlocal writer終端LF差は元のactual GET bytesからmaterializeし直し、失敗digestをprivate保存しています。upstream source/pin修正は0です。

## 再開条件

1. C既存Git原本4件を本文取得し、指定bytes/SHA256でactual readbackする。
2. Frozen State9／Transition／Path／PATH_FROZEN.pyと固定EXITの必要依存物を原本で回収し、State/auxiliary/availability fieldを正式contractへ対応付ける。Entry/teacherとcutoff・calendar・session/lunch・missingness・maturityのQAを閉じる。
3. 58-session露出済み母集団に対し、実在date/Entryからchronological split・maturity purge・有限threshold候補・exact blocks・整数PLUS miss・最小MINUS rejection・support/session/uncertainty Gateを結果前に決める。
4. 最終PRECOMMITをGitHub保存しactual GET/readbackしてから、teacher非可視のfeature builderを作る。6 runs proposalを守り、future suffix mutation、gap/reset/aux/Volume/Value/UNKNOWN試験を実施し、feature archiveとmatrix schema/hashをsealする。
5. その後だけA/B/C/D/Eの限定logistic fitとCALへ進む。CAL不合格ならTESTは開かない。PASSでも次Layerへ自動進行しない。

今回のREPRESENTATION_PROPOSALは実行可能PRECOMMITではありません。結果後のfeature追加・split変更・Gate緩和・旧Sign再開・別family救済・provider代替取得を認める文書ではありません。
