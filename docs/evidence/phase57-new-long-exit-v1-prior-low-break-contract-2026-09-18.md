# Phase57 NEW LONG EXIT v1 — Prior-Bar-Low Breakdown FAST-FAIL Contract

Date: 2026-09-18 JST

Status: **PREDEVELOPMENT_CONTRACT_FROZEN**

The v0 Loss Defense rule is permanently KILLed. This v1 is a structurally different, more selective deterioration confirmation; it is not a threshold retune.

## Frozen rule

States: HOLD, DEFENSIVE, terminal EXIT_SIGNALLED.

At each completed 5m CLOSE:

1. HOLD:
   - CLOSE >= Entry: HOLD.
   - CLOSE < Entry: enter DEFENSIVE.

2. DEFENSIVE:
   - CLOSE >= Entry: reclaim -> HOLD.
   - otherwise, if the **current completed CLOSE is strictly below the immediately prior completed 5m bar LOW**, signal EXIT.
   - otherwise remain DEFENSIVE.

3. EXIT reference:
   - next regular 5m OPEN after the signalling CLOSE.
   - missing/boundary -> UNKNOWN/EXPIRED; no imputation.
   - no re-entry.

The prior bar LOW is already fully observed when the current bar closes. No current-bar or future intrabar ordering is assumed.

## Why this is distinct from v0

v0 exited when a negative CLOSE was merely lower than the previous DEFENSIVE CLOSE. It improved the 21 deepest cases but failed winner preservation and worsened the 106 broader continued-drop cohort.

v1 requires a completed CLOSE to break the **entire prior completed bar range on the downside**. This is intended to demand stronger persistence evidence without introducing a numerical percentage threshold.

## Frozen gates

Exactly the same gates as v0:

- INITIAL +3/+5 preservation >=90% each.
- DIP_REPRICE +3/+5 preservation >=90% each.
- evaluator-only 106 cohort: >=10% relative mean-loss reduction vs frozen Fixed12 on comparable identities.
- evaluator-only 21 cohort: mean non-worse vs frozen Fixed12.
- INITIAL and DIP own60 mean policy return non-worse than own60 endpoint baseline.
- full identity/causality/safety preservation.

Any failure -> `NEW_LONG_EXIT_LOSS_DEFENSE_V1_FAST_FAIL_KILL`.
All pass -> `NEW_LONG_EXIT_LOSS_DEFENSE_V1_FAST_FAIL_PASS`.

No threshold adjustment, fallback variant, cohort-specific rule or additional confirmation is authorized after measurement.

## Frozen scope

Selector / NEW Entry / existing EXIT runtime / Capital / Portfolio unchanged.
No model fit/prediction, Fresh/OOS, provider request, 1m research, main merge or trading/write path.
