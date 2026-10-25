# Phase57 Frozen NEW LONG Entry v1 × Existing LONG EXIT

Date: 2026-09-18 JST. **Decision: BUILD_NEW_LONG_EXIT** (Development research disposition only).

Mechanical transfer **PASS for both INITIAL and DIP_REPRICE**. Unchanged policy replay is possible; mechanical compatibility does not establish suitability. Existing EXIT improves some tails, but DIP average/PF/winner capture deteriorate and the exact additional-downside106/21 cohorts have worse mean outcomes. Retain the existing policy as a frozen control/foundation; do not adopt it as the completed new two-opportunity EXIT. This is a design judgment on exposed Development, not proof that another policy will outperform, a numerical acceptance-gate pass, or an OOS/Portfolio claim.

## Audit / exact lineage

Starting remote HEAD `efa7efb5235dcb1b711599d5c0ba0a196ec5fab9` exactly matched the handoff; PR #587 open/Draft/unmerged. PR body was stale and was not used as Entry authority. Freeze / Contract / Parity were read at the pinned snapshot. Frozen implementation/evidence `6fabde7dfe208e19d5611e0a290b4df6724e562e` remains unchanged.

Saved parity run35250519787/job105301441720 SUCCESS; artifact10508583428 ZIP and all3 files independently hash-verified. No Entry study/kernel replay was run for this diagnostic. Initial HEAD CI API returned6 successful checks and4 skipped research workflows (skipped is not a pass); existing parity CI at that HEAD was already successful.

| Lineage | Exact evidence / applicability |
|---|---|
| Existing selected LONG EXIT | `LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1`, freeze `ba0ccdb2aea7e5fc9fee817c0bd95f09427108f8`; `LONG_EXIT_DEVELOPMENT_FINAL_SELECTED_NOT_VALIDATED` |
| Runtime/interface | `predict/long-only/phase57_long_exit_continuation_v1.py` / `phase57_long_exit_development_final.py`; exact hashes in contract and manifest, unchanged |
| Prior selected-population evidence | 277 old MSH ENTER identities, common173; mean+0.370759%, PF1.254518, worst−23.579412%; these are not current cohort results |
| v3/v4 | Frozen analog dependency uses56-day window ending2026-08-12; all dates after this target2024-09-17–2025-01-09 period. PIT requires analog.sessionDate < entry.sessionDate and fullyRealizedAt < decision. Eligible frozen analog rows0. No new pool built |
| v5 BAR5 | `EXIT_V5_DYNAMIC_RECLAIM_BAR_5`, candidate417ad9d6dc92c3110e680cdc4a6c8dcf94b4ee5e, simulatoraaa99030295ffb447de273881b16aad1eab1a7e9; mechanical parity but blocked on original causal v4 result/trace. Not silently replaced by BAR6 or Fixed12 |
| Newer LONG policy dependency | No model/analog/train period. Designed/selected on exposed old277 Development; transfer is a different population and reference location |

The old EXIT freeze commit has4 successful PR-triggered CI workflows in the queried API page, including Predict Tests, Historical Re-Measurement Integrity and LONG-only Research Foundation. The API only returns PR-triggered runs; absence of a dedicated EXIT workflow in that page is not a claim it never ran. Current focused local tests:17/17 PASS under kernel Internet-socket denial, including frozen runtime/state tests, evidence pins and new transfer tests.

## Research interface and execution limits

See contract.md, committed locally before measurement as9d87997 (direct git push lacked credentials; connector publication follows measurement, so this is **not remote preregistration**). INITIAL and DIP are independent hypothetical funded unit positions at the exact saved OPEN reference. No automatic funding, combined return, notional, cash allocation or Entry mutation. DIP starts at its saved opportunity timestamp, with a new state and price-rebased CLOSE; no pre-DIP OHLC or state. EXIT uses only completed CLOSE, inherited BAR5 reclaim, two lower CLOSEs, 12-trading-bar/calendar cap and0.05pp round-trip cost. Missing before exit censors; missing after exit cannot alter the exit.

Reference OPEN and contemporaneous decision-CLOSE exit are optimistic marks, not executable fills. Zero latency/queue/slippage is an explicit research assumption; actual execution remains unresolved. Bar count skips lunch; clock time includes it. Strict wall-clock diagnostic horizons never cross lunch. SAFE_REGULAR_END is15:00 before2024-11-05 and15:25 thereafter, excluding the unresolved auction gap; this separate diagnostic does not modify the inherited EXIT calendar cap. No overnight, interpolation, missing-flat fill, or provider substitution.

## Population / same-identity comparison

