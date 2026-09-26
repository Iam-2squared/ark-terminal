# State Definition — 一案への採用決定

記録日時: **2026-09-21 17:06 JST** / 作業開始確認: 2026-09-21 17:02 JST
開始HEAD: `9a764e27086bf6bb1133c304b73c0027d1275760` / PR #587 open・Draft・unmerged
状態: **ONE_DEFINITION_ADOPTED_AND_PINNED / G_NOT_STARTED / STOP**

## 決定

**mechanical-v1を、以後の5分State正解表の唯一の研究用基準定義として採用する。**
ユーザーの「一案に整理して」という指示に基づく選定であり、ユーザーが各数値の市場最適性まで保証したという記録ではない。

v0.2は不採用の参考履歴として保持。混合した第3案を作らず、どちらを使うかという保留を今後のCURRENTに残さない。
採用状態の機械可読な正本は[ADOPTED_DEFINITION.json](ADOPTED_DEFINITION.json)。パラメータ・計算手順の正本は[contract.json](mechanical-v1/contract.json)と[SPEC-ja.md](mechanical-v1/SPEC-ja.md)。

## この案に統一する理由

これは保存済みソースとレポートに基づく**設計上・実装上の選定判断**であり、市場精度の勝敗ではない。

| 比較軸 | 選定理由 |
|---|---|
| 一貫した実装 | mechanical-v1にはraw形式の合成1mから尺度・pivot・構造・局面・referenceをつなぐ参照実装とcontractがある。v0.2の85テスト修正版はhelper検証で、全体の未実装が残るとレポートされている |
| ユーザーの5分設計 | 前日5分blockの尺度を使い、最新5本の内部形と前日/Daily contextを分離する構成を、そのまま1つの基準にできる |
| 時刻・順序 | 終値pivotのeffectiveAt/confirmedAtが明示され、同一1m足内High/Lowの順序をpivotのために推測しない。High/Low自体は別descriptor/eventに残る |
| 追跡性 | code/contract/SPEC/test/verifierのhashと93テストの保存Evidenceが対応している。選定のために実市場で再分類やパラメータ探索をする必要はない |

**93と85の数の大小で優劣を判断していない。** 合成テストで整合しても相場の表現力・収益は別問題。10分と15分、終値とHigh/Lowのうちどちらが市場で最適かを検証したとは言わない。

## 一案として採用する内容 — 変更なし

| 要素 | 採用するmechanical-v1の仕様 |
|---|---|
| 更新時刻 | Tで初回、T+5k active minutes。State(t)はtで終了した最新5分とt時点の構造 |
| Context | D-5〜D-1、実際の前営業日observed 1m、Today Open→t、最新5本 |
| Scale S | 前日の完全・非重複5分TR中央値、最低6block、当日固定、fallbackなし |
| Swing | 終値1S反転、同値極値は最初、gap/recessで反転の連続性を切る |
| Structure | 交互4pivotのHH/HLまたはLH/LL。保護水準を終値で厳密に破れば失効 |
| Range | 30連続1m、幅<=2S、効率<=1/3、上下各2blockで接触、成立後の上下境界は固定 |
| Phase | PROGRESSION / CORRECTION / RECOVERY / BALANCE / RESTRUCTURINGを根拠付きで保持 |
| Recovery | 隣接確認HIGH→LOW episodeを参照。回復途中、開始高値回復完了、構造復帰を分離 |
| CHOP | 最新5本の終値方向反転>=2、効率<=1/3、幅>=0.5S。ほかの局面を消さない |
| Breakout/Reclaim | 水準IDとcross履歴付き。wick、close cross、cross後2予定closeの維持を分離 |
| Future確認 | 同日内の次10 active minutes。次5分予測と現在Stateを取り違えず、不足は項目別に打切り |

数値は保存済みの定義をそのまま選択したもの。新しい閾値の追加・変更・市場による最適化0。
細部に要約との違いが生じた場合、採用hashのSPEC/contract/referenceを読み、黙って再解釈せず不一致として報告する。

## 採用sourceの固定

source commit: `9a764e27086bf6bb1133c304b73c0027d1275760`
directory: `docs/phase57-five-minute-entry-state/mechanical-v1`
source-lock Git blob: `eb851634270b02f41ce42df999f388e0b16d2ed3`
contract Git blob: `8612986f268064e526a6783a803c8d851f50079a`

