# STATE9_STRUCTURAL_EXIT_V2

Document: WORK_STATE9_STRUCTURAL_EXIT_V2_20261003. Single zero-fit policy, fixed before replay outcomes. This fixes a research decision contract, not adoption or production readiness.

Use all 1,600 immutable FIRST_ENTRY_V2_P1_Q70 fills at Frozen HEAD 4a2d6f35946b16820a13449a9288a6685a5c283c. A failed v1 remains inherited historical evidence; its contents, teacher, models, OOF, threshold and 2-consecutive rule are not accessed or reused. No other EXIT arm or comparison is run.

## Frozen source and reconstruction

The six byte identities are pinned in IDENTITY_RECEIPT.json. State9 candidate and independent implementations, profile and the M0 80/120 adapters are exact copies of existing frozen source. PATH_FROZEN.py is byte-identical to ad59222fcc0f9dfed4698efb49a87d66ea4e01b90562cdcaa8b9bc028ffffbf8. No semantic change or threshold search is permitted.

For each participating watch, replay every original dated scheduled slot, from the beginning of the session through the original terminal source slot. Original saved raw values are used with the exact original Entry reconstruction mapping: raw minute m closes at m+1; scheduled_t=m+1-540; historical actual known_at is UNKNOWN, assumed available_at is bar_end. M0 is fixed using existing previous-session source before the current session. 80/120 coordinates must agree. Missing or invalid rows remain missing or rejected; no interpolation. Source-unavailable watches have explicit formal unavailable responses and no observed State. Their saved Entry feature observed/context/local fields were missing, not observed market states; overlap checks retain that provenance and require no observed State, formal null and null directions.

Check every existing saved overlap for the participating 1,600 watches: formal Primary, context, local direction, observed status, segment and display Primary. Compare full candidate and independent RC2 responses for every scheduled slot. A reconstruction mismatch is BLOCKED_STATE9_TRACE_RECONSTRUCTION_MISMATCH; missing required raw or frozen code is BLOCKED_STATE9_SOURCE_NOT_RECONSTRUCTIBLE. Persist the full formal response, Path endpoint and all row-local Path events. Historical full trace processing after an EXIT is evidence reconstruction, not a position decision.

## Lifecycle and causal clock

Only PRE_UP_STRUCTURE and UP_STRUCTURE_ACTIVE are market phases; STRUCTURE_OBSERVATION_SUSPENDED is a quality flag. Initialize PRE at the unchanged Entry fill timestamp. Use the latest supplied State snapshot no later than that timestamp (including a scheduled missing row at that time). If it is valid observed context=+1, arm immediately; otherwise wait for the first valid observed UP. UP_STRUCTURE_ARMED_AT is the first such timestamp and is never overwritten. Re-arm timestamps after quality interruptions are saved separately.

In PRE, DOWN families, RANGE, formal null, elapsed time and losses are never SELL reasons. In ACTIVE, keep HOLD while UP context survives; PULLBACK, RISE_STOP and protected-level tightening alone cannot SELL. Loss of observed adjacency, a segment reset, ordinal gap or source/auction change suspends observation. A resumed observed UP starts a new active structure; any other resumed valid observation returns to PRE. No cross-segment UP-to-DOWN connection is invented.

EXIT-A requires ACTIVE, two adjacent valid observed endpoints in the same segment, previous context=+1 and current context=-1, the frozen structure-break event and consistent Path CONTEXT_CHANGE. EXIT-B requires the same active observed connection, current formal RANGE / BALANCED / context=0, the frozen CONTEXT_RETIRED_BY_OBSERVED_BALANCE event and consistent Path RANGE_ENTER / CONTEXT_CHANGE. Record EXIT_INTENT on that closed-bar confirmation. Stop position decisions immediately on the first valid EXIT_INTENT, including while awaiting fill.

## Execution

Canonical structural sell: earliest saved valid regular raw open with raw start >= intent bar_end, strictly after the Entry fill minute, excluding fixed opening mixed minutes 540/750 and the actual first saved AM/PM mixed source bars; multiply raw Open by 0.9995. The dated unchanged regular calendar excludes lunch and terminal auction. No new data and no invented open. Entry +5bps is already inside immutable fill_price and is not charged again. Commission=0.

