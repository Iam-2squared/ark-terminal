# R1 execution repair record R9

2026-09-25 JST. One-shot execution only; scheduled automation remains stopped.

## Failed executions retained

1. Dedicated CI run `36099241905` at `f62e40847a8b77d309c9ace700c2c4ea945f239d` failed before any model fit: the frozen legacy import chain needs pandas, but the newly added workflow installed only numpy/scipy/sklearn. Repair commit `afb38b7a5421ca4f6ff6d439bf89096236efd119` supplies existing `pandas==2.2.3`. The 36 configurations, input builder, model code, numerical model dependencies and all gates are unchanged. The initial failure is not a PASS.

2. Local `run-a` completed nine inner fits for outer fold 1, wrote its complete 36-configuration inner comparison, and was terminated by the container memory limit before its first outer-test stream completed. Linux cgroup records `oom=1`, `oom_kill=1`; no complete 2,155-candidate scorecard was produced. Partial model files, label accounting, inner comparison and log are preserved. This is an execution failure, not a rejected performance hypothesis.

## Authorized same-protocol recovery

A new append-only output directory will rerun the identical frozen R8 code and input hashes after releasing unused local memory. No model, hyperparameter, feature, label, fold, wait horizon, trigger threshold, preservation threshold or sampling rule is changed in response to the observed inner results. All repeated fits are same-protocol execution/reproducibility work and must be counted separately from the 36 unique configurations. Never overwrite the failed output directory.

The dedicated CI independently reconstructs the same prefit data and verifies its fixed hashes before fitting. CI completion and two-run determinism remain pending, not presumed.

## Independent checks completed while the original fit ran

A deterministic SHA256-ID sample of 32 current Opportunities, selected without outcomes, covered 155 available checkpoints. Deleting or modifying the future suffix produced identical closed inputs, new 90-column overlays and immutable current signal/State outputs in 310 variants. All 149,900 row metadata timestamps precede their decisions. Five outer and fifteen inner temporal/purge layouts passed identity checks. The fast inner metric implementation equals the canonical current ONE_MINUTE comparator for population, fills, valid EP count, mean EP and all +1/+2/+3/+4/+5 Capture counts/rates. This is scoped implementation evidence, not independent historical knownAt certification or OOS validation.

Provider requests=0; protected data opens=0; main unchanged; all nine safety flags remain false.
