Phase57 LONG-only Global Fresh Data Budget — 2026-09-16 JST

**PHASE57_LONG_ONLY_GLOBAL_DATA_BUDGET_BLOCKED**

Candidate 2.0、final model/scaler、Selector、Fit Contract、Development Evidenceの保護対象ハッシュは一致。今回の成果はmetadata監査と未確定事項の固定であり、Global Allocation ContractのFreezeではない。新規allocation、取得、prediction、outcome閲覧は行っていない。

対象は `research/phase57-long-only-cash-equity` / PR #587。監査基準headは `825da2af3256f554f4586be0db6d5ba36cc23309`、確認したmainは `6b6c4d522cd1863132185463a0aed74bc819be01`。公開commitはこの監査成果を追加するcommitであり、機械可読レポートのauditedHeadとは区別する。

全95項目の回答は [final-report-95-items.json](final-report-95-items.json)。session別identity・secondary flags・旧allocationは [resolved-master-ledger.json](resolved-master-ledger.json)。出典は前監査の [source index](../phase57-long-only-fresh-allocation-audit/audit.json) にcommit/blob/SHAを固定し、今回追加したidentity調査は [unknown-resolution.json](unknown-resolution.json) に保存した。

| 排他的primary分類 | 前回 | 今回 | 差分 |
|---|---:|---:|---:|
| EXPOSED | 375 | 375 | 0 |
| RESERVED | 5 | 4 | -1 |
| SEALED | 32 | 25 | -7 |
| PROTECTED | 未分離 | 1 | 分類を明示 |
| FRESH_AVAILABLE | 0 | 0 | 0 |
| PURGED | 未分離 | 3 | 分類を明示 |
| EXCLUDED | 未分離 | 4 | 分類を明示 |
| UNKNOWN | 101 | 101 | 0 |
| TOTAL IDENTIFIERS | 513 | 513 | 0 |
| 日付対応済み | 412 | 412 | 0 |

これは前回の513識別子に限定した台帳であり、Repo全historyやprovider在庫の総量ではない。日付推定、Fresh昇格、予約解除は0。primary分類を細分化しただけでsecondaryのsealed/protected/reserved flagsは保持した。EXPOSEDと予約は両立し、予約解除でFreshへ戻ることはない。

UNKNOWN 101はProtected parent ordinal 181–281。13種類のmetadata path、過去版を含む15個の異なるmetadata blobで明示的なordinal/date対応を調べたが、解決0、残101。元allocation生成コードも確認し、remainingReserveは先頭・末尾・件数・ordinal範囲のみを保存していることを確認した。休日推定で埋めない。親Protected103には日付既知の先頭と末尾があり、末尾には既存exposure記録がある。Protected103を新たな103日として台帳へ加算しない。

| 前回の分類対象 | 用途・細分類 | 件数 | 今回の扱い |
|---|---|---:|---|
| SEALED32 | Legacy Entry Validation | 15 | SEALED維持、LONG Candidateへの転用不可 |
| SEALED32 | Legacy Entry OOS | 10 | SEALED維持 |
| SEALED32 | Protected先頭 2026-01-08 | 1 | PROTECTED、seal維持 |
| SEALED32 | 恒久source-validation除外 2025-01-14～17 | 4 | EXCLUDED、保護維持 |
| SEALED32 | purge 2025-01-30 / 03-10 | 2 | PURGED、保護維持 |
| RESERVED5 | EXIT DEV_A / LONG Development_A 2024-09-10～13 | 4 | RESERVED維持、未曝露と断定しない |
| RESERVED5 | Legacy Entry embargo 2026-10-06 | 1 | PURGED、予約維持 |

旧Entry候補30日は25 EXPOSED、4恒久除外、1 purge。EXIT予約も残る。予約解除・再取得によるFresh化は不可。

Capital/Integration向けfuture20は、旧integrated candidateの「2026-10-22以降、条件を満たす最初の20 market sessions」という1つの予約枠。正確なsession listは未保存。LONG Entryへの転用は認めず、513件へ追加せず、Integration・Portfolio・比較の各々に20日ずつあるとも数えない。LONG側のprospective25も日付未固定で、旧Entry予約期間やfuture20との所有範囲を解決していない。

| LONG工程 | 必要session数 | 既存根拠・allocation | 現時点の不足 | 判定 |
|---|---|---|---|---|
| Entry Validation | 30 | LONG data plan。旧30はFresh不適格 | 30 | 必要数のみRESOLVED、identity BLOCKED |
| Entry OOS | UNRESOLVED | LONG共有Primary30/Contingency30と旧Entry future10は別責務 | UNRESOLVED | UNRESOLVED |
| EXIT Development | UNRESOLVED | 旧EXIT70+20。LONG共有Development80 / 使用済76 | UNRESOLVED | LONG専用必要量未固定 |
| EXIT Validation | UNRESOLVED | 旧EXIT30+Historical Holdout25、cross-research exposureあり | UNRESOLVED | UNRESOLVED |
| EXIT OOS | UNRESOLVED | 旧EXIT30+reserve30、cross-research exposureあり | UNRESOLVED | UNRESOLVED |
| Integration Validation | UNRESOLVED | 専用LONG listなし | UNRESOLVED | NOT_YET_ALLOCATED |
| Capital / Portfolio | UNRESOLVED | 旧future20は保護、LONGへの移管なし | UNRESOLVED | UNRESOLVED |
| Existing Ark最終比較 | UNRESOLVED | 同一window/cost原則、LONG exact listなし | UNRESOLVED | UNRESOLVED |
| Final Integration OOS | UNRESOLVED | 最終比較と同一責務か別枠か未固定 | UNRESOLVED | UNRESOLVED |

