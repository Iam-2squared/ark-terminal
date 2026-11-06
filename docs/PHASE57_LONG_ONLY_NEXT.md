# Phase57 LONG-only — 現在の方針・次作業

## 最新追加記録 — 2026-09-21 22:41 JST — v2設計前Gate完了 / State Definition v2仕様案作成 / STOP

ユーザー承認「進めて」を受け、先にCompletion Gate G1〜G8を固定し、Claudeがfreeze前に要求した残り3診断R1〜R3を既存G measurementだけで完了。そのEvidenceからState Definition v2の**設計案のみ**を作成した。実装・正確表v2生成には進んでいない。

### R1 固定Horizon
B 11,326を既存ORACLE_HORIZON=10 active minutesで再集計。
- 10分を完全評価できた5,733行中、Structure成立 **998 = 17.41%**
- pivot0 10.07% / pivot1 10.29% / pivot2 18.03% / pivot3 41.21%
- observation censor 4,750 / session censor 843
同日終端まで追った旧39.37%を「形成率」とは使わない。pivot<4はPRE/FORMINGへ昇格させず `INSUFFICIENT_PIVOTS(k)` を維持。

### R2 36 chart rubric
固定seed既存sample 36 checkpoints / 36 Opportunities / 29 sessionsを単一reviewerで再確認。
- EXISTING_AXES_SUFFICIENT **36/36**
- DATA_OR_OBSERVATION_ARTIFACT_SUSPECTED overlay **1/36**
- VOCABULARY_GAP_CANDIDATE 0
新Structure名の明確な必要例はこのsampleでは確認されず。ただしv2 freeze時の2者独立reviewは未実施。

### R3 Observation multi-flag
77,214全checkpointをpriority reasonではなく重複flagで監査。
- current bar missing 30,986
- latest5 incomplete 48,740
- Scale unavailable 37,932
- current missing ∩ scale unavailable 23,116
- latest5 incomplete ∩ scale unavailable 31,747
- 3つすべて 23,116
旧primary reasonは順序依存表示であり原因の排他分解ではないことを確定。

### v2 DESIGN DRAFT
- Layer0 ObservationQualityをメタ層化
- 共通status: DEFINED / INSUFFICIENT / AMBIGUOUS / NOT_APPLICABLE / NOT_EVALUATED
- Structureは必須軸ではない
- pivot<4は INSUFFICIENT_PIVOTS(k)
- pivotSignatureはdescriptor
- Scaleはversioned ScaleSpecでState vocabularyから分離
- NOWとFuture Resolutionを別artifact/schema/hash
- 全77,214 rowのtruncation invariance 100%をhard gate
- v1は上書きせずv1→v2 transition matrix必須

Evidence:
- [Completion Gate Protocol](evidence/phase57-state-v2-design-gate/PROTOCOL.md)
- [R1〜R3 Report](evidence/phase57-state-v2-design-gate/R1_R2_R3_REPORT-ja.md)
- [Remaining Diagnostics Summary](evidence/phase57-state-v2-design-gate/remaining-diagnostics-summary.json)
- [State v2 Design Draft](phase57-five-minute-entry-state/STATE_DEFINITION_v2_DRAFT.md)
- [R2 single-reviewer rubric](evidence/phase57-state-v2-design-gate/R2_REVIEW.csv)

会話添付ZIP SHA256 `c26a3194226c9f9c4186e4bb71ee50c3067eb7353095539267e963e19572d5f2`。

**STOP。次はState Definition v2仕様案の人間/Claude設計レビュー。承認前にv2 code・正確表v2を生成しない。**

State Definition v1変更0 / v2 implementation 0 / PnL 0 / future return 0 / provider 0 / protected data 0 / Causal Recognition 0 / Signal 0 / BUY-WAIT 0。Safety9全false。

---

## 最新追加記録 — 2026-09-21 20:33 JST — 追加診断①〜⑤ 保存確認 / STOP

20:24 JSTに保存した追加診断①〜⑤のEvidenceを再読し、branch HEADと保存内容を確認した。数値結論は変更なし。

- D 2,154のstrict residual = **0**。
- B 11,326のsame-session次Structure解決 = **4,459 (39.37%)**、6,867は同日中に未解決。
- SCALE_INSUFFICIENTは絶対活動量は低い一方、前日→当日の相対活性化がAVAILABLEより強い。
- pivotSignature 3×3はStructureと一対一対応せず、descriptorとして保持する診断結果。
- 層別chart sampleは36 checkpoints / 36 Opportunities / 29 sessions。
- local固定入力の各診断を二重実行し対象出力hash一致。

