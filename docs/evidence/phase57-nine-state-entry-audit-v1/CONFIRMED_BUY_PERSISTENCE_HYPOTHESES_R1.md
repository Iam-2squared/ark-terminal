# Phase57 9-State Entry — Confirmed BUY Persistence Hypotheses R1

2026-09-24 JST / Development-only / precommitted before candidate replay.

## Evidence available before this lock

The eight nonzero-T0 semantic review lanes were frozen before sealed scoring and all reviewed cases matched the fixed Contract/baseline labels. `RISE_STOP` has no observed T0 or later checkpoint rows. The authoritative Nine-State Anatomy v2 and the accepted one-minute artifact show that the current Entry remains far from the user's aspirational mean EntryPosition `<0.15` target.

A causal Low-centered attribution diagnostic was then frozen and run without changing decisions. It built all State-v3 / frozen-six-signal witnesses before opening evaluator-only Oracle Low. The dedicated run `35896350202` passed closed-bar and baseline-identity guards. It showed that the current one-minute entries frequently occur before the eventual Development Oracle Low: RISE about 76.7%, DROP about 55.2%, PULLBACK about 61.7% among comparable filled/evaluable cases. Around the evaluator-only Low, BUY-state prevalence is depressed and rises again after the Low. This supports a timing-instability diagnosis, not use of Oracle Low as a decision input.

No candidate defined below has been replayed before this lock. No threshold sweep is authorized.

## Shared minimal causal rule

Candidate family ID: `CONFIRMED_BUY_PERSISTENCE_V1`.

For one target initial State at a time, replace only that State's current intent timing with the following rule; every non-target opportunity remains exact ONE_MINUTE baseline.

At every available active-minute checkpoint, recompute the **unchanged** State-v3 classifier from previous session + current closed-price prefix, at one-active-minute cadence. Retain the existing six frozen Signals unchanged.

A target opportunity may issue BUY intent at the first checkpoint satisfying either:

1. current State is one of the existing frozen BUY states (`RISE`, `SHARP_RISE`, `REBOUND`) **and** an existing frozen Signal fires at that same checkpoint; or
2. the current and immediately previous active-minute checkpoints are both existing BUY states (two consecutive BUY-state observations).

Otherwise WAIT. There is no fixed-time fallback. A Signal while the current State is a WAIT state is not sufficient. No new Signal, price threshold, recovery threshold, Volume, Dictionary or learned model is introduced.

The two-observation persistence is the minimum possible persistence check beyond a single State flip: one additional causally closed active-minute observation. It is fixed here before any candidate performance is measured.

## Independent State hypotheses

### RISE — hypothesis 1/1

ID: `RISE_CONFIRMED_BUY_PERSISTENCE_V1`.

Current RISE buys immediately at T0, while the causal anatomy shows that most comparable filled RISE entries precede the eventual evaluator Low and that many RISE prefixes leave BUY-state near that Low. Hypothesis: suppressing the unconfirmed T0 BUY and requiring the minimal persistence/concurrence rule above will reduce unstable early RISE entries without materially reducing Opportunity preservation.

### DROP — hypothesis 1/1

ID: `DROP_CONFIRMED_BUY_PERSISTENCE_V1`.

The accepted one-minute DROP baseline enters at the first existing Signal or first BUY-state transition. More than half of comparable filled DROP entries still precede the eventual evaluator Low. Hypothesis: requiring either State+Signal concurrence or two consecutive BUY states will filter transient local rebounds while retaining the accepted one-minute cadence.

### PULLBACK — hypothesis 1/1

ID: `PULLBACK_CONFIRMED_BUY_PERSISTENCE_V1`.

The accepted one-minute PULLBACK baseline has high Fill but a majority of comparable filled entries still precede the eventual evaluator Low. Hypothesis: the same minimal confirmation rule will reduce premature local-bounce entries while retaining most Opportunities.

These are three independent one-shot State hypotheses measured in one deterministic run for efficiency. Acceptance of one State does not imply acceptance of another.

## Precommitted acceptance / rejection gate — each State separately

Candidate may be retained as a provisional component for its target State only if **all** hold versus the immutable ONE_MINUTE baseline on the original fixed T0 cohort:

1. common-case paired EntryPosition mean improves (`candidate - baseline < 0`);
2. common-case paired Low→Entry distance improves (`candidate - baseline < 0`);
3. `<=15%` EntryPosition case rate improves;
4. `<=25%` EntryPosition case rate improves;
5. Fill-rate degradation is no worse than `-2pp`;
6. +3 Capture degradation is no worse than `-2pp`;
7. +5 Capture degradation is no worse than `-2pp`;
8. causal closed-bar / future-suffix / evaluator-isolation / non-target invariance checks PASS.

The `-2pp` preservation tolerance is inherited from the previously precommitted accepted DROP/PULLBACK one-minute gate and REBOUND lock; it is not selected from these candidate outcomes.

The whole-Entry mean `<0.15` remains an aspirational completion gate, not a tune-until-pass criterion for any State. If a State candidate fails, that State's unattended performance-hypothesis budget is consumed and no alternate threshold/persistence length/rule may be tried automatically in this bounded pass.

## Required reporting

For each target State: N, Fill/Fill rate, no-entry reason, EntryPosition mean/median and <=10/15/25/50%, Low→Entry, Entry→Later High, +3/+5 Capture, 30m/60m MFE/MAE, common-case paired deltas, and concentration if favorable. Also report full-2155 candidate impact separately from target-cohort paired impact.

## Safety / scope

Provider requests 0. Protected data opened 0. No Common Holdout / REPORT19 / Validation / OOS / Fresh / Prospective. No EXIT / Capital / Portfolio work. Frozen Selector, 9-Pattern meanings/thresholds, six Signals and immutable baselines remain unchanged. All trading/write/promotion flags remain false.
