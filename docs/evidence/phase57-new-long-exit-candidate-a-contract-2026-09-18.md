# Phase57 NEW LONG EXIT Candidate A — +3/+1 Profit Protect + Fixed12 Cap

Date: 2026-09-18 JST
Status: **PREDEVELOPMENT_CONTRACT_FROZEN**

## Purpose

Test whether the strongest winner-preserving Profit Protection component creates a materially better realized reference EXIT than the frozen Fixed12 control, without any Loss Defense rule.

This is an integrated EXIT candidate, not a claim that Loss Defense is solved.

## Frozen policy

For each frozen INITIAL or DIP_REPRICE Entry:

- hold by default;
- once a completed 5m bar establishes running HIGH >= +3%, arm PROTECT;
- after arming, the first later completed CLOSE <= +1% signals EXIT;
- EXIT reference = next regular 5m OPEN;
- if no PROTECT exit occurs, use the exact frozen Fixed12 cap/reference;
- 0.05pp round-trip cost semantics identical to the frozen comparator;
- no re-entry.

No existing BAR5 / TWO_LOWER_CLOSES logic is used.

## Gates on identical Fixed12-resolved identities

For INITIAL and DIP separately:

1. mean net return >= Fixed12 mean;
2. PF >= Fixed12 PF;
3. p05 net return >= Fixed12 p05;
4. +5 opportunity preservation >=90%;
5. +3 opportunity preservation =100% by construction/causal audit;
6. safety/identity/reproducibility pass.

All pass -> `NEW_LONG_EXIT_CANDIDATE_A_DEVELOPMENT_PASS`.
Any fail -> `NEW_LONG_EXIT_CANDIDATE_A_KILL`.

A PASS is Development-only and does not authorize Fresh/OOS, Capital, Portfolio or main merge.
