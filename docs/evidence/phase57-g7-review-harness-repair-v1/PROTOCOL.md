# Phase57 G7 review-harness repair v1 — preregistered scope

Recorded: 2026-09-22 10:43 JST. Starting HEAD: fdcdde9c099dd6b0f59a313f596118083e0de1eb.
User authorized continuation of the adjudication's display/reader repair. This is NOT authorization to waive G7, freeze State v2, launch a new blind run, or start model/Entry research.

## Fixed inputs and rules
- Previous G7 admin ZIP SHA256: 15e389cbf3638e89e5555e934fe73152b3d4782b5304d4348372ea407d3d932b.
- Previous review ZIP SHA256: 303acb5c66b586917b75d1a48bb0e4b0fc848b7d48d86f9d63bb8273283676c1.
- G source ZIP SHA256: cc921c476af1079344975daa78e89fe03ee0dfc20ee62333170199178ade795e.
- Original mechanical-v1 reference.py SHA256: e57d41b1a9472fb0ed254895d956623a438557f540443c0bee14a6db8f2d8d3d at 9a764e27086bf6bb1133c304b73c0027d1275760. Use the exact original module, not the previous adjudication port. Hash mismatch stops execution.
- Cohort: ONLY the 36 ACTUAL cases in the original admin key. They are outcome-exposed regression examples, not fresh or new independent confirmation. Original control/actual labels and all previous evidence remain immutable.

## Repair
1. Normalize raw minute START to END=start+1 under the pinned G adapter contract. Admit only regular bars with END<=t and, where known, knownAt<=t. No filling/retiming. Reject a future bar at the computation boundary. Do not infer historical arrival timestamps.
2. Compute NOW using the original snapshot(closed_prefix, schedule, t, scale). Never copy saved oracle state into a NOW card, even when lateConfirmedPivots=0.
3. Recompute Scale from the actual previous session using the original function. Keep inherited corporate-action/price-basis/receivedAt limitations visible. Preserve same-day valid Direction independently of Scale. No alternative Scale.
4. Render from an explicit causal JSON sidecar only; preserve break/missing gaps. Show latest5 O/H/L/C/end stamps, Direction equation, active Structure witnesses/protected level and birth/confirmation times, local vs structure-origin pivots, Range birth window/bounds/touch witnesses, per-axis reasons. Include the fixed rule brief, not just the rubric.
5. Full-archive hashes belong to a run-level provenance receipt, not to causal feature values. Card content and admitted-prefix hash must not vary with a changed post-t suffix. Display no future-resolution, return target, PnL, control key, or hidden sidecar fields.

## Required repair acceptance (not G7 or State v2 acceptance)
- 36/36 identities preserved; no new sample selection.
- Exact original reference.py hash verified before each module load.
- 36/36 Direction/observation/Scale match pinned saved calculations; fresh-prefix State matches prior adjudication's causal output, not oracle payload.
- All displayed bar-end, confirmation and event timestamps <=t; missing markers use the same END clock.
- For each case, change and remove post-t price suffixes independently: causal sidecar, rendered HTML and plot bytes must remain unchanged within the fixed runtime.
- Recompute in reversed case order with fresh state; output hashes must match.
- Synthetic boundaries: rawStart=t rejection, rawStart=t-1 inclusion, missing4/5, missing current, short opening history, recess, closing auction exclusion, knownAt delay, Scale failure variants, active Structure inheritance, Range with <4 local pivots, future pivot/event rejection, forbidden future fields, bad input/duplicate/source-lock rejection.
- Negative-control repair checks MUST actually detect deliberately invalid display payloads; ordinary input missingness is not a display defect.
- Report each comparison denominator and every failure; no test-count or coverage claim implies predictive accuracy.

## Deliverables and stop
Versioned repair code, tests/logs, 36 regression sidecars/cards, old-vs-fixed endpoint table, deterministic manifest, exact input/source locks, and a revised review protocol DRAFT. A new blind review is not executed here. Original G7 remains FAIL, State v2 remains NOT_FROZEN, and the full 77,214-row runner is not implemented/generated.
Safety9=false, provider requests=0, protected data opened=0, State thresholds changed=0. No Selector, Entry, EXIT, allocation, main or trading-circuit edits.
