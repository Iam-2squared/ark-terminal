# Phase57 LONG-only — 現在の方針・次作業

更新日: 2026-09-21 JST
対象: Iam-2squared/ark-terminal / research/phase57-long-only-cash-equity / PR #587
開始時に確認したremote HEAD: `2ef307a31bea156110dc8b9181b7582373b2887e`

## 現在地点

**5-Minute Entry State Definition v0.1 の設計案を保存。STOP FOR HUMAN REVIEW。**

仕様の設計案作成は完了。ただし人間承認・機械的な判定パラメータ固定は未完了。
`DESIGN_DRAFT_COMPLETE / NOT_LABEL_READY / NO_MEASUREMENT`

- [設計仕様](phase57-five-minute-entry-state/STATE_DEFINITION_v0.1.md)
- [今回のソース監査](phase57-five-minute-entry-state/SOURCE_AUDIT_2026-09-21.md)
- [作業記録・次回チェック](phase57-five-minute-entry-state/WORK_LOG.md)

これは旧STEP 1/2を改善する研究ではない。旧5+1の名前・優先順位・閾値・終日ラベルを新Stateの正解に流用しない。旧Evidenceは歴史記録として残す。

## ユーザー承認済みの方針

SelectorはWHAT、EntryはWHEN IN、EXITはWHEN OUT。
Frozen SelectorのOpportunityを再filterしない。Signal/State/Qualityを理由に候補を捨てない。

将来のEntryは選出時点Tで現在状況を評価し、BUY NOWまたはWAIT。最初から5分待つ仕様にはしない。WAIT時は5 active trading minutes後に再評価する。

材料は最新5分を構成するclosed 1m、Today Open→NOW、前営業日のobserved 1m、D-5〜D-1の日足。前日分足は価格構造・重要水準・終盤の流れを解釈するために使う。1分ごとに最終Stateを決める設計にはしない。

SignalはState解釈にも、将来のBUY/WAITにも直接利用し得る。ただしState別の増分価値を別Gateで検証する。今はSignal測定をしない。保有後SELLは将来の別EXIT研究であり、今のEntryには入れない。

## 新ロードマップ — 一度に1 Gate

| Gate | 内容 | 現在 |
|---|---|---|
| D | State Definition: 意味、時刻、参照構造、境界、パラメータ契約 | v0.1設計案保存、人間確認待ち |
| G | 固定した定義で5分ごとのFuture-assisted reference labels作成 | BLOCKED |
| C | 未来を隠した同一時点・同一定義のCausal Recognition | BLOCKED |
| S | State × Signalの増分情報を測定 | BLOCKED |
| E | State + Signal + ContextによるBUY NOW / WAIT評価 | BLOCKED |
| L | 必要なEntry Learningを人間判断で検討 | BLOCKED |
| Later | Dictionary増分 → 別NEW LONG EXIT → Capital/Portfolio → protected evaluation | BLOCKED |

**次にすることはDの設計レビューのみ。**
3軸の表現（Direction / Structure / Phase）、Breakout等を別Eventにする案、最新5分の終端時刻をState時刻とする案を人間が確認する。
その後も同じD内で、未固定のSwing scale・Range条件・Future確認期限を1つの機械的契約にする。市場データの再分類・成績による閾値選択はしない。
Dを人間が承認し、parameter lockとlabeler仕様が完成するまでGへ進まない。D承認はGの自動実行許可ではない。

## 停止中・不採用の系統

`docs/evidence/phase57-path-state-vocabulary-v1/DECISION.md`、`docs/evidence/phase57-causal-state-recognition-v1/PROTOCOL.md`、`scripts/phase57_causal_state_recognition_v1.py`の旧STEP 2/3系統は、新研究を進める根拠にはしない。旧ファイルは変更しない。この文書の新方針を優先する。

Workが報告したローカル4 commits（be52f30 / b045dc0 / 182d2ab / 66fc3c2）、75,059区間＋T+0 2,155行、10bps/30bps試作ラベルは**未承認prototype**として保持。報告値であり、今回ローカル実体を監査・採用していない。削除・自動push・rebase・正解表への昇格をしない。75,059は新仕様の期待行数にしない。

## 毎回の作業終了時に必須のGitHub記録

ユーザーの2026-09-21指示: **作業を終えるたびに、この後することと方針をGitHubへ記録する。**

1. 開始時にremote HEADとPR、現在の承認範囲を確認する。
2. 終了時にこのCURRENT入口を更新し、WORK_LOG.mdへ追記する。旧記録を消さない。
3. 今回したこと/していないこと、変更ファイル、開始SHA、保存commit、Evidence、検証範囲、CI、未解決点、Safety、次の1 Gate、再開条件を残す。
4. 実施済み、設計提案、人間承認、コード完成、計測完了、科学的PASSを区別する。docs-onlyや専用CI PASSをPR全体GREENと呼ばない。
5. remote再読で保存を確認する。認証失敗ならLOCAL_ONLY等と明記し、GitHub保存済みと言わない。
6. 最後にPR #587へ当該保存commitと方針・次作業への参照を残す。自分自身のcommit SHAを本文に埋めるためだけの循環commitは不要。正確な保存SHAはGit履歴/PRコメントで記録できる。
7. 人間確認前に次Gateへ進まない。会話終了後に自動で進む作業や監視を今回作っていない。

## 保護境界

LONG-only / cash-equity-only。Frozen Selectorのmodel/score/rank/universe/選出周期/価格定義を変更しない。
新規市場データ取得、Common Holdout/Fresh/OOS/Prospective開封、旧測定再実行、Signal/BUY-WAIT/Entry学習/Dictionary/EXIT/Capital/Portfolioを今回実施しない。mainへmergeしない。

executionAllowed=false
brokerWriteAllowed=false
excelOrderWriteAllowed=false
rssOrderFunctionAllowed=false
liveTradingAllowed=false
paperTradingAllowed=false
automaticPromotionAllowed=false
productionUpdateAllowed=false
transmitted=false