| Source | 保存済みSHA-256 |
|---|---|
| SPEC-ja.md | `f640e0b6bd04bd1a3f65130d64d904607064e34227e99467fc46b96b48988f70` |
| contract.json | `f00134b85218eba4dad8409a00ce7f1076d1a3abdc02d8a4cb7e2e2b3511279e` |
| reference.py | `e57d41b1a9472fb0ed254895d956623a438557f540443c0bee14a6db8f2d8d3d` |
| test_reference.py | `eed192e39e957a97229e8bdfc4b75e0c79dc393a70d150ca0b714eab31907ec6` |
| verify.py | `bda692eab389f7802c1d8f13d4100febe313174b06df8b48fa74b348c8f74e95` |

今回、GitHubのcontract/source-lock/verification summaryと採用状態を読み、同じ5 source hashがsource-lockと93テストsummaryに記録されていることを照合した。既存の合成93テスト・二重実行を今回再実行したとは主張しない。full sourceを今回すべてruntimeへ再downloadしてbyte hashを再計算した主張でもない。

元package中のFROZEN_CANDIDATE_HUMAN_REVIEW_REQUIRED等は、検証当時のsource/hashを維持するため変更しない。本決定と採用manifestが**現在の採用状態**を表す。過去の実験scopeを市場実験の許可へ書き換えない。

## 不採用・未反映成果物の扱い

| 資料 | 扱い |
|---|---|
| v0.2の仕様追記とrepository helper/test | 不採用、削除しない、Gで使わない、並行開発を続けない |
| 会話内v0.2修正85テストパッチ | 不採用案の検証履歴。今回active scriptsへ適用しない |
| 旧5+1 / 旧STEP2/3 / Work 10bps/30bps | 歴史資料。教師ラベル・期待row数・閾値に使わない |
| 16:34のADOPTION_UNRESOLVED記録 | 当時の事実として保持し、本決定で採用保留を解消 |

16:49の会話内監査レポートを今回直接読んだ。既存7 PASS、追加反例7 FAIL、修正後85 PASSを2回、全15受入条件は完全0/部分9/未実装6という報告であり、mechanical-v1の未実装指摘ではない。今回この85テストは再実行していない。

会話内ファイルの今回確認したSHA-256:
- phase57_state_definition_synthetic_audit_20260921.zip: `3a5dea1c10042d143737ad1eb632e46c6fd08fd0776aa2fc0e0009080a508def`
- phase57_state_definition_validation_20260921.md: `8011b44757f89475326efc06998456c10c8d8fcfde3e15ce89ccf05ee2c5b7f1`

これらのZIP全体やパッチがremoteへ追加済みとは言わない。**今後のactive定義を直すための反映待ちタスクからは外し、不採用案のローカル履歴として保持する。** 過去の書込失敗の経緯は消さず、今回の採用判断をGitHubへ記録する。

## 次の1 Gateと停止

Dの採用整理は完了。次は**G: Input Admission＋5分Future reference table**だけ。
実市場データadapter、calendar、ID、前日、Daily lag、price basis、bar時刻、availability、欠測を既存Development内で確認してから採用contract通り処理する。2,155 IDsを照合し、75,059という試作row数に合わせない。adapterが必要でも定義を再設計しない。

Gは別の開始承認後。今回Gを自動開始しない。Gの後は分類率・reason・代表チャートを保存してSTOPし、Causal RecognitionやState×Signal、BUY/WAITへ進まない。
データ不足・中央値0・未来確認10分内の未確定は残り得る。UNKNOWNを0に見せるための強制分類・補間・protected dataや新規取得での穴埋めはしない。

## 今回の検証範囲・Safety

今回は採用決定と日時付き記録のみ。code/parameter変更0、合成テスト再実行0、市場データ読取0、市場State生成0、Signal/BUY-WAIT/学習/Dictionary/EXIT/Capital/Portfolio実行0、新規provider0、protected data開封0。
CURRENT/WORK_LOG/採用文書/manifestだけを更新。full regression・研究CIは実行しない。[skip ci]で保存し、未実行をPASSやPR全GREENと呼ばない。source packageが無変更であることと差分範囲を保存後に確認する。
runtimeのraw GitHub取得補助はDNS失敗だった。採用元をGitHub connectorで確認できたことと区別し、通信補助の失敗を隠さない。

Frozen Selector・既存Entry/EXIT/Capital・旧Evidence・mainを変更しない。LONG-only / cash-equity-only。
executionAllowed=false / brokerWriteAllowed=false / excelOrderWriteAllowed=false / rssOrderFunctionAllowed=false / liveTradingAllowed=false / paperTradingAllowed=false / automaticPromotionAllowed=false / productionUpdateAllowed=false / transmitted=false。

**今回確定したのは唯一の研究基準定義。相場の正解表、実時間認識、利益を実証したという意味ではない。**
