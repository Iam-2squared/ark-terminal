# Frozen Selector Measurement Protocol v2 — PRECOMMIT

Primary: each original Top5 mean OPEN-to-exact-CLOSE net return at an eligible decision timestamp, paired only when BOTH original full Top5 have observed endpoints; equal timestamp weights within each session, equal session weights. The repair removes the unnecessary requirement that all intermediate bars exist for a terminal return. It does not relax Top5 to 3/5 or replace missing symbols.

The all-timestamp original-Top5 population value remains NOT_IDENTIFIED when endpoint outcomes are missing. Complete-case estimates are conditional and are not survivor-unbiased economic performance. The primary interpretation gate is at least 38 sessions and 76 paired timestamps.

Secondary: observation-conditional means of the ORIGINAL observed members, at identical timestamps; record every missing member and zero-observed timestamp. These means do not substitute for full Top5 performance. No missing return is imputed, set to zero, estimated by an untested MAR model, or turned into a cash/no-trade outcome. Membership is identical to v1 in all arms.

Terminal availability and full-path availability are separate. MFE/MAE, first-hit, peak/trough and giveback require full regular 5m paths. Common60/90/120 endpoint cohorts are fixed within each curve and explicitly observation-conditioned. Calendar eligibility is fixed before observing outcomes; fixed horizons do not cross lunch. Session end is a separate analysis. 0m is only gross reference zero.

Random is the exact prior SHA256 seed20260919 Top5, one draw per timestamp; no redraw or seed search. Momentum is the exact canonical momentum30Pct descending order. Source scores and all three memberships are checked against the frozen ledgers.

5bps round-trip is canonical; 0/10/20bps sensitivities. 10,000 session-cluster bootstrap replicates, seed20260919, seven fixed-horizon Random primary contrasts receive Bonferroni intervals. Secondary CIs are descriptive. A fixed circular five-session-block bootstrap checks serial sensitivity without claiming cross-date independence.

Tail rules, price bands, PIT volatility bins, threshold levels and path timing are copied from v1. Full/positive top1% and top5% excluded/worst1% and worst5% excluded/winsorized diagnostics remain outcome-conditioned. Score deciles use the full PIT eligible universe before future availability; endpoint terminal and full-path excursion samples are reported separately.

No unconditional directional/delayed/short-lived alpha claim can be recovered merely by discarding unobserved members. Final tags state scope, power and missingness limitations. An Economic Selector v2 design may be written if objective-mismatch evidence supports it; no fit, target implementation, feature selection, Entry/EXIT/Capital work or sealed data access follows.

Prior v1 returns were already exposed; Phase A new calculations are availability-only. This precommit precedes NEW v2 outcome measurement; it does not convert Development into an unseen test. Existing evidence is immutable. All nine safety flags false, new provider requests zero. STOP after diagnosis and optional design.

Machine-readable rules and source hashes: protocol.json.

## Active premeasurement clarification

The active machine contract is protocol-final.json. Session-end analysis preserves the existing first-regular-OPEN baseline for 11:30 decisions: the first possible entry is12:30. Fixed horizons still cannot cross lunch. The initial Phase A calendar labels excluded those session-end rows; its observed-row counts and pairability intersections were unaffected. Corrected per-slot/calendar evidence will be stored separately in the measurement output. No v2 return measurement has occurred; initial protocol and all Phase A files remain preserved.