GitHub Actionsについて、このEvidence HEADに紐づくpull_request workflow runを確認したが、**専用 `Phase57 State Additional Diagnostics v1` runは見つからなかった**。したがって専用CI PASSとは呼ばない。PR全GREENとも呼ばない。local replayの結果とActions未起動を分離してreceiptへ保存した。

Evidence:
- [REPORT](evidence/phase57-state-additional-diagnostics-v1/REPORT-ja.md)
- [summary](evidence/phase57-state-additional-diagnostics-v1/diagnostic-summary.json)
- [verification receipt](evidence/phase57-state-additional-diagnostics-v1/verification/receipt.json)

**ここでSTOP。次は人間確認後、State Definition v2の設計Gateを開始するか判断する。v2 / 正確表v2 / Causal Recognition / Signal / BUY-WAITは未開始。**

---

## 最新追加記録 — 2026-09-21 20:24 JST — State追加診断①〜⑤完了 / v2未開始

Claude再レビュー後に事前登録した追加診断①〜⑤を、既存G measurementのみで完了した。State Definition / threshold / Selector / Entry / EXIT / Capitalは変更していない。PnL・future return・新規provider・protected dataは未使用。

- D 2,154のstrict residualは **0**。旧「Phaseなし+CHOPなし231」をVocabulary gap最優先とする扱いは撤回。
- B 11,326のsame-session next Structure解決は **4,459 = 39.37%**。pivot0 25.95% / pivot3 64.43%。Bを一律FORMINGとは呼ばない。
- Observation density Q1の解決18.11%に対しQ4は69.08%。pivot数と観測品質を分離して扱う根拠。
- SCALE_INSUFFICIENT 1,105は前日bars median40→当日82、当日/前日比median1.71x。Selector時点までのbarsが前日全日barsを超える割合44.43%（AVAILABLE 5.47%）。相対活性化への偏りはあるが、まだSを変更しない。
- pivotSignature 3×3はidentified StructureとDへ混在。H_DOWN|L_UPはUP245 / DOWN434 / RANGE58 / D479。signatureをStructure classへ昇格しない。
- 固定seedで36 checkpoints / 36 Opportunities / 29 sessionsを層別抽出。9 signature ×4。actual1m / pivot / S / latest30 windowのchartを会話添付ZIPに保存。PnL抽出なし。
- 数値producerとsampleを独立2回実行し対象hash一致。
- Evidence: [REPORT](evidence/phase57-state-additional-diagnostics-v1/REPORT-ja.md) / [summary](evidence/phase57-state-additional-diagnostics-v1/diagnostic-summary.json) / [protocol](evidence/phase57-state-additional-diagnostics-v1/PROTOCOL.md)

**STOP。次は人間がこのEvidenceを確認し、State Definition v2設計へ進むか判断する。v2 / 正確表v2 / Causal Recognition / Signal / BUY-WAITは未開始。**

local manifest SHA256 `5e0ef437d86e7ae3e70e8f0df50a7e92ebb8c8fb22edec88616c12d568f79224`  
conversation ZIP SHA256 `1abde291d4a4cea59ebe59f48966ef5ba3fadff6c562e4eb4150d1168e7c7f79`

---

## 最新追加記録 — 2026-09-21 19:19 JST — 未識別68,405 Deep Audit完了 / Claude独立レビューへSTOP

固定 `five-minute-state-mechanical-v1` とG参照表を変更せず、Structure未識別68,405 checkpointを原因分解した。

