Phase57 LONG-only End-to-End Data Responsibility / Session Budget — 2026-09-16 JST

**必要量・責務・再利用条件の設計は解決。Global Freeze判定はBLOCKED。**

Verdict: `PHASE57_LONG_ONLY_GLOBAL_DATA_BUDGET_BLOCKED`

今回のuser指示は、既存契約に値がない工程についても、責務・標準block・保守的なsample設計から新規必要量を決めることを明示的に許可した。本成果では前回の未確定session予算をすべて解決した。価格取得、予測、モデル変更、実session再配分は行っていない。

ただし、session identityの確認時にFrozen Candidate Contractの `trainingIdentity` 全体を表示し、その中の既存Development class別件数も表示した。これはoutcome由来metadataであり、厳密なNO OUTCOME DISPLAYを満たしたとは報告できない。数値は本成果に再掲せず、予算の根拠・計算には使用していない。Validation/OOS/EXIT outcomeやraw価格を開いてはいない。この逸脱を理由に正式Global FreezeとそのSHA発行を留保する。詳細は [audit-incident.json](audit-incident.json)。監査で0件に書き換えたり、独断で例外を許可したりしない。

対象branchは `research/phase57-long-only-cash-equity`、PR #587。監査開始head `c024ce7a68a4034a18f8663930d866d7925c892f`、確認したmain `b7801ce2c13772cbc3f5b51506819c119fe868ea`。Candidate／model／scaler／Selector payload／Fit／Development Evidence／前Global AuditのSHAは一致。RidgeはFrozen payload内の参照を維持し、外部artifactの再取得はしていない。

全86項目は [final-report-86-items.json](final-report-86-items.json)。詳細設計は [responsibility-budget-contract.json](responsibility-budget-contract.json)、出典・履歴・scopeは [source-recovery.json](source-recovery.json)。既存のFrozenファイルや監査記録は一切変更していない。

| 工程 | 責務 / 評価単位 | session最低量 | distinct first-entry最低量 | 使用block |
|---|---|---:|---:|---|
| Entry Validation | Frozen2.0の1回評価 / session・symbol-session | 30 | 新規event gateなし | A |
| Entry OOS | Validationとは別のEntry外部確認 | 30 | 新規event gateなし | B |
| EXIT Development | LONG専用candidate構築 / session・first Entry | 76既存 | 200 | DEV |
| EXIT Validation | 凍結済EXITの未見評価 | 30 | 97 | C |
| EXIT OOS | EXITの独立外部確認 | 30 | 97 | D |
| Integration Validation | 全体の接続・path・cash ledger確認 | 20 | 97 | E |
| Capital Allocation | Development上で適合・調整を予算化、その後共同評価 | 76既存＋20評価 | 評価97をEと共有 | DEV＋E |
| Portfolio | 資金/risk/position集約の開発、その後共同評価 | 76既存＋20評価 | 評価97をEと共有 | DEV＋E |
| Existing Ark比較 | 完全凍結2系統の同条件paired比較 | 30 | session/portfolio day単位 | F |
| Final Prospective OOS | 比較後も無変更で独立forward確認 | 25 | session/portfolio day単位 | G |

A～Gは相互に異なるsession集合。DEVもA～Gと分離する。今回は新しい具体的日付を割り当てていない。Capital/Portfolioの内部parameterやEXIT候補を今回選んだ意味ではない。それらの開発は別契約・別実行許可が必要で、すべてE開封前に凍結する。

30日は既存Phase57のValidation/outer OOS標準、20日は既存replication標準、25日は既存LONG prospective目標を採用した。Entry Validation30は従来どおり。旧EXITの70＋20日を新LONGの必須90日と読み替えず、共有Development契約に従って実際に使用済みの76日だけを再利用する。元80日の残り4日は既存予約を維持し、今回消費しない。

旧EXITの200 / 500 / 1000+ / 2000+は段階的checkpoint。200はCheckpoint Aのtargetであり、今回は新LONG Developmentの最低適格性条件として明示採用した。500は独立review後の拡張段階、1000は後段target、2000はcoverage次第の後段targetで、今回のminimumにはしない。v3/v4はそれぞれ別upstream・cutoff・研究責務を持ち、既存performanceを理由にLONG EXITへ採用していない。

