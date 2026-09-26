# R42 controlling handoff — R41 finite workflow running

Observed 2026-09-26T09:50:08.541Z. This is the controlling next-Work restore document.

| Item | Verified value |
|---|---|
| Active Action | [36233758837](https://github.com/Iam-2squared/ark-terminal/actions/runs/36233758837) |
| Exact execution SHA | `c031976a319130b6be379586147fff53cee6f741` |
| Protocol SHA256 | `5fdc059936ba31466a7dace520f218353c634e6c8444d20d5ab21069c745deb4` |
| Launch marker SHA256 | `b3655a5197221b7aa519c47cb263511c81b86228bf8a4e77efc638748d59e444` |
| Frozen candidate / fit budget | 16 policies / 64 expected fits |
| Required exact-source CI | 36233629987 SUCCESS, 97 tests; source `0d20b9aee00ff0b667f698e4c93d5f92ee057f38` |
| Required CI archive | artifact10903097039; SHA256 `e489d3500b06a790868119da0718ed71d24addeeb9a7099980fd227dadedaf7b` |
| Existing EXIT foundation CI | 36233629977 SUCCESS |
| Last observed stage | launch authorization PASS; frozen dependencies PASS; R35 restoration PASS; feature/label PREPARATION IN_PROGRESS |
| Fitting / replay | PENDING at observation; actual fit start and completion not yet confirmed |
| Performance / selection | Not inspected; no scorecard; selection null |
| Controlling handoff branch | `research/phase57-gen2-r41-handoff-20260926` |

Machine-readable snapshot: `GEN2_RUNNING_HANDOFF_R42.json`. The complete observed job steps are included. The workflow continues on GitHub after this Work ends; no completion waiting, polling automation or duplicate launch is created.

## Controlling stop and scope

This handoff supersedes earlier operational next-step instructions for this Work. The user's permitted stopping point is a normally launched, verified finite Gen2 GitHub Actions workflow with exact execution identity, frozen protocol/counts, artifact plan and Safety/Exposure confirmed. This Work stops after successful launch preflight and R35 restoration, while feature/label preparation is running, and does not spend Work time waiting for Actions computation. The model-fitting step itself is still PENDING in the last observed job metadata; actual model fitting has NOT been claimed as started. No Gen2 scorecard, SELECT/NO_SELECTION decision, Final EXIT Freeze or Capital MAX3/MAX4/MAX5 result has been inspected or produced here. A running job is not a performance PASS.

Repository: `Iam-2squared/ark-terminal`; branch: `research/phase57-long-only-cash-equity`; PR: #587, Draft and unmerged. Do not merge main, force push or alter Entry Freeze. This handoff is on dedicated branch `research/phase57-gen2-r41-handoff-20260926`, whose parent is the exact execution SHA. The execution branch deliberately remains at `c031976a319130b6be379586147fff53cee6f741` so the Action's still-pending pre-fit HEAD check can succeed. Do not advance the execution branch while preparation/pre-fit checks are pending. Restore the execution SHA for computation; use this dedicated handoff branch for controlling instructions.

## Completed chain and immutable anchors

- R36 Formal Closure remains `NO_SELECTION_STOP`: original 144 fits, 24 policies, 0 passing candidates. R38 repaired only NumPy-scalar owned-giveback reporting and rescored saved ledgers with zero new fits/replays; R39 preserved the negative result.
- R40 comprehensive Failure Anatomy, all 24 complete candidate summaries and Claude finding dispositions are committed at `0ba0112fff98cd1d8d864dc1967bbd76095e8d66`. Claude evidence is a user-relayed review summary, not a direct complete Claude response. Universal HGB superiority and MAX-alone causal claims remain PARTIAL. Measured association is not causal attribution.
- Gen2 architecture, Continuation/Failure labels, feature/causality/leakage contract, finite search space, selection rule and Completion Gate were frozen in that same commit, before implementation or Gen2 performance.
- Frozen protocol `GEN2_PRECOMMIT_R41.json` SHA256: `5fdc059936ba31466a7dace520f218353c634e6c8444d20d5ab21069c745deb4`.
- Four classifier specifications × two heads × two Entry arms × four folds = 64 fits. Two threshold pairs × persistence 1/2 per specification = 16 policies. No extra candidate, fallback, search expansion or performance-dependent change is authorized.
- Original implementation `33a8e73ffca450d078403dd9a7149237c75aa809` passed Gen2 CI `36233205154` (91 focused tests) and EXIT foundation CI `36233205098`. Its CI archive SHA is `777c0c8334b1bae3901c126c3e8fd8209ee058ef2e1189eb6757c2f735dc5f6d`, artifact `10903351214`.
- First launch `36233376942`, SHA `8ecad9f0fd412e9ceb9ed04cc1e691979ad60d99`, failed on legitimate GitHub comparison URL validation before dependencies, preparation, fit or replay. It consumed zero Development fits. Archive `10903576190` SHA `f4830ec87fc55c00de2397056e657fbba01f49f4d09b50ca381482e6fe0456b8` and job step evidence are preserved under `r41-zero-fit-launch-failure/`.
- Launch transport repair `0d20b9aee00ff0b667f698e4c93d5f92ee057f38` changes only URL validation and explicit evidence checks for that single failed zero-fit run, plus tests/docs. It changes no protocol, feature, label, model, split, threshold or gate. Local tests: 84 Gen2 + 13 R40 = 97 PASS. A new exact-source CI and marker-only commit precede the active run specified above. Original failure evidence remains intact; no silent rerun/resume was used.

## Artifact plan

The active heavy workflow uploads `phase57-exit-gen2-r41-RUN_ID` for 90 days, including partial failures. It includes `gen2/`, `gen2-logs/`, the prerequisite `gen2-contract/`, and any early `partial-failure-*.json`.

Expected completed Gen2 content: execution/protocol/source/dependency/input hashes; row identity; independent training labels with masks, reasons and known-at/window-end metadata; 64 model/preprocessor bundles and hashes; single immutable OOF prediction archive; all 16 policy ledgers in each `gen2/run-a/` and `gen2/run-b/`; `HOLD_TO_TERMINAL_DIAGNOSTIC.jsonl.gz` in both; ledger hash manifests; fit/replay receipts and final `AWAITING_POST_RUN_AUDIT` receipt. The neutral ledger is diagnostic only and cannot become a 17th candidate or fallback. A/B reuses the same fitted models/OOF predictions; it is not a second independent 64-fit run.

The temporary prepared-data pickle is deliberately outside the uploaded artifact. Reconstruct source/features from immutable GitHub inputs and receipts if required; never refit merely to restore scratch. Next-Work scoring requires only audited ledgers and pinned opportunity records, not a fresh model fit.

Historical source archives, already independently verified:

| Evidence | Run ID | Artifact ID | ZIP SHA256 |
|---|---:|---:|---|
| R35 observation preparation | 36220335998 | 10899151845 | `a12852e36f270e247a9a0bb7f0f7f618da934297c05f7c687fccb7ceade40434` |
| R36 original finite result | 36222151340 | 10901042535 | `1c574848c6106d34c1d53e902b339e1be2f43b7b5c615e40a7010c29332d997a` |
| R38 corrected scoring | 36227400437 | 10901355944 | `993c3a744b971ae8ccada9784a2c26180beb2abfd3c9c46e8b854ba28ce2f510` |

Those older artifacts expire 2026-10-26. R40 overall and all 24 complete candidate summaries are durable Git files under `r40-result/`. Detailed derived rows/trajectories can be reconstructed without fitting or policy replay using `python -m scripts.phase57_exit_failure_anatomy_r40 --root <extracted-r36-root> --core-root <extracted-r35-root> --corrected <extracted-r38-root> --out <new-output>`. Verify all input archive hashes first; compare `complete-derived-output-hashes.json` after reconstruction.

## Next Work: restore and audit before performance interpretation

1. Read this controlling handoff, `GEN2_PRECOMMIT_R41.json`, `GEN2_ARCHITECTURE_CAUSALITY_PRECOMMIT_R41.md`, `GEN1_FORMAL_CLOSURE_CLAUDE_DISPOSITION_R40.md`, `GEN2_IMPLEMENTATION_PREPERFORMANCE_R41.md` and `GEN2_ZERO_FIT_LAUNCH_REPAIR_R41.md` from GitHub. Refresh branch HEAD, PR and active run status. Do not launch a duplicate.
2. If the run is still active, leave computation on Actions. If failed, preserve partial evidence and distinguish calculation failure from NO_SELECTION. Investigate actual fit attempts/completed bundles; do not silently rerun, refit, reduce the grid or discard failures.
3. On successful completion, download the exact run's artifact, record ID/digest, verify ZIP SHA and execution/protocol/source/dependency/input hashes. Require final status `AWAITING_POST_RUN_AUDIT`, exactly 64 completed model fits, 16 candidate policies, 32 candidate replay passes, two diagnostic replay passes, A/B byte equality, selection null, zero scorecards and no promotion.
4. Verify all 64 bundle identities/hashes, OOF array keys/shapes/row order, fold/arm/head lineage, terminal NaNs, finite valid OOF scores and absence outside scored sessions. Validate train-only preprocessing, independent head eligibility and support slices; verify label metadata maturity and future-information isolation. Do not equate occurrence scores with calibrated probabilities or structural failure.
5. Independently require complete expected ledger IDs and populations in every candidate, arm and A/B run. Full Development is 2,155 opportunities, 58 sessions, 656,247 checkpoints; filled Entries are IMMEDIATE 1,963 and R1 1,885. OOF covers 34 sessions and 1,267 opportunities per arm, with fills 1,150/1,107 and No Entry 117/160. OOF six-bucket populations are 85/220/246/151/106/393, plus 66 not evaluable. Check these against the immutable inputs; never replace them with all-Development Winner N=666.
6. Keep No Entry, unavailable labels, invalid/missing scores, missing ordinary OPEN and censored terminal distinct. Do not drop unfavorable cases. The original cohort's 63 terminal-reference missing cases are not a candidate-specific OOF censor count. Preserve null certified giveback for incomplete owned prefixes. Validate R24 exact references, lunch, auction, exit-candle ownership and cost rules.
7. Only after independent artifact audit PASS, call `phase57_exit_gen2_scoring_r41.score_audited_artifact` on the saved flat `run-a/<candidateId>.jsonl.gz` and corresponding `run-b/` ledgers. The audit must supply `GEN2_ARTIFACT_AUDIT_PASS`, protocol SHA and exact `inputLedgerHashes` for all 34 ledgers. Generate full arm/bucket/fold and metric-specific paired scorecards and compare A/B outputs. No model fitting or policy replay is needed for scoring.
8. Apply only frozen R25/R31 numeric gates in both arms. Among passing candidates minimize worst capability rank, then rank sum; any best tie is NO_SELECTION_STOP. Preserve a negative result without extra search. Only SELECT authorizes a Final EXIT Freeze; only after that may Capital MAX3 PRIMARY / MAX4 / MAX5 proceed under existing contracts. R37 is preparation only, not a completed portfolio study.

## Safety and Exposure

Safety9 all false: executionAllowed, brokerWriteAllowed, excelOrderWriteAllowed, rssOrderFunctionAllowed, liveTradingAllowed, paperTradingAllowed, automaticPromotionAllowed, productionUpdateAllowed, transmitted. R41 provider requests 0; protected partitions opened 0. No orders, live/paper trading, production changes, main merge or force push. Entry Dual Freeze `4878a1cc53430e816261dea0fb16aeb53b3c238d` remains unchanged.

All 2,155 opportunities remain outcome-exposed Development. No Fresh/OOS, universal model superiority, live profitability, completed EXIT or Capital result is claimed. Gen2 performance inspection is deferred to the next Work; active fit counts are expected counts until the artifact audit proves completion.
