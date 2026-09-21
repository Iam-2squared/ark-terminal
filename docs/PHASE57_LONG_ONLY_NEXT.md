# Phase57 LONG-only — 現在の方針・次作業

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