- **A: INPUT_OR_OBSERVATION_LIMITED = 54,925**。CURRENT_BAR_UNAVAILABLE 30,986、SCALE_UNAVAILABLE 14,816に加え、primary reasonはUNRESOLVEDでもlatest5がPARTIALだった9,123を観測制約側へ分離。
- **B: STRUCTURE_NOT_YET_CONFIRMED = 11,326**。latest5 COMPLETE + S availableだがconfirmed pivot<4。pivot0=3,723 / pivot1=4,091 / pivot2=2,185 / pivot3=1,327。
- **D: STRUCTURAL_VOCABULARY_GAP_CANDIDATE = 2,154**。latest5 COMPLETE + S available + pivot>=4でもUP/DOWN/RANGEなし。H_UP+L_DOWN 845、H_DOWN+L_UP 479が主。
- Dのcurrent PhaseはRESTRUCTURING 1,427 / RESTRUCTURING+RECOVERY 348 / RECOVERY 93 / NONE 286。Phase NONEの286中CHOPあり55、**Phase NONE + CHOPなし231**を最も強いrepresentation-gap review候補として残す。
- C「StructureなしでもDirection/Phase等で説明可能」はB/Dと重複するため、無理な排他4分類にせず**overlay**として監査した。これは新State定義ではない。
- SCALE_INSUFFICIENT 1,105 Opportunitiesのcomplete 5m block数は0:748 / 1:136 / 2:76 / 3:50 / 4:52 / 5:43。欠測原因をno-trade/halt/provider lossのどれかには断定しない。
- 保存済みG measurement 179ファイルをmanifestで再hash検証。Deep Audit producerを独立2回実行しoutput manifest SHA256 `cdd251ec8aab55c061ac1385a8f21b00543a2c5f8d04e27272d3ee4a538115ad` 一致。
- 代表チャート10枚＋producerを含む会話添付 `phase57_state_unknown_deep_audit_20260921.zip` SHA256 `ea2e175fe70b145bdd51fc179ee7b1ad4cca64ff14757e5130a8229bbcb10245`。チャート画像本体をGit trackedとは主張しない。

正本:
- [Deep Audit Protocol](evidence/phase57-state-unidentified-deep-audit-v1/PROTOCOL.md)
- [Deep Audit Report](evidence/phase57-state-unidentified-deep-audit-v1/REPORT-ja.md)
- [Deep Audit Summary](evidence/phase57-state-unidentified-deep-audit-v1/audit-summary.json)
- [Claude Review Handoff](evidence/phase57-state-unidentified-deep-audit-v1/CLAUDE_REVIEW_HANDOFF.md)

**次はClaude独立レビュー。State Definition v2、正確表v2、Causal Recognition、Signal、BUY/WAITはまだ開始しない。**
ClaudeレビューではAをObservation Qualityとして維持すべきか、Bのpivot0-3をFORMINGとして表現すべきか、Dのbroadening/contracting/equal geometryをStructure/Transitionとしてどう扱うか、231強候補にVocabularyの穴があるかを確認する。

State Definition変更0 / threshold search 0 / new provider 0 / protected data 0 / Causal Recognition 0 / Signal 0 / BUY-WAIT 0。Safety9全false。開始HEAD `90325a549b083c0d6ff2749cc52c3c3fbd8f59f9`。

---

## 最新追加記録 — 2026-09-21 18:30 JST

同時更新 `13181b14b18019353405f04bf84562031f251dd5` のG終了確認・限定retry方針・共通WORK_LOG追記を保全したうえで、このチャットの独立入力/全CSV照合と可視化レビューを追加する。以下の18:23時点の記録を削除せず、その補足として読む。

- [追加レビュー結果](evidence/phase57-five-minute-reference-g-v1/review-20260921/REPORT-ja.md)
- [今回の日時付きWORK_LOG](evidence/phase57-five-minute-reference-g-v1/review-20260921/WORK_LOG.md)
- [追加検証・subset分母の数値](evidence/phase57-five-minute-reference-g-v1/review-20260921/review-summary.json)

179ファイルをこのチャットで再hash検証。全77,214CSV行の重複/集計と、独立した予定時刻・Observation/Direction/S/Future窓statusを照合した。これは構造ラベルの独立正解検証ではない。
最新5本+Sが揃う22,289行の構造識別8,809（39.52%）。未識別13,480行のうちpivot4個未満11,326、4個以上で有効構造なし2,154。最新5本の完全性だけで過去の連続履歴も十分と断定しない。
前日raw presentの43件は15:30引けの1本だけで通常分足0。14:30以後の構造識別2,416/24,786、15:00選出では98/1,074。
6つの状態条件からID順に抽出した実チャートと各例の全checkpointを、自己完結HTML/ZIPとして会話に添付した。画像本体はGitのmeasurementに格納したとは言わず、ZIP hashと代表IDを追加レビューへ保存した。
当日action原本・独立calendar全体・historical receivedAtは未検証。先の別パスphase57-five-minute-state-reference-v1/PROTOCOL.mdが計画した暗号化raw復元まで完了したとはしない。

