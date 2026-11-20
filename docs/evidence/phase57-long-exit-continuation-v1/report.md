# Phase57 LONG EXIT Development Final — 2026-09-16 JST

Selected: **LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1**. Status: **LONG_EXIT_DEVELOPMENT_FINAL_SELECTED_NOT_VALIDATED**. One research handoff candidate, not an independent superiority finding or trading approval.

Repo `Iam-2squared/ark-terminal`, branch `research/phase57-long-only-cash-equity`, PR #587. Start head `3a42db5b1ca000308bd91b3dbda9ac455bdfa956`; main checked `b7801ce2c13772cbc3f5b51506819c119fe868ea`. This report belongs to its publishing commit; final-head CI is recorded by GitHub checks.

All 76 sessions (2024-09-17–2025-01-09) are direct Entry Development, IN-SAMPLE, outcome-exposed Historical reuse. Frozen 277 ENTER identities are retained. Common complete-case comparison N=173; 104 remain censored/unpaired, without replacement. Selected standalone availability is 192, which is **not** used against a 173-trade baseline. Informative missingness/complete-case selection may limit generalization.

## Design and causal execution semantics

The prior v5 remains V5_LONG_MEASUREMENT_BLOCKED: its unavailable historical v4 continuation has not been fabricated. This is explicitly new LONG Development research inheriting BAR5 Defensive/Reclaim and replacing continuation. No v3/v4 performance replay or new analog pool was run.

| State/input | Rule |
| --- | --- |
| firstCloseNonAdverse | CONTINUATION; zero is non-adverse |
| firstCloseAdverse | DEFENSIVE |
| reclaim | completed CLOSE return >=0 by bar5 inclusive; enter CONTINUATION, reset decline streak |
| noReclaim | exit at completed bar5 reference close |
| continuation | exit after two consecutive strictly lower completed CLOSEs; equal/rising resets |
| maxHolding | 12 expected trading bars or shorter calendar-known remaining regular slots |
| costPct | 0.0500 |
| missing | CENSOR before exit; do not fill |
| fillSemantics | COMPLETED_CLOSE_REFERENCE_ONLY_NOT_GUARANTEED_EXECUTION |


The first completed trading bar uses CLOSE >= Entry reference as non-adverse, including exactly flat. Negative enters DEFENSIVE; reclaim by BAR5 inclusive resets the decline streak. Continuation exits after two consecutive strictly lower completed CLOSEs; equality or increase resets the streak. Both initial non-adverse and reclaimed cohorts use this same rule. A pre-existing Fixed12/calendar cap bounds every candidate. No symbol/sector exceptions.

Inputs are observed completed CLOSE and past state only. Future HIGH/LOW/MFE/MAE are evaluator-only. HIGH/LOW order within a bar is UNKNOWN_INTRABAR_ORDER and never inferred. Decisions at a completed CLOSE are valued at that same reference CLOSE, **not a proven executable fill**. Latency, subsequent tradable price and slippage remain integration work. Round-trip cost = 0.05 percentage point for all arms.

Five-minute expected trading slots skip lunch; clock holding time includes lunch. No overnight carry. Calendar-known shortened sessions cap before the regular-session boundary. Missing expected bars censor before an exit; missing bars after an already emitted exit do not change that exit. No forward-fill/interpolation/provider substitution. The inherited post-November 15:25/auction gap is not silently repaired. Session-End is diagnostic only on 41 complete paths, not a main comparison arm.

## Candidate family and selection

Before the candidate replay, contract.json fixed only three research candidates: BAR5 + inherited Fixed12 continuation; BAR5 + half of observed positive completed-CLOSE peak giveback; BAR5 + two consecutive lower CLOSEs. The half ratio and two-confirmation count are explicit simple design assumptions, not calibrated optimums. They were not swept or changed after the replay. Contract and outputs are published together; their generation order is local, not a separately timestamped remote preregistration.

| Component | Predeclared ordinal-rank weight |
| --- | --- |
| tail | 2 |
| p05 | 2 |
| worst | 2 |
| winner3 | 2 |
| winner5 | 2 |
| pf | 1 |
| dd | 1 |
| median | 1 |
| capture | 1 |
| concentration | 1 |


Lower weighted rank loss wins, ties by predeclared simplicity order. Net sum is not the selection objective. This is a Development design choice with subjective weights, not statistical proof.

