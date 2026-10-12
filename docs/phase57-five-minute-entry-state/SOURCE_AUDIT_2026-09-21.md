# Source / Scope Audit — 2026-09-21

## 監査範囲

対象repo: Iam-2squared/ark-terminal
branch: research/phase57-long-only-cash-equity
PR: #587、開始時open / Draft / unmerged
開始HEAD: `2ef307a31bea156110dc8b9181b7582373b2887e`
base tree: `7291c7e6534d8c5650946633c02ab0f4d28126e2`

今回の監査はコードと仕様を読む静的監査。市場データの測定や過去Stateの正解判定はしていない。新文書の親snapshotは上記SHAで固定する。branchの値を未来の再開時に決め打ちしない。

## 読取ソースと確認したこと

| ID | パス | Git blob SHA | 確認できたこと |
|---|---|---|---|
| S1 | scripts/phase57_causal_entry_state.py | 165be0b905b402aac89bf9df08bcc7ac57e79c39 | daily_context、state、efficiency、dominant、timingの既存実装 |
| S2 | scripts/phase57_entry_timing_signals.py | 18b17e9974540ddb793bff3da77a200148839998 | regular/window/observed_vwap/activity、6 Signal定義、時刻と欠測契約 |
| S3 | docs/evidence/phase57-path-state-vocabulary-v1/DECISION.md | e285b0a1f8438669ada9d57ebe4c9f21052a7999 | 旧Vocabulary決定書。新ゼロベース定義を実装した文書ではない |
| S4 | scripts/phase57_causal_state_recognition_v1.py | b1098723945e1f83b89795537d3dad5b875a6e0a | 保存checkpointを終日旧predicate等と比較する旧STEP3実装 |
| S5 | docs/evidence/phase57-causal-state-recognition-v1/PROTOCOL.md | ed45d4f84b14dd642ddab9e85a2fbcfe8eb06a99 | 旧T+0/5/10/15/30計画。新しい全5分state定義の計測contractではない |

上記ファイルは全て開始HEADをrefに指定してGitHub connectorから読んだ。S2は冒頭〜240行の範囲を読んだ。blob SHAはファイル全体を識別するが、範囲外の全コードをレビューした主張ではない。

## 重要な区別

### 前日分足
S1はprevious配列を受け取り、previousReturn、previousRange、previousEfficiency、previousCoverageを計算する。PULLBACKスコアには前日最初の観測openとの比較がある。
この範囲では前日のstructural swing列や終盤構造をStateへ統合していない。したがって「前日分足を取り込んでいる」ことと「前日構造を十分理解できている」は別。
S2には前日観測高安、前日同時刻活動量との比較がある。ただし新State側へそのまま組み込まれているとは限らない。

### 時間窓と尺度
S1のlocal主窓は5/10本、High/Low隣接比較・反転は10本に対する定義。5本化しても同じ回数閾値を維持してよい根拠はない。
S2のwindowは同一half-session内の予定stampを完全一致で要求する。S2のobserved_vwapは観測足数/予定足数のcoverage判定であり、期待出来高に対するcoverageではない。旧説明の語感を新仕様へ引き継がない。
S2のregularは2024-11-05を境に終了minuteを変え、通常ザラバと終端を分離している。新仕様でも日付別calendar・auction分離は必要だが、コード変更は今回しない。

### 因果性の意味
S1/S2にはfuture bar拒否条件がある。ただし保存barの時刻制約だけではhistorical knownAt/配信遅延/revisionを検証したことにはならない。
新Stateは設計段階であり、因果認識が既に成功したとは主張しない。

### 旧STEP3の対象
S4は旧終日predicateを各checkpointのtruthに使う。これはその日全体でRecovery条件を満たすか等との関連を調べるもので、同じ時点にRecovery中だったかの正解表ではない。
新研究では「State(t)」「次5分」「当日終日」を分離し、旧プログラムや結果を新State認識のPASSに使わない。S4/S5を修正・実行していない。

## Work停止報告 — 未検証のユーザー提供状況

ユーザーが共有した停止報告では、Workは次をローカルに保持し、pushは失敗した。

| 項目 | 報告値/内容 |
|---|---|
| local commits | be52f30 / b045dc0 / 182d2ab / 66fc3c2 |
| Opportunity | 2,155 |
| 生成済みprototype | 75,059区間＋T+0 2,155行 |
| 完全観測prototype区間 | 27,410 |
| 仮定義 | 旧Vocabulary、Direction/Reversal 10bps、もみ合い30bps |
| tests | 人工19件、照合、再実行hash比較と報告 |

今回そのWorkローカル環境・生成物を直接監査していない。remote未反映という停止報告を開始remote HEADと整合確認しただけで、全ローカルcommitの存在・内容の検証ではない。
新Stateの正解、期待分類数、期待row数、閾値にはしない。削除・上書き・追加測定・自動pushしない。

## 外部一次資料 — 制度/操作の確認だけ

State語彙の実証根拠としては使っていない。参照日2026-09-21。

- E1: JPX「内国株の売買制度・売買立会時」 https://www.jpx.co.jp/equities/trading/domestic/01.html
  前場/後場の時刻を確認。
- E2: JPX「システム概要（arrowhead）」 https://www.jpx.co.jp/systems/equities-trading/01.html
  ザラバ終了、プレ・クロージング、引け板寄せを別フェーズとする根拠を確認。
- E3: GitHub Docs「Skipping workflow runs」 https://docs.github.com/en/actions/how-tos/manage-workflow-runs/skip-workflow-runs
  docs-only保存でpush/pull_request型Actionsを新規発火させないため[skip ci]を使用。全イベント/既存runの停止を保証するものではなく、Pendingや未実行をPASSと呼ばない。

## 変更境界

追加対象はdocs/PHASE57_LONG_ONLY_NEXT.mdとdocs/phase57-five-minute-entry-state/の文書だけ。
既存scripts、.github/workflows、provider、モデル、旧Evidence、live circuitを変更しない。新規Actionsの起動/再実行や古い研究の測定は要求しない。CI実行結果と仕様設計レビューは別に報告する。

## Safety契約

executionAllowed=false
brokerWriteAllowed=false
excelOrderWriteAllowed=false
rssOrderFunctionAllowed=false
liveTradingAllowed=false
paperTradingAllowed=false
automaticPromotionAllowed=false
productionUpdateAllowed=false
transmitted=false

これは本作業の保護契約。文書内にfalseと記述したことを、稼働中の全環境の実測監査と混同しない。実行系コードを変更・実行していない。