**次はG結果の人間確認。必要観測の不足と固定定義の表現限界を分離する診断を検討するが、今回C/Signal/Entryへ進まない。mechanical-v1と閾値は変更しない。**
保存SHA・実保存時刻は本追記commit metadataとPR終了コメントに記録する。

---

最終更新記録: **2026-09-21 18:23 JST**
今回の確認時刻: 2026-09-21 18:19 JST / 記録整理: 18:23 JST（Asia/Tokyo、UTC+09:00）。
対象: Iam-2squared/ark-terminal / research/phase57-long-only-cash-equity / PR #587。
今回の開始確認HEAD・G Evidence保存SHA: `d8240b380fa0201ccca11e909665c9689300bdcb`。
G実行HEAD: `20ebb47323b7c1aca4e4579c7783fc9f48c75792`。
この更新の保存SHA・実保存時刻はGit履歴とPR終了コメントを参照。次回開始時にlatestを再取得する。

## 現在地点 — G生成・再現・保存は成功、結果レビュー待ち

**G本体のrun35581246681はverify/preserve両jobがSUCCESS。2,155 Opportunities・77,214 checkpoint行の固定State参照表をGitHubに保存済み。**

`G_TABLE_GENERATED / DEDICATED_REPLAY_PASS / SOURCE_LIMITATIONS_REMAIN / HUMAN_REVIEW_REQUIRED / C_NOT_STARTED`

前の入口に残っていたG_NOT_STARTEDは古い状態。本記録はrunのjob結果、保存summary/admission/ci-receiptを再読した現在状態。生成・再現に成功したことと、相場を十分に分類できることは別。
ユーザーの「失敗したら修正して続けて」を受けて確認したが、当該G runは既に成功・保存完了だったため、コード修正・追加再実行は行っていない。

## 正本・Evidenceの入口

| 文書 | 役割 |
|---|---|
| [ADOPTED_DEFINITION.json](phase57-five-minute-entry-state/ADOPTED_DEFINITION.json) | 唯一の採用version、source/hash、不採用案の扱い |
| [採用決定](phase57-five-minute-entry-state/ADOPTION_DECISION_20260921_1706_JST.md) | mechanical-v1への一本化理由 |
| [採用仕様](phase57-five-minute-entry-state/mechanical-v1/SPEC-ja.md) / [contract](phase57-five-minute-entry-state/mechanical-v1/contract.json) | 変更しない判定定義 |
| [G実行protocol](evidence/phase57-five-minute-reference-g-v1/PROTOCOL.md) | 今回の生成・入力・評価境界 |
| [G集計](evidence/phase57-five-minute-reference-g-v1/measurement/summary.json) | 全checkpoint分布・制約・STOP |
| [G入力監査](evidence/phase57-five-minute-reference-g-v1/measurement/admission.json) | source/ID/calendar/日足/尺度の利用可能性 |
| [G専用CI receipt](evidence/phase57-five-minute-reference-g-v1/verification/ci-receipt.json) | 93定義tests、22adapter tests、179ファイル照合、local replay一致 |
| [5分表CSV](evidence/phase57-five-minute-reference-g-v1/measurement/checkpoints.csv.gz) | 生成した全checkpoint表。未識別行も保持 |
| [WORK_LOG](phase57-five-minute-entry-state/WORK_LOG.md) | 過去履歴を消さない日時付き追記 |

保存Evidenceのreceipt日時は2026-09-21 18:13:26 JST。Evidence保存commit日時は18:13:39 JST。今回18:23の記録は生成処理の再実行ではなく、その終了確認と引継ぎの更新。

## 保存結果の要点

割合は77,214全checkpointを分母に計算。Opportunity件数とは混ぜない。

| 項目 | 件数 | 全checkpoint比 |
|---|---:|---:|
| 全checkpoint | 77,214 | 100% |
| 最新5本が完全観測 | 28,474 | 36.88% |
| 最新5本が部分観測 | 34,638 | 44.86% |
| 最新5本が観測不能 | 14,102 | 18.26% |
| UP/DOWN/RANGE Structure識別 | 8,809 | 11.41% |
| Structure未識別 | 68,405 | 88.59% |

観測率とStructure識別率は別指標。DirectionはUP11,542 / DOWN12,753 / UNCHANGED4,179 / UNAVAILABLE48,740。
StructureはUP2,358 / DOWN4,856 / RANGE1,595 / UNIDENTIFIED68,405。
未識別の排他的stateReasonはCURRENT_BAR_UNAVAILABLE30,986、SCALE_UNAVAILABLE14,816、UNRESOLVED_STRUCTURE22,603。stateDetailReasonは重複があるので合計しない。
Phase/CHOP等が付くこととStructure識別は別。複数State属性は排他的に潰さない。