| Candidate | Weighted rank loss |
| --- | --- |
| BAR5_FIXED12 | 18 |
| BAR5_TWO_LOWER_CLOSES | 3 |
| BAR5_CLOSE_PEAK_HALF | 14 |


## Post-entry path diagnostic

| Cohort | All 277 | Paired N |
| --- | --- | --- |
| A_FIRST_BAR_NON_ADVERSE | 189 | 125 |
| B_ADVERSE_RECLAIM_BY_BAR5 | 33 | 28 |
| C_ADVERSE_NO_RECLAIM_BY_BAR5 | 25 | 20 |
| D_PATH_INCOMPLETE | 30 | 0 |


A includes 135 strictly positive and 54 flat first bars. B=33 reclaim, C=25 no reclaim, D=30 incomplete. First-bar observation uses the next trading bar: 250 observed; strict wall-clock +5m availability below is a different definition.

| Wall-clock horizon | Available N | CLOSE median % | MFE median % | MAE median % | Giveback median pp |
| --- | --- | --- | --- | --- | --- |
| 5 | 225 | 0.3236 | 1.6279 | -0.1729 | 0.6711 |
| 10 | 212 | 0.4389 | 2.2005 | -0.5847 | 1.3356 |
| 15 | 206 | 0.1902 | 2.5568 | -0.8836 | 2.0168 |
| 20 | 196 | 0.2991 | 2.5992 | -1.0555 | 2.1987 |
| 25 | 193 | 0.3066 | 2.7512 | -1.2961 | 2.2727 |
| 30 | 181 | 0.5587 | 3.3333 | -1.5337 | 2.2767 |
| 45 | 156 | 0.0000 | 3.4739 | -1.7610 | 3.1250 |
| 60 | 145 | 0.0000 | 3.5955 | -1.8277 | 3.3450 |
| SESSION_END | 41 | -1.4038 | 3.5117 | -4.7872 | 5.7143 |


Horizon denominators differ; these are not paired duration improvements. path-diagnostic-ledger.json preserves per-ENTER returns, observed running extrema/update times, first-positive/reclaim/threshold-hit times and missing status.

| Cohort | 30m N | 30m CLOSE median | 30m MFE median | 60m N | 60m CLOSE median | 60m MFE median |
| --- | --- | --- | --- | --- | --- | --- |
| A_FIRST_BAR_NON_ADVERSE | 136 | 0.9677 | 3.9179 | 108 | 0.3456 | 4.3961 |
| B_ADVERSE_RECLAIM_BY_BAR5 | 24 | 0.5447 | 2.3727 | 19 | 0.2597 | 2.6790 |
| C_ADVERSE_NO_RECLAIM_BY_BAR5 | 21 | -3.3516 | 0.3356 | 18 | -4.6778 | 1.0780 |


Initial non-adverse paths have more upside than reclaimed paths; no-reclaim paths have materially negative subsequent CLOSE medians. These observations justify separating Defensive from Continuation, but not automatic early liquidation of every adverse trade or assuming recovery from deep losses.

## Winner timing (post-selection diagnostic)

This supplemental table was generated after selection, and was not a selection input. Available MFE means the inherited Fixed12/calendar window, not all-day maximum or attainable profit. Longer-bar rows drop calendar-shortened cases; denominators are explicit.

| Bar | Available N | Mean observed/full-window MFE fraction | +3 first hit by bar | +5 first hit by bar |
| --- | --- | --- | --- | --- |
| 1 | 173 | 0.5661 | 48/101 (47.5248%) | 29/64 (45.3125%) |
| 2 | 173 | 0.7154 | 69/101 (68.3168%) | 42/64 (65.6250%) |
| 3 | 173 | 0.7817 | 78/101 (77.2277%) | 49/64 (76.5625%) |
| 4 | 173 | 0.8274 | 83/101 (82.1782%) | 55/64 (85.9375%) |
| 5 | 173 | 0.8736 | 86/101 (85.1485%) | 57/64 (89.0625%) |
| 6 | 173 | 0.9106 | 94/101 (93.0693%) | 59/64 (92.1875%) |
| 9 | 170 | 0.9606 | 96/100 (96.0000%) | 63/64 (98.4375%) |
| 12 | 170 | 1.0000 | 100/100 (100.0000%) | 64/64 (100.0000%) |


The bar6 snapshot sees about 91% of the reference-window MFE on average, but misses some +3/+5 first hits. This does not establish bar6 as an optimal exit. The chosen runtime has no new bar6 timeout. Giveback after the hindsight MFE bar is saved in winner-timing-supplement.json as evaluation only.