A contingent planned closing liquidation exists from Entry onward. If no eligible regular open fills the locked structural intent before the session deadline, or no structural trigger occurs, use only the saved valid terminal-auction closing source at the exact dated session-close minute (900 before 2024-11-05, 930 thereafter); multiply its raw Close by 0.9995. This is an explicit closing-auction fill source, separate from the decision-bar Close. Source aggregation is assumed available at close+1, while the execution reference is the closing-auction minute; precise intrabar execution chronology is unknown. The fallback is not a third market trigger. Preserve an unfilled structural trigger reason separately if closing fallback fills it. Absent valid closing source: UNRESOLVED. Never substitute a last-observed Close. For no structural intent, record planned-close intention at regular deadline 900/925, preceding closing-source availability.

## Evaluation definitions fixed before outcomes

All percentages use immutable Entry fill price. Realized return=100*(sell_fill/entry_fill-1). Winner opportunity is the maximum valid saved raw High at raw start strictly greater than Entry fill minute through the dated session close, excluding the fill-bar High. High is observed-only; incomplete paths and absent later High remain explicit, and a partial observed non-winner is not certified as a complete-session non-winner. The earliest maximum-High raw start is the final-High reference; save latest tied maximum separately.

Cumulative Winner buckets are >=1/2/3/4/5%; exclusive are <1,1–<2,2–<3,3–<4,4–<5,>=5 plus UNKNOWN_HIGH. Every table retains denominator, sell-filled and unresolved. >=3 and >=5 each receive a separate detailed table.

MFE Realization %=100*realized_return_pct/observed_entry_to_high_pct only if MFE>0 and sell-filled; do not clip negative or above-100 values. Peak Giveback pp=observed_entry_to_high_pct-realized_return_pct on the Entry-fill basis. Also report peak-price-relative giveback % and pre-sell observed-peak giveback separately. The full-session High can occur after EXIT, so full-session giveback includes missed upside and is not necessarily a peak experienced while held.

Later High is the maximum observed raw High with raw start strictly greater than sell fill minute. Missed upside %=max(0,100*(later_High/sell_fill-1)); no later observed bar yields null, not zero. Also save its Entry-basis difference, intent-to-later-High and fill-to-later-High active time. EXIT-before-final-High is determined from sell fill minute, with the intent-based version separately saved. High/fill-bar intrabar ordering is not inferred.

Active time excludes lunch and dated closing-auction waiting time. Summaries use finite known values only and publish metric-specific N; positive rate is among filled returns. Armed coverage is ever-armed; entry-UP, later-first-UP, re-arms, suspension, never-armed, structural intents, fill sources and unresolved are separate counters. Report holding, first Entry-to-arm, first arm-to-EXIT, protected tightening, PULLBACK/RISE_STOP distinct runs, last three distinct Primary values and exit context/protection/balance/dwell. Keep evaluator data separate from decision code.

## Audit, budget and stop

An independently written decision scan derives adjacency, phase, first trigger, execution and metrics from frozen trace and raw source without importing lifecycle.py or evaluator logic. Full trace reconstruction also uses the byte-pinned independent RC2 kernel. All 1,600 Entries must pass; mismatch_N=0 and future_causal_leakage_N=0 are mandatory. Shared raw, exact APIs and Python runtime dependencies are disclosed; this is a separate implementation audit, not an independent external reviewer.

New EXIT policies=1. Teacher/model fits/OOF model/probability/score/rank/threshold/feature search=0. State9/Path/profile/M0 changes=0. Provider/new market data=0. Old EXIT access/replay/comparison=0. Hard1/fixed stop/trailing=0. Protected/Fresh/Validation/OOS/Prospective/Re-entry/Capital/Portfolio/orders/main merge/force push=0. All ten safety flags remain false; LONG-only cash-equity research.

Normal stop: STATE9_STRUCTURAL_EXIT_V2_EVIDENCE_READY. Other integrity stops: BLOCKED_STATE9_STRUCTURAL_EXIT_CAUSAL_LEAKAGE or BLOCKED_STATE9_STRUCTURAL_EXIT_AUDIT_MISMATCH. Stop even if performance is poor. Do not formally adopt/freeze EXIT, add a policy, run Re-entry or Capital, or merge main.