### 前回の「前日分足が全件present」の読み方を訂正

sourceに対象ID/コンテナがあることは、全件で前日分足が完全・尺度計算可能であることを意味しない。最終admissionではOpportunity単位の尺度利用可能は**1,005/2,155**。
残りはSCALE_INSUFFICIENT1,105、PREVIOUS_CONTEXT_UNAVAILABLE43、PRICE_BASIS_UNVERIFIED1、SCALE_ZERO1。
Daily5が揃ったのは1,961/2,155、partial194。前回のpresent報告を、そのままState入力の完全性PASSとして使わない。
raw/ID照合に成功したことも、historical receivedAtやcorporate actionを独立再検証した証明ではない。入力にはINHERITED_RAW_PRICE_BASIS、INHERITED_SAME_DAY_METADATA_NOT_INDEPENDENT_PIT、CURRENT_ACTION_RAW_NOT_REAUDITED等の留保が残る。

## 失敗時の修正範囲 — 今回のユーザー指示

実行エラーがあれば、最新HEAD・対象G run・ログを確認し、G内の実装不具合、時刻/型/adapterの契約違反、保存/再現処理の不具合を特定して修正・限定再検証する。成功済みjobや旧研究を理由なく再実行しない。変更・失敗原因・テスト・保存先を日時付きで残す。

**「未識別が多い」「成績が期待より悪い」は、処理失敗と同じではない。** それを理由にS、1S、30分Range、10分Future等を変更したり、欠測を架空足で埋めたり、Opportunityを再filterしたりしない。
source hash不一致・保護データ要求・秘密情報・定義変更が必要な場合は、guardを外して継続せずEvidenceを保存して人間確認。
今回のG runは成功済みで修正・retry対象なし。後続Gateの自動監視/自動進行は設定していない。

## 次にすること — Gの結果確認を先に行う

**次は同じG内で、保存済み表の未識別理由・入力制約・代表チャートを人間が確認すること。Cへはまだ進まない。**
今回の確認はrun/receipt/summary/admissionの読取まで。全件をこのチャットで再計算したとは主張しない。代表チャートと時刻別の詳細レビューの完了も今回確認していない。
未識別が多い原因を、現在足の欠測・前日尺度不足・固定構造条件未成立に分ける。追加の値動き研究や閾値探索へ自動拡張しない。

| Gate | 現在 |
|---|---|
| D — 基準定義 | mechanical-v1のみ採用、code/contract/hash不変 |
| G — 5分参照表 | 生成・専用再現・GitHub保存成功。品質/制約/可視化の人間レビュー待ち |
| C — 未来なし認識 | 未開始、人間承認前はBLOCKED |
| S — State × Signal | BLOCKED |
| E — BUY NOW / WAIT | BLOCKED |
| Later — 学習/Dictionary/別EXIT/Capital/Portfolio/protected評価 | BLOCKED |

## 継続する設計・保護境界

Selector=WHAT、Entry=WHEN IN、EXIT=WHEN OUT。Frozen Selectorをretrain/rerank/refilterしない。OpportunityをState/Signal/Qualityで捨てない。
将来のEntryはTで初回評価、WAITなら5 active minutes後。最初から5分待たせない。State(t)は直前5本closed 1mとtまでの構造で、次5分の予測とは別。
4時間軸はD-5〜D-1 Daily、前営業日observed1m、Today Open→t、最新5本。Direction/Structure/Phase/Events/Attributes/Context/Observationを分離。
採用尺度は前日完全5m TR中央値（最低6block、当日固定、fallbackなし）、終値1S Swing、4pivot構造、30分Range、重複CHOP、同日次10active分Future確認。意味未識別を無理に既知ラベルへ押し込まない。
Signalは将来State認識とBUY/WAITの入力になり得るが、有用性はSの別Gate。Signalなし=候補廃棄にしない。SELLは別EXIT研究。
v0.2/helper/85-test patch、旧5+1/旧STEP2・3、Workの10/30bps試作は履歴のみ。採用案へ適用・混合・並行改良しない。
今回、採用定義/Selector/既存Entry/EXIT/Capital/旧Evidenceを変更しない。新規provider、Holdout/Fresh/OOS/Prospective開封、Causal Recognition、Signal/BUY-WAIT評価、学習はしない。main未merge。

