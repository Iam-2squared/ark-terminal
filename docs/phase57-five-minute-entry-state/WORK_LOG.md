# Phase57 Five-Minute Entry State — 作業ログ

このログは追記運用。最新の方針・次作業は ../PHASE57_LONG_ONLY_NEXT.md を入口とする。
各作業終了時に方針・次作業をGitHubへ残すユーザー指示を継続する。無承認で次Gateを実行する自動化はしない。

## 2026-09-21 15:30–15:46 JST — Zero-Based State Definition v0.1

### 承認された作業

ユーザーはWorkの利用上限のため本チャットでの継続を依頼し、State Definition仕様設計を進めることを承認した。正解表の作り直し、因果認識、Signal Stats、BUY/WAIT、学習、Dictionary、EXITへ進む許可ではない。
作業終了時にGitHubへ「この後することと方針」を毎回記録する追加指示を受領。

### 開始時の事実

GitHub PR #587を直接確認: open / Draft / unmerged。
head branch: research/phase57-long-only-cash-equity。
start HEAD: 2ef307a31bea156110dc8b9181b7582373b2887e。
base tree: 7291c7e6534d8c5650946633c02ab0f4d28126e2。

Root/docs treeを確認した範囲ではAGENTS.mdなし。既存同名文書・同名新設ディレクトリなしを確認し、既存Evidence上書きでなく新規docsとして作成する。

### 今回したこと

既存Daily/State/Signalの入力・窓・前日扱い、旧Vocabulary、旧STEP3計測対象を静的監査した。詳細とblob pinsはSOURCE_AUDIT_2026-09-21.md。

新State設計案を作成:
- 4時間軸: Daily5 / Previous Day observed1m / Today / latest5×1m。
- Direction、3 Structure、5 Phase、Events/Attributes、Observation/Contextの分離。
- 前日高安と当日/局所高安、structural pivotと隣接足の高安比較の区別。
- Tで初回、5 active minutes周期、State(t)は直前5分を終えた現在。次5分とは別。
- 現在観測、oracle解釈、将来確認・打切りの分離。
- 観測欠測、価格basis、同一足順序、意味未識別を別reasonにする。
- Signalが後でStateにもBUY/WAITにも直接効き得る設計。ただし今は測定しない。
- 固定bpsを勝手に採用せず、必要なparameter lock箇所と未決事項を明示。

### 保存対象

- docs/PHASE57_LONG_ONLY_NEXT.md
- docs/phase57-five-minute-entry-state/STATE_DEFINITION_v0.1.md
- docs/phase57-five-minute-entry-state/SOURCE_AUDIT_2026-09-21.md
- docs/phase57-five-minute-entry-state/WORK_LOG.md

保存commitはこの追記を含むGit履歴と、保存後のPRコメントから特定する。実際のremote更新成功を再読してから完了を報告する。

### 検証と未実施

本作業はdocs-only。科学的実験、全件再分類、学習、synthetic分類テスト、full regressionを実行していない。旧19 testsや既存CI結果を今回の検証数に流用しない。
保存時は文書間の参照・設計境界・未固定parameter表示・9 Safety項目を点検する。commitメッセージに[skip ci]を付け、push/pull_request型の新規測定起動を避ける。CI未実行はPASSではない。PR全体GREENやmerge可能とは主張しない。

生成した市場State行数=0。provider新規取得=0。保護データ開封=0。Signal/Entry/EXIT測定=0。旧Evidence変更=0。
WorkローカルprototypeはUSER_REPORTED / UNAPPROVEDのまま。取得・再利用・削除なし。

### 到達点と停止

**DESIGN_DRAFT_COMPLETE / NOT_LABEL_READY / STOP FOR HUMAN REVIEW。**
State Definitionの案は文書化完了だが、ラベル生成可能な定義freeze完了ではない。認識率改善、UNKNOWN削減、経済価値を示す結果はまだない。

### 次にすることは1つ

人間がv0.1案をレビューする。承認された範囲で同じDefinition Gate内のpivot scale・range成立・future確認期限等を機械化契約として固定する。
次回開始時もremote HEADとCURRENT入口を再確認する。今の文書を承認済み仕様へ自動昇格させない。GのFuture正解表はDefinition/parameter lockを人間確認した後の別承認が必要。

### 維持した保護契約

Frozen Selectorと既存Entry/EXIT/Capitalは未変更。main未変更・未merge。LONG-only / cash-equity-only。
executionAllowed=false
brokerWriteAllowed=false
excelOrderWriteAllowed=false
rssOrderFunctionAllowed=false
liveTradingAllowed=false
paperTradingAllowed=false
automaticPromotionAllowed=false
productionUpdateAllowed=false
transmitted=false

