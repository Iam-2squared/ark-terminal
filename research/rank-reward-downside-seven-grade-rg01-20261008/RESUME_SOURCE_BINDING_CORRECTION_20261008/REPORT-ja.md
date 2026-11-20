# RG01 continuation：SOURCE_BINDING訂正済み／別の依存manifest bytes差でS1停止

RD01のSOURCE_BINDINGはPRIVATEに実在し、指定原本をactual GETして3202 bytes、SHA256 `4d6c7eabcb09ffcf3a542bfd5fc6f3dd3c7269c4b04bff77b36431db22aaa473`、Git blob `7fdb1b86e1ab95fa2b3fd52c53603670785e05d5`を検算した。公開RD01 receiptと公開RD02 SOURCE_BINDINGによる独立保存参照も一致した。訂正を公開・非公開の同branch新subtreeへcommitし、両方の実GETで正確なbytes/hash一致を確認した。

原本のexact pin：`Iam-2squared/ark-capital-private-`、commit `cfb6c9277de332a7eeee95a78d6313fc62452355`、path `research/rank-reward-downside-rd01-20261008/SOURCE_BINDING.json`。SOURCE_INDEXへの代用・rename・原本生成は行っていない。旧公開誤パス404は解消済みで、今回のSTOP理由ではない。

新S〜Fは未生成。一次assignment 0 campaign／失敗attempt 0、評価0、ranking独立検算0、保存assignment再現0、precommit未seal。新Sが0件という実験結果ではなく、全方式・全gradeがN/A（未割当）である。新SのPLUS/MINUS・全12帯・旧S43件の移動・負け33件/Winner・同数K43/197/494・Winner保全は未実行のため数値を作っていない。親研究の成績をRG01の評価結果として再掲していない。

| method | S | A | B | C | D | E | F |
|---|---|---|---|---|---|---|---|
| U7 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| G7_FULL | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| B7_FULL | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| G7_PRICE | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| B7_PRICE | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

旧rootのBLOCKED文書・receipt・logは改変していない。今回のcanonical navigationはこのsubtreeのREPORT-ja.mdとCURRENT_STATE_RG01.json。SOURCE_AUTHORITY_CORRECTION_RECEIPT.jsonとSOURCE_CORRECTION_READBACK.jsonは訂正の完了証拠であり、研究評価PASSを表さない。

## 検出したsource差分と停止根拠

AD01原本manifestとRD01内の保存コピーはJSON内容・archive・parts・membersの全pinが一致するが、保存コピーの末尾にLF 1バイトが多い。両方の原本bytesをそのまま保持した。

| 項目 | AD01 exact原本actual GET | RD01 archive内保存コピー |
|---|---|---|
| commit | `8d02f4520cd52cbf92a0a04f6d0928289a2098e2` | `cfb6c9277de332a7eeee95a78d6313fc62452355` |
| path/member | `research/capital-v5-vacancy-admission-ad01-20261007/shared/SHARED_INPUTS_MANIFEST.json` | `rd01_sources/ad_private_SHARED_INPUTS_MANIFEST.json` |
| bytes | 17624 | 17625 |
| SHA256 | `feaaf4263e1868822b0539722963eda5750e353571b2a77f4eecd3298f63ac63` | `e6f87c9c4402ddccac832a368522ccfa7918dfb6ba8903e779cc7f726146791a` |
| Git blob / member virtual identity | `be3a2ec29c80d313e789dc8f50d5fcb34e5d49c4`（実Git object） | `bea92ebb43ecff3de5dbbffc237838f1dba8b5a9`（carrier member identity） |

差分はzero-based offset17624の追加`0a`。AD01原本はcontents GET、Git blob GET、同commit directoryのbytes/blob metadataで一致。RD01保存コピーは復元archiveと377 member内部manifestに一致。score/labelの相違を検出したという意味ではない。指示書§3「出所間で食い違いが見つかったら、対象path、差分bytes/hash/IDを記録してSTOP」と、§11の許容訂正3点に従い、末尾LFの正規化や同一原本扱いを無断適用せずCOMPOSE前で止めた。詳細はSOURCE_DIFFERENCE_STOP_RECEIPT.json。

## 完了範囲と残工程

開始HEADは公開 `e97bf8b5e4eb21700e590c1063138c4684f291ba`／非公開 `97f45a881d3ab32d3085f62346ec80e004bbe491`。両HEADに新たなassignmentはなかった。旧rootトップ各18ファイルの実bytes/blob一致、private checkpoint53 membersの全carrier再結合、公開・非公開checkpoint receipt/confirmationの取得を完了。

RD01の11 parts・6083860 bytes・378 members、RD02 S1の9 members、B01〜B08の計224 membersを実GET・archive全bytes/SHA256/連結virtual blob・member pinsで検証し復元した。RD01内部manifestはself除外の377 membersすべて一致。sealed q列・B0・H2/H3/H5 native materializationの出所を読んだが、1039行の全件join・as-of照合は完了していない。expected1039/38 sessions/583 symbols/R-known1016/R-unknown23は親研究の期待値であり、RG01全row検証PASSにはまだしていない。

このSTOPはmixed-asofのみを理由にしたものではない。source同一性が解決すれば、指定どおり全1039のretrospective overlayを続行する。現時点はHISTORICAL_MIXED_ASOF_RESEARCH_ONLY、BUY_INTENT_DEPLOYABLE=false、CANDIDATE_FOR_CAPITAL_BRIDGE=false。strict subsetは未検証N/Aであり0件と解釈しない。

最小修復は、双方の異なるhashを保持したまま「同じarchive/member pinを記述するserializationが異なる保存manifest」と区別して扱えるかを確定すること。その許可がある場合、bindingに保存されたactual_part_prefixとmanifest basenameで共通24partsをGET・復元し、S1の未完了入力監査から続行する。SOURCE_BINDING訂正の再実験やモデルfit・score再推論は不要。6方式・定数・screenを変更しない。

既存transport/tool事象2件は継承。今回の読取／orchestration事象はWORK_STATUS_LOG_S1_STOP.jsonlに記録し、write technical repair1（local exact-byte transfer）・rank repair0・GitHub書込repair0を分離した。rank計算は未実行であり、失敗した実験回数は0。

mainRank=SAVED_R0、selectedNewRank=null、mainRankChanged=false。mainCapital=CAPITAL_MAX3_SLOT_RESERVE_V1、mainExit=SHARP_DROP_FIRST_OBSERVED_EXIT_V0、CapitalReplay=0、capitalImprovement=NOT_EVALUATED。FIRST LAYER変更false、P1追加gate OFF、productionReady=false、Safety9全false。fit/refit/score再推論0、実注文・紙注文・RSS/Excel/Broker write0、main merge0、force push0、workflow dispatch0。Fresh/OOS/Protected/Prospective未実行。

判定はBLOCKED_INTEGRITY_OR_ASOF（source manifest bytes同一性の未解決）。Champion未選定。将来固定screen・Winner保全・同数K・strict asofを満たす場合の次研究案は元仕様の1案だけ：別Workで7段階→V5 Admission/Allocation bridgeを凍結し、9×RESET20・100万円同条件で研究用Capital比較。本Workでbridge/Capitalは実装していない。

保存・実GET状態はREADBACK_RECEIPT_PUBLICATION.jsonとその後続commitのREADBACK_CONFIRMATION.jsonを参照。これは訂正・停止checkpointの保存検証であり、ランキング研究評価PASSではない。
