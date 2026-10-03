# Persistent Re-entry v1 — Frozen P1_Q70 fresh cross

Document: WORK_EXIT_V3_FREEZE_TO_REENTRY_V1_FASTTRACK_20261003.
One Re-entry policy; one primary replay over the unchanged 1,600 FIRST ENTRY watches.

## Frozen authorities

FIRST ENTRY v2 P1_Q70: 4a2d6f35946b16820a13449a9288a6685a5c283c.
EXIT v3: c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad, now officially frozen by F0.
V4 rejected: 4a5be18763cebb08c658ba7a9725ada979dd80c9 / V4_NOT_BETTER_KEEP_V3.
V4 EXIT-D and Recovery Floor are absent.
V3 A/B/C, PRE, observation suspension, local pivot prefix, dated calendar and sell fill are whole-byte immutable copies.
The saved State9/Path market traces are read-only. No reconstruction.

## Decisions and chronology

The same session|symbol stays watched until session close. Maximum one position per watch.
Trade #1 is the exact Frozen FIRST ENTRY fill plus the exact saved V3 outcome; no baseline decision replay or performance recalculation.
After a FILLED sell, WAIT_FOR_RESET starts. Scores on or before the sell raw minute are ineligible.
Every later eligible closed1m uses the exact corrected-lineage P1 OOF score and fold-specific Frozen Q70 threshold on the original persistent grid.
First score < threshold arms the fresh-cross machine. After that, previous eligible score < its threshold and current score >= its threshold produce one locked BUY_INTENT.
There is no score read while a position or pending buy/sell fill is open, no same-bar sell/buy, no cooldown and no count cap.
Across missing observed score rows and lunch, previous eligible score retains its stated meaning; no synthetic score row is generated.
SESSION_CLOSE is terminal. A sell filled at or after the regular end is also terminal for the score clock.
An unresolved sell keeps the position open and terminates that watch's simulation; it is never treated as flat.

## Buy and EXIT

Re-entry BUY: first valid eligible regular raw Open with raw start >= closed-bar intent minute, excluding literal 09:00 and 12:30 mixed opens, multiplied by 1.0005 using Frozen FIRST ENTRY numeric convention.
This is the unchanged FIRST ENTRY buy eligibility; it is not replaced by the sell's additional mixed-source exclusion.
No next regular Open: NO_REENTRY_NO_NEXT_REGULAR_OPEN, no invented fill.
On each Re-entry fill create a new Frozen V3 lifecycle. No prior position phase, arm, guard or pending intent carries over.
The saved market prefix strictly before that fill can seed the already confirmed local pivot suffix exactly as Frozen V3 does; it carries market observations, never a previous position's guard.
New positions use only EXIT-A main UP→DOWN, EXIT-B independent RANGE retirement, EXIT-C mature local guard break, or Frozen planned SESSION_CLOSE.
SELL is the whole-byte Frozen canonical next-open function with adverse 5bps and exact closing source fallback. Entry 5bps is never charged twice. Commission 0.

## Evaluation, fixed before replay

Original FIRST Entry→strictly-later observed High bucket is joined only after all decisions are sealed; never an engine input.
Exclusive buckets: <1%, 1–<2%, 2–<3%, 3–<4%, 4–<5%, >=5%, UNKNOWN.
Primary: simple sum of all fully realized trade returns in each watch. Incremental = simple total − saved FIRST trade return.
Secondary: 100 × (product(1 + trade return/100) − 1), same-watch theoretical compounding only.
A watch with any unresolved trade has simple/compounded total UNKNOWN; save known partial sums separately, never zero-impute.
The paired primary comparison uses the common completely realized watches. Also show original watch N, common N, unresolved N and all saved FIRST-only statistics so denominator loss cannot masquerade as an improvement.
Mean delta is mean of paired increments; median delta is difference of common group medians. Median paired increment is a separate diagnostic.
Activity distributions count all 1,600 watches and all sessions, including zero Re-entry watches/sessions.
Timing is active trading minutes from actual sell fill: EXIT→reset, reset→cross, EXIT→next buy intent/fill.
Trade-index #1/#2/#3/#4+; independent >=5 and each 2–<3/3–<4/4–<5 multi-leg tables; return, holding, reason and unresolved counts.
Churn: nonpositive trades, holding <=1/3/5 and exit-to-buy <=1/3/5 minutes. Adverse cost is an execution diagnostic, not a new policy: compare exact raw Open/closing source round trips with adjusted fills; source-unknown is null.
Portfolio/cash constraints/position sizing/Capital are not evaluated.

## Audit and finite stop

Separate logic checks all 1,600 watches and all Re-entry cycles, score/grid lineage, strict reset/fresh cross, chronology, independent V3 arithmetic, canonical fills, fixed original bucket, paired sums/compounding and null handling.
Required: mismatch_N=0, future_causal_leakage_N=0, position_overlap_N=0, future_bucket_decision_reads=0.
Historical actual_known_at remains UNKNOWN; bar_end is an availability assumption, not verified historical arrival evidence.
No new fit, teacher, score computation, threshold/model/feature search, provider/new market data, State9/Path change, V4 replay, first-only V3 replay, fixed stop/profit/trailing, cooldown, trade cap, Capital, Portfolio, orders or main merge.
All ten safety flags are false. LONG-only and cash-equity-only; productionReady=false.
After PERSISTENT_REENTRY_V1_EVIDENCE_READY or explicit Integrity BLOCK: STOP. No automatic Re-entry Freeze or Capital.