### 作業終了時の追記 — 保存・確認の実績

設計保存commit: `fb509512428df17e5b1732e29638810b207bd83a`。
GitHub compareで開始HEADから1 commit ahead、4文書の新規追加だけ、既存ファイルの削除/変更0を確認した。force=falseで対象branchをfast-forwardし、GitHubからCURRENT入口と設計仕様を再読できた。
設計仕様は310行、18節。これは文書量であって研究成果件数や分類精度ではない。

検証実績を分けて記録する:
- GitHub connectorで読取ソースのref/blob、文書の保存、差分範囲、方針/STOP/未固定事項を確認した。
- runtimeからpublic raw GitHubを取得して文書lintを実行する補助チェックを試したが、DNS解決失敗でファイル取得前に終了した。自動lint PASS/自動hash検証済みとは主張しない。
- この補助チェック失敗はGitHub connectorによるcommit/branch更新の失敗ではない。保存自体は成功した。
- 設計保存commitについて確認したpull_request型Actionsの応答は0 runs。full PR GREEN、専用CI PASS、全イベント停止の保証は出さない。
- 新規分類コード、測定、provider calls、Signal/Entry/EXIT処理は実行していない。

最終状態は変わらず **設計案保存・人間レビュー待ち / NOT_LABEL_READY**。
次作業は設計レビューと、承認された範囲での同じDefinition Gate内の判定条件固定だけ。正解表・因果認識へ自動進行しない。
この終了記録を含む最終保存SHAと文書への参照はPR #587へ記録する。

## 2026-09-21 15:46 JST — 記録運用の追加固定

ユーザー確認により、今後は各作業終了時のGitHub記録へ**日付だけでなくJST時刻も必須**とする。
CURRENT入口は最終更新 `YYYY-MM-DD HH:MM JST`、このWORK_LOGは可能な範囲で開始〜終了時刻を記録する。
目的は、次回開始時に「いつの状態か」「どこまで進んだか」「次に何をするか」を即座に判別できるようにすること。

このルール自体も継続方針としてGitHubへ保存し、以後毎回適用する。

## 2026-09-21 15:58 JST — Mechanical State Definition v0.2

開始HEAD: `907f1016cd46dd784b2a7269aa10945e75e12543`
終了HEAD: `7d125e37149d16092a30ebfc187b06d067d801d3`

### 今回したこと
- v0.1の未固定項目P2〜P7に対し、Swing/Structure/Range/Phase/Breakout/Reclaim/Choppiness/Future確認期限の機械契約案v0.2を追加。
- 固定bpsではなくcausal scale S(t)と2 tick floorを使用する案を明文化。
- UP/DOWN structureはconfirmed swing high/lowとprotected levelで判定、wick-only breachは失効扱いにしない。
- RECOVERYはexplicit episodeとrecoveredFractionの増加、RESTRUCTURINGはprotected level close break後の新構造未確定状態として分離。
- Rangeはtrend不成立の補集合にせず、交互pivot＋低efficiency＋20 active minutes以上を要求。
- Choppinessは5本内directionChanges/efficiency/envelope-to-scaleの複合属性として定義案を固定。
- Future reference確認期限は15 active minutes・same-session固定、right-censorを明示。
- 小さなdeterministic helperとsynthetic unit testsを追加。これは市場データ測定ではない。

### 未実施
- 実市場データでの正解表生成0
- Causal Recognition 0
- Signal Stats 0
- BUY/WAIT評価0
- provider取得0
- Holdout/Fresh/OOS開封0

### 現在地
**MECHANICAL_LOCK_DRAFTED / SYNTHETIC_TESTS_ADDED / NOT_FROZEN**
まだtestsを実行しておらず、definition freeze完了とは言わない。

### 次にすること
1. synthetic testsを実行し、失敗があれば定義矛盾だけを修正する。
2. test PASS後にDefinition contract/hashを固定してD GateをFreeze候補にする。
3. 人間確認後のみFuture reference tableへ進む。

Safety9項目false維持。Frozen Selector/Entry/EXIT/Capital/main未変更。

## 2026-09-21 16:04–16:27 JST — 別候補mechanical-v1の実装・合成検証

開始時に直接確認したHEAD=907f1016cd46dd784b2a7269aa10945e75e12543、PR #587 open/Draft/unmerged。
今回の承認範囲は同じDefinition Gate内の機械ルール固定と合成例/反例テスト。市場正解表生成・Causal Recognition・Signal/Entry評価へは進まない。