根拠のJSONキーと各allocation案は [requirements-and-plans.json](requirements-and-plans.json)。旧EXIT90とLONG80、旧Entry15/10とLONG Validation30は同じ実験への数値矛盾ではなく、scopeが違う。小さい数字を選んで不足を解消しない。既存共有Developmentの利用義務は、後段のValidation/OOSを開発に使う許可とは異なる。

| Plan | 保全方法 | 新規必要量 | 制限 |
|---|---|---|---|
| A CONSERVATIVE | 各工程を独立identityで確保 | 30 + 各未確定工程の必要量。合計UNRESOLVED | 必要数を発明しない |
| B MINIMAL | 明示許可された共有Development、同一cache、比較2群の同一windowだけ共有 | UNRESOLVED | 評価データの工程間再利用を新たに許可しない |
| C BUFFERED | 解決済base planに事前根拠のあるintegrity予備を加える | base、bufferともUNRESOLVED | event labelabilityをsession欠損率に読み替えない |

推奨は **Bの条件付きdraft**。物理的な重複取得と許可済Developmentの重複を抑え、独立評価は保護する。ただし数値・日付・scope未確定のため、Plan採用やallocation Freezeとはしない。新規bufferは設定しない。

Existing usable freshは0、一覧は空。Protected/SEALEDは使用不可。Entry Validationの不足30日はGlobal新規取得総数ではない。全工程の新規必要総量、J-Quants取得要否、期間、session list、symbol数、data volume、request数はUNRESOLVED。外部取得なしで満たすprivate cacheの存在も確認できていない。

Repo記録の2026-09-15 entitlementではLight/minute addonの終了予定が2026-10-06であり、future20の開始下限2026-10-22より前。現在のアカウントや契約を照会していないため、将来取得可能とは保証しない。既存source metadataのraw未保存・artifact期限切れは、現在の全private cacheが存在しない証明ではない。

取得draftは [acquisition-draft.json](acquisition-draft.json)。Frozen JPX common-equity universe、PIT eligible cross-section、因果的な日次/master/minute fieldsを維持。Entry cadenceは既存10 decisions/sessionで、5分Selectorへの変更なし。価格取得の前に全工程budget、identity、必要fields、cache照合、entitlementとrequest上限を固定する。後工程fieldsは未確定であり、現時点の30日取得が最小十分だとは主張できない。

Protected ordinal解決のための将来のmetadata候補は `/v2/markets/calendar`、Date/HolDiv、2025-04-15～2026-06-11、symbolsなし、既存実装上の基本1 request。ただし今回実行0。元calendar snapshot・除外registry・既知anchor・282件identityの照合が必要で、現在calendarだけでは元allocationやFreshnessを証明できない。calendarが解決しても後工程budgetは未解決なので、ここでqueryは行わない。

| 消費段階 | 後工程に残す責務 | 残数保証 |
|---|---|---|
| Entry Validation後 | Entry OOS、EXIT、Integration、Capital/Portfolio、比較 | UNRESOLVED |
| Entry OOS後 | EXIT、Integration、Capital/Portfolio、比較 | UNRESOLVED |
| EXIT Development後 | EXIT Validation/OOS、Integration、Capital/Portfolio、比較 | UNRESOLVED |
| EXIT Validation後 | EXIT OOS、Integration、Capital/Portfolio、比較 | UNRESOLVED |
| EXIT OOS後 | Integration、Capital/Portfolio、比較 | UNRESOLVED |
| Integration後 | Capital/Portfolio、比較、必要ならFinal OOS | UNRESOLVED |
| Capital/Portfolio後 | 最終比較、独立ならFinal OOS | UNRESOLVED |
| 最終比較後 | 別契約ならFinal Integration OOS | UNRESOLVED |

今回の消費は全段階0。将来の十分量は保証できない。取得順はGlobal Budget解決→identity/cache/取得契約→Entry Validation→Entry OOS→EXIT Development→EXIT Validation/OOS→Integration/Capital/比較→必要ならFinal OOSというdraftにとどめ、各開封は別gate。悪い結果を理由に期間追加・交換しない。

Blockers: `UNKNOWN_IDENTITY_UNRESOLVED`, `ENTRY_BUDGET_UNRESOLVED`, `EXIT_BUDGET_UNRESOLVED`, `INTEGRATION_BUDGET_UNRESOLVED`, `PORTFOLIO_BUDGET_UNRESOLVED`, `PROTECTED_DATA_CONFLICT`, `INSUFFICIENT_METADATA`。

検証はmetadata-only監査スクリプト、台帳不変条件、保護hash、全95項目、diff/manifestの確認に限定。model・評価regressionやCIを今回のFreeze成功根拠に使わない。Full regression PASSとは報告しない。今回のoutcome閲覧、Candidate/Validation prediction、OOS/EXIT outcome、model/scaler fit、SHORT評価、Yahoo/J-Quants/その他market-data価格request、provider metadata request、実allocation変更は全0。Safetyは全false。

次の工程は **LONG Stage Budget / Evaluation Reuse Responsibility Contract** の不足部分だけをoutcome-blindで固定すること。Entry OOS、LONG EXIT Dev/Validation/OOS、Integration、Capital/Portfolio、最終比較の必要量と共同評価の可否を定義し、既存予約とfuture20を保護する。必要なら元Protected calendar identityをmetadataだけで回収する。価格取得・Validation測定には進まない。

Global Data Budget Contract SHAは **未発行**。manifest SHAはBLOCKED監査成果の整合性証拠であり、FROZEN allocation contractのSHAではない。