## Paired performance — N=173 in every column

Returns below are reference-price/cost-adjusted trade percentages. Net/gross sums and drawdown proxies are percentage-point sums over unweighted trades, **not portfolio return or portfolio mark-to-market drawdown**.

| Arm | Net sum pp | Gross sum pp | Mean % | Median % | Win rate | PF | Worst % | p05 % | <=-10% N | DD entry-order proxy pp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FIXED12 | 58.7295 | 67.3795 | 0.3395 | -0.0500 | 81/173 (46.8208%) | 1.1840 | -29.4618 | -9.0907 | 6 | -67.8207 |
| BAR5_FIXED12 | 64.7423 | 73.3923 | 0.3742 | -0.0500 | 77/173 (44.5087%) | 1.2081 | -29.4618 | -7.9919 | 5 | -68.0749 |
| BAR5_CLOSE_PEAK_HALF | -13.6122 | -4.9622 | -0.0787 | -0.0500 | 66/173 (38.1503%) | 0.9333 | -29.4618 | -5.2322 | 4 | -82.6615 |
| BAR5_TWO_LOWER_CLOSES | 64.1413 | 72.7913 | 0.3708 | -0.0500 | 78/173 (45.0867%) | 1.2545 | -23.5794 | -6.6609 | 4 | -64.8562 |


| Arm | Mean loss % | Median loss % | Mean holding bars | Median bars | Mean clock minutes | Pre-exit MAE median % | Pre-exit MAE p05 % | MFE capture median | Giveback mean pp | Giveback median pp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FIXED12 | -3.4685 | -1.9793 | 11.8960 | 12.0000 | 68.1503 | -2.0794 | -12.5000 | 0.0000 | 5.2005 | 3.3450 |
| BAR5_FIXED12 | -3.2402 | -1.9643 | 11.0867 | 12.0000 | 64.1040 | -2.0794 | -12.4315 | 0.0000 | 5.1657 | 3.3450 |
| BAR5_CLOSE_PEAK_HALF | -1.9082 | -0.4053 | 5.4566 | 5.0000 | 33.1792 | -1.1546 | -10.5983 | 0.0000 | 5.6186 | 3.9568 |
| BAR5_TWO_LOWER_CLOSES | -2.6527 | -1.5554 | 7.5549 | 7.0000 | 44.7110 | -1.6260 | -10.5983 | 0.0000 | 5.1692 | 3.6778 |


MFE capture = gross reference exit return / common available MFE. MFE<=0 is undefined (8 cases; capture N=165), not zero-filled. Full distributions and exit-order DD proxies are in measurement.json. This ratio can be large negative when positive MFE is tiny.

## Winner preservation

| Arm | Level | Available winner N | Final net positive | Final net >= level | Exit before first HIGH touch | Winner mean net % |
| --- | --- | --- | --- | --- | --- | --- |
| FIXED12 | 1 | 153 | 80/153 (52.2876%) | 63/153 (41.1765%) | 0/153 (0.0000%) | 1.0689 |
| FIXED12 | 2 | 132 | 73/132 (55.3030%) | 49/132 (37.1212%) | 0/132 (0.0000%) | 1.6847 |
| FIXED12 | 3 | 101 | 65/101 (64.3564%) | 31/101 (30.6931%) | 0/101 (0.0000%) | 2.6271 |
| FIXED12 | 5 | 64 | 42/64 (65.6250%) | 21/64 (32.8125%) | 0/64 (0.0000%) | 4.2324 |
| BAR5_FIXED12 | 1 | 153 | 77/153 (50.3268%) | 62/153 (40.5229%) | 5/153 (3.2680%) | 1.0693 |
| BAR5_FIXED12 | 2 | 132 | 71/132 (53.7879%) | 49/132 (37.1212%) | 4/132 (3.0303%) | 1.6696 |
| BAR5_FIXED12 | 3 | 101 | 63/101 (62.3762%) | 31/101 (30.6931%) | 4/101 (3.9604%) | 2.5868 |
| BAR5_FIXED12 | 5 | 64 | 42/64 (65.6250%) | 21/64 (32.8125%) | 0/64 (0.0000%) | 4.2324 |
| BAR5_CLOSE_PEAK_HALF | 1 | 153 | 66/153 (43.1373%) | 37/153 (24.1830%) | 11/153 (7.1895%) | 0.5443 |
| BAR5_CLOSE_PEAK_HALF | 2 | 132 | 62/132 (46.9697%) | 25/132 (18.9394%) | 13/132 (9.8485%) | 0.8972 |
| BAR5_CLOSE_PEAK_HALF | 3 | 101 | 51/101 (50.4950%) | 15/101 (14.8515%) | 16/101 (15.8416%) | 1.3866 |
| BAR5_CLOSE_PEAK_HALF | 5 | 64 | 34/64 (53.1250%) | 9/64 (14.0625%) | 6/64 (9.3750%) | 2.4455 |
| BAR5_TWO_LOWER_CLOSES | 1 | 153 | 78/153 (50.9804%) | 56/153 (36.6013%) | 7/153 (4.5752%) | 1.0073 |
| BAR5_TWO_LOWER_CLOSES | 2 | 132 | 74/132 (56.0606%) | 38/132 (28.7879%) | 6/132 (4.5455%) | 1.5332 |
| BAR5_TWO_LOWER_CLOSES | 3 | 101 | 65/101 (64.3564%) | 30/101 (29.7030%) | 8/101 (7.9208%) | 2.4392 |
| BAR5_TWO_LOWER_CLOSES | 5 | 64 | 43/64 (67.1875%) | 19/64 (29.6875%) | 1/64 (1.5625%) | 3.9760 |