評価event floorの97は新設値。保守的率p=0.5、nominal95%、記述的binary diagnosticのhalf-widthを10 percentage pointsとする設計選択から、`ceil(1.96² × 0.5 × 0.5 / 0.10²) = 97` とした。10 pointsは今回のminimum-viable設計上の明示assumptionで、昔からのgateとは呼ばない。Developmentの実測率・Entry/sessionをplug-inしていない。

first Entry / symbol-sessionは重複management stateを排除する操作上の単位であり、IIDを保証しない。session内・銘柄間・日をまたぐ相関を将来の不確実性報告で明示する。97件がcluster-adjusted精度、複数比較の信頼度、P&L推定精度や有意差を保証するとはしない。固定全session **AND** event最低量を満たす必要があり、97件/200件に達しても期間を早期終了しない。不足ならINCONCLUSIVEで停止し、日数追加・threshold変更・有利なevent選択はしない。

| 再利用 | 可否 | 条件 / 理由 |
|---|---|---|
| 既存LONG DEV76 → EXIT / Capital / Portfolio開発 | YES | 既存共有Development契約。in-sampleでありFresh claimなし |
| Entry Validation → EXIT開発 | NO | 独立評価を後段tuningへ流さない |
| Entry OOS → EXIT開発 | NO | component OOSを開発に戻さない |
| EXIT Validation → Integration開発 | NO | 接続修正はsynthetic/DEV。holdoutで調整しない |
| EXIT OOS → Integration Validation | NO | DとEは独立 |
| Integration E → Capital/Portfolio評価 | CONDITIONAL | 全component・rule・metricをE開封前に固定し同時評価。独立3回の再現とは数えない |
| Integration E → Portfolio tuning | NO | E後の調整は別研究・別data責務 |
| A～E → 最終比較F | NO | FはSYSTEM_FRESH |
| 最終比較F → Prospective G | NO | Gは別25日、F後の改変も禁止 |
| Legacy future20 → 今回のE等 | NO | 所有権を維持。新E20とは別物 |
| 同一identityの物理cache | CONDITIONAL | 重複取得回避のみ。曝露状態や用途許可はリセットしない |

FreshnessはENTRY_FRESH、EXIT_FRESH、INTEGRATION_FRESH、SYSTEM_FRESHを分ける。component-freshはそのcomponentの開発/選択にoutcome未使用であること。system-freshは両比較系統の全component・接続・配分・Portfolioの設計/選択に未使用であること。後段componentだけ未使用でもSystem-freshとはしない。本設計は新しい評価blockにはcross-research未曝露も要求し、上流曝露済dataでFresh不足を補わない。別々の定義とstage許可は [freshness-matrix.json](freshness-matrix.json) に記録した。

既存台帳は375 EXPOSED /4 RESERVED /25 SEALED /1 PROTECTED /3 PURGED /4 EXCLUDED /0 FRESH_AVAILABLE /101 UNKNOWN、合計513、日付対応412のまま。利用可能な既存Freshは0。Developmentに利用可能なidentityは375全体ではなく、既に許可済みの76日だけ。価格cache/pathの現存と200 Entry適格性は今回未測定であり、76日を持つことは200件保証ではない。

SEALED25は旧Entry Validation15＋OOS10。RESERVED4は旧EXIT DEV_AとLONG Development_Aの予約。UNKNOWN101を推測でFreshへ変えない。旧候補30は25曝露＋4恒久除外＋1purgeで、再取得してもFreshには戻らない。Legacy future20は2026-10-22以降の旧Capital統合OOSの規則枠として保護し、新LONG予算へのcreditは0。

| 予算集計 | sessions |
|---|---:|
| Gross工程別session-role | 463 |
| うちDevelopment role合計 | 228 |
| うちEvaluation role合計 | 235 |
| Development共有による控除 | -152 |
| E共同Validationによる控除 | -40 |
| Net unique全体 | 271 |
| 既存DEV identity credit | -76 |
| **Net unique新規Fresh / 不足** | **195** |

