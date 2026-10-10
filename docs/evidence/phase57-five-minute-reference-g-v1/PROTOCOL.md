# G Gate — Five-minute Future State Reference Table v1

記録日時: 2026-09-21 17:50 JST
作業開始: 2026-09-21 17:33 JST
開始HEAD: 39ace6de4c73abc53f5050d4d9c59c74b6f5f414
承認: ユーザーの「進めて」「次進めて」。G（入力確認・adapter検証・正解表作成）のみ。
Status: PRECOMMITTED_BEFORE_MARKET_STATE_GENERATION

## 問い

採用済みmechanical-v1を一切変更せず、固定2,155 OpportunitiesのTとT+5k active minutesにおける価格状況を、保存された実データと同日最大10active分の未来確認でどこまで記述できるか。
これは定義付きreference annotationであり、唯一絶対の正解、因果認識精度、将来利益の証明ではない。

## 固定定義

唯一の正本はdocs/phase57-five-minute-entry-state/ADOPTED_DEFINITION.jsonが指すmechanical-v1。
contract SHA256=f00134b85218eba4dad8409a00ce7f1076d1a3abdc02d8a4cb7e2e2b3511279e。
reference.py SHA256=e57d41b1a9472fb0ed254895d956623a438557f540443c0bee14a6db8f2d8d3d。
test_reference.py SHA256=eed192e39e957a97229e8bdfc4b75e0c79dc393a70d150ca0b714eab31907ec6。
前日完全5m TR中央値S、最低6block、終値1S pivot、4pivot構造、30分Range、CHOP重複属性、HIGH→LOW回復episode、同日future10active分を固定。旧5+1/v0.2/10bps/30bps、既存Signal/Entry/WHO/Dictionaryをラベルに使わない。

## 入力・同一性

既存Actions artifactを再利用する。新しい市場provider要求や旧研究の再実行はしない。
1. run35510863265 artifact10605887642: substrateのopportunities/raw-paths/source-ledger/inventory/manifest。
2. run35553422490 artifact10619378314: daily.json.gzとreceipt。
3. 既存Step1 archive: ID/session/symbol/start/referencePriceだけの照合、およびraw分足の一致確認。旧predicate/class/outcomeは対象外。

全ZIP・対象メンバーのhashを既存manifest/receiptと照合。固定cohort protocol SHA256=6b02b3088dd8ea7f8ce53112bc276df442bae3ce0716b8139c92733be4de2994、Git blob=94b7e7296f8ab38bed4551454feec1c8dfca8b2b。Step1のID配列と保存inventory日付を使って同じprotocol JSONを復元できても、完全byte hash一致を必須にし、一致しない復元値は使わない。protocolのSignal/Entry設定はロード対象識別の証跡だけで、新Stateへ入力しない。

source opportunityは5375件を含むが、計測するのは固定cohortの2155件だけ。id/session/symbol/origin時刻・価格のallowlist projectionとする。WHO、score、rank、old Path、Entry/outcomeを計測入力へ渡さない。
cohortに1件でもID重複/消失/時刻不一致があれば生成前STOP。評価59sessionのうちcohortが0件の日も0件として表示する。全体の75,059試作区間を期待行数にしない。

## 時刻・価格・観測のadmission

保存raw columnsはminute_start,O,H,L,C,Vo,Va。regular1mだけend=start+1へ変換。前場/引けauctionを通常1mへ変換しない。regular startはAM540..689、PM750..(2024-11-05前899、それ以降924)。これは保存元timestamp契約に従う再構成であり、新たな約定時刻の主張ではない。
重複/非有限/不正OHLC/負の活動量を拒否。欠測を埋めず、1本でも欠ければその項目に理由を保存。5active分は予定取引時間であり、5本集まるまで時刻をずらさない。Tで初回、正規gridの終端まで。昼休み/終端の余りは別に残す。

実際の前営業日は保存されたexact daily lag datesおよびsource previousSessionと照合。必要日付のunion calendarは、全cohortのD-6..D-1配列との一致を検証した範囲の注入calendarであり、独自の平日推定や全取引所calendarと呼ばない。authorized Development外の前日・日足は読まない。

