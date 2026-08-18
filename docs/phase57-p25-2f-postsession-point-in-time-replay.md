# Phase57 P25.2F - Post-session point-in-time Day replay

Status: **READ-ONLY OOS REPLAY INFRASTRUCTURE - NOT LIVE EXECUTION**

P25.2F makes the five-variant Day experiment practical without pretending that 30-85 symbols were scored live every five minutes on the local Excel machine. The universe is frozen before the session by P25.2C. After the session, frozen 5-minute OHLCV can be replayed through the unchanged Phase57 policy one cutoff at a time.

## Information boundary

The replay controller may hold the completed session bar set, but each Phase57 scorer call receives only the prefix ending at that decision cutoff. Future bars are never passed into the current feature feed or current decision.

This is explicitly labeled **post-session point-in-time replay**. It is not claimed to be a historical wall-clock live decision. Its OOS legitimacy comes from the model/policy/universe being frozen before the session and from the current decision path being prefix-only and outcome-free.

## Fair cutoff grid

A cutoff is eligible only when every symbol in the union of Fixed5 / OldFixed30 / Dynamic30 / Dynamic40 / Dynamic50 has the minimum completed prefix at the same timestamp. If one target cannot be scored, P25.2E preserves the partial sweep but excludes its signals from the five-variant comparison.

## Phase57 parity

The default scorer is the existing `buildPhase57ProspectiveSnapshotPipeline` with the exact frozen `PHASE57_P24_COMBINED_PROSPECTIVE_V1` policy and `REUSABLE_RESEARCH_TARGET` mode. No Entry threshold, horizon list, feature family, model family, round-trip cost assumption or inner-only selection rule is changed here.

## Why this comes before quote/microstructure gating

The existing MARKETSPEED II `RssMarket` / `RssTickList` capture remains available. P25.2 first needs a clean base comparison of universe expansion under the frozen Phase57 Entry policy. Quote/microstructure can be audited alongside the result later, but it must not silently create/delete/reverse base P25.2 entries.

## Safety

No outcome is materialized in P25.2F. All broker, Excel-order, RSS-order, live, paper, promotion, production, transmission and fresh-holdout flags remain false.
