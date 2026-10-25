# Phase57 Gen3 R45 — verified implementation / learning launch handoff

Saved at JST: 2026-09-27T00:12:29+09:00.
Repository: `Iam-2squared/ark-terminal`; research branch `research/phase57-long-only-cash-equity`; Draft PR #587 remains unmerged.
Basis research HEAD: `98345947c14ffd40c6283ce4e9be33139989b609`.
Tested implementation / intended execution SHA: `a65b3530df53a7a28334d7d1d4218d561e38b06b`.
Dedicated CI branch: `research/phase57-gen3-r45-ci-20260926`, without a PR.

## 現状

The frozen Gen3 implementation and required pre-performance CI are complete. This is **implementation readiness**, not an EXIT performance PASS or a Final EXIT Freeze. No Gen3 estimator has been fitted and no Development candidate policy has been replayed by this implementation/CI lane at this checkpoint.

The user subsequently explicitly authorized continuing in this chat through Action launch (「ここで進めて。action起動までやって」 and 「@GitHub つづけて」). The earlier Work instruction to stop before launch remains a historical stop boundary, not a revocation of this later approval. The protocol bytes, labels, features, candidate set and performance gates have not been modified. The launch approval will be recorded separately in the new `GEN3_LAUNCH_R45.json` marker only after publishing these tested sources.

## Existing research remains unchanged

- Entry Dual Freeze: `4878a1cc53430e816261dea0fb16aeb53b3c238d`; IMMEDIATE and ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF unchanged.
- Gen1 R36/R39 and Gen2 R41/R43 remain formal NO_SELECTION_STOP. No old candidate is selected, revived, used as a fallback, or retuned.
- Gen3 protocol: `GEN3_PRECOMMIT_R45.json`, SHA-256 `e7b38e7e6aaf909926852467152fffef2532f58f960a95e6f2d18efd66f5d1b5`.
- Exactly 4 structural policies, one HGB+Pattern187 prediction spec, 3 heads, 2 Entry arms and 4 temporal folds: exactly 24 model fits planned.
- Existing completion gates remain intact, including overall Mean Net >=2.00% and >=5% Mean/Median Net >=3.25%/2.00%, Median Capture >=50%.

## 実作業と前回報告の区別

The previous chat reported local code and 87 tests, but that local implementation was not present in the active runtime at the start of this continuation and had not reached GitHub. Those claims were **not** accepted as launch evidence. The implementation was reconstructed against the immutable GitHub protocol and reverified. The 79 CI tests below are the actual current suite, not a claim that the old 87 tests were rerun or byte-identical.

A source-recovery-only workflow copied an explicit hash-pinned source/Development-input allowlist from the existing freeze, with no fit, replay or new provider acquisition. Recovery run `36248952985`, artifact `10908397617`, ZIP SHA-256 `3cba03b6615fa6d3d3f3bfa074877917134168ca8a1da1b2b278368f09aa2530`. Its default artifact export omitted two inherited hidden `.github` files; those were not claimed locally restored. The actual repository CI verifies them, and the required CI export uses an explicit source allowlist with hidden-file inclusion. No credential or `.git` directory is in that allowlist.

Added implementation modules:

- `scripts/phase57_exit_gen3_runtime_r45.py`: pure three-authority state machine, strict transport allowlist, no model/label/evaluator imports.
- `scripts/phase57_exit_gen3_facts_r45.py`: Entry-local State/Signal histories and exact already-closed price facts; UNKNOWN is not FALSE; incomplete owned prefix cannot certify giveback.
- `scripts/phase57_exit_gen3_labels_r45.py`: isolated sampled executable-utility labels and independent Protection eligibility.
- `scripts/phase57_exit_gen3_pattern_r45.py`: frozen two-worker deterministic transport of unchanged Pattern187.
- `scripts/phase57_exit_gen3_data_r45.py`: all 656,247 original row identities, train-only target transport, support-only mode without Pattern regeneration or fitting.
- `scripts/phase57_exit_gen3_runner_r45.py`: one-shot 24 fits, saved actual train indices/weights and preprocessors, immutable OOF predictions, four candidate A/B ledgers plus neutral A/B; no scorecard or selection.
- `scripts/phase57_exit_gen3_preflight_r45.py`: exact tested-source/CI/support/branch/run identity and duplicate-learning guards.
- Two new test modules and contract/learning workflows. No inherited Entry, Gen1, Gen2 or gate file was edited.

