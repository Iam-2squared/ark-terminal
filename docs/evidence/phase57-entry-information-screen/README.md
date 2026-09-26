# Entry-time information screen — 2026-09-17

## Decision and scope

**No v2.4 implementation or candidate promotion.** The preregistered automatic screen returns `FAST_FAIL_KILL` because no field meets every progression condition. This is a kill of automatic model escalation under this eight-field screen, **not proof that Entry cannot improve or that every field is uninformative**. Several conditions are unassessable because the frozen v1 anchor population has too few within-symbol class comparisons. Those support limitations must not be described as demonstrated model failure.

This task extracted eight additional/recomputed causal fields from the same authorized 76 Development sessions (2024-09-17–2025-01-09), then measured single-field associations with saved outcomes. It did not train, predict with, or change any Entry model; did not add a trading filter; did not open Fresh/OOS; did not acquire prices. Frozen Selector/v1/EXIT/allocation/cash-ledger semantics remain unchanged. Historical conditional-universe and upstream in-sample limitations remain.

## Source and reproducibility

- Source head: `7599df41199a8c4d1ea86d5f3cb595edd599dd21`.
- Branch: `research/phase57-long-only-cash-equity`; PR #587 Draft/unmerged. main is not changed.
- Eight-field protocol precommit: `a42c8c52aa4f3048cf259065f97947402ef6a962`, before new feature/outcome associations were measured. Protocol is embedded in `scripts/phase57_entry_information_screen.py`.
- Existing encrypted Development minute artifacts: runs `34926225832`, `34936002178`, `34964031692`, eight checkpoints. Existing credential is used only for local checkpoint decryption in the authorized workflow, never printed or sent to a provider. Raw cache is purged after the run.
- Initial saved-evidence export: run `35182363612`, artifact `10480479336`.
- Causal feature reconstruction: run `35182861083`, artifact `10480949205`, `entry-information-features-35182861083`.
- Feature gzip SHA-256: `625afba25ae64faf20c97352b1a59c395d385d836f3cd133415e3f1e89b2e8cc`.
- Reproduced descriptive analysis: run `35183220791`, artifact `10480978007`, `entry-information-screen-result-35183220791`.
- Full result JSON SHA-256: `f8b250c901c64f7662d98db5272b75667fdd21889101bd87b2cb3e86e4a69521`.
- Local calculation and independent GitHub runner result are byte-identical. Complete feature/target/panel numbers are in result.json, including NULLs and reasons.
- Code: `scripts/phase57_entry_information_screen.py` and `scripts/analyze_phase57_entry_information.py`.
- Reproduction with a downloaded feature artifact: `python3 scripts/analyze_phase57_entry_information.py . /path/to/features.json.gz /new/path/result.json`.
- Artifact retention is finite (features 7 days, result 20 days). Retention is not permanent archival; the same pinned encrypted source can reproduce features while available.

## Denominators and methods

3,800 candidates / 760 decision times / 76 sessions. Primary descriptive population is the frozen 277 v1 ENTER anchors; 181 have strict30m outcomes, and 192 have the selected frozen-EXIT reference outcome under the current all-stream projection. This is not the former 173-common-comparator set or 166 actually cash-admitted trades.

First 16 sessions contain 45 anchors and are used only to establish feature direction; the following 60 sessions contain 232 anchors, split into four consecutive 15-session panels. This is not new OOS: the upstream models and historical outcomes have already been exposed. Direction selection is an outcome-based descriptive preprocessing operation, not a fitted Entry model. No model predictions or Entry thresholds were generated.

Primary outcomes are (1) fixed EXIT net reference return >0 and (2) strict30m D30>=5%. Supporting MFE>=3/5 and D30>=10 are descriptive only. Different fields/outcomes have different observed samples. Single-field AUC is a pairwise ranking statistic, not win rate or portfolio return.

Five fixed hash symbol groups are descriptive panels, not trained symbol-disjoint OOS models. Macro within-symbol AUC requires both classes with at least two observations and three eligible symbols; at most two profit symbols and one risk symbol qualified, so these macro results remain NULL. Initial16 anchors have only one severe-risk observation for most fields, so risk orientation cannot be established under the prespecified minimum-class rule. Reported risk AUCs below use raw increasing feature values and are **descriptive only**, not a passing directed-risk test.

## Eight fields and availability

| Field | Definition | Available /277 | Available /3800 |
|---|---|---:|---:|
| last5CloseLocation | (last completed C-L)/(H-L); zero range is NULL | 238 | 2721 |
| last5UpperWickFraction | (H-max(O,C))/(H-L); zero range is NULL | 238 | 2721 |
| trailing30MeanRangePct | Mean of six completed 5m (H-L)/decisionPrice*100; all six slots required | 197 | 2210 |
| trailing15ToPrior15TurnoverRatio | Observed actual turnover, last15m / preceding15m; all six 5m slots and numeric raw turnover required | 197 | 2210 |
| trailing15ObservedMinuteFraction | Observed regular-minute records /15; missing records are not zero-volume trades | 277 | 3800 |
| scoreChangeSincePriorSelection | Current frozen Ridge score minus earlier same-symbol/session selection score; no prior gives NULL | 33 | 1057 |
| priorSelectionCount | Count before current event, checked against existing source | 277 | 3800 |
| observedTurnoverVwapDistancePct | Price/(sum observed turnover / sum observed volume)-1, same-session prefix only | 277 | 3800 |