| Cohort | Opportunities | Priced reference | Existing standalone | Fixed12 standalone / paired | Original primary subset paired |
|---|---:|---:|---:|---:|---:|
| DIP_REPRICE_OPPORTUNITY | 541 | 541 | 449 | 397 / 397 | 324 |
| INITIAL_ENTRY_OPPORTUNITY | 2743 | 1907 | 1232 | 1072 / 1072 | 878 |

INITIAL retains all2743 anchors:483 missing references and353 expired;675 more censor before existing EXIT. DIP retains exactly541 emitted opportunities;92 censor before existing EXIT. Standalone existing results are never compared against a smaller Fixed12 population. The original dip328 primary panel becomes324 paired for an own-start12-bar EXIT comparison: 4 lack the extra required post-DIP coverage; the original328 are not dropped from the ledger. Trading-bar EXIT eligibility can exceed strict wall-clock+60 eligibility because EXIT may skip lunch or use a shorter known session cap.

All return sums and DD below are unweighted percentage-point sums/proxies, **not Portfolio return or portfolio MaxDD**. N differs between INITIAL and DIP; do not add them or infer a fund-all policy.

| Cohort / arm | N | Net sum pp | Mean % | Median % | Win rate | PF | Worst % | p05 % | Worst5% mean % | Entry-order DD pp | Exit-order DD pp |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| DIP / fixed | 397 | -130.1370 | -0.3278 | -0.2416 | 160/397 (40.3023%) | 0.7413 | -13.6338 | -5.3436 | -7.4331 | -170.1557 | -170.1557 |
| DIP / existing | 397 | -135.2610 | -0.3407 | -0.4755 | 137/397 (34.5088%) | 0.6828 | -8.4635 | -4.0008 | -6.0012 | -157.8249 | -157.9891 |
| INITIAL / fixed | 1072 | -352.2294 | -0.3286 | -0.0500 | 442/1072 (41.2313%) | 0.7625 | -29.4618 | -5.8558 | -9.1738 | -415.4811 | -415.4811 |
| INITIAL / existing | 1072 | -292.3470 | -0.2727 | -0.3475 | 386/1072 (36.0075%) | 0.7607 | -23.5794 | -4.6321 | -7.4056 | -365.1791 | -363.3974 |

| Cohort / arm | Mean holding bars | Mean clock min | Mean pre-exit MAE % | Median MFE capture | Capture N | Mean giveback pp | Median giveback pp |
|---|---:|---:|---:|---:|---:|---:|---:|
| DIP / fixed | 11.7028 | 75.2897 | -2.6267 | -0.0670 | 378 | 2.7546 | 1.9286 |
| DIP / existing | 6.9521 | 40.9572 | -1.9228 | -0.2396 | 378 | 2.7675 | 2.1739 |
| INITIAL / fixed | 11.6922 | 66.2407 | -2.7388 | 0.0000 | 948 | 2.9328 | 2.1091 |
| INITIAL / existing | 7.3993 | 41.2500 | -2.1014 | 0.0000 | 948 | 2.8769 | 2.1970 |

MFE capture=gross reference exit/common Fixed12-window MFE, undefined if MFE<=0. This is a ratio, not realized HIGH execution. A negative value means closing below the entry reference despite a positive observable high.

| Cohort | Existing exit reason on paired population |
|---|---|
| DIP_REPRICE_OPPORTUNITY | {'BAR5_NO_RECLAIM': 61, 'CALENDAR_SESSION_CAP': 12, 'FIXED12_CAP': 69, 'TWO_LOWER_COMPLETED_CLOSES': 255} |
| INITIAL_ENTRY_OPPORTUNITY | {'BAR5_NO_RECLAIM': 205, 'CALENDAR_SESSION_CAP': 27, 'FIXED12_CAP': 275, 'TWO_LOWER_COMPLETED_CLOSES': 565} |

## Conditional path diagnostics

Own position-start horizons; each row has its own complete-case N. Time-to-MFE/MAE is recorded as the containing bar interval, not an invented exact intrabar time. First-positive/recovery uses completed CLOSE; recovery after an adverse LOW requires a later bar. summary.json contains distributions, times, +1/+2/+3/+5 hits, adverse/recovery rates and deep-downside outcomes; ledger.json.gz retains every event.

