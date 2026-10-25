# Phase57 NEW LONG EXIT — Profit Protection v0 FAST-FAIL Contract

Date: 2026-09-18 JST

Status: **PREDEVELOPMENT_CONTRACT_FROZEN**

Loss Defense v0/v1 are KILLed and are not part of this experiment. This test isolates Profit Protection only.

## Frozen rule

No protection state exists until a completed 5m bar has observed running HIGH >= +3% from the frozen Entry reference.

At the CLOSE of that completed bar:
- enter PROTECT;
- remember the running HIGH and that completed CLOSE.

While PROTECT:
- if a new running HIGH is observed in a completed bar, refresh the running peak and reset the giveback-persistence counter;
- otherwise, if the completed CLOSE is lower than the previous completed CLOSE, increment giveback persistence;
- a non-lower CLOSE resets giveback persistence;
- **two consecutive lower completed CLOSEs without a new running HIGH** signal EXIT;
- EXIT reference = next regular 5m OPEN;
- no re-entry.

No percentage giveback threshold is introduced. +3 is not newly fitted: it is the Path Study milestone that exposed the full-retracement problem.

## Frozen gates

For INITIAL and DIP_REPRICE separately:

1. +5 opportunity preservation >= 90%.
2. Among own60 +3 winners, mean policy return >= own60 endpoint baseline mean.
3. Overall own60 mean policy return >= own60 endpoint baseline mean.
4. Among +3 winners with a later completed CLOSE <= Entry (the pre-existing full-retracement problem), at least 50% must be exited **before** that first full-retracement CLOSE and with positive policy reference return.
5. Full identity/causality/safety preserved.

Any failure -> `NEW_LONG_EXIT_PROFIT_PROTECTION_V0_FAST_FAIL_KILL`.
All pass -> `NEW_LONG_EXIT_PROFIT_PROTECTION_V0_FAST_FAIL_PASS`.

No threshold adjustment or fallback variant is authorized after measurement.

## Scope

Frozen Selector and NEW Entry unchanged. Existing EXIT runtime unchanged.
No Loss Defense integration, model, Fresh/OOS, provider, 1m, Capital, Portfolio, main merge or trading/write path.
