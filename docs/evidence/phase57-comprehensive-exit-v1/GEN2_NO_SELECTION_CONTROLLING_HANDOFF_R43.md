# Phase57 EXIT Generation 2 — NO_SELECTION controlling handoff R43

Saved at JST: 2026-09-26T20:28:05.975729+09:00
Basis HEAD: `63a123a371d486f58c9c4d726a82a73e9c8a3c3b`
Repository: `Iam-2squared/ark-terminal`
Research branch: `research/phase57-long-only-cash-equity`; Draft PR #587 remains unmerged.

## Controlling result and stopping point

**NO_SELECTION_STOP. Exactly 16 candidates scored; 0 candidates pass all frozen gates across both Entry arms. Selected candidate: null.**

This Work completed the first authorized Gen2 post-run integrity audit, frozen scoring, complete numerical reporting, independent gate crosscheck, and required post-run CI. Its Gen2 audit/scoring/reporting lane performed **0 model fits, 0 policy replays, 0 Capital replays, 0 new provider requests, 0 protected partition openings**. No R41 models, predictions, ledgers, Entry, candidate configuration, gate, or frozen scorer were modified.

No Final EXIT Freeze was created. Capital MAX3/MAX4/MAX5 was not run because SELECT is a prerequisite. The descriptive maxima (#11 IMMEDIATE overall mean, #07 R1 overall mean, #14 winner capture) are not selected candidates. Do not adopt them, add candidate 17, revive R36, loosen the gate, retune Gen2, or automatically start Gen3.

This document supersedes the *current-state/next-action* portions of R42 running handoff `cab859afa590a176aa8b0993204c8594eeb2fc53` on branch `research/phase57-gen2-r41-handoff-20260926`; it does not rewrite its historical observations. R36/R39 remain formally negative. The R41 architecture/label/feature/protocol freeze remains immutable and historical, not a Final EXIT deployment freeze.

## Identity and chronology

| Evidence | Exact identity |
|---|---|
| Entry Dual Freeze | `4878a1cc53430e816261dea0fb16aeb53b3c238d` |
| Gen2 pre-performance freeze | `0ba0112fff98cd1d8d864dc1967bbd76095e8d66`, 2026-09-26 18:21:46 JST |
| Protocol SHA-256 | `5fdc059936ba31466a7dace520f218353c634e6c8444d20d5ab21069c745deb4` |
| Required pre-performance CI | run `36233629987`, SHA `0d20b9aee00ff0b667f698e4c93d5f92ee057f38`, 97 tests PASS |
| Exact R41 execution SHA | `c031976a319130b6be379586147fff53cee6f741` |
| R41 workflow run / job | `36233758837` / `108381667257`, SUCCESS |
| R41 artifact | `10904078164`, `phase57-exit-gen2-r41-36233758837` |
| R41 artifact ZIP SHA-256 | `dbbc9e79292c8701d962a09f9ddf50d817241273fc50a5652d6b28d5580dffcd` |
| Artifact bytes / files | 27,249,656 / 128 |
| Actual finite fit/replay step | 2026-09-26 19:09:24–19:40:51 JST |
| Completed fit/policy counts | 64 fits; 16 candidates; 32 candidate A/B replay passes plus 2 neutral passes |
| Audit completed before score | 2026-09-26 20:06:36 JST |
| Audit PASS commit before score | `596fc039618b4563313cdab07d6726ff7815d78d` |
| Audit receipt SHA-256 | `11814cf07516d5d0c3e18822e5d90ca827ed6ebbfdd4c8f75eb89179de5059bf` |
| First official scoring start | 2026-09-26 20:08:25.613 JST |
| Full result checkpoint | `63a123a371d486f58c9c4d726a82a73e9c8a3c3b` |
| Scorecard receipt SHA-256 | `b8caf7a1f6fc0d2a0dcef3c8d06bcaf628ba2ce840bd2d40c96e0b75506aa2c2` |
| A/B selection JSON SHA-256 | `5986e63374ec3205bf4c6c2fdf4daccf0bdd1e457f9fb15de684f4c5cf9b01b5` |
| Durable full report archive SHA-256 | `2eae6515a198d1ee496e09948297c94a139be98230d65f0278ae39d7a494b402` |

The launch execution is a direct child of the required-CI SHA and changes only the launch marker. The first attempted launch `36233376942` failed transport validation before dependencies/preparation/fitting (0 fits); the narrow metadata transport repair and successful CI are preserved. Do not count the failed transport attempt as another learning experiment.

The previous Work stopped at preparation, before fit start was confirmed. Preserve that reporting/procedure gap; the subsequent successful fit step is verified *in this post-run Work*. Claude review provenance remains `USER_RELAYED_REVIEW_SUMMARY`; there is no claim of a direct independent Claude execution or a complete raw review transcript.

## Audit scope and limits

The independent audit verified exact archive and extracted bytes; frozen protocol, 52 source files, seven baseline files and dependencies; all 64 model bundle hashes and fit-grid identities; 128 fit-journal events; Entry/arm/fold/head/configuration identities; all 656,247 checkpoint identities; all two-head labels, complete-window masks and maturities reconstructed from raw data; support and reconstructed weighting statistics; fitted train-only medians/categories; OOF shapes/keys/value masks; and all 34 ledger hashes with 17 A/B byte-identical pairs. Ledger checks validated Entry identity, execution references/prices/times, evaluator formulas, owned-prefix null semantics, current-score joins and safety/exposure. Full 16-candidate scorecards are A/B byte-identical. An independent recalculation of 32 candidate/arm gates found zero numerical or boolean mismatches.

Scope is explicit: no full causal policy replay or reconstruction of every persistence/missing-intent transition occurred in this Work. Replay assurance combines frozen source, successful pre-performance CI, original receipts, A/B identity and independent saved-row checks. Pattern187 was not fully regenerated in the post-run data audit. Actual training weight arrays were not persisted; their support/weight statistics were independently reconstructed and the frozen training code was verified. Saved estimators were deserialized solely for metadata/attribute inspection under local sklearn 1.8.0 versus recorded 1.7.2; the compatibility warning was retained, and no fit or predict was called. Required CI uses the frozen numerical versions.

The frozen scorer and selection rule are unchanged. Supplemental comparisons require resolved execution and finite metrics on both matched sides; these populations can differ from the frozen scorecard. Supplemental strict pairing and ratio-of-sums diagnostics do not replace or alter a gate. Capture median is not a ratio of sums. Owned-peak giveback is null for incomplete owned prefixes; post-exit upside is a different measure. C/F outputs are classification scores, not independently calibrated probabilities or proof of structural thesis failure.

## Result and evidence map

All 16 candidates fail the overall +2.00% Mean Net gate in both arms; all six opportunity-bucket completion gates also fail for every candidate in both arms. Coverage and concentration gates pass all 16. Relative winner/retention/loss passes cannot override these failures. At sell cost 0.20pp, no candidate passes the PF gate in either arm. Selection does not reach ranking/tie-break selection because no candidate is eligible.

Development cohort: 2,155 outcome-exposed opportunities across 58 sessions. Scored OOF population: 1,267 opportunities per arm across 34 sessions, with 1,150 IMMEDIATE and 1,107 R1 frozen fills; 117/160 no-Entry cases. In >=5% bucket, resolved return N=387/381; capture N=377/363. Do not describe this as Fresh/OOS, independent prospective evidence, or portfolio profit.

All paths below are relative to `docs/evidence/phase57-comprehensive-exit-v1/`:

| File | Use |
|---|---|
| `GEN2_POST_RUN_REPORT_R43.md` | Japanese report, all-candidate numerical tables and interpretation |
| `GEN2_PRECOMMIT_R41.json` | Sole frozen candidate/label/feature/selection/gate contract |
| `r43-result/artifact-audit.json` | Combined pre-performance audit PASS and component findings |
| `r43-result/data-audit.json`, `ledger-audit.json` | Independent detailed component receipts |
| `r43-result/lineage.json`, `audit-checkpoint.json` | Timing, source hashes, previous handoff gap |
| `r43-result/formal-negative-result.json` | Formal negative decision/checkpoint; its CI=PENDING is a historical snapshot superseded below |
| `r43-result/independent-gate-crosscheck.json` | Independent 32-combination gate verification |
| `r43-result/scorecard-receipt.json` | Frozen score hashes, A/B identity, no-fit/no-replay selection |
| `r43-result/candidate-summary.csv` | 32 candidate/Entry rows, full precision and all overall metrics/eligibility/cost/concentration |
| `r43-result/bucket-summary.csv` | 224 candidate/Entry/bucket rows including NOT_EVALUABLE |
| `r43-result/full-scorecards-and-reports.zip` | 53 exact original files: both 16-candidate scorecard sets and selection, complete supplemental JSON/CSV, all pair/metric details and receipts |
| `r43-result/gen1-diagnostic-comparison.json` | Hash-verified R36 diagnostic comparison, never a selection competitor |
| `r43-result/manifest.json` | SHA-256 of every committed R43 result file except the manifest itself |

The archive includes `source-file-hashes.json`; check every inner file's original byte length and SHA-256. Its contents use `scorecards/` and `supplemental/` prefixes. The two small `r43-result/scorecards/run-{a,b}/selection.json.gz` files are exact convenience copies for CI verification.

## Required post-run CI

SUCCESS: [run 36238525156](https://github.com/Iam-2squared/ark-terminal/actions/runs/36238525156), exact head `63a123a371d486f58c9c4d726a82a73e9c8a3c3b`, job `108394625404`. 35 R43 synthetic/corruption/report tests plus 18 unchanged R41 scoring/runtime tests = **53 PASS**. All 15 committed result-file hashes, all archive inner hashes, original A/B selection and fixed selection recomputation passed. The dedicated CI performed zero model fits, policy replays, provider calls and protected data opens.

Artifact `10904557327`, `phase57-exit-gen2-postrun-r43-36238525156`, 2,670 bytes; ZIP SHA-256 `5edd0581926c26a55939988c3011b3a2d4f95271f2d5d201b22f143104979935`. Downloaded independently and verified. CI receipt SHA-256 `7fe6c1408f1cc13b94d7f859bd892af0e25eab50f9c842beac40ec56e300c518`.

The exact original receipt and both test logs are saved in `r43-closure/`, with `ci-closure.json` recording run/job/artifact identities. Final closure changes only this report/handoff and CI/operational evidence. The tested code and result bytes remain at the exact successful CI SHA. The final documentation commit uses `[skip ci]` to avoid another round of legacy PR reruns; this does not skip the required R43 CI, which has already completed successfully.

### Legacy automatic CI side effects — separate operational observation

Research-branch pushes also synchronized the existing Draft PR and its broad cumulative path filters. They automatically started historical workflows: 88 run records at the audit checkpoint SHA and 89 at the result SHA. A read-only inspection observed 18 historical replay steps. These are not all synthetic tests, so **do not generalize the R43 zero-fit/zero-replay receipts to every workflow in the repository**. This duplication was an unintended consequence of saving the research checkpoints; no manual rerun or new legacy experiment was dispatched.

Snapshot `r43-closure/legacy-auto-ci-snapshot.json` records the exact run/job/step, frozen workflow command and conditions. At that snapshot, earlier-checkpoint runs `36237879740` (job `108392879368`) and `36237879842` (job `108392879632`) were performing legacy 77,214-row State-v2 reconstruction/replay; their result-checkpoint successors `36238533530` and `36238533881` were pending. Historical one-minute replay `36238533631` had completed. **Do not wait for these nonrequired historical jobs to close R43.** Their status can change after the snapshot.

No R41 finite-learning restart or Capital workflow was present in either exact-head run collection. The inspected expansion acquisition gate skipped acquisition and reused existing material; the metadata probe recorded `PRESERVED_EXISTING_METADATA_NO_REQUESTS`. This is not a complete audit of every provider/protected-data/fit operation in all legacy jobs; unknowns are explicit in the snapshot. No legacy performance outputs were inspected or used for Gen2 selection. No cancel tool is exposed in this connected GitHub toolset; none of these runs was manually cancelled. Future documentation-only saves should avoid these duplicate triggers; this closure uses `[skip ci]` after required R43 CI success.

## Safety and exposure

All nine values remain **false**: executionAllowed, brokerWriteAllowed, excelOrderWriteAllowed, rssOrderFunctionAllowed, liveTradingAllowed, paperTradingAllowed, automaticPromotionAllowed, productionUpdateAllowed, transmitted.

Common Holdout, REPORT19, Validation, OOS, Fresh and Prospective remain unopened. Provider requests=0. Entry IMMEDIATE and ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF remain permanently frozen. No main merge, force push, live/paper trading, production promotion, or order submission occurred. Within the R43 audit/scoring/reporting lane, exposure changed only by officially inspecting the already outcome-exposed Development Gen2 performance after the pre-performance freeze and audit checkpoint.

## Capital readiness, not Capital completion

Existing R34 cash-only engine and R35 causal priority were reviewed during artifact/CI work: initial JPY 1,000,000, 100-share lots, MAX3 primary and MAX4/MAX5 sensitivity, confirmed exit cash release before sizing, fresh known-now MTM, and cash never negative. Priority remains newEligibleRank ASC → savedV1Score DESC → symbol ASC. No future outcome is admitted to ranking/sizing.

No Gen2 Capital integration or replay was performed. The historical R37 guard accepts the older freeze schema; a Gen2 adapter and historical event/rank/MTM bridge would be required *only after an authorized valid SELECT*. Missing terminal/fresh marks must censor or leave sizing unresolved, not create cash or substitute stale/cost/future marks. Existing capital allocation and >=5% share diagnostics are not complete. These are preserved readiness findings, not progress claims or authorization to implement them after NO_SELECTION.

## Restore and next action

1. Fetch the actual latest research HEAD and this handoff first; inspect later commits, PR #587 and active Actions for other writers. Do not assume a saved SHA is still HEAD.
2. Verify `r43-result/manifest.json`, the full report ZIP and its inner hashes. Read the frozen selection and independent gate receipt. This recovers the formal result and every reported number directly from GitHub without fitting or replay.
3. For deeper raw audit only, download Action run `36233758837` artifact `10904078164` and verify the exact ZIP digest above. The raw artifact expires 2026-12-25; this is not permanent model storage. Full formal scorecards/reports/receipts are retained in Git, independently of Action retention. Do not refit or recreate missing raw evidence silently after expiry.
The historical R35 raw/core source is run `36220335998`, artifact `10899151845`, ZIP SHA-256 `a12852e36f270e247a9a0bb7f0f7f618da934297c05f7c687fccb7ceade40434` (Action retention expires 2026-10-26). Corrected R36 diagnostic source is R38 run `36227400437`, artifact `10901355944`, ZIP SHA-256 `993c3a744b971ae8ccada9784a2c26180beb2abfd3c9c46e8b854ba28ce2f510`. These historical source identities are not permission to open new partitions or refit.

4. Audit source and tests are `scripts/phase57_exit_gen2_{audit,data_audit,ledger_audit,report}_r43.py` and their corresponding tests. Frozen scoring remains `scripts/phase57_exit_gen2_scoring_r41.py`. For raw data reconstruction, use the pinned R35 artifact sources identified in audit receipts; no new provider data.
5. Current research is closed **NO_SELECTION_STOP**. There is no valid Final EXIT for Capital. Any next generation requires an explicitly authorized new research scope and a new pre-performance protocol; this Work neither starts it nor declares an architecture causal conclusion from the failed grid.