## 毎回の日時付き記録

開始時にlatest HEAD/PR/この入口/採用manifestを読む。終了時にCURRENT更新＋WORK_LOG追記＋PRコメント。`YYYY-MM-DD HH:MM JST`、開始SHA、実施/未実施、結果、未解決、次の1 Gate、停止条件、保存SHAを残す。
保存直前にremote再確認、同時更新を保全、force=false。保存後に再読。保存失敗を保存済みと言わない。旧ログは削除せず訂正は追記。
合成PASS、専用CI PASS、PR全GREEN、実市場妥当性、因果認識、利益は別。今回の状態はG_DEDICATED_REPLAY_PASS_NOT_PR_GREENであり、市場State認識成功の認定ではない。

executionAllowed=false
brokerWriteAllowed=false
excelOrderWriteAllowed=false
rssOrderFunctionAllowed=false
liveTradingAllowed=false
paperTradingAllowed=false
automaticPromotionAllowed=false
productionUpdateAllowed=false
transmitted=false


---

## 最新追加記録 — 2026-09-22 00:43 JST — State v2 Rule-Spec Hardening 完了 / Freeze Candidate / STOP

Claude独立レビューの `APPROVE_WITH_REQUIRED_CHANGES / NOT_SAFE_TO_FREEZE_V2_DESIGN` を受け、C1〜C8の最小修正を **仕様だけ** に反映した。v2実装・77,214 row再生成には進んでいない。

### 完了
- mechanical-v1数値ルールを source commit + SHA-256 で完全pin。v2.0では閾値変更0。
- `Ground Truth` 呼称をやめ、NOW=`now_state_reference_v2` / Future=`future_resolution_v2` へ分離。
- common statusを `DEFINED / INSUFFICIENT / NOT_EVALUATED / NOT_APPLICABLE` に整理。未定義の `AMBIGUOUS` はv2.0から除外。
- 評価済み陰性を `DEFINED(NONE/[])` とし、maskと分離。
- `reasonCodes[]` multi-flag + display-only `primaryReason` を固定。Future censorも重複flag化。
- ObservationQuality / Scale / timestamp / knownAt / corporate-action as-of / data-vintage / pivot confirmation / calendar / stateful carry-overのPIT契約を明文化。
- Causal Recognition targetを「未来確認で遅延確定するState-at-t軸」と定義し、Direction等のNOW既知descriptorとの責務を分離。
- v1→v2 transition audit、canonical serialization、golden vectors 12本を固定。
- Freeze GateとGeneration Acceptance Gateを分離。
- G7を status-cell層別 + rare-cell oversampling + 2者独立 + synthetic negative controls で事前登録。
- 既存G artifactを再利用し、非gating coverage reportを作成。閾値変更0。

### 既存G artifact coverage（Development / descriptive only）
- 77,214 checkpoints / 2,155 Opportunities
- Direction defined 28,474 = 36.88%
- Scale AVAILABLE 39,282 = 50.87%
- Structure defined 8,809 = 11.41%
- Phase non-empty 11,621 = 15.05%
- Opportunity単位でAny Structure defined 604/2,155 = 28.03%
- current bar missing時のScale unavailable 74.60% / current observed時 32.05%

上記はmissingness/selection biasの開示であり、結果に合わせてState定義を緩めない。

### 保存
- `docs/phase57-five-minute-entry-state/STATE_DEFINITION_v2_FREEZE_CANDIDATE.md`
- `docs/evidence/phase57-state-v2-hardening/HARDENING_EVIDENCE.md`
- `docs/evidence/phase57-state-v2-hardening/GOLDEN_VECTORS_v2.json`
- `docs/evidence/phase57-state-v2-hardening/FREEZE_CANDIDATE_MANIFEST.json`

### 現在のFreeze blocker
1. G7 two-reviewer semantic chart review
2. Claude differential reviewで `SAFE_TO_FREEZE_V2_DESIGN`

**まだFROZENではない。次は上の2点だけを最短で潰す。承認前にv2実装へ進まない。**

### 最終North Star（State定義には使用禁止）
最終統合評価は、future-assisted Oracleの Selector後Low→later High 値幅のうち、未来情報なしのEntry+EXITで何%回収できたかを中心に評価する。Entry Low Gap / EXIT High Gap / Realized Return / Oracle Capture / Opportunity-weighted Captureを併記する。