Positive final net is a weak preservation measure and is separated from realizing the full opportunity level. Same-bar touches are not called premature because intrabar order is unknown.

## Dynamic state and cohort performance

| Arm | DEFENSIVE | RECOVERED | BAR5 failure | Recovered mean net % | Recovered positive | Failed recovery N | No-reclaim mean net % | False defensive exit later Fixed positive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FIXED12 | 0 | 0 | 0 | N/A | 0/0 (N/A%) | 0 | N/A | 0 |
| BAR5_FIXED12 | 48 | 28 | 20 | -0.6270 | 12/28 (42.8571%) | 16 | -3.5967 | 4 |
| BAR5_CLOSE_PEAK_HALF | 48 | 28 | 20 | -0.6533 | 10/28 (35.7143%) | 18 | -3.5967 | 4 |
| BAR5_TWO_LOWER_CLOSES | 48 | 28 | 20 | -0.0989 | 13/28 (46.4286%) | 15 | -3.5967 | 4 |


| Cohort | Arm | N | Mean net % | PF |
| --- | --- | --- | --- | --- |
| A_FIRST_BAR_NON_ADVERSE | FIXED12 | 125 | 1.2339 | 1.8445 |
| A_FIRST_BAR_NON_ADVERSE | BAR5_TWO_LOWER_CLOSES | 125 | 1.1108 | 1.9757 |
| B_ADVERSE_RECLAIM_BY_BAR5 | FIXED12 | 28 | -0.6270 | 0.6892 |
| B_ADVERSE_RECLAIM_BY_BAR5 | BAR5_TWO_LOWER_CLOSES | 28 | -0.0989 | 0.9267 |
| C_ADVERSE_NO_RECLAIM_BY_BAR5 | FIXED12 | 20 | -3.8973 | 0.0254 |
| C_ADVERSE_NO_RECLAIM_BY_BAR5 | BAR5_TWO_LOWER_CLOSES | 20 | -3.5967 | 0.0000 |


False recovery here means recovered then negative final net; false defensive exit means BAR5 exit followed by a positive Fixed reference close. These are retrospective diagnostics, not decision inputs.

| Arm | Available-window MAE<=-10 cohort N | Cohort mean final net % | Cohort worst net % | Saved net winners vs Fixed | Lost net winners vs Fixed |
| --- | --- | --- | --- | --- | --- |
| FIXED12 | 17 | -7.0020 | -29.4618 | 0 | 0 |
| BAR5_FIXED12 | 17 | -6.9764 | -29.4618 | 0 | 4 |
| BAR5_CLOSE_PEAK_HALF | 17 | -4.7734 | -29.4618 | 18 | 33 |
| BAR5_TWO_LOWER_CLOSES | 17 | -4.7716 | -23.5794 | 12 | 15 |


The available-window deep-adverse cohort has 17 cases and differs from strict30m. All 10 previously identified strict30m MAE<=-10% cases are retained in the paired sample; no deep-tail case was removed from that prior cohort.

## Concentration and fragility

