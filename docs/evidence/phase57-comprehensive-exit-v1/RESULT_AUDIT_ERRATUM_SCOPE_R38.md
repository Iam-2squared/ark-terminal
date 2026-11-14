# R38 — finite result audit and narrowly bounded evaluator erratum

Saved at: 2026-09-26 16:38 JST. Basis/latest checked HEAD:
`a10b3f25f79f8221c9a71c1b3ede245777bce058`.

R36 run `36222151340` succeeded. Artifact `10901042535` ZIP independently hashes
to `1c574848c6106d34c1d53e902b339e1be2f43b7b5c615e40a7010c29332d997a`.
Its recorded result is NO_SELECTION_STOP, 144 fits, 24 policies, zero passes.
All 48 candidate/arm mean-net values are below the fixed +2.00% gate, before
the correction below. No candidate is selected or frozen. No Portfolio replay
is authorized. R37 is preparation and synthetic tests only.

## Discovered implementation defect and scope locked before correction

R36 `_position` returns NumPy float32 values; `numeric` accepts only Python
int/float, so the observed peak and confirmation time become missing. The
resulting Owned Peak Giveback is null for every candidate. This is an evaluator
transport defect, NOT evidence that every market path is incomplete. Original
receipts/ledgers/scorecards are never overwritten, and the frozen runner is not
edited (editing it would trigger the one-shot fit workflow again).

R38 reads immutable R36 ledgers, reconstructs only the R20 completed owned prefix
at the uniquely recoverable decision endpoint, and converts the original float32
peak transport value to a Python scalar before the unchanged R21 evaluator.
Ordinary exit NOW is its OPEN minute except lunch OPEN 750 maps to NOW 690;
terminal uses last continuous checkpoint 925. Exit-candle High/Low remain excluded.
Incomplete prefixes and unresolved exits remain null. No future reference is
used for ownership. Only `metrics.ownedPeakGivebackPp` may change; decision,
execution, all return/cost values, 24 configurations, predictions and models must
remain identical. All existing scorecard groups and gates are regenerated using
the unchanged R36 functions. Two independent correction passes must hash equally.

Additional fits = 0; additional policy replays = 0; Portfolio replays = 0.
The correction cannot rescue any candidate because the independent primary net
gate already fails for every candidate/arm. This does not authorize fresh research.

## Safety and next

Entry Dual Freeze unchanged; old exits historical only. Development remains
outcome-exposed; provider requests/protected opens 0; Safety9 all false. No main
merge, force push, live/paper/production. Preserve the original defect and corrected
evaluator outputs side by side, verify hashes and tests, then save the final
NO_SELECTION_STOP handoff. Any new candidate/model/threshold/feature work requires
the user's decision and a new precommit, not an automatic extension.