### 完了したもの

mechanical-v1/に、前日完全5分TR中央値S、終値1Sのpivot、4pivot Structure、protected level失効、30分Range、CHOP属性、回復episode、typed cross/VWAP、同日future10active分の契約を独立実装。
contract/SPEC/reference/test/verifier/source-lockと検証Evidenceを作成。実市場結果による選択ではない。

### 検証実績

local Python 3.13.5、named synthetic tests **93/93 PASS**、失敗/エラー0。固定sourceで2回実行しsummary/snapshot SHA-256・manifest一致。6模式snapshotを保存。別途、既存output上書き拒否とsource破損拒否を確認。
初回1件のprotectedLow期待値を旧101から仕様上の更新102へ訂正し再実行した。市場結果による閾値調整ではない。アップロードの空行差をローカルbyteへ揃え、最終lockで再検証。

実市場ファイル読取0、市場State行生成0、75,059再分類0、fit0、Signal/BUY-WAIT/EXIT評価0、provider取得0、protected data開封0。
旧実行系・workflow・モデルへ接続せず、docs内のpure referenceだけ。local synthetic PASSをGitHub CI/全PR GREENにしない。

16:27に候補結果報告をまとめ、準備commit ee0387378232d754a80263609f4f208bf145e939を作成した。この時点ではbranch更新前。

## 2026-09-21 16:34 JST — 同時更新保全と最終採用の留保

保存前のremote再読で686bad3fa0c2283a776d1434f30820c3d1e35fb5への5 commits進行を確認。STATE_DEFINITION_v0.1.mdのv0.2追記、helper/test、CURRENT、WORK_LOGが追加更新されていた。
同時更新のv0.2と本候補は尺度・pivot・Range・Phase・future期限が異なるため、黙って上書き/混在しない。詳細は[採用状態記録](ADOPTION_STATUS_20260921_1634_JST.md)。

元の準備commitをforce pushせず、686bad3を親にして新規mechanical-v1 packageを追加、CURRENTを両案の状態へ更新、WORK_LOGはこのように履歴保持＋追記。v0.2仕様・scriptsは無変更。実行済みsource-lockは維持する。

最終状態: **mechanical-v1は機械定義候補固定・合成検証完了 / branch全体の正式採用は未確定 / STOP**。
次は人間がD内で採用定義を1つに整理する。G開始はその後の別承認。93 PASSをv0.2へ流用しない。人間の確認前に両案を市場データで比較・調整しない。

開始・結果整理・同時更新確認のJST時刻を残し、GitHubの最終保存SHA・保存時刻・再読確認はPR #587へ記録する。Frozen Selector/旧Evidence/Entry/EXIT/Capital/main無変更。LONG-only現物、Safety9項目false。研究gateの自動進行なし。


## 2026-09-21 17:06 JST — 一案への採用整理完了

開始確認: 2026-09-21 17:02 JST。開始HEAD `9a764e27086bf6bb1133c304b73c0027d1275760`。PR #587 open/Draft/unmergedとbranch refを直接再確認した。
ユーザー指示は「一案に整理して」。この指示を受けて採用を1つ決めるD内の作業であり、市場正解表Gの開始許可ではない。

### 決定・方針

**mechanical-v1を唯一の研究用基準定義として採用。v0.2は不採用の参考履歴。**
採用packageのcode/数値/contract/source-lock/Evidenceは一切変更せず、1S・30分Range・10active分Future等を混ぜ物なしで固定。旧仕様を削除せず、新しいADOPTED_DEFINITION.jsonと採用決定を現在の正本とする。
理由は実装全体とcontract・時刻/観測の扱いが一つのpackageとして揃っていること。93対85という件数や、市場精度/利益の優劣ではない。

### 既存Evidenceと未反映作業の照合

source-lockとverification summaryの5 source SHA-256の対応を確認。既存93合成PASS記録を読んだが、今回再実行していない。
会話内v0.2監査レポートとZIPを読取/ハッシュ確認。16:49レポートの85テストはhelper部分の報告で、全体未実装あり。修正patchをactive scriptsへ適用せず、不採用案の検証履歴として保持する。以前のremote未反映を解消したと偽らず、今後active定義の修正待ちからは外す。
元WORK_LOGのbyte列を会話内patch packageから復元し、GitHubの現blob `91dc7ef95af890557f94f3956de619bf242738ab` と完全一致を確認してからこの末尾を追記。過去時刻と履歴は書き換えていない。

