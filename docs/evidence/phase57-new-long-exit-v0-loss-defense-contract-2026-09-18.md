# Phase57 NEW LONG EXIT v0 — Loss Defense FAST-FAIL Contract

Date: 2026-09-18 JST

Status: **PREDEVELOPMENT_CONTRACT_FROZEN**

This contract freezes one minimal Loss Defense hypothesis before any replay of the rule. It does not authorize Profit Protection, threshold search, model fitting, Fresh/OOS, 1m research, Capital/Portfolio tuning, production promotion or main merge.

## Frozen upstream

- Frozen LONG Selector: unchanged.
- Frozen NEW LONG Entry timing/location: unchanged.
- Entry opportunities remain `INITIAL_ENTRY_OPPORTUNITY` and `DIP_REPRICE_OPPORTUNITY`.
- Entry source is logged for diagnostics only. **The Loss Defense rule is identical for both cohorts.**
- Existing `LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1` remains a historical comparator only and is not modified.

Source Path Study head: `cdafa3fcf0dafa205700c4d6542c6069d68a6f71`.

## Research question

Can a threshold-free, causal persistence rule cut genuine deterioration earlier without destroying the recovery winners documented by the Path Study?

The Path Study established both sides of the conflict:

- t+5 negative can later become +3: INITIAL 56/267, DIP 22/69;
- DIP deep-drop 5% cohort loses a further 1.746pp on average from t+5 to t+15;
- no universal t+5 negative signature separates deep losers.

## Frozen state machine

States: `HOLD`, `DEFENSIVE`, terminal `EXIT_SIGNALLED`.

At every completed regular 5m CLOSE after Entry:

1. **HOLD**
   - if current CLOSE return >= 0: remain HOLD.
   - if current CLOSE return < 0: enter DEFENSIVE and remember this completed CLOSE.

2. **DEFENSIVE**
   - if current CLOSE return >= 0: Entry price has been reclaimed; return to HOLD and clear the adverse reference.
   - else if current CLOSE return < previous completed CLOSE return: signal EXIT.
   - else: remain DEFENSIVE and update the previous completed CLOSE.

3. **EXIT reference**
   - EXIT is referenced at the next regular 5m OPEN after the completed CLOSE that signalled deterioration.
   - if that next OPEN is missing or beyond the session boundary, result is UNKNOWN/EXPIRED; it is never imputed.
   - no later re-entry exists in this FAST-FAIL.

This deliberately introduces **no percentage loss threshold, no cohort-specific threshold, no bar-count timeout and no model**.

## Causality

Decision inputs are limited to:

- frozen Entry reference price/timestamp/source;
- completed 5m CLOSEs observed up to the decision;
- previous completed CLOSE while DEFENSIVE;
- next regular OPEN only as the contemporaneous reference price after a signal.

Forbidden decision inputs:

- future HIGH/LOW/CLOSE;
- future MFE/MAE;
- future winner/recovery labels;
- D30 risk cohort labels;
- final outcome;
- existing EXIT result;
- symbol-specific or time-of-day rules.

Future path fields may be used only by the evaluator.

## Primary Development FAST-FAIL gates

All gates are frozen before the rule is replayed.

### G1 — Opportunity preservation

For each cohort separately, among own60-complete paths that eventually reach the level:

- +3 winner preservation >= **90%**;
- +5 winner preservation >= **90%**.

A winner is preserved only if the Loss Defense policy does not exit before the first causally later +3/+5 HIGH touch. Same-bar HIGH/LOW order is not assumed in the policy's favor.

### G2 — Continued-deterioration improvement

On the pre-existing evaluator-only DIP cheaper/D30 additional-drop >=2% cohort (106 identities), compare the policy reference return with the frozen Fixed12 comparator on comparable resolved identities.

Required relative mean-loss reduction: **>=10%**.

The 106 identities are evaluator-only and cannot alter the rule.

### G3 — Deep-drop sanity

On the pre-existing additional-drop >=5% cohort (21 identities):

- mean policy reference return must be non-worse than the frozen Fixed12 comparator on comparable resolved identities.

This is a small-sample guardrail, not an optimization target.

### G4 — Overall cohort non-worsening

For own60-complete INITIAL and DIP_REPRICE separately:

- policy return = EXIT reference return when resolved; otherwise own60 endpoint return when no EXIT signal;
- mean policy return must be >= mean own60 endpoint return on the same comparable population.

UNKNOWN/EXPIRED exits are excluded from this paired price comparison and reported explicitly.

### G5 — Coverage / causality

- full 2,743 anchor identity must remain unchanged;
- no missing reference may be imputed;
- decision replay must be prefix-only;
- Selector / Entry / existing EXIT runtime / Allocation / Portfolio changes = 0;
- model fit/prediction, Fresh/OOS, provider requests, 1m research = 0;
- all trading/write/promotion safety flags remain false.

## Disposition

- If **any primary gate fails**: verdict `NEW_LONG_EXIT_LOSS_DEFENSE_FAST_FAIL_KILL`.
- If all primary gates pass: verdict `NEW_LONG_EXIT_LOSS_DEFENSE_FAST_FAIL_PASS`.
- No threshold adjustment is authorized after a KILL.
- A PASS authorizes only the separately contracted Profit Protection FAST-FAIL. It does not authorize integration or Fresh/OOS.

## Diagnostics, not gates

Report:

- signal rate and signal time distribution;
- false-exit counts for future +1/+2/+3/+5;
- recovery/reclaim counts;
- INITIAL vs DIP separately;
- four chronological blocks;
- top-frequency symbol exclusions;
- 106 and 21 evaluator-only cohorts;
- UNKNOWN/boundary states.

No diagnostic may be promoted into a new rule during this run.

## STOP boundary

Run exactly this rule once, save deterministic evidence, assign PASS/KILL, and STOP.