| Arm | Positive-profit Top1 share | Top3 | Top5 | Positive improvement Top1 share | Top3 | Top5 | Net delta pp | Net delta removing best improvement pp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FIXED12 | 0.0722 | 0.1844 | 0.2615 | N/A | N/A | N/A | 0.0000 | 0.0000 |
| BAR5_FIXED12 | 0.0726 | 0.1854 | 0.2629 | 0.2012 | 0.5212 | 0.7456 | 6.0128 | 1.5514 |
| BAR5_CLOSE_PEAK_HALF | 0.1432 | 0.2961 | 0.4230 | 0.0734 | 0.1830 | 0.2668 | -72.3417 | -84.4913 |
| BAR5_TWO_LOWER_CLOSES | 0.0863 | 0.1800 | 0.2700 | 0.0737 | 0.1920 | 0.2738 | 5.4118 | -4.8685 |


Shares are fractions of summed positive trade profits or summed positive paired improvements, not shares of net profit. Full symbol/session concentration is saved for every arm.

| Selected arm group | Identity | Trades | Net sum pp | Absolute return share |
| --- | --- | --- | --- | --- |
| symbol | 89180 | 22 | 93.5429 | 0.1673 |
| symbol | 57590 | 12 | -31.4033 | 0.1484 |
| symbol | 90730 | 1 | 27.2888 | 0.0480 |
| symbol | 81070 | 4 | -6.9055 | 0.0338 |
| symbol | 39360 | 2 | 11.5996 | 0.0337 |
| sessionDate | 2024-12-30 | 4 | 23.0393 | 0.0589 |
| sessionDate | 2024-11-08 | 5 | -6.2670 | 0.0457 |
| sessionDate | 2024-11-25 | 2 | 25.3577 | 0.0446 |
| sessionDate | 2024-12-26 | 3 | 22.1556 | 0.0438 |
| sessionDate | 2024-12-25 | 3 | -24.1556 | 0.0425 |


## Decision and remaining risk

Freeze the two-lower-CLOSE policy as the single Development Final because it balances fewer severe final losses, better PF/p05, retained positive +3/+5 winners and simple causal continuation. The half-peak candidate reduced p05 but damaged aggregate performance and winner preservation; the Fixed continuation control had slightly higher net sum but poorer worst-tail/PF trade-offs. No additional parameters were tried.

- Same exposed data used to design/choose3 candidates; no independent performance claim
- Primary common coverage173/277; no replacement; standalone192 not used as comparator
- Worst net reference trade still -23.5794%; not a risk guarantee
- Largest positive paired improvement removed makes net delta negative
- Recovered cohort mean net remains negative
- Median net trade remains -0.05%; observed MFE capture median remains0
- Closing-price fills/latency/slippage not established; execution adapter required before realistic portfolio claims
- Session-end15:25/auction coverage unresolved; not silently changed
- DD is unweighted trade-order proxy, not portfolio mark-to-market drawdown

The +5.4118pp total net improvement becomes -4.8685pp after removing its largest improvement trade. Consequently improvement robustness is not established. The selected policy is a research foundation, not a claim that downside risk is solved. Net median remains -0.05%, MFE capture median is zero, and median giveback worsens. Recovered winners remain a weak cohort.

## Integrity and handoff

Frozen Selector/Entry/277 identity and all pinned upstream artifacts verified unchanged. Entry prediction/refit=0; new analog=0; SHORT evaluation=0; provider requests=0; Fresh consumption=0; OOS access=0. Global Fresh budget stays195. All nine safety flags are false. Initial targeted regression:17 PASS under kernel network denial; final publishing-head CI must be checked separately. No Claude independent review was performed.

Development Final SHA-256: `e69b4257ec9a9895c939f873740924665fe8b00550bc6ea676054cf23c1f4460`. Exact identities and all hashes are in development-final.json. See [capital-handoff.md](capital-handoff.md). Next: Capital Allocation **research integration** of this one frozen Development policy, with explicit executable-fill/latency, cash constraints, overlapping positions, missing-position accounting and portfolio MTM semantics before claiming portfolio performance. No automatic promotion, main merge or Fresh/OOS evaluation.

## Frozen upstream file hashes

