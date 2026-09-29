# Phase57 Post-PRR Phase A — Controlling Handoff

保存：2026-09-29T12:25:04+09:00 / Repo `Iam-2squared/ark-terminal` / branch `research/phase57-long-only-cash-equity` / draft PR #587 / 開始HEAD `4552d53d7984850c4de76802a63c272365e1dbd6`。

## 終了判定

**Phase A完了、次実験仕様は草案のみ。** PRRの`NO_SELECTION`、`selectedDevelopment=null`、`adaptiveDevelopmentOnly=true`、`productionReady=false`を維持する。旧closure・旧PnLは不変。新fit 0、新policy Replay 0、provider 0、保護partition 0、発注 0、main merge 0。

## 再開時に優先する原本

1. `PHASE_A_PRECOMMIT.json` (SHA-256 `25e6f97b191a8d343a9361f73e48d179dd4ddcd94a229cac5f55c46b210381e9`) と `START_AUDIT.json`。原本hashとPR状態を再照合する。
2. `ACCOUNTING_RECONCILIATION_RECEIPT.json`、`ACCOUNTING_RECONCILIATION_ROWS.jsonl.gz`。R34はEntry原価basisの売却費用。Primaryと全100株worldを混ぜない。
3. `A0_CENSUS.json` (SHA-256 `cc7280eead274f00e90ec1c69d3dfed479c2af11506a0b247cd54937c64700c6`) と **append-only intent訂正** `A0_INTENT_SEMANTICS_CORRECTION.json` (SHA-256 `d235c2a49efcc2c6ef57d0b89e7144106e27047b5c304fb3c109098a4a1aab2b`)、`COMPARISON_MASK_ROWS_INTENT_V2.jsonl.gz`。A0初版の`control_intent_time_known`はMODEL_EXIT限定だった。訂正版ではR50強制終端の判断時刻も別クラスで数える。fill時刻は混同しない。訂正はA1閲覧後に行った事実をExposure ledgerに保存。
4. `A1_ANALYSIS_SPEC.json` (SHA-256 `8dc2bd97dcc4a7c209051dc964ac01c407240880a0d5e82f32d78a1407ad6ed0`)、`A1_RESULTS.json` (SHA-256 `acb3ef902ab0a7411f166709b4e2dfb647ac7f0ca2d6353c19dfe2b35b966dd6`)、`A1_INTENT_SEMANTICS_SUPPLEMENT.json`。全pairedでΔ=0を維持。IM/R1は別Entry世界、Primaryは部分集合。
5. `INDEPENDENT_AUDIT.json`と`INDEPENDENT_INTENT_AUDIT.json`はPASS。読みやすい表と図は`REPORT-ja.md`、`REPORT_ACCOUNTING_METRICS.md`、`REPORT_INTENT_CORRECTION.md`。
6. `NEXT_EXPERIMENT_SPEC_DRAFT.json` (SHA-256 `4adf2377315d139642ce1b43f9e1aa6d790d9290d9d87da0e35d142e62828223`)。案Bの対象route、最小support、tail許容度、実験Gate、学習・Replay予算は未確定。

## 結果の要点

全100株のCCMG−R50は同じpaired maskでIM 728件／−¥254,400、R1 706件／−¥168,700。凍結route−R50はIM +¥65,500、R1 −¥13,200。R1の5–10%帯だけでroute差−¥41,500、≥10%は−¥19,800。円差と平均Net％は別のGateであり、IM全Entry Winnerでは円差が正でも平均Net％が負。

CCMG初回intentはIM 376、R1 343。両outcome既知のintentはIM 296、R1 263。既存DEFENSIVE routeに限るとIM 55、R1 68。guard traceのas-of確認は可能だが、完全なstage-2 runtime特徴snapshotは0。別の独立Development期間の両EXIT教師も未確認。Potentialの順位情報は保持し、EXIT差分価値の証明とはみなさない。

## 次の境界

案Bは初回SELL_INTENTで一度だけ売却を許可／R50継続を判断する草案。条件と予算を根拠付きで固定した新Precommitができるまで、実装、fit、calibration、Replay、保護partition、provider、発注、mergeへ進まない。