### 記録先

- docs/PHASE57_LONG_ONLY_NEXT.md
- docs/phase57-five-minute-entry-state/ADOPTED_DEFINITION.json
- docs/phase57-five-minute-entry-state/ADOPTION_DECISION_20260921_1706_JST.md
- このWORK_LOGへの末尾追記

採用contract SHA-256: `f00134b85218eba4dad8409a00ce7f1076d1a3abdc02d8a4cb7e2e2b3511279e`。
既存contract内の候補statusは当時のEvidenceとして無変更。現在の採用決定は外側のmanifestで示し、過去のscopeを書き換えない。

### 未実施・限界

市場データ読取/正解表生成/因果認識/Signal/Entry/学習/Dictionary/EXIT/Capital/Portfolio/新規provider/保護データ開封=0。
合成テスト/全体regression/研究CIも今回再実行していない。raw GitHubへの補助downloadはDNS失敗し、GitHub connector読取で確認した。自動source全量byte検証PASSとは呼ばない。
未識別0、市場妥当性、収益性は未実証。adapterと実データ入力の確認は次のGに残る。

### 次とSTOP

**D採用整理は完了。次の1 GateはGの入力確認・5分Future reference table。**
別承認後に既存Developmentだけを使い、全2,155 IDsを照合し、採用仕様で全予定checkpointを記録する。75,059試作row数に合わせない。G結果を見てその場で閾値調整しない。G後にSTOPし、C/S/Eへ進まない。
今回の保存commit/保存時刻/再読・差分確認はPR #587の終了コメントへ記録する。各回JST日時付きのCURRENT/WORK_LOG/PR更新を継続。

Frozen Selector・既存Entry/EXIT/Capital・旧Evidence・main未変更。LONG-only現物。Safety9全false契約。売買・自動昇格・次Gateの自動実行なし。

## 2026-09-21 18:23 JST — G終了確認・失敗時修正方針の記録

確認時刻: 18:19 JST、結果整理: 18:23 JST。過去の開始時刻を推測しない。
開始確認HEAD: `d8240b380fa0201ccca11e909665c9689300bdcb`。PR #587 open/Draft/unmerged。
ユーザーの「失敗したら修正して続けて」を受け、前回進行中だったG run `35581246681` の現在jobsと保存Evidenceを直接確認した。

### 結果・今回したこと

verify `106274394010`、preserve `106276954627` ともcompleted/success。生成、独立local replayとの全出力比較、artifact保存、branchへのEvidence保存まで成功していた。
Evidence保存commitは `d8240b380fa0201ccca11e909665c9689300bdcb`、commit metadataは2026-09-21 18:13:39 JST。
`docs/evidence/phase57-five-minute-reference-g-v1/verification/ci-receipt.json` は18:13:26 JSTの記録で、定義93/adapter22合成tests、179 measurement files照合、independentLocalReplayMatched=trueを報告。
今回このチャットでは既存結果を読んで確認した。93/22 testsや179ファイル照合を再実行したとは言わない。

summaryは2,155 Opportunities、77,214 checkpoint、定義/Selector変更0。
latest5 COMPLETE28,474（36.88%）/PARTIAL34,638/UNAVAILABLE14,102。
Structure IDENTIFIED8,809（11.41%）/UNIDENTIFIED68,405。割合分母は全checkpointでありOpportunity数や認識精度ではない。
未識別の排他的stateReasonはCURRENT_BAR_UNAVAILABLE30,986、SCALE_UNAVAILABLE14,816、UNRESOLVED_STRUCTURE22,603。詳細理由は重複がある。

### 入力説明の訂正・残る留保

前回の「前日分足2,155/2,155 present」は、source/コンテナの存在を入力全件の完全性と同じに読ませていた。最終admissionでは尺度利用可能は1,005/2,155。
SCALE_INSUFFICIENT1,105、PREVIOUS_CONTEXT_UNAVAILABLE43、PRICE_BASIS_UNVERIFIED1、SCALE_ZERO1。Daily5完全1,961、partial194。
欠測、前日尺度不足、構造条件未成立を分ける。コンテナやIDの照合成功を、全分足完全・全State判定可能・独立PIT監査完了と呼ばない。
INHERITED_RAW_PRICE_BASIS、INHERITED_SAME_DAY_METADATA_NOT_INDEPENDENT_PIT、CURRENT_ACTION_RAW_NOT_REAUDITED等は解消していない。市場全体の理解、未知0、利益の証拠ではない。