Dailyは保存daily.json.gzのD1..D5/OHLC/Vo/Vaと同一lagのreasonのみを抽出。既存源はraw daily pages hashを照合してから保存したprojection。派生スコア/Stateは再利用しない。D6の不備だけで有効D-5..D-1を捨てない。欠測/INVALID_OHLC/CORPORATE_ACTION/OUTSIDE_AUTHORIZED_DEVELOPMENTを明示し代用しない。

価格は保存抽出コードが選んだ非調整O/H/L/Cの共通RAW価格単位を用い、調整済みAdjCや別価格系列へ置換しない。元L1は同日corporateActionFlagを除外するcontractである。今回その保存選出のadmissionを継承するが、todayの元Daily AdjFactor/ExRTや全corporate-action原本をこのartifactだけで独立再監査したとは言わない。各出力にINHERITED_RAW_PRICE_BASIS、INHERITED_SAME_DAY_METADATA_NOT_INDEPENDENT_PIT、CURRENT_ACTION_RAW_NOT_REAUDITEDを記録する。既存日足reasonで判明する不適合は該当context/scaleへ反映。明白なbasis矛盾は該当比較を禁止して理由付きnullにする。原本未確認をPIT完全検証済み/実運用可能と誤表示しない。

availableAt/receivedAtの原本がなければNoneを渡しHISTORICAL_CLOSED_RECONSTRUCTIONを保持。bar終了時刻を実受信時刻として捏造しない。

## 生成・保存

採用reference_atをそのまま呼ぶ。previous context/Daily/raw factsとoracle State、futureConfirmationを分離。assemble等のprefix machineryをcontext構築に利用しても、因果予測とoracleの性能比較はしない。
現在Stateはtで終了した最新5分と構造、未来はpivot確認専用。future10分の後はラベルを変えない。翌日で救済しない。引け前はfuture確認だけ打切り、現在の観測事実を一括削除しない。

入力を共通保存し各行から参照してよいが、Opportunityを削除しない。checkpoint raw、source IDs/hash、Observation、Direction、Structure、Phase集合、Attributes、typed level events、future確認、Transitionを保存する。全日raw OHLCV/value/auction sidecar、前日とDailyの文脈、adapterとsource-lock、集計、plots、completionを残す。
独立output directoriesへ固定入力で2回生成し、全JSON/CSV/rawのhash一致を確認する。描画のtimestamp等は機械出力と分離する。既存output/Evidence上書き拒否。

## 報告

全2155件・全予定checkpointを分母として、完全/部分/未観測、Direction、Structure、Phase、multi-label、未識別reason、前日尺度/Daily availability、future打切り、selection time・clock time別、14:30/15:00選出のcoverageを報告。
Structure不明でもRecovery等が記述できる場合を別に示し、『何か1列埋まる率』を『完全分類率』と呼ばない。未来確認window観測率をラベル正確性と混同しない。
代表図は種類・不足reasonごとの辞書順最小ID等の決定的選択とし、利益で選ばない。例示は全母集団の有効性証明ではない。

## Completion / STOP

ID/hash/admission照合、adapter tests、採用93 synthetic tests、全grid行生成、二重実行、raw/summary/plots/hash保存を確認。元データの限界・definition未識別があれば残す。厳密な正解保証やPIT完全性のGateは人間レビューへ留保。
致命的なID/hash不一致、定義codeが変わる修正の必要、無承認データが必要になればSTOP。市場結果を見てSwing/Range/horizonを変えない。
G結果保存後STOP。Causal Recognition/Signal/State×Signal/BUY-WAIT/Entry Learning/Dictionary/EXIT/Capital/Portfolioは未着手。main未merge。CURRENT/WORK_LOG/PRへ終了JST・保存SHA・結果・限界・次Gateを記録する。

executionAllowed=false
brokerWriteAllowed=false
excelOrderWriteAllowed=false
rssOrderFunctionAllowed=false
liveTradingAllowed=false
paperTradingAllowed=false
automaticPromotionAllowed=false
productionUpdateAllowed=false
transmitted=false
