# STATE9_STRUCTURAL_EXIT_V4_RECOVERY_FAILURE

Document: WORK_STATE9_STRUCTURAL_EXIT_V4_RECOVERY_FAILURE_FASTTRACK_20261003.
Research-only one-policy contract, fixed before one primary V4 replay. V3 is the immutable fallback; this is not formal EXIT adoption Freeze.

## Frozen authority and exact reuse

Repository: Iam-2squared/ark-terminal. Starting actual GET of V3 branch matched c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad. FIRST ENTRY v2 P1_Q70: 1,600 selected FIRST_ENTRY rows from the frozen original 2,155-watch archive; selection, timestamps and fills unchanged. Entry file SHA256 e7a6140b6b11d8d078a271fad76b75e68a5b2fda9e45c7db43d98ee2f282abeb.

The V3 full State9/Path trace is its exact original V2 FULL_TRACE dependency, not duplicated in the V3 ZIP. Original ZIP SHA256 31a0fd8b8ec9c790b912a8da06ea601127fac0a5936f12181740d20e8627fe89; V3 ZIP SHA256 16cb53e6c986963f5a103e56c9f3fafad142548d7d9fd3286bb9e8c92e5a04b3. Both archives and all existing components are verified by bytes/hash only. V3 economics, exclusive opportunity/buckets and paired rows remain read-only. No State9/Path engine import or reconstruction; no V3 runner, Entry replay or earlier EXIT replay.

Frozen scales remain theta_local=1U, theta_structure=4U, delta_break=0.5U, epsilon_progress=0.5U. RC2/profile/source snapshot/M0/State Path Contract/PATH_FROZEN pins are inherited unchanged and independently rechecked. Historical actual_known_at remains UNKNOWN. Only the inherited assumed bar_end availability is audited, not actual market arrival.

## Preserved V3 behavior

frozen_v2_lifecycle.py, local_guard.py, reused_clock.py and reused_fill.py are whole-file exact-byte copies from V3 FINAL. V3 PRE, arming, suspension, A/B/C and guard behavior are executed as the fallback component of the one V4 stream; no separate V3 replay is run. Input prefix pivots are retained for V3's prior-bar LHL guard only. No Recovery Floor is established before Entry or before an active UP arm.

A: observed same-segment main UP->DOWN. B: independent RANGE/BALANCED/context NONE retirement. C: V3 effective local guard break, unchanged. Precedence within a bar is A, B, C, then D. A/B/C exact original reason and intent fields are retained when first. Only a still-held V3 fallback position is eligible for D. The same existing planned closing-intent deadline applies: new D must precede regular_end (900/925), and cannot relabel liquidation at that same clock. This is inherited execution/lifecycle ordering, not a dwell or price threshold.

## LOCAL_RECOVERY_FLOOR

New position-local EXIT metadata, not a State9 state or semantic change. In active UP, the current observed row's local_pivot_confirmed must have kind L and generation_reason DC_CONFIRMED. The exact pivot lexical x and confirmation fields are retained. extremum_t <= confirmed_at <= current scheduled t. It belongs to the current active causal segment. main protected_before must exist; L > protected_before. Floor unset or L > current floor. With no A/B/C/D intent on this bar, set floor=L, updated_at=t, effective_from=t+1. Current-bar pending floor is never used for a break. No LHL, progress, return, gain, loss, sequence or duration rule is added. The floor never decreases within a continuous active UP segment.

## EXIT-D LOCAL_RECOVERY_FAILED

For the current closed bar: active UP; valid observed and continuous same-segment connection; context still UP; floor_before already effective and from this segment; floor_before > protected_before; Close_u <= floor_before - 0.5U. With no A/B/C on this bar and before the preplanned closing deadline, fix the first EXIT-D intent and stop all position decisions. Exactly equal break boundary qualifies. Arithmetic uses Fraction over original RC2 numeric strings; no epsilon/tolerance in policy decisions.

PULLBACK alone, local DOWN alone, RISE_STOP alone, time/dwell, stop count, gain/loss/giveback percentages and future Entry->High buckets are not decision inputs. Source outcomes and future prices are inaccessible to the lifecycle. Current local L updates occur only after the current-bar break test and first-intent test.