新規FreshはA30＋B30＋C30＋D30＋E20＋F30＋G25。これは採用した責務・標準block・共有条件の下でのminimum viable designで、統計的十分量の保証ではない。Entryと最終Portfolio-day blockに架空のEntry event最低量を付け足さない。適用対象だけのevent floor合計はgross685、重複Eを除いたnet491＝DEV200＋C97＋D97＋E97、新規Fresh部分291。将来実際に発生するevent数ではない。

| 段階 | 次工程に保持する新規Fresh設計残数 |
|---|---:|
| Entry Validation後 | 165 |
| Entry OOS後 | 135 |
| EXIT Development後 | 135 |
| EXIT Validation後 | 105 |
| EXIT OOS後 | 75 |
| Integration＋Capital/Portfolio共同Validation後 | 55 |
| Capital/Portfolio完了後 / 最終比較前 | 55 |
| 最終比較後 / Final OOS前 | 25 |
| Final OOS後 | 0 |

残数は未取得の設計reserveであり、実在cache保証ではない。各blockのidentityと予算を事前登録し、独立したrelease gateで順番に開ける。前段FAIL/BORDERLINEで自動OOSへ進まない。Final比較は同じsession/PIT universe/cost/cadence/capital/execution仮定、両群LONG現物のみ。旧ArkのSHORT分を評価しない。比較可能なLONG現物baselineを事前固定できなければ、最終比較を停止して互換性を解決する。

新規data設計不足は195日、7block（historical候補A～F170日＋prospective G25日）。既存raw cacheから同じDEV76日を再取得する必要があるかはUNKNOWNで、fresh shortageには加えない。exact dates、session list、hard request capは次の取得Contractで固定する。今回は価格request予算0。

計画上のsymbol数は既存LONG data planの3700を使用。1日330取引分・66本の5m barというdense上限assumptionなら、新195日で47,619,000本の5m、238,095,000 minute rows。100～200 uncompressed bytes/minute rowという工学的assumptionでは約23.81～47.62GB（decimal、daily/master/index等を除く）。実際の銘柄数、欠損/no-trade、昔の取引時間、codecで変わり、取得量上限の承認ではない。

既存coverage metadataの205日2899 minute pagesを使用したpoint estimateは、`ceil(195×2899/205)+195×2+1 = 3149 requests`。日次/masterのpagination、追加causal warmup、DEV cache回復は含まず、hard capではない。実symbol list・query・pagination・storage・entitlementは次Contractで固定する。取得した値を見て期間を選ぶことは禁止。

Bufferは0。session-level integrity欠損率が証明されていないため、event labelabilityからsession bufferを作らない。元reserve15/contingency30は従来用途のままで、新LONGの自由な予備にはしない。data-quality failureやevent不足では固定blockを無言で追加・交換しない。旧契約上の期限情報はsnapshotで、現在のJ-Quants利用可能範囲を照会したわけではない。

責務と必要量の旧UNRESOLVEDは残していない。新契約draftで解決したscopeは、旧別系統の予約やモデルをsupersedeしない。実allocation変更0、予約解除0、sealed/protected開封0、Candidate/Validation/OOS prediction0、model/scaler fit0、SHORT評価0、Yahoo/J-Quants/その他価格request0。Safety全false。

**唯一のFreeze blocker:** `OTHER:OUTCOME_BLIND_METADATA_DISPLAY_VIOLATION`。outcome-derived metadata displayは1件と明記し、raw outcome access0、Validation/OOS/EXIT outcome access0とは区別する。Recommendationは **C — GLOBAL_BUDGET_REQUIRES_CONTRACT_RESOLUTION**（予算値の未定ではなく、この監査逸脱の扱いが必要）。逸脱の独立reviewが完了した場合の設計上の経路はB、新規Fresh195日である。

次工程は、この完成済みbudget draftと逸脱の独立integrity review。数値を再探索せず、outcome閲覧も繰り返さない。正式Freeze後にのみ **MINIMAL J-QUANTS FRESH DATA ACQUISITION CONTRACT** を作り、exact dates/session list/universe/fields/cadence/request/storageを固定する。今回、取得・Validationへは進まずSTOP。

Global Budget Frozen Contract SHAは未発行。draft/artifact SHAは再現性確認用であり、正式FROZEN SHAの代用にはしない。