### 失敗時の修正・継続範囲

今後このG作業の実行不具合があれば、ログを根拠にG内のadapter/時刻/型/保存/再現処理を修正し、必要な限定テスト・再実行を行って証拠を保存する。
今回のrunは成功済みで失敗修正・retryは不要。現在の変更はCURRENT更新と本ログ追記だけ。採用定義、数値閾値、source-lock、旧Evidence、workflow、scriptsは変更しない。
未識別が多いという研究結果をエラー扱いして閾値変更・架空足補完・Opportunity除外で救済しない。source hash不一致、保護データ要求、定義変更が必要ならguardを外さず人間確認。
この指示はCausal Recognition/Signal/BUY-WAIT/学習/EXIT等の開始許可ではない。

### 保存と次の1 Gate

CURRENTの古いG_NOT_STARTEDを更新し、実行成功とState識別率・入力制約を分離した。GitHubへ日時付きでこの追記を保存し、PRコメントに最終保存SHAを記録する。
次はG内の保存結果・未識別理由・入力制約・代表チャートの人間確認。今回の読取だけで代表チャートレビューやG品質承認まで完了したとはしない。C/S/Eへ進まない。
状態: `G_TABLE_GENERATED / DEDICATED_REPLAY_PASS / SOURCE_LIMITATIONS_REMAIN / HUMAN_REVIEW_REQUIRED / C_NOT_STARTED`。

今回、raw GitHubからログbyteを取得する補助試行はDNS失敗。GitHub connectorで読んだ文書とjob/receiptを根拠とし、通信失敗を研究CI失敗や自動lint PASSにしない。
新規テスト再実行0、State再生成0、provider0、保護データ開封0。採用定義/Frozen Selector/既存Entry/EXIT/Capital/main不変。Safety9全false契約。成功runの追加再実行・自動監視・後続Gate自動進行は設定していない。


## 2026-09-21 19:19 JST — 未識別68,405件 Deep Audit v1 完了

開始時remote HEAD: `90325a549b083c0d6ff2749cc52c3c3fbd8f59f9`。ユーザー指示「進めて」を受け、State正確表v1の未識別原因監査だけを実施。

### 実施
- G保存measurement 179ファイルをmanifest SHAで再検証。
- 全77,214 checkpoint / 未識別68,405を、定義・閾値を変えずに監査。
- current bar不足、S不足、latest5 partial、confirmed pivot数、last-4 pivot geometry、current Phase/CHOP/level eventを分解。
- A/B/D hard partitionとC descriptor overlayを分けた。Cを排他カテゴリへ強制しない。
- producerを固定入力で2回実行しmanifest byte hash一致。
- ID辞書順でA/B/Dの代表10 checkpointを抽出し、保存raw 1mからchartを作成。profit/outcomeで代表抽出していない。

### 結果
A_INPUT_OR_OBSERVATION_LIMITED 54,925。
B_STRUCTURE_NOT_YET_CONFIRMED 11,326（pivot0 3,723 / 1 4,091 / 2 2,185 / 3 1,327）。
D_STRUCTURAL_VOCABULARY_GAP_CANDIDATE 2,154。H_UP+L_DOWN 845、H_DOWN+L_UP 479が最大。
DでPhase NONE 286、うちCHOPあり55、Phase NONE+CHOPなし231。
SCALE_INSUFFICIENT 1,105 Opportunitiesはcomplete5m block 0=748,1=136,2=76,3=50,4=52,5=43。

Aは「providerで直せる欠損」と断定していない。Bは新しいFORMING Stateを追加した結果ではなく、現在定義が4 pivot確認前であるという診断。DはVocabularyの穴の**候補**であり、新State追加を正当化した結論ではない。

### 検証・保存境界
G measurement manifest SHA256 `4e11b8eb576dcdd0552f2461c699f57bdabc1db37d8e4c2be9a389a80748d6d1`。
Deep Audit二重実行manifest SHA256 `cdd251ec8aab55c061ac1385a8f21b00543a2c5f8d04e27272d3ee4a538115ad`。
会話添付ZIP SHA256 `ea2e175fe70b145bdd51fc179ee7b1ad4cca64ff14757e5130a8229bbcb10245`。
Gitには数値Evidence/Protocol/Claude handoffを保存し、添付chart本体をtrackedしたとは主張しない。

### STOP / 次
**Deep AuditでSTOP。次はClaude独立レビュー。**
Claudeレビューが返るまでmechanical-v1を修正せず、State v2/正確表v2/C/S/Eへ進まない。