| Artifact | SHA-256 |
| --- | --- |
| predict/research/phase57-long-only-global-data-budget-v1.json | b91699704f80ef7fda60fe0596e8f8736a181cd00dc879f5070f9caed4d4a62f |
| predict/research/phase57-msh-entry-long-v1-validation-candidate-v1.json | 4a2f52cd6f25f480fe6d7de9db525860ddf3c1600abed06b6222c0990c055a23 |
| docs/evidence/phase57-msh-entry-long-v1-final-validation-model/final-model.json | b053a858edda22bee7b9939162648740507964cc5ed8d613c2d778d15534589e |
| docs/evidence/phase57-msh-entry-long-v1-final-validation-model/final-scaler.json | 1e4865915a2ad1ec51dd4ebf2116d48b9f89b9b884f8dc732fdb2861dbf4fe4b |
| predict/research/phase57-msh-entry-long-v1-fit-contract-v1.json | 64c20d785be5f23b0a9103f419726b191a12a58fd5d3a7ad5185c69f9644a938 |
| docs/evidence/phase57-msh-entry-long-v1-offline-freeze/development-evidence-freeze.json | 68d2a02c988a05b3178e903d628a53662b01bb704fa0700ebcb98e3b32547ead |
| docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz | 73e566aba4d1a3f5af33b74be52ae90736c088b1091841f1eb44e93d5476084c |
| docs/evidence/phase57-long-only-current-entry-transfer-v1-events.ndjson.gz | a36eecfed29aa0e9da50b051839578ca2e8f3a37d500de17bd6c3acfd8ce3a53 |
| docs/evidence/phase57-long-only-entry-filter-recovery-audit-v1-first-opportunities.json.gz | 74ca5797a117df37ec78f7e2f859a52ab634affa088fcdabd2a3a0ec4e16d30a |
| predict/research/phase57_msh_entry_long_v1_proportional_odds.py | 9e5910c476c6957aab65cc24490ffb2759084e5e49b36db42fe284674979ae74 |
| predict/long-only/phase57-long-only-integrated-dataset.js | 390e2df4ddc0be571d285e05754ce9ad90f2618eb5902797cf8e7bae4a5f667f |
| predict/long-only/phase57-long-only-entry-preimplementation-feasibility.js | d785c6cadfe95fd8a2f8ee5620edfb4e4edf9748ad071829f782c197affbf10e |
| docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/measurement.json | f43b00b4959698ba6f97883ea2291e2e47dfdbd7d1dc4d2f07a421ac241f0b02 |
| docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/assessment.json | 843bd90ba8583b774ce243ff341e0537b0049ee655742fc8737a73c882ec219c |
| docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/manifest.json | b3e30dee5b73d4bc0477ecf7fbfaf48d83c05df4845de7076ac4118042893448 |
| docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/dataset-contract.json | 4a1d3e4ec4229d32ee2a50678db8fe3f8739abb3530df521e3036d201e75b441 |
| docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/frozen-predictions.ndjson.gz | a11313909248d2c8aa1c39bac807f8a5c476c19c0be75a0e15dde41690cdb8be |
| docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/prediction-receipt.json | 47aec60ccf2c7fc51dac91aedad781f7ec71e525205a8e2c2f015817473043dc |
| docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/session-exposure-ledger.json | c83077a0cbbf92b373c0c1af0985ede5fea7d0ed7fb88f6221eb684c6a2a14df |
| docs/evidence/phase57-msh-entry-long-v1-upstream-freeze/manifest.json | b1755d173e25267f00c9ab89f2ab3f2cfb82bbaf841d2d88dc6ad19421284a32 |
| docs/evidence/phase57-msh-entry-long-v1-upstream-freeze/historical-enter-identities.json | 72224ac9fd073f7da45c488aaf8ca999752b466e715837c21440e7dd93970236 |
| predict/research/phase57-long-only-frozen-selector-v1.json | d93b3560f4be7dd231b88780f7d6d51cf8ecda85d4f599debcdd22c0c3feb5c8 |
| predict/daytrade/phase57-p25-exit-v3-dual-gate.js | db4c52836509c471a9c5c96a471c07d4a787cca348a998fee5fc7cf33921017b |
| predict/daytrade/phase57-p25-exit-v4-structural-risk.js | 393e9c6ee5201699ad8ea1cb8843fc57b6d91ef055fadee1ee88905190fd0405 |
| predict/daytrade/phase57-p25-exit-v2-state-conditioned.js | 72c19d2ad5977fcc0d27de3ba9e1a28cf223844c2b5d7a8acd9fc471946a2b41 |
| predict/daytrade/phase57-p25-2k-pinned-history-bridge.js | 574e0177106824a85c474d4fdb40fda5b291fc52970d9061c8b75aa5e8a17e54 |