| Cohort | Horizon | N | Median CLOSE % | Median MFE % | Median MAE % | Median giveback pp | +3 reach | +5 reach |
|---|---|---:|---:|---:|---:|---:|---|---|
| DIP | 5 | 541 | 0.0000 | 0.4678 | -0.4425 | 0.4329 | 16/541 (2.9575%) | 1/541 (0.1848%) |
| DIP | 10 | 523 | 0.0000 | 0.7968 | -0.6907 | 0.7812 | 35/523 (6.6922%) | 9/523 (1.7208%) |
| DIP | 15 | 516 | 0.0000 | 0.9804 | -0.8816 | 0.9589 | 52/516 (10.0775%) | 16/516 (3.1008%) |
| DIP | 20 | 505 | 0.0000 | 1.1111 | -1.0596 | 1.0811 | 65/505 (12.8713%) | 20/505 (3.9604%) |
| DIP | 30 | 394 | 0.0000 | 1.3296 | -1.3004 | 1.4533 | 76/394 (19.2893%) | 27/394 (6.8528%) |
| DIP | 45 | 364 | -0.2311 | 1.4975 | -1.6225 | 1.8321 | 84/364 (23.0769%) | 32/364 (8.7912%) |
| DIP | 60 | 264 | -0.1956 | 1.7161 | -1.8807 | 1.8805 | 69/264 (26.1364%) | 27/264 (10.2273%) |
| DIP | SAFE_REGULAR_END | 355 | -0.7937 | 2.4155 | -2.9328 | 3.2258 | 150/355 (42.2535%) | 78/355 (21.9718%) |
| INITIAL | 5 | 1907 | 0.0000 | 0.2625 | -0.2538 | 0.2558 | 120/1907 (6.2926%) | 45/1907 (2.3597%) |
| INITIAL | 10 | 1679 | 0.0000 | 0.6729 | -0.6570 | 0.7002 | 207/1679 (12.3288%) | 80/1679 (4.7647%) |
| INITIAL | 15 | 1555 | 0.0000 | 0.9390 | -0.9009 | 0.9499 | 248/1555 (15.9486%) | 105/1555 (6.7524%) |
| INITIAL | 20 | 1462 | 0.0000 | 1.0801 | -1.0799 | 1.1969 | 264/1462 (18.0575%) | 109/1462 (7.4555%) |
| INITIAL | 30 | 1303 | 0.0000 | 1.3230 | -1.3410 | 1.3903 | 293/1303 (22.4866%) | 125/1303 (9.5932%) |
| INITIAL | 45 | 994 | 0.0000 | 1.5784 | -1.6608 | 1.8977 | 262/994 (26.3581%) | 121/994 (12.1730%) |
| INITIAL | 60 | 878 | 0.0000 | 1.7112 | -1.9231 | 2.1592 | 267/878 (30.4100%) | 123/878 (14.0091%) |
| INITIAL | SAFE_REGULAR_END | 933 | -0.4149 | 2.2222 | -2.8037 | 3.0702 | 372/933 (39.8714%) | 202/933 (21.6506%) |

## +3/+5 winner preservation

| Cohort / arm | Level | Available winners | Final net positive | Final net >= level | Exit before first HIGH touch |
|---|---:|---:|---|---|---|
| DIP / fixed | 3 | 106 | 76/106 (71.6981%) | 38/106 (35.8491%) | 0/106 (0.0000%) |
| DIP / fixed | 5 | 41 | 33/41 (80.4878%) | 12/41 (29.2683%) | 0/41 (0.0000%) |
| DIP / existing | 3 | 106 | 73/106 (68.8679%) | 28/106 (26.4151%) | 22/106 (20.7547%) |
| DIP / existing | 5 | 41 | 32/41 (78.0488%) | 10/41 (24.3902%) | 7/41 (17.0732%) |
| INITIAL / fixed | 3 | 314 | 235/314 (74.8408%) | 113/314 (35.9873%) | 0/314 (0.0000%) |
| INITIAL / fixed | 5 | 145 | 120/145 (82.7586%) | 56/145 (38.6207%) | 0/145 (0.0000%) |
| INITIAL / existing | 3 | 314 | 217/314 (69.1083%) | 88/314 (28.0255%) | 39/314 (12.4204%) |
| INITIAL / existing | 5 | 145 | 107/145 (73.7931%) | 44/145 (30.3448%) | 20/145 (13.7931%) |

Same-bar touch and exit are not classified as premature; HIGH/LOW order is unknown. Positive final net and reaching the full level are different measures.

## Exact cheaper-DIP106 /21 risk cases

All original primary328 → cheaper299 → additionalD30>=2%106 / >=5%21 identities were matched to the saved parity ledger. Both risk subsets have complete paired EXIT results for every requested identity. Thresholds select evaluator-only retrospective diagnostics, never Entry/EXIT inputs.

| Subset | Paired N | Fixed mean % | Existing mean % | Fixed worst % | Existing worst % | Fixed p05 % | Existing p05 % | Existing exit before / same / after adverse bar |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| D30 >= 2% | 106 | -1.4849 | -1.7944 | -13.6338 | -8.4635 | -6.8736 | -5.7366 | {'AFTER_ADVERSE_BAR': 77, 'BEFORE_ADVERSE_BAR': 14, 'SAME_BAR_ORDER_UNKNOWN': 15} |
| D30 >= 5% | 21 | -4.0014 | -4.3571 | -13.6338 | -8.4635 | -7.3894 | -8.3069 | {'AFTER_ADVERSE_BAR': 13, 'BEFORE_ADVERSE_BAR': 3, 'SAME_BAR_ORDER_UNKNOWN': 5} |

