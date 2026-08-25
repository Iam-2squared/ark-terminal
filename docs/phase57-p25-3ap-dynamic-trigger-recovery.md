# Phase57 P25.3AP Dynamic persistence trigger recovery

This change is trigger-only.

It adds `predict/daytrade/phase57-p25-2f-postsession-point-in-time-replay.js` to the Dynamic HOLD/EXIT persistence workflow `push.paths` list so replay implementation changes can deterministically retrigger the existing research-only Dynamic persistence workflow.

No Fixed baseline, Frozen Entry, model, universe, threshold, Dynamic-N, fair-cutoff, fresh holdout, evaluation logic, persistence semantics, or safety flags are changed. All execution/write/trading capability remains disabled.