Source publication uses the ordinary contents API followed by non-force fast-forward of the research ref. There is no force push, history rewrite, main merge, or security-control bypass.

## 必要CIと独立検証

| Item | Verified identity/result |
|---|---|
| Required workflow | Phase57 Gen3 Contract R45 |
| CI run | 36250723100 |
| CI job | 108428118489 |
| Exact tested SHA | a65b3530df53a7a28334d7d1d4218d561e38b06b |
| CI conclusion | SUCCESS |
| Tests | 79 PASS: 47 Gen3 synthetic tests + 3 narrow Pattern transport/causality tests + 29 inherited runtime/label tests |
| CI artifact | 10908534909; phase57-gen3-contract-r45-36250723100 |
| ZIP SHA-256 | 2f41b3a935334733e4905bd0adff9f092bfd7b68fd9286e38bdde7a7538d44c0 |
| Contract receipt SHA-256 | 8d3853b64669ce0ea252dea9d79ed6ffb7d6e235c1099b0ff475b0607f69eac6 |
| Support gate SHA-256 | 47603e6f659202436098b45311cafd382fb550362c7161a99db1a4fa9e395e9f |
| Tests log SHA-256 | aa98a7eb6e1648f1f378639749750ba6eb02a626d943e473ff6b9a2597136792 |
| Exported source files independently hash-verified | 67 |
| Reconstructed local Gen3 source/workflow files matched to tested bytes | 11 |
| All-support slices | 24/24 PASS |
| Original checkpoint population | 656,247 |
| Local vs CI target, availability, maturity, horizon and reason arrays | equal |

A separate local verification used independent schedule/reference/utility formulas, without importing the new label function: 656,247 rows / 1,968,741 head cells, target mismatches=0 and maturity mismatches=0. The CI arrays were independently compared to that local verified dataset. This is label/support verification, not prediction or strategy-performance inspection.

The required CI artifact contains `contract-receipt.json`, all allowlisted source bytes under `source/`, focused test logs, support receipt, data receipt, label arrays, feature transport and row identities. Verify the GitHub ZIP digest, every receipt `sourceHashes` entry and the support/data output hashes when restoring. The exact tested source remains in Git independently of artifact retention.

### Label support, not model performance

| Arm | Head | Total available labels | Positive | Negative |
|---|---|---:|---:|---:|
| IMMEDIATE | CONTINUATION | 129834 | 32156 | 97678 |
| IMMEDIATE | PROTECTION | 36899 | 16370 | 20529 |
| IMMEDIATE | DETERIORATION | 129834 | 37897 | 91937 |
| ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF | CONTINUATION | 116008 | 28222 | 87786 |
| ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF | PROTECTION | 29166 | 12928 | 16238 |
| ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF | DETERIORATION | 116008 | 33568 | 82440 |

All 24 fold/arm/head train slices passed the unchanged support minima. Across slices: train rows 11,513–101,794; Opportunities 178–1,209; sessions 22–46; positive class rows 5,374–29,853; negative class rows 6,139–76,941. These are descriptive support counts only. Labels and horizons were not adapted to obtain support.

## Launch protocol and artifact plan

