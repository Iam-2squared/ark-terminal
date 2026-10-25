# Phase57 R52 cycle 2 — controlling handoff

Saved JST: 2026-09-27 23:20. Basis before closure: `0c3aa73b88d186062b5cd112633fadd179b0a930`. Branch: `research/phase57-long-only-cash-equity`; draft PR #587. This is **outcome-exposed Development research**, and neither new EXIT nor Capital is formally selected. The final machine-readable decision is [`FINAL_CLOSURE.json`](FINAL_CLOSURE.json).

## Disposition and exact execution

The former R52 Action [36320075928](https://github.com/Iam-2squared/ark-terminal/actions/runs/36320075928) stopped after three estimator fit calls because the OOF target-row boolean expression implemented the frozen specification incorrectly. Its artifact contains two serialized models and label support, but no saved candidate predictions, AUC, EXIT/Portfolio replay, or candidate scorecard. There was no candidate performance read that directed the correction. The earlier `INTEGRITY_ABORT` and evidence remain intact. [`PERFORMANCE_EXPOSURE_AUDIT.json`](PERFORMANCE_EXPOSURE_AUDIT.json) and [`RETEST_DISPOSITION.json`](RETEST_DISPOSITION.json) permit a **separate** cycle under the user's authorization. The corrected source changed only the mask parentheses and its regression test, retaining the frozen R52 hypothesis, labels, features, action, model, folds, purge, execution, and Gate. The original protocol SHA256 is `64d30cf679939172e6aca0e9dc4212d7e663fea32114862289ca969009c4206e`.

The new [`INTEGRITY_CHECKPOINT.json`](INTEGRITY_CHECKPOINT.json) and 56-test zero-fit CI [36324340624](https://github.com/Iam-2squared/ark-terminal/actions/runs/36324340624) preceded performance. The new finite [Action 36324570199](https://github.com/Iam-2squared/ark-terminal/actions/runs/36324570199), job `108634717782`, ran once at exact execution SHA `c6c445b8c85a50b7179c62b9d8a5f79314f29dcd` from 2026-09-27 14:03:55 to 14:08:47 UTC. It completed 16 estimator fits, 16 train-only imputers, 16 train-only scalers; all IM/R1 × control/A/B chronological cash replays; and two byte-identical replays from the **same saved OOF prediction**. Artifact ID `10933203911`, ZIP SHA256 `92536baa192907189b7a51a4f9903d08df4bad16b44edc4bc6f3c705b60294d1`. The 8 ordered parts and exact reassembly instructions are in [`RESULT/ARTIFACT_REASSEMBLY.json`](RESULT/ARTIFACT_REASSEMBLY.json). Models, predictions, six full ledgers, A/B Layer A, curves, and daily/equity files are inside. The archived R50-A control ledger is byte-identical.

Independent [`OOF_AUDIT.json`](OOF_AUDIT.json) passed: 381,223 disjoint scored rows overall, 272,803 in the 24-session window, eight whole-session fold/arm slices, exact model and prediction hashes, 0 additional fits, and no candidate performance read until the OOF audit. Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0, scikit-learn 1.8.0. The additional [`INDEPENDENT_CLOSURE_AUDIT.json`](INDEPENDENT_CLOSURE_AUDIT.json) independently reconciles all six ledgers, lot/slot/cash, cash conservation, realized PnL, mark knownAt, buckets and null EOD. Independent **retraining** byte identity has not been tested; the proven identity is deterministic replay from the saved predictions. The earlier Capital v3 prediction-byte discrepancy is not claimed resolved.

## Layer B — complete 24-session chronological integration

Dates 2025-07-22–2025-08-25, 35 calendar days, **24 scheduled trading sessions**, ¥1,000,000 initial cash, 100-share lot, MAX3, exact saved CAPITAL_V3_B rank and R37 sizing. A/B use their new EXIT; control uses R50-A. Each starts anew and scans **all Frozen Entry events**, with actual exits releasing cash before same-time Entry. The number of buys is a replay result, not fixed at 79.

| IM metric | R50-A control | R52 A CORE | R52 B PREFIX/PATTERN |
|---|---:|---:|---:|
| Purchases / confirmed exits | 79 / 79 | 40 / 39 | 42 / 41 |
| Initial / Replacement | 72 / 7 | 6 / 34 | 6 / 36 |
| Purchases/day mean; median; p75; max | 3.29; 3; 4; 4 | 1.67; 0; 0; 22 | 1.75; 0; 0; 25 |
| Funded ≥5%; ≥10% | 27; 15 | 11; 3 | 12; 3 |
| ≥5% reach, same 158 opportunities | 27/158 = 17.09% | 11/158 = 6.96% | 12/158 = 7.59% |
| Replacement upside mean; median | 1.93%; 1.79% | 2.87%; 1.92% | 2.95%; 2.16% |
| Replacement ≥5%; ≥10% | 0/7; 0/7 | 8/34; 1/34 | 9/36; 1/36 |
| Replacement closed PnL | −¥123,935.66 | +¥20,325.01 | +¥19,041.26 |
| Valid-mark time-weighted utilization | 76.84% | 42.73% | 46.93% |
| Valid-mark share of time at ≥80% | 58.29% | 23.08% | 12.92% |
| Valid mark minutes / 7,800 scheduled | 7,779 / 7,800 | 650 / 7,800 | 650 / 7,800 |
| Time at MAX3, scheduled minutes | 6,994 / 7,800 | 196 / 7,800 | 111 / 7,800 |
| Mean holding, wall minutes | 326.63 | 29.13 | 30.83 |
| Certified EOD / null EOD | 24 / 0 | 1 / 23 | 1 / 23 |
| Closed trade PF; win rate | 0.814; 44.30% | 2.061; 56.41% | 0.993; 51.22% |
| Closed loser drag; sell costs | −¥606,533.36; ¥10,987.24 | −¥37,629.11; ¥5,595.10 | −¥65,957.06; ¥5,887.04 |
| Closed realized PnL | −¥112,868.99 | +¥39,912.60 | −¥471.14 |
| **Final Equity / 24-day Return** | **¥887,131.009125 / −11.2869%** | **null / null** | **null / null** |
| EOD MaxDD | −16.12% | null | null |
| Daily arithmetic / median / geometric | −0.3938% / −1.2299% / −0.4978% | null / null / null | null / null / null |

The control buys on all 24 sessions. Both new IM policies buy on July 22 and 23 only. Both retain `2025-07-23|62650|883` (100 shares, ¥229,914.90 cost) after a terminal auction that cannot be confirmed; its subsequent cross-session mark/corporate-action continuity is not allowlisted. From July 24 onward, the fixed R37 equity-based sizing rejects **759 later Entry intents** as `MISSING_FRESH_MARK_UNRESOLVED_SIZING`. A has ¥809,997.70 cash at the end, B ¥769,613.96; **neither cash balance is equity**. We cannot release unresolved proceeds, invent a terminal fill, or use a future price to produce 24-day returns. The 42.73%/46.93% utilization values cover only 8.33% of scheduled minutes and do not certify the 80% target. Concentration also changed: the most active session carries 54.93% (A) / 60.20% (B) of buy notional, versus 5.63% control.

Miss attribution is exclusive: control IM `CAPACITY_FULL` 123, `INSUFFICIENT_CASH` 1, `RANK_LOSS` 6, `OTHER_CAUSAL` 1; A `UNRESOLVED_CASH_LOCK` 146, `CAPACITY_FULL` 1; B `UNRESOLVED_CASH_LOCK` 146. Moving misses from capacity to unresolved valuation is not improved reach. All bucket details, including Initial/Replacement/Combined and UNKNOWN/CENSORED, are in [`RESULT/scorecard.json`](RESULT/scorecard.json) and the six `RESULT/*_buckets.json` files.

## Layer A — same original Entry ID and quantity, diagnostic only

For the original **79 IM** funded positions with unchanged Entry and quantity, control PnL is −¥112,868.99, A −¥47,950.50, B +¥8,721.15. That result excludes the changed funded set and must **not** be called a Portfolio Return. The old 27 positions with ≥5% later upside generated +¥329,595.75 under R50-A; under A they yield +¥9,589.10, under B +¥61,163.30. Their mean Net falls **4.896% → 0.231% / 0.962%** and median Capture **30.26% → −0.87% / 6.94%**. In the 15 ≥10% cohort, mean Net falls 7.468% → 0.340% / 1.145%. The 17 positions with 3–5% upside improve from −1.089% mean Net to +0.298% / +0.206%; the 20 below 1% improve from −4.660% to −0.404% / −0.943%. These strata explain how loss containment and premature winner exit coexist.

At candidate sell intent for the old cohort, R50-A would still report `UNARMED_HOLD` for 57 (A) / 43 (B), `UNCERTIFIED_HOLD` for 18 (A) / 27 (B). The formerly blocked decision path did open. The new policy often sells before major subsequent upside and materially reduces winner capture. See [`LAYER_A_SAME_QUANTITY_COMPARISON.json`](LAYER_A_SAME_QUANTITY_COMPARISON.json) for all ten buckets, costs, PF, holdings, and R50 reasons.

## Cash recycling and currency attribution

Versus the same control funded IDs, A adds **34** (≥5%: 8, ≥10%: 1) and displaces **73** (≥5%: 24, ≥10%: 13); B adds **35** (≥5%: 9, ≥10%: 1) and displaces **72** (≥5%: 24, ≥10%: 13). The closed new-only PnL is +¥20,325.01 for A and +¥15,146.14 for B. In closed-PnL accounting, the identity `common-ID difference + new-only PnL − control-only PnL` equals +¥152,781.59 for A / +¥112,397.85 for B. These **are not final-equity differences** because each candidate has an unresolved open position. The exact ID sets, quantities, winner changes, and signed terms are in [`RECYCLING_IDENTITY_ATTRIBUTION.json`](RECYCLING_IDENTITY_ATTRIBUTION.json). The remaining-upside High is evaluator-only; it was not an executable sell price or a buy input.

## R1 and the final decision

| R1 metric | R50-A control | R52 A | R52 B |
|---|---:|---:|---:|
| Purchases / exits; Initial / Replacement | 32 / 31; 30 / 2 | 103 / 102; 7 / 96 | 211 / 210; 21 / 190 |
| Funded ≥5%; ≥10%; reach ≥5% | 12; 8; 12/143 | 17; 8; 17/143 | 43; 20; 43/143 |
| Replacement median upside; ≥5% | 7.74%; 1/2 | 1.82%; 13/96 | 1.86%; 35/190 |
| Replacement confirmed PnL | +¥44,894.45 | +¥9,562.67 | −¥50,548.70 |
| Valid-only utilization; coverage | 70.33%; 41.44% | 34.88%; 20.83% | 46.72%; 49.38% |
| Certified EOD / null EOD | 9 / 15 | 4 / 20 | 11 / 13 |
| Final Equity / full-period Return / daily rates | null | null | null |

R1 control retains its unresolved August 4 auction. A has an unresolved July 28 position; B a different unresolved August 6 position. R1's higher B trade count and reach do not establish full portfolio profitability. No invalid EOD was changed to zero or carried forward.

The **unchanged frozen Gate** requires all 24 IM EOD equity points, positive Final Equity above ¥1,000,000 and the control, ≥5% reach at least 17.09%, and at least 13 funded ≥10% opportunities, together with the stated Replacement support/quality checks. Both candidates pass the three Replacement checks but fail the full EOD, economic, ≥5% reach, and ≥10% checks. The final verdict is **NO_SELECTION_STOP** for R52 cycle 2. The separate user goal of ≥80% capital utilization is **UNVERIFIED** for the candidates because 91.67% of scheduled minutes lack valid marks. Neither R50-A nor CAPITAL_V3_B is retrospectively selected. See [`RESULT/selection.json`](RESULT/selection.json) and [`FINAL_CLOSURE.json`](FINAL_CLOSURE.json).

One audit-report field needs explicit correction. The immutable Action's `independent-audit.json` reports `cashMinJpy` using string rather than numeric ordering and misleadingly shows ¥1,000,000. Its **cash >= 0 assertion** independently used `Decimal` and is valid. The appended closure audit computes numeric minima: IM control ¥22,681.09, A ¥30,750.89, B ¥17,131.43; all remain nonnegative. No trade, Gate, or verdict changed. This is preserved as an append-only reporting correction, not an overwrite of the Action artifact.

Safety9 are all false; protected partitions newly opened 0, provider requests 0, Selector/Entry/Capital changes 0, no broker/Excel/RSS orders or live/paper/production action. The next research cycle, if any, needs its own causal valuation-continuity proof and separate performance-blind contract. Do not relabel the certified closed PnL as the missing 24-day Portfolio Return, refit this frozen R52 A/B after seeing outcomes, or change the frozen Capital sizing to force a return figure.