The VWAP field uses actual saved turnover/volume, not the earlier HLC3-volume proxy. It remains an observed-prefix VWAP: missing provider minutes need not be absent trades. Bid/ask/depth/fill probability and dated tick-size ratio were not available/audited and were not invented. Inverse price is not substituted for tick size.

## Main findings

### 1. Recent range contains descriptive adverse-risk information, but not a solution by itself

On 126 held-period v1 anchors with range and strict risk observable (19 severe, 107 non-severe), raw range versus D30>=5 has AUC **0.765371**. After diagnostic removal of the previously known concentration symbols 89180 and 57590, it is **0.756629** on 100 observations (12 severe /88 non-severe). This is removal for diagnostic sensitivity, not a blacklist or proposed trading rule.

Median pre-entry mean range is **6.707317%** in the severe cohort versus **4.166667%** in the non-severe cohort. Chronological panel AUCs: **0.571429 /0.703125 /NULL /0.893519**. The third panel lacks enough severe cases. The risk direction warmup and macro within-symbol support conditions remain unassessable.

Higher range also associates with MFE>=3/5 (AUC **0.603405 /0.671138** in their respective observed panels). Therefore simply rejecting high-range candidates may sacrifice upside. No such rule was tested, and no loss reduction / winner retention / incremental Entry improvement is claimed.

### 2. Turnover change is a weak profit-quality lead, sensitive to concentrated symbols

Last15m / prior15m turnover versus fixed-EXIT net-positive has oriented AUC **0.602352** on 138 held anchors (56 positive /82 nonpositive). The direction was fixed as increasing from the first16-session panel. Median ratio: **0.648145** in positive outcomes, **0.456172** in nonpositive outcomes; this describes relative turnover change, not necessarily acceleration above 1.

Chronological AUCs: **0.485714 /0.561688 /0.660287 /0.678125**. Four of five hash panels are above0.5. Removing 89180/57590 reduces the AUC to **0.546775** (110 observations), and the macro-symbol comparison lacks support. This does not pass progression criteria.

### 3. Other fields do not currently justify a new model

Held-period profit AUCs, direction frozen from first16 where supported:

| Field | Profit AUC | Observed N | Comment |
|---|---:|---:|---|
| last5CloseLocation | 0.561987 | 162 | Small separation; no macro-symbol proof |
| last5UpperWickFraction | 0.564773 | 162 | Temporal direction mixed |
| trailing30MeanRangePct | 0.467552 | 138 | Risk relation is not profit discrimination |
| trailing15ToPrior15TurnoverRatio | 0.602352 | 138 | Weakens to0.546775 after known-dominant removal |
| trailing15ObservedMinuteFraction | 0.459648 | 171 | Observability is not reliable profit quality here |
| scoreChangeSincePriorSelection | 0.589744 raw | 22 | Direction unestablished; 33/277 feature coverage |
| priorSelectionCount | 0.503521 | 171 | Approximately no ordering in this panel |
| observedTurnoverVwapDistancePct | 0.521690 | 171 | Little ordering in this panel |

The tests are single-feature screens; interactions, non-linear models and incremental value over existing predictors have not been tested. Overlap between distributions does not itself prove absence of useful information.

## Frozen-source / missing / safety checks

- 132 original source pins verified in the evidence-check workflow.
- 3,800 real feature snapshots unchanged when all post-decision source minutes are removed. Every used minute ends at or before its decision; no future path is used as an input.
- 406,901 raw minute records for selected symbols inspected across the fixed76 sessions. Raw missing volume=0 and missing turnover=0 **within these inspected records**. This does not imply complete minute coverage or audit all market records.
- Feature tests12 and analysis tests8 PASS. Separate local brute-force pairwise AUC verification:16 comparisons, maximum difference0.
- Existing old results and contracts not rewritten. No Selector/Entry/EXIT/allocation/cash-ledger logic changes. Full-stream unresolved335,300JPY position remains unresolved; no synthetic close or cash release.
- New predictive model fit0; new model prediction0; Entry threshold search0; Fresh/OOS/Prospective access0; new market-provider requests0 in this diagnostic; all nine execution safety flags remain false.

## Next decision

Do not automatically build v2.4 from this screen and do not extend to dozens of indicators. Preserve two observations: range tracks some adverse risk but also upside; turnover change has weak, concentration-sensitive profit ordering. A subsequent experiment, if separately authorized, must test incremental benefit with a frozen baseline and explicit support/coverage handling, not claim that these descriptive AUCs are already an improved Entry. No next model or trading gate is implemented here.