1. Publish the tested source plus this documentation-only closure to the research branch, preserving the tested execution SHA. This document's commit uses `[skip ci]` after the required CI succeeded; it does not replace or skip the required CI.
2. Recheck research HEAD, PR and finite workflow runs. Add a separate marker `GEN3_LAUNCH_R45.json` with explicit user authorization, exact execution SHA, protocol hash and successful contract run ID.
3. The marker-only push starts `Phase57 Gen3 Finite Learning R45`. Creating this handoff itself does not start learning.
4. The job preserves the marker outside checkout, downloads the matching CI artifact, checks out the exact tested execution SHA, verifies current research HEAD and marker/closure-only difference, CI source receipt, support and R35 artifact identity.
5. Full preparation recomputes Pattern187 at strict NOW using two workers. Immediately before fitting, the same authorization/HEAD/no-duplicate checks run again.
6. Then and only then, fit exactly 24 models once and replay the four frozen policies twice from a single saved prediction set. No second fit is used to prove A/B replay identity.
7. Emit `AWAITING_POST_RUN_AUDIT`, with 24 fits, 4 candidates, 8 candidate replay passes, 2 neutral passes, A/B ledger identity, scorecardsProduced=0 and selection=null. No successful EXIT selection is claimed by workflow SUCCESS.

Expected learning artifact name: `phase57-exit-gen3-r45-<actual_run_id>`. The actual run ID and stage must be verified from GitHub after the marker push; no run ID is invented here. Keep research HEAD unchanged while preparation/pre-fit guards are active. Record later launch status in a PR comment or separate handoff branch, not by advancing the guarded research branch.

Learning artifact preserves sources/CI authorization, protocol lineage, labels/maturities, row identities/features, 24 models/preprocessors, actual train-support weights, fit journal, saved OOF predictions, all A/B ledgers, authority explanations, missing-reference details, hashes and partial failures. The own-process pickle cache stays outside the exported artifact. Numerical dependencies remain exactly pinned by the frozen protocol.

Any failed finite attempt is preserved; no automatic retry/resume. A failed support/source/identity gate must not be bypassed. If fitting did start, subsequent work must inspect the failure journal before considering any separately authorized technical repair.

## Freeze / Exposure / Safety

At this readiness checkpoint: Gen3 model fits=0; Development policy replays=0; Gen3 performance inspected=false; new market-provider requests=0; protected partition opens=0. Synthetic replay tests are not Development policy experiments. No Entry/Selector refit, Capital replay, main merge, live/paper/production promotion or order transmission occurred.

Safety9 all false: executionAllowed, brokerWriteAllowed, excelOrderWriteAllowed, rssOrderFunctionAllowed, liveTradingAllowed, paperTradingAllowed, automaticPromotionAllowed, productionUpdateAllowed, transmitted.

Only the existing outcome-exposed Development cohort is allowed. Common Holdout, REPORT19, Validation, OOS, Fresh and Prospective stay sealed. Historical bar-end knownAt remains a proxy, not proof of live publication latency. Sparse-path and incomplete owned-prefix limitations remain; source causality and support PASS do not establish profitability.

Dedicated CI branch work avoided broad legacy PR replay triggers. A subsequent research marker push can still synchronize existing broad PR workflow filters; those legacy jobs must be distinguished from Gen3 and must never supply Gen3 selection evidence. Do not claim all repository jobs perform zero work merely because the dedicated Gen3 preflight lane has zero fits/replays.

## 今後の方針 / superseded state

This handoff supersedes only the implementation-pending/current-action portion of `FINAL_PRE_GEN3_ANALYSIS_AND_ARCHITECTURE_R44_R45.md` and the unverified local 87-test status. It does not supersede the frozen R45 protocol or previous negative studies.

Next action is the explicitly approved one-shot launch, not architecture redesign. After the learning job completes, begin with independent artifact integrity and lineage audit, then score all four immutable policies under the unchanged frozen gate. SELECT only if every requirement passes; otherwise NO_SELECTION_STOP. No fifth candidate, hidden threshold, gate relaxation, Entry change or Capital performance comparison is authorized by this implementation checkpoint.
