# Phase57 EXIT — 20-Session Diagnostic Checkpoint

Status: RESEARCH_ONLY / DRAFT / NO MAIN INTEGRATION

## Purpose

Large-scale EXIT v3/v4 validation is temporarily deprioritized. The immediate objective is to use at most 20 causally eligible sessions to answer two narrower questions before spending more research budget:

1. Does Frozen Minimal Hybrid v1 × MSH-Entry v1 still show useful historical Entry quality on the current substrate?
2. Do Frozen EXIT v3/v4 appear directionally suitable or unsuitable for this new Entry path distribution?

This is a diagnostic checkpoint, not a final validation or promotion gate.

## Fixed upstream inputs

- Selector: Frozen Minimal Hybrid v1
  - model digest: `444e296d31b0e59263f268706b4c8a7c7e9e59d6f7c9547e9f90342a24040fc2`
  - freeze SHA: `a744d599e430d23efe4dea6600e418d3410d8a18df5055b35e1cc71432bf64da`
- Entry: MSH-Entry v1
  - threshold: strictly `> 0.60`
  - candidate SHA: `f05def20081e51dfe7391c7e80e8b8474e5c140c42a47dc29dcd94bca367ab8a`
  - allocation SHA: `7df4cb026d966628c9b3fbc91037eb13704397a700c076e865d817a273df00e6`
  - fit SHA: `e1567951bcc81d50497a42e24411a32112b36638fbc0ff67247a16a6ce80859c`
  - repeatEntryAllowed=false
- EXIT v3/v4 policies remain frozen.
- Same Entry timestamp/reference price/direction/market data/cost assumptions across paired arms.

## Causal session eligibility

The previous 2024 DEV-A allocation is not valid for frozen v3/v4 analog scoring because the canonical analog substrate is later in time. For this checkpoint, use only evaluation sessions for which all EXIT analog constraints are causal and supported.

Minimum requirements:

- evaluation session date is later than every analog row used for that decision
- `analog.sessionDate < evaluated.sessionDate`
- `analog.fullyRealizedAt < decision timestamp`
- state-conditioned eligible analog count >= 30 where required
- no future labels or future extrema used as decision inputs

Scan candidate sessions result-blind. Select up to 20 causally eligible sessions in chronological order. Do not choose dates based on performance.

If fewer than 20 sessions are causally eligible, run the maximum available count and report `20SESSION_DIAGNOSTIC_CAPACITY_LOW` rather than relaxing causality.

## Entry-quality diagnostics

For each independent First ENTER event, evaluate at minimum:

- +1 bar directional return
- +3 bar directional return
- +6 bar directional return
- MFE / MAE
- time-to-MFE / time-to-MAE where available
- Immediate Adverse YES/NO using the existing definition if one exists
- recovery after Immediate Adverse
- session-end directional return as an evaluation reference
- LONG / SHORT
- symbol concentration
- time-of-day distribution

Future path values above are evaluation-only and must never be fed back into Selector, Entry, or EXIT decisions.

## Concentration diagnostics

Report:

- First ENTER count
- unique symbols
- per-symbol event count
- Top-1 / Top-3 / Top-5 symbol concentration
- LONG / SHORT split

The current working hypothesis is that the new Hybrid × MSH substrate may concentrate on a small number of symbols. Measure this directly rather than assuming it.

## Paired EXIT diagnostics

For every common First ENTER event, compare:

1. Fixed / session-end reference
2. Frozen EXIT v3
3. Frozen EXIT v4

Hold all non-EXIT inputs fixed.

Report at minimum:

- independent paired N
- Net / trade return
- Profit Factor
- Win Rate
- Average / Median trade
- MFE Capture Ratio
- Profit Giveback
- holding bars / time
- winner hold time
- loser hold time
- EXIT reason / timing
- Early Exit tendency
- Late Exit tendency
- Additional Loss Avoided where already supported by existing evaluation infrastructure

With only ~20 sessions, do not treat Sharpe, p-values, or formal significance as primary decision criteria.

## Diagnostic interpretation

Case A — Entry weak:
Hybrid × MSH historical Entry quality itself is weak. Stop deeper EXIT work and return findings to Entry research.

Case B — Entry good, v3/v4 usable:
Keep v3/v4 as baselines and continue with a new EXIT challenger only if justified.

Case C — Entry good, v3/v4 weak:
Deprioritize large-scale v3/v4 validation and move research effort toward a new EXIT design. Do not tune v3/v4 on this diagnostic sample.

## Data-management rule

Metadata access is not outcome access. Result-independent session metadata, causal analog counts, lineage, schema, symbol counts, bar counts, and availability checks may be scanned in bulk.

Outcome access for this checkpoint is limited to the selected diagnostic sessions only. Do not consume additional Protected/Fresh/Validation/OOS/Reserve outcomes automatically.

## Speed rule

Do not re-audit resolved Stage0–2 timestamp, 5m aggregation, Golden/MSH parity, Entry reconstruction, or Tier2 contracts unless a directly relevant critical inconsistency appears.

Complete causal eligibility scan → exact session freeze → replay → diagnostic aggregation → report/tests/CI in one research pass where practical.

## Safety

All safety flags must remain false:

- executionAllowed=false
- brokerWriteAllowed=false
- excelOrderWriteAllowed=false
- rssOrderFunctionAllowed=false
- liveTradingAllowed=false
- paperTradingAllowed=false
- automaticPromotionAllowed=false
- productionUpdateAllowed=false
- transmitted=false

No main modification, merge, Ready transition, auto-merge, or performance promotion.

## Final gates

Use exactly one:

- `20SESSION_DIAGNOSTIC_COMPLETE_ENTRY_GOOD_EXIT_V34_WEAK`
- `20SESSION_DIAGNOSTIC_COMPLETE_ENTRY_GOOD_EXIT_V34_USABLE`
- `20SESSION_DIAGNOSTIC_COMPLETE_ENTRY_WEAK`
- `20SESSION_DIAGNOSTIC_CAPACITY_LOW`
- `20SESSION_DIAGNOSTIC_INTEGRITY_BLOCKED`

After the diagnostic report and CI are complete, STOP. Do not automatically expand to 70/500 sessions, do not unlock DEV-B/Validation/OOS, and do not start a new EXIT implementation without explicit authorization.
