# Phase57 LONG-only — 現在の方針・次作業

最終更新記録: **2026-09-21 17:06 JST**
今回の開始確認: 2026-09-21 17:02 JST。日時はJST / UTC+09:00、24時間表記。
対象: Iam-2squared/ark-terminal / research/phase57-long-only-cash-equity / PR #587
開始HEAD: `9a764e27086bf6bb1133c304b73c0027d1275760`
保存commitと実保存時刻はGit履歴・PR終了コメントを参照。次回開始時はlatestを再取得する。

## 現在地点 — 一案に確定

**採用定義は mechanical-v1 の1案だけ。v0.2との採用整理は完了。**

`ONE_DEFINITION_ADOPTED_AND_PINNED / EXISTING_SYNTHETIC_EVIDENCE_REVIEWED / G_NOT_STARTED / STOP`

ユーザーの「一案に整理して」を受け、既存mechanical-v1を研究用の基準定義として採用した。両案を混ぜた第3案は作らず、採用packageのcode・数値条件・source-lock・既存Evidenceを変更していない。

| 正本 | 役割 |
|---|---|
| [ADOPTED_DEFINITION.json](phase57-five-minute-entry-state/ADOPTED_DEFINITION.json) | 唯一の採用version・source commit・hash・不採用案の扱い |
| [採用決定](phase57-five-minute-entry-state/ADOPTION_DECISION_20260921_1706_JST.md) | 選定理由、限界、今回の実施/未実施 |
| [mechanical-v1/SPEC-ja.md](phase57-five-minute-entry-state/mechanical-v1/SPEC-ja.md) | 採用した判定手順の正本 |
| [mechanical-v1/contract.json](phase57-five-minute-entry-state/mechanical-v1/contract.json) | 採用したパラメータの正本 |
| [WORK_LOG.md](phase57-five-minute-entry-state/WORK_LOG.md) | 日時付きの追記履歴 |

旧採用状態文書のADOPTION_UNRESOLVEDやpackage内のFROZEN_CANDIDATEは保存時点の履歴。**現在の採用状態は上記manifestと今回の決定を優先する。** 元Evidenceのstatus文字列を書き換えてhashを変えない。この採用は市場分類・売買・自動昇格の実行許可ではない。

## 採用ルールの要約

| 項目 | 唯一の採用仕様 |
|---|---|
| 更新 | Selector選出Tで初回、WAITなら5 active minutes後に再評価 |
| State時刻 | tまでの最新5本closed 1mと現在構造。次5分の予測とは別 |
| 4時間軸 | D-5〜D-1 Daily、前営業日observed 1m、Today Open→t、最新5本 |
| 尺度S | 前日完全5m blockのTrue Range中央値、最低6block、当日固定、fallbackなし |
| Swing / Structure | 終値1S反転、交互4pivotのHH/HL・LH/LL、protected levelの終値失効 |
| Range | 30連続1m、幅<=2S、効率<=1/3、上下各2block接触、境界は成立時固定 |
| Phase | PROGRESSION / CORRECTION / RECOVERY / BALANCE / RESTRUCTURING、根拠付き集合 |
| 高値・安値 | 重要水準、HH/HL、wick、cross、幅等として保持。終値pivotだから無視するわけではない |
| CHOP | 最新5本で終値方向反転>=2、効率<=1/3、幅>=0.5S。他属性を消さない |
| Future確認 | 正解表側だけ次10 active minutes・同日内。確認不足は項目別に打切り |

これらは再現用に固定した1つの定義であり、市場で最適と検証した値ではない。観測が足りないものや意味未識別を無理に既知Stateへ押し込まない。

## 次にすること — Gだけ

**次の別承認で、既存Developmentの入力確認・adapter検証を含む、5分ごとのFuture reference tableを作る。**

2,155 Opportunity ID、正確な前営業日とDaily lag、calendar、price basis、bar時刻・availability・欠測を照合する。入力adapterは採用定義を呼ぶだけで、そこでパラメータを変えない。75,059を期待row数にしない。
14:30/15:00以後も観測可能なcheckpointを保持し、未来確認の不足と現在の観測不足を分ける。市場の分類率・未知率・代表チャートを保存し、人間確認までSTOP。

| Gate | 状態 |
|---|---|
| D — 基準定義の採用整理 | **完了: mechanical-v1に一本化、source/hash固定** |
| G — 入力確認・5分正解表 | **次。未開始・別承認待ち** |
| C — 未来なしState認識 | BLOCKED |
| S — State × Signal | BLOCKED |
| E — BUY NOW / WAIT評価 | BLOCKED |
| Later — 必要な学習・Dictionary・別EXIT・Capital/Portfolio・protected評価 | BLOCKED |

## 不採用案・未反映パッチ

v0.2の仕様追記、repository helper/testは削除せず**不採用の参考履歴**へ。今後Gの基準として使わず、並行改良・再比較を今回の予定に入れない。mechanical-v1へv0.2の3S/20分/15分等を混ぜない。

会話内のv0.2修正85テストのZIP/レポートは履歴として保持。今回そのレポートを読んだが、パッチをactive scriptsへ適用していない。85はhelper部分の検証であり、採用mechanical-v1の93件へ合算しない。詳細hashと反映待ち解消方針は今回の採用決定に記録。
旧5+1、旧STEP2/3、Workローカル10/30bps試作も歴史資料のみ。新State正解表の教師として使わない。

## 継続方針・保護境界

Selector=WHAT、Entry=WHEN IN、EXIT=WHEN OUT。Frozen Selectorを変更せず、OpportunityをState/Signal/Qualityで再filterしない。Tで初回判断し、最初から必ず5分待たせない。
Signalは将来State解釈にもBUY/WAITにも直接入れ得るが、State別の増分価値はSで測る。Signalなし=候補廃棄にしない。SELLは別EXIT研究。
今回、実市場読取/正解表生成/因果認識/Signal/BUY-WAIT/学習/Dictionary/EXIT/Capital/Portfolio/新規provider/保護データ開封は実施しない。mainへmergeしない。
93合成PASSは既存Evidenceを確認した記録であり、今回の再実行やCI PASSではない。実相場での精度・UNKNOWN0・収益を保証しない。

## 毎回の日時付き記録

開始時にlatest HEAD/PR/この入口/採用manifest/承認範囲を読む。終了時はCURRENT更新＋WORK_LOG追記＋PRコメントに、`YYYY-MM-DD HH:MM JST`、開始SHA、実施/未実施、結果、検証範囲、方針、次の1 Gate、停止条件、保存SHAを残す。不明な過去時刻を推測しない。
保存前にremote再確認、同時更新を保全、force=false。保存後に再読。保存失敗はLOCAL_ONLY等と明示。旧ログは削除せず訂正は新日時で追記する。合成PASS/市場妥当性/因果性能/利益/CIを混同しない。人間確認前に次Gateを自動実行しない。

executionAllowed=false
brokerWriteAllowed=false
excelOrderWriteAllowed=false
rssOrderFunctionAllowed=false
liveTradingAllowed=false
paperTradingAllowed=false
automaticPromotionAllowed=false
productionUpdateAllowed=false
transmitted=false
