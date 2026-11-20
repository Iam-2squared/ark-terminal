# Timing-only Entry: Frozen Selector census / 2026-09-17

Status: **TIMING_ONLY_SELECTOR_CENSUS_COMPLETE_5M_ONLY**. New 1m Entry performance remains unmeasured. This change adds this document only; no Selector, Entry kernel, EXIT, Capital, cash ledger, workflow or trading changes.

## User-approved responsibility split

Keep the current Frozen LONG Selector unchanged. NEW Entry optimizes timing without inheriting the old E[L]>=2.0 gate or limiting its universe to the old 277 ENTER anchors. Do not force every candidate into a trade. EXPIRE remains an opportunity loss in the full-candidate denominator; changing the name of SKIP to EXPIRE does not remove selective behavior.

Actual intended sequence: Frozen Selector -> Timing Entry intent -> Capital accept/size -> reference fill -> Frozen EXIT -> cash release. Allocation occurs before a position is bought, not after EXIT. Allocation rejects must be distinguished from Entry expiry. Allocation is not evidence that a negative trading edge can be repaired automatically.

## Confirmed horizon correction

The Frozen contract `predict/research/phase57-long-only-frozen-selector-v1.json`, read at `5b3954eab70c2e516d9d04313cd9db6b0e14626e`, explicitly contains trainingTarget **Y30**, defined as the short-horizon endpoint return represented by 6 closed 5-minute trading observations. The contract explicitly distinguishes this from the wall-clock 30-minute evaluator.

Separately, its published +1/+2/+3/+5 Opportunity metrics use selection price to same-session future HIGH. These are not the probability that the exact 30-minute terminal CLOSE is positive. The prior chat's uncertainty about the training target is corrected here. Neither target implies a mandatory 30-minute Entry wait.

## Newly computed census

Input: existing exposed Development export, 76 sessions, 3,800 selection events. Main population: first event per symbol-session, 2,743 anchors, chosen without outcomes. Prices are pinned Selector decisionPrice references, not executed fills. Only saved 5m paths are used; no artificial 1m reconstruction.

Observed same-session HIGH hits among all 2,743 first anchors:

| Threshold | Observed hits | Fraction of all anchors, lower bound | No recorded hit and incomplete path |
|---|---:|---:|---:|
| +1% | 2,055 | 74.92% | 585 |
| +2% | 1,619 | 59.02% | 956 |
| +3% | 1,212 | 44.19% | 1,304 |
| +5% | 609 | 22.20% | 1,831 |

These are observed lower bounds, not complete-window accuracy estimates. Missing observations without a hit are unresolved, not failures. A hit does not prove an executable profit or a known first-hit time across missing bars.

Complete saved 5m-grid subsets:

| Window | Complete anchors | +1 HIGH | +2 HIGH | +3 HIGH | +5 HIGH | Terminal CLOSE above selection |
|---|---:|---:|---:|---:|---:|---:|
| 30 wall-clock minutes | 1,303 | 860 (66.00%) | 557 (42.75%) | 360 (27.63%) | 157 (12.05%) | 641 (49.19%) |
| 60 wall-clock minutes | 878 | 633 (72.10%) | 440 (50.11%) | 296 (33.71%) | 141 (16.06%) | 391 (44.53%) |
| Saved regular-session end | 384 | 281 (73.18%) | 216 (56.25%) | 157 (40.89%) | 81 (21.09%) | 147 (38.28%) |

The populations differ; do not interpret the row differences as a holding-time experiment. Saved regular-session end is not a full auction-semantic replication. Complete 5m grids can still have incomplete underlying minute observations.

On exactly the same 878 complete-60m anchors, 30m HIGH hits are 584/371/235/105; 60m hits are 633/440/296/141 at +1/+2/+3/+5 respectively. Terminal CLOSE positivity is 427/878 (48.63%) at 30m versus 391/878 (44.53%) at 60m. A longer opportunity window is not automatically a better terminal return.

Prior path-study facts were independently reproduced: of 360 +3% hits in the complete-30m set, 145 occur in the first 5m bar, 74 have a >=1% dip in an earlier bar, and 8 have only hit-bar dip evidence with unknown intrabar ordering. Corresponding +5 counts are 157 total / 64 first-bar / 27 earlier-dip / 1 ambiguous. These are evaluator labels, not causal Entry predictions.

## Keep the original Frozen aggregate separate

The Frozen saved aggregate has 3,800 selected / 3,790 HIGH-evaluable events with hits 2,895/2,323/1,791/947. Those published metrics were read from the repository, not recomputed as part of this new census.

The currently accessible saved-path observed-HIGH counts across all 3,800 events are 2,837/2,278/1,756/926. They do not reproduce the original Frozen aggregate. Detailed source/evaluator parity is not completed here. This separate, stricter path census must not replace the Frozen result or be used to declare Selector deterioration.

## Real 1m replay still pending

Checked current PR head, recent branch-run metadata, existing export runs 35182363612 and 35183197002, and mounted ZIP member names. No usable minute-entry-paths.json.gz was confirmed in these checked sources. This is not an exhaustive repository-artifact absence claim.

The 878 complete 5m-hour anchors include only 249 with observedMinutes=5 in every included bar. This is a source-metadata check, not possession or validation of the minute price sequence. The strict 1m replay must not assume it can use the same 878 anchors. Missing and no-trade semantics need to remain distinct; no interpolation is allowed.

Required input remains an already-authorized 1m projection and audit for the pinned 76 sessions / 2,743 anchors, through selection+60m where the session permits. No secret retrieval, decryption, blocked-export retry or alternate-route execution was performed. No new provider/Fresh/OOS access.

## Evidence and reproducibility

New local census implementation: census.py. 20 unit tests PASS. 42 independent source, aggregation and saved Phase0-parity checks PASS. These are not trading-performance validation tests. Complete local report and reproducibility bundle: Ark_Terminal_Timing_Only_Selector_Census_2026-09-17.md / .zip in the conversation.

Source ZIP SHA256: `043dc99ad42ac3036ff280cb139de3fa6740f5386d0829a4cbaf13e360507505`.
First-anchor SHA256: `985218fd1520bde127a72e9b049dd5a1840d42a928e7e850ea4e3e4d7ed82121`.
New census protocol SHA256: `268742d31fe7b64241da9176eef3ae66e17f25a9fd5ad935cfd210b66c040237`.
New result.json SHA256: `832aca95ec54f840b6e782daae73e437894f36d8689a1bfa6df2c4ced65e852c`.

Protocol recorded before this aggregation; source outcomes have already been repeatedly exposed. Historical Development only, not Fresh/OOS. New model fits/predictions/1m Entry replay/provider requests/Fresh/OOS/EXIT/Capital/Portfolio replay are all 0. Existing 1m rule and gates unchanged. All nine trading/write/promotion flags remain false. No main merge.
