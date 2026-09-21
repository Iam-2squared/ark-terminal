# Phase57 LONG-only — 現在の方針・次作業

最終更新記録: **2026-09-21 16:34 JST**
今回の開始: 2026-09-21 16:04 JST / 機械定義・合成検証の結果整理: 16:27 JST
日時はJST / UTC+09:00、24時間表記。GitHub保存時刻はcommit metadataとPR終了コメントに記録する。
対象: Iam-2squared/ark-terminal / research/phase57-long-only-cash-equity / PR #587
開始HEAD: `907f1016cd46dd784b2a7269aa10945e75e12543`
保存直前に見つかった同時更新HEAD: `686bad3fa0c2283a776d1434f30820c3d1e35fb5`
最終保存SHAは本更新を含むGit履歴とPRコメントを参照。次回は必ずlatestを再取得する。

## 現在地点

**機械判定ルール1案の実装・合成93テスト・二重実行は完了。ただし別案v0.2の同時追加を確認したため、最終採用は未確定。**

`MECHANICAL_V1_SYNTHETIC_93_PASS / CONCURRENT_V02_PRESERVED / ADOPTION_UNRESOLVED / STOP_FOR_HUMAN_REVIEW`

- [最優先：同時更新の差分・採用状態](phase57-five-minute-entry-state/ADOPTION_STATUS_20260921_1634_JST.md)
- [今回のmechanical-v1候補と検証結果](phase57-five-minute-entry-state/mechanical-v1/REPORT-ja.md)
- [mechanical-v1の仕様](phase57-five-minute-entry-state/mechanical-v1/SPEC-ja.md)
- [機械可読contract](phase57-five-minute-entry-state/mechanical-v1/contract.json)
- [93合成テストEvidence](phase57-five-minute-entry-state/mechanical-v1/verification/summary.json)
- [v0.1概念案と同時追加されたv0.2追記](phase57-five-minute-entry-state/STATE_DEFINITION_v0.1.md)
- [時系列作業ログ](phase57-five-minute-entry-state/WORK_LOG.md)

## 継続する方針

Selector=WHAT、Entry=WHEN IN、EXIT=WHEN OUT。
Frozen Selectorを変更せず、OpportunityをState/Signal/Qualityで捨てて成績を改善しない。

将来のEntryは選出時点Tで初回評価し、BUY NOWまたはWAIT。最初から必ず5分待つ仕様にはしない。WAITなら5 active minutes後に再評価。

材料は最新5本closed 1m、Today Open→NOW、前営業日observed 1m、D-5〜D-1 Daily。Direction / Structure / Phase / Events / Attributes / Context / Observationを分離する。
Signalは将来State解釈にもBUY/WAITにも直接影響し得る。State別の追加価値は別Gateで測る。Signal単独BUYにしない。Signalなしを候補拒否にしない。保有後SELLは別EXIT研究。

## 今回完了した候補実装

mechanical-v1は前日完全5mブロックのTrue Range中央値S、終値1Sのpivot、交互4pivotのHH/HL・LH/LL、保護水準失効、30分Range、CHOP重複属性、HIGH→LOW回復episode、typed cross、同日次10active分のFuture確認を固定。

local Python 3.13.5でnamed synthetic tests 93/93 PASS。固定sourceで2回実行し、summary/snapshot SHA-256とmanifest一致。別途上書き拒否・source破損拒否を確認。市場データの成績による閾値探索0。

合成検証は仕様/実装整合の確認であり、実相場の分類精度や最適性の証明ではない。実市場正解表は0行。

## 保存直前に見つかった別仕様

remoteには同時にv0.2の仕様追記とhelper/testが追加されていた。v0.2は1m return尺度・High/Low3S・2tick floor・20分Range・15分Futureなど、mechanical-v1と異なる。

**両案を混同しない。** v0.2側の変更はそのまま保持し、今回の候補は独立ディレクトリに保存。93テストPASSをv0.2へ流用しない。相場の結果を見て都合の良い部品を選ばない。
同時更新の出現によって直ちにどちらかを正式採用したり、branchを古い開始HEADへforce resetしたりしない。

## 次の1 Gate

**D内の採用整理。人間がどの機械定義を正解表の基準にするか確認する。**
採用の記録（日時・contract/hash・不採用案の保存扱い）が完了するまでGを開始しない。

|Gate|内容|現在|
|---|---|---|
|D|State意味・機械契約・合成検証|mechanical-v1検証完了、同時追加v0.2との採用整理待ち|
|G|採用された定義で5分Future reference table|BLOCKED・市場生成0|
|C|未来を隠した同じ時点のState認識|BLOCKED|
|S|State × Signalの追加情報|BLOCKED|
|E|State + Signal + ContextのBUY NOW / WAIT評価|BLOCKED|
|Later|必要な学習、Dictionary増分、別EXIT、Capital/Portfolio、protected評価|BLOCKED|

Gを別途承認したら、既存Developmentのみでcalendar/identity/price basis/timestamp/欠測のInput Admissionを行い、全Opportunityのcheckpointと正解表を生成する。75,059を期待row数にしない。欠損をprotected dataや新規provider取得で救済しない。
Gで分類率やUNKNOWNが多くてもその場で定義を変えず、分母・reason・例・チャートを保存してSTOPする。

## 停止中の旧系統

旧5+1 Path、旧STEP2/3、scripts/phase57_causal_state_recognition_v1.pyは新Stateの教師・合格証拠として使わない。旧Evidenceは削除・上書きしない。
Workローカル4 commits（be52f30 / b045dc0 / 182d2ab / 66fc3c2）、75,059区間＋T+0 2,155行、10/30bps試作はUSER_REPORTED / UNAPPROVEDのまま。今回取得・再分類・自動pushしていない。

## 毎回の日時付きGitHub記録

1. 開始時にlatest HEAD・PR・この入口・承認範囲を確認。
2. 終了時にこの入口を更新しWORK_LOGへ追記。必ず`YYYY-MM-DD HH:MM JST`。不明な過去時刻は推測しない。
3. 実施/未実施、結果、検証範囲、未解決、方針変更、次の1 Gate、停止条件、Safety、開始SHAを記録。
4. 合成PASS、実市場妥当性、因果認識、経済価値、CIを分離。
5. 保存直前にremoteを再確認。同時更新があれば保全し、定義の差を黙って統合しない。force=false。
6. 保存後の再読と正確な保存SHA・時刻をPR #587に記録。失敗時はLOCAL_ONLY等と明記。
7. 旧ログは消さず訂正は新日時で追記。人間確認前に次Gateを実行しない。

## Safety / 実行境界

LONG-only / cash-equity-only。Frozen Selector・既存Entry/EXIT/Capital・mainは未変更。
今回の新コードはdocs下の孤立した定義参照で、既存実行系に未接続。実市場ファイル読取0、正解表生成0、fit0、Signal/Entry/EXIT評価0、新規provider0、保護データ開封0。
GitHub Actions/旧研究を再実行しない。commitに[skip ci]を付け、未実行をPASSと呼ばない。PR全GREEN主張なし。

executionAllowed=false
brokerWriteAllowed=false
excelOrderWriteAllowed=false
rssOrderFunctionAllowed=false
liveTradingAllowed=false
paperTradingAllowed=false
automaticPromotionAllowed=false
productionUpdateAllowed=false
transmitted=false