## Quality and execution

Clear floor on any invalid observation or disconnected adjacent endpoint (null/unavailable/rejected, observation loss, ordinal gap, changed causal segment including source/auction/reset changes). No cross-segment carry or synthetic break. Upon new-segment UP re-arm, only that segment's current confirmed L can establish a new floor. PRE semantics unchanged; no missing-driven SELL.

Same canonical raw open and session close source as V3: first available eligible regular raw Open at/after closed-bar intent timestamp, strictly after Entry; start/mixed-auction exclusions unchanged. Sell adverse 5bps (raw price x 0.9995); commission 0; frozen Entry adverse cost never charged twice. Existing exact terminal auction close is the only closing fallback. No last-observed-close imputation. No sell source -> UNRESOLVED.

## Evaluation and fixed selection

First table: exclusive 2-<3, 3-<4, 4-<5, combined 2-<5 (426 watches, original V3 common filled 417), and >=5 protection. UNKNOWN and unresolved stay null and have explicit counts. >=5 excluded from combined. V3 outcomes join by exact watch_key. Original observed Entry->High, high timestamps and bucket values reused; only V4 sell-dependent metrics computed.

For every group show old/new means and medians, change in group statistics, and separately true per-entry paired deltas with common denominators. Pre-sell peak giveback uses observed High strictly before sell; later missed upside uses observed High strictly later than sell. Do not interpret changed-denominator raw missed-upside means as paired improvement. Full-session opportunity is only the original observed window; completeness and UNKNOWN counts retained.

Fixed quantitative gate order: integrity failure -> exact Integrity BLOCK; combined mean<=V3 or median<=V3 -> V4_NOT_BETTER_KEEP_V3; if both combined statistics improve but any target exclusive mean or >=5 mean/median worsens -> V4_MIXED_KEEP_HUMAN_JUDGMENT; if all seven user strict conditions pass -> V4_STRICT_IMPROVEMENT_CANDIDATE; otherwise no clear breadth (fewer than two target exclusive means improve) -> V4_NOT_BETTER_KEEP_V3. Numerical comparisons use unrounded values. No missed-upside standalone FAIL.

The qualitative few-case dependence clause has no numerical cutoff in the Work. No new cutoff will be invented. We save D changed-N per target bucket, positive/negative paired changes, total net gain, largest positive contribution and leave-largest-positive-out mean-gain evidence. The report explicitly evaluates whether the observed primary improvement has breadth or is concentrated. Status does not authorize adoption, a rescue rule or another candidate; V3 fallback stays unchanged in all statuses. No result-dependent edits to this contract, D code or quantitative gate.

## Audit, budget and STOP

Independent boolean latch, full pivot ledger, floor ledger, fill/calendar and economics implementation audits all 1,600 entries. It does not import primary lifecycle, guard, floor, fill, clock, replay or evaluator code. Audit is a distinct implementation sharing immutable data, standard Python and I/O/hash helpers; it is not an external reviewer. All 24 required gates and selection are checked; mismatch_N=0 and future_causal_leakage_N=0 required.

new policy=1; Recovery Floor variant=1; primary V4 replay=1. fits/teacher/OOF/probability/score/rank/search/provider/new data/Entry replay/State9 or Path reconstruction or semantic change/V3 replay/old EXIT replay/Hard1/fixed stop/fixed trailing/Protected/Fresh/Validation/OOS/Prospective/Re-entry/Capital/Portfolio/orders/main merge/force push=0. All ten safety flags=false, LONG-only, cash-equity-only, productionReady=false.

Three checkpoints only: V4_S0_START_AND_CONTRACT, V4_S1_REPLAY_AND_EVALUATION, V4_FINAL_AUDIT_AND_SELECTION. Every checkpoint has actual JST time and current basis HEAD, status, completed work, evidence, blocker, direction, next step, frozen boundaries and budget/exposure. Commit then actual branch GET; never predict the new SHA.

Complete replay, evaluation, reason decomposition, mechanics, independent audit, selection and FINAL evidence even if performance is poor. STOP at the specified selection status or explicit Integrity BLOCK. Formal EXIT Freeze, further EXIT improvement, Re-entry and Capital never follow automatically.