In the106 group,31/106 recover at a later completed CLOSE within ownD30, but88/106 finishD30 below reference. In the21 group,1/21 later-close recovery and20/21 negativeD30 close. These definitions can overlap (recover then fall again). Later bar +3/+5 after >=2% downside:10/106 and5/106; after >=5%:0/21 and0/21 inD30. Same-bar recoveries/winners are not assumed.

Existing EXIT strictly precedes the threshold bar for only14/106 and3/21; same-bar15/106 and5/21 remain conservatively uncredited, after-bar77/106 and13/21. It reduces average pre-exit MAE but does not improve average final reference PnL in either subset. The21-case p05 actually worsens even as its single worst loss improves. Consequently “Dip is safe” or “risk solved” is not supported.

## Coverage / sensitivity / interpretation

| Cohort / panel | N | Fixed mean % | Existing mean % | Fixed PF | Existing PF |
|---|---:|---:|---:|---:|---:|
| DIP / primary60Subset | 324 | -0.2660 | -0.3179 | 0.7852 | 0.6997 |
| DIP / fullUnderlyingMinutesPaired | 134 | -0.4265 | -0.6622 | 0.7418 | 0.5513 |
| INITIAL / primary60Subset | 878 | -0.2656 | -0.2183 | 0.8040 | 0.8046 |
| INITIAL / fullUnderlyingMinutesPaired | 307 | -0.5818 | -0.4720 | 0.6815 | 0.6715 |

Full-underlying-minute sensitivity uses only saved observedMinutes metadata, not new1m data. Sparse coverage, informative missingness, same-data architecture exposure, overlapping unit positions, and execution assumptions prevent generalization/portfolio claims. The retained median-PnL and winner losses are not evidence to retune Entry; old277-selected EXIT success cannot be transferred to these populations.

## Disposition and minimal next architecture (proposal only)

**BUILD_NEW_LONG_EXIT** is the research recommendation because mechanical adaptation alone leaves the measured DIP risk/upside problem. It is not a declaration that every existing mechanic failed: first-bar routing, reference-relative reclaim, causal completed-bar state, missing handling and session cap are reusable. INITIAL has modest average/tail improvement but negative mean and lower winner preservation; there is no basis to call the whole pipeline improved.

A minimal first challenger can reuse the same state machine and the already-existing **two consecutive lower completed CLOSEs** condition as an early breakdown exit while DEFENSIVE, before the inherited BAR5 no-reclaim deadline. Keep reclaim priority at CLOSE>=0, reset state at each actually funded position, and keep continuation/cap/cost unchanged for that single comparison. This isolates the current policy’s DEFENSIVE wait risk without a stop/TP/trailing/VWAP grid, new feature, symbol rule, or Entry change. It is only a concrete unmeasured proposal; it may cut eventual recoveries and cannot be assumed to repair continuation’s premature winner exits. Do not add another continuation variant automatically.

Before any challenger result, pin its exact decision ordering and compare that one modification on identical identities, with tail AND winner metrics. No new policy code or challenger replay was created in this task. The requested audit/conditional replay/architecture decision is complete. Fresh/OOS remains sealed until separately predefined integrated validation after Selector→Entry→EXIT→Allocation→Portfolio is fixed.

## Reproducibility and artifacts

- `contract.md`: interface, lineage, assumptions and measurement plan.
- `entry-parity/`: exact original saved opportunity inputs.
- `summary.json`: all requested aggregate metrics and explicit denominators.
- `ledger.json.gz`:3284 separate cohort records, path timing/risk/exit details.
- `manifest.json`: immutable input/output hashes and zero counters.
- `audit.json`: remote/CI receipts, publication boundary and scope.
- `scripts/phase57_new_long_entry_exit_conditional.py`: deterministic offline evaluator.
- `scripts/test_phase57_new_long_entry_exit_conditional.py`: integrity tests.

```bash
ARK_TEST_OFFLINE=1 python3 scripts/offline/kernel_exec.py python3 -m scripts.phase57_new_long_entry_exit_conditional --out /tmp/phase57-exit-repro
ARK_TEST_OFFLINE=1 python3 scripts/offline/kernel_exec.py python3 -m unittest scripts.test_phase57_new_long_entry_exit_conditional
```

All9 safety flags remain false. Selector/Entry/Allocation/legacy EXIT unchanged; no market provider acquisition, model fit, analog pool, Fresh/OOS opening, live/paper order, production promotion or main merge. The research branch remains Draft/unmerged. CI success verifies integrity only.
