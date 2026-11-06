# R41 implementation and pre-performance verification

Controlling scope: finish design, implementation, focused verification and required CI; launch one finite GitHub Actions fit/replay; stop this Work after fitting begins. Do not wait for its completion. Artifact audit, Gen2 scorecards, SELECT/NO_SELECTION, Final EXIT Freeze and Capital MAX3/MAX4/MAX5 belong to the next Work.

## Frozen before implementation and performance

Architecture/precommit commit: `0ba0112fff98cd1d8d864dc1967bbd76095e8d66`.
Protocol: `GEN2_PRECOMMIT_R41.json`.
SHA256: `5fdc059936ba31466a7dace520f218353c634e6c8444d20d5ab21069c745deb4`.
The protocol bytes, 16 candidates, 4 prediction specifications, 2 heads, 2 Entry arms, 4 folds and 64 expected model fits are unchanged.

## Implementation boundaries

- `phase57_exit_gen2_labels_r41.py`: exact anchor, independently complete event windows, separate head masks, maturity timestamps, lunch/calendar handling and terminal exclusion.
- `phase57_exit_gen2_data_r41.py`: audited R35 A/B files, fixed row identity, original CORE fields, three calendar features, canonical causal Pattern187 and separate label arrays. Future label availability is not a feature.
- `phase57_exit_gen2_runtime_r41.py`: protocol-hash-pinned candidate admission; only scores, freshness, counter, candidate and NOW enter the action rule. Invalid scores HOLD; 925 forces the terminal path.
- `phase57_exit_gen2_runner_r41.py`: all support slices before any estimator; train-only preprocessing; exactly 64 fits; immutable saved OOF scores; 16 independent Run A/B policy replays plus the nonselectable hold-terminal diagnostic. Native scalar transport preserves valid owned-peak values. No scorecard or selection is called.
- `phase57_exit_gen2_scoring_r41.py`: next-Work-only scoring after independent artifact audit; unchanged frozen numeric gates; worst capability rank then rank sum; best tie means NO_SELECTION. It is absent from the fit/replay call path.
- `phase57_exit_gen2_preflight_r41.py`: required CI and full transitive source identity, current branch SHA, marker-only direct-child launch, attempt 1, no duplicate Gen2 run and no active R36 fitting run.

R36 and its existing model/prediction/ledger artifacts remain unchanged. R40 repairs only its new NumPy scalar serializer and preserves the failed attempt separately; the complete R40 summaries and hashes are committed with the architecture freeze.

## Verification before any Development fitting

The accompanying `r41-local-focused-tests/` evidence records the complete synthetic/focused suite and exact source hashes. Tests cover independent label masks, full-window positive and negative labels, missing anchors and bars, auction exclusion, future-prefix mutation, train-only preprocessing, every support slice, fixed fit accounting, hard convergence failure, invalid scores, persistence, execution ownership, missing-open behavior, label-poison replay isolation, saved-prediction A/B identity, provenance failures and selection ties.

Tiny generated-data estimator integration checks are synthetic tests; they are not Development research fits or candidate performance inspection. Local runtime is Python 3.12 / sklearn 1.8, so the required GitHub contract CI repeats the tests on the frozen Python 3.13 / sklearn 1.7.2 dependency set. Local success alone does not authorize the launch.

Independent code reviews found no blocking label/feature/runtime leakage or workflow integration defect after repairs. Next Work must independently verify complete expected opportunity/Entry-arm ledger populations and IDs, in addition to file hashes, before issuing `GEN2_ARTIFACT_AUDIT_PASS`.

## Required CI and launch protocol

1. Push this implementation without the launch marker. `Phase57 Gen2 Contract R41` runs all Gen2 focused tests plus the 13 R40 tests, then saves the protocol, complete transitive source hashes and zero-Development-fit receipt.
2. Require that exact implementation-SHA CI to finish successfully; verify its artifact receipt and source/protocol hashes.
3. Commit only `GEN2_LAUNCH_R41.json` as its direct child, referencing the successful CI run and immutable R35 artifact. No code changes are permitted in the launch commit.
4. `Phase57 Gen2 Finite Learning R41` rechecks authorization, restores R35, builds features and isolated labels, rechecks latest HEAD and duplicates, then enters the separate finite-fitting/replay step.
5. Once actual fitting has begun, save the exact execution SHA, run ID, protocol hash, expected counts, artifact plan and Safety/Exposure in a new controlling handoff. Stop this Work without waiting for completion or inspecting Gen2 performance.

The heavy workflow is triggered only by that marker, not by implementation or handoff documents. Source changes never silently start fitting. Failed or partial runs preserve evidence and cannot silently resume or rerun.

## Artifact and safety contract

Required CI artifact: `phase57-exit-gen2-contract-r41-RUN_ID`.
Heavy artifact: `phase57-exit-gen2-r41-RUN_ID`, retained 90 days, uploaded even on failure. It contains protocol/source/dependency identity; pinned input references; row identity and label metadata; all 64 model/preprocessor bundles with hashes; immutable OOF predictions; 16 candidate ledgers plus the neutral diagnostic in both `run-a/` and `run-b/`; byte-identity manifests; receipts and partial failure evidence. The temporary pickle cache stays outside the artifact.

All nine Safety flags are false: executionAllowed, brokerWriteAllowed, excelOrderWriteAllowed, rssOrderFunctionAllowed, liveTradingAllowed, paperTradingAllowed, automaticPromotionAllowed, productionUpdateAllowed and transmitted. Provider requests 0; protected partitions opened 0; all existing opportunities remain outcome-exposed Development. No Entry changes, new providers, Fresh/OOS claim, main merge, force push, trading, production update, Final EXIT Freeze or Capital replay is authorized by this checkpoint. Gen2 Development fits, candidate replays and performance inspection are 0 before launch.
