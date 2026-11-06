# G — Five-Minute Future State Reference Table v1

記録: 2026-09-21 17:46 JST。作業開始確認: 2026-09-21 17:25 JST。
Repo Iam-2squared/ark-terminal / research/phase57-long-only-cash-equity / PR #587。
開始HEAD: 39ace6de4c73abc53f5050d4d9c59c74b6f5f414。
ユーザーの「進めて」により、採用済みmechanical-v1を使うG（入力監査・adapter・正解表・可視化）だけを実施する。G結果を保存してSTOP。C/S/Eへ進まない。

## 単一の問い

固定されたState定義は、全2,155 Development Opportunitiesの各5取引分checkpointを、どの状態・観測品質・未識別理由として記述するか。
Stateは定義依存のFuture-assisted reference labelで、唯一絶対の相場正解・未来なし認識性能・利益の証明ではない。

## 不変の採用元

ADOPTED_DEFINITION.jsonのfive-minute-state-mechanical-v1を使用。source commit 9a764e27086bf6bb1133c304b73c0027d1275760。
contract SHA256=f00134b85218eba4dad8409a00ce7f1076d1a3abdc02d8a4cb7e2e2b3511279e。
reference.py SHA256=e57d41b1a9472fb0ed254895d956623a438557f540443c0bee14a6db8f2d8d3d。
S、1S close pivot、30m Range、CHOP、10 active-minute Future horizon、missingルールを変更しない。v0.2/85-test patch/旧5+1/10・30bps試作/Dictionary/Signal trigger/Entry outcomeは使わない。

## 入力と既存Evidenceの復元

1. census protocol.jsonのopportunityIdsを母集団の正本とする。substrate/opportunities.json.gzの5,375件全体からID一致する2,155件だけを取得。Deep Auditの保存済み2,155 identity witness、Daily contextのIDとも照合する。人数・選出時刻・銘柄・基準価格を照合し、outcomeで抽出しない。
2. raw-paths-evaluator-only.json.gzのtoday/previousは実1m観測配列（minute START,O,H,L,C,Vo,Va）。Source archive run35510863265 / artifact10605887642。ZIP SHA256=749caf82bbd9d39969f5712ef5a6f2705ac973a2f74483f03307c671586ae05a。current repoのmanifestとblob/SHAを確認する。
3. 保存daily.json.gzはrun35553422490 / artifact10619378314。ZIP SHA256=279388c00b6a97501a578d8ab1f2dd813ba5b56a8a1d91c7ee7afeea39b805e0。DailyのD1..D5/O,H,L,C,Vo,Vaは既存producerで原列をコピーしたものだが、当日action metadataの完全な原本ではない。
4. 必要なDaily action/basis/日付を補うため、既存run35447995157の暗号化raw archivesを既存CI credentialで復元してよい。これは新規provider取得ではない。tar内のcensus Development allowlistかつ必要な日付のdaily-pages.jsonだけを読み、必要銘柄の原列とAdjFactor/ExRTの明示screen情報だけを投影する。秘密値を記録・出力しない。Holdout/excluded/その他日の市場bodyは抽出・解析しない。全原ページをGitへ公開しない。
5. calendarは保存probe-v2/calendar.jsonのHolDiv=1、exact previousとD-5..D-1。calendars/allowlistsはmetadataとして読めるが、protected市場dataは読まない。必要lagが対象Development外ならOUTSIDE_AUTHORIZED_DEVELOPMENT、古い別日代用なし。
6. raw archive/file/page-response hash、Date/Code重複、O/H/L/C有効性、価格列RAW/adjustedの一致、既知corporate actionを監査。action/basis未確認はcross-day/Sを無効にし、現在5分の単独記述は残す。sourceの条件で消えた行・no-trade/halt/provider lossを今回断定しない。

## 時刻・adapter契約

原時刻STARTを通常分足について一度だけENDへ+1分変換。既存calendarと日付別regular-session定義を注入する。前引け/引けauctionは別区分に保持し、通常5本へ混ぜない。前日のcontext尺度も通常分足から作る。
Tで初回、以後5予定active minutesごと、観測不足でも予定時刻は動かさない。State(t)はtまでの最新5本＋構造。t後10 active minutes内で確認したeffectiveAt<=tのpivotだけをoracle側で使う。次5分の予測対象へすり替えない。
14:30/15:00以後を一律削除せず、現在観測とFuture右打切りを別欄にする。最後の5分未満tailは別記録。75,059を期待行数にしない。
保存archiveにreceivedAt/knownAtがない場合はnullとしHISTORICAL_CLOSED_RECONSTRUCTION。START+1を実受信時刻として捏造しない。

## 出力

全Opportunity×全予定checkpoint行を保存。欠測行も母集団から除外しない。元inputへのID・source/hash参照を残す。
Direction、Structure、Phase集合、CHOP等Attributes、typed level Events、Daily/previous/Today/Latest5 context、Observation、Future確認/censor、欠測・basis・scale理由を分離する。
context組立にclosed-prefix primitiveを使っても、現在Gateはoracle reference生成のみ。Causal precision/recall/State差の性能比較やSignal・BUY/WAITの評価を作らない。
複数Opportunityが同じsecurity/session/tを参照する場合は計算cache可。ただし全Opportunityの行・分母を保持し、同一scope同一inputは同一出力とする。

## 集計と図

全行数、T+0、latest5 complete/partial/unavailable、Direction分類率、Structure識別率、Phase有無、multi-label率、理由の重複あり/排他的primary reasonを分ける。
全母集団、完全観測subset、basis/scale利用可能subsetを混ぜない。UNKNOWN名称変更だけで分類率向上と呼ばない。
時刻別、selection time別、session別、14:30/15:00以後、Future確認別を集計。連続checkpointのState変更は集合変化/構造更新として記録し、欠測を跨ぐ転換を断定しない。
代表例はState/観測reason strataの安定ID順による決定的抽出。利益や勝者で選ばず、選んだ理由を保存。実1mと5m checkpoint Stateをチャート表示する。類似名の重複Stateを強制単一化しない。

## 検証・停止

adapterの合成例/反例、採用source hash、全ID一致、prefix/window、日付/価格basis、無補間、source/結果再実行hashを確認する。可能な範囲では全label二重実行。未完了なら未完了と記録する。
Inputs/protocol/code/tests/raw/summary/plots/manifestsを保存。大きな原本は既存artifactとhashへ参照し、今回生成のrawは別添artifact/添付に保存できるが、GitHub本体と添付の保存先を明記する。
結果を見て定義や閾値を修正しない。実相場を十分表せない場合もEvidence保存してSTOP。Causal Recognition/Signal/BUY-WAIT/学習/Dictionary/EXIT/Capital/Portfolioは実行しない。新規provider requests=0。
GitHubへJST日時、今回結果、未解決、次の1 Gate、保存SHAを毎回記録。既存Evidenceを上書きしない。専用CIとPR全GREENは別。

## Safety

LONG-only / cash-equity-only。Frozen Selector不変。main未merge。
executionAllowed=false
brokerWriteAllowed=false
excelOrderWriteAllowed=false
rssOrderFunctionAllowed=false
liveTradingAllowed=false
paperTradingAllowed=false
automaticPromotionAllowed=false
productionUpdateAllowed=false
transmitted=false
