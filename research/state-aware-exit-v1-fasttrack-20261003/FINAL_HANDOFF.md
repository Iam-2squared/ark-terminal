# State-aware EXIT v1 FastTrack handoff

saved_at_jst: 2026-10-03T17:05:35.246402+09:00
basis_head: `b4b0c0317b9df5ce7faaea05bd46e24d270db91d`
status: `STATE_AWARE_EXIT_V1_TWO_ARM_OOF_EVIDENCE_READY`

Frozen P1_Q70 Entry HEAD `4a2d6f35946b16820a13449a9288a6685a5c283c` remains unchanged. Exactly 5 new EXIT fits, Hard1 additional fits 0. Two actual saved-source OOF replay arms only. No arm has been officially selected or frozen. Production ready=false; all safety flags=false.

1600 frozen Entries /58 sessions. Normal filled1564/unresolved36; Hard1 filled1571/unresolved29. Primary paired N1564. Mean realized returns normal0.060180% /Hard1 0.000919%; paired Δ−0.059261pp. Hard1 observed triggers449; negative losses improved191. Confirmed subsequent ≥3/≥5 Winners cut99/61; unknown missing-source cases340/374. Winners overlap and must not be added.

Independent audit PASS/mismatch0/future causal leakage0/audit fit0. Detailed definitions, denominator scope and source limitations are in REPORT-ja.md and EVALUATION_PRECOMMIT.json. A small observed MFE denominator can make MFE realization ratios extreme. No tick-level stop guarantee or net −1% loss bound is claimed.

The learner is a position-independent signed continuation-value head fitted on selected-watch context rows in the existing earlier chronological train sessions; it does not generate training Entries. Runtime is only post-fill for the immutable 1600 Entries. Exact RC2 State9 and past-only path/history are reused without logic changes; Legacy State0. No old EXIT logic, thresholds, routes or results are included.

STOP: human decision remains pending. New policy/search, Entry refit, old EXIT comparison, Re-entry, Capital/Portfolio replay, provider requests, protected opens, orders and main merge are all0.
