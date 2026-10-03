# Phase57 — NEW EXIT sequential observation substrate R20

Date: 2026-09-25 JST  
Basis HEAD: `1708384fd2539a96553750b844e926440c8fd246`  
Scope: R18 zero-base EXIT / R19 initial inventory → implemented observation substrate.  
Status at commit: **IMPLEMENTED_SYNTHETIC_CORE_TESTED_CANONICAL_CI_AND_FULL_CENSUS_PENDING**.

## 現状 / 今回の実作業

Entry Dual Freeze `4878a1cc53430e816261dea0fb16aeb53b3c238d` remains unchanged.
IMMEDIATE and ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF are the only Entry arms.
Fixed12 and Candidate A remain historical Evidence only; no old EXIT policy is
called, compared, inherited as fallback or used as a learning target.

This checkpoint adds actual Python implementation, synthetic tests and a dedicated
read-only CI census. It does NOT implement or claim a successful SELL policy.
No new EXIT model is fitted, selected or measured. No Capital run is performed.
The hourly task is paused by user instruction; this is interactive development.

Local execution: 31 core synthetic tests passed. The canonical producer test
class could not run locally because repository source imports were not mounted;
it is mandatory (no skip permitted) in CI via ARK_REQUIRE_CANONICAL=1. Source
transport from this container failed DNS; GitHub connector reads/writes remain
available. Do not report local tests as canonical integration PASS.

Basis-HEAD CI failure query returned six failed workflows. The new focused CI
cannot establish that the entire PR is green. Main merge remains prohibited.

## Observation contract fixed BEFORE running the new census

1. **Clock:** one checkpoint for EVERY scheduled completed continuous 1m endpoint
   after each preserved Entry OPEN. No Entry+30 deadline, no twelve-bar EXIT cap.
   Calendar is the existing signal/Pattern continuous-minute calendar: 09:00–11:29
   and 12:30–15:24 for this 2025 cohort; endpoints include 11:30 and 15:25.
   This fixes an observation domain, NOT an executable terminal liquidation rule.
2. **Ownership:** Entry at the actual 09:31 OPEN owns the 09:31–09:32 candle.
   The first position observation is 09:32. Pre-Entry highs/lows are not owned.
   No rounding to 5m and no synthetic Entry-anchored 5m candles.
3. **NOW input:** only candle start+1<=NOW AND knownAt<=NOW. Seven-column archive
   rows lack provider publication timestamps, so m+1 is explicitly a HISTORICAL
   BAR-END PROXY. This proves historical closed-prefix causality, not live arrival
   time or executable latency. Explicit delayed knownAt inputs stay unavailable.
4. **Missingness:** retain every scheduled checkpoint, including no-new-bar slots.
   A missing minute is not a no-trade certificate, zero volume or interpolated price.
   Current mark-to-close return is null unless the newest owned closed candle ends
   at NOW. Last observed close/time remain separately labeled as stale observations.
5. **Owned extrema:** observedRunningHigh/Low and observedMfe/Mae describe observed
   owned candles. If ANY expected owned candle is absent, completePrefixMfe/Mae
   are null. They are not future MFE/MAE. Peak time is the latest equal-high candle's
   confirmation time, not an invented intrabar time. No intrabar max-drawdown ordering
   is inferred. No High after an actual EXIT can later be credited as owned; this
   observation-only stage has no executed EXIT yet.
6. **P&L:** currentReturnPct=100*(fresh closed reference / unchanged effective Entry
   price - 1). It is NOT realized net return. Existing Entry price already includes
   the original buy slippage; R20 adds no second slippage or artificial EXIT cost.
   Actual NEW EXIT execution/cost/terminal contracts must be fixed before performance.
7. **Recognition:** call canonical classify_state_v3 and detect with strict prefixes.
   No Entry replay/model is called. Previous-session identity comes from the pinned
   raw archive; its producer uses actual calendar predecessor and clears history
   when saved sessions are nonconsecutive (Pattern producer lines 150–156).
8. **Signals:** state/event/trigger remain true/false/null. No fresh closed price
   makes the history sample UNKNOWN, not FALSE or confirmed signal disappearance.
   The absent original selector price is passed as None to the detector; its sole
   dependent selectorMovePct context is omitted, never relabeled as Entry move.
   The six signal definitions are unchanged; direct producer parity is tested.
9. **History:** last 3/5/10 scheduled observations; local history resets at lunch.
   Count known and unknown samples and adjacent known-state pairs separately.
   Disappearance requires observed TRUE→FALSE, never TRUE→UNKNOWN.
   State dwell counts consecutive reliable same-state active observations, resets
   on unknown or lunch, and is not limited to the ten-sample history buffer.
   Entry-time State is a retrospective causal observation, not a changed Entry rule.
10. **Isolation:** final price paths exist only in the offline source/auditor.
    The decision-facing snapshot gets no final PnL, future state, oracle Low/High,
    future peak timestamp or expected future missingness. Future suffix mutation
    cannot alter an earlier snapshot. Full-source hashes are manifest metadata,
    not model input columns.

## R19 refinement — the 476-column producer is not the four-field exporter

R19 recorded an older 3,800-event information-export audit. That exporter is not
synonymous with Pattern-v2's complete feature registry. R20 additionally locates
`phase57_entry_pattern_v2.py::features` and the actual `substrate/names.json`.
The census exports a column-by-column inventory of all 476 names and families,
with distinct pending paths for intraday-prefix, prior-daily-context and frozen
Selector context. No column is silently promoted to MODEL_ADMITTED.
In particular, an unresolved legacy `relativeVolume5` field is not evidence that
all canonical `RVOL*/volume` transforms are unusable. Their exact source/coverage
must be assessed independently. R19 stays append-only; this distinction refines it.

## Exact census / reproducibility / exposure

- Original two frozen Entry ledgers are SHA-pinned; six-field envelopes only.
- Current 2,155 IDs are taken from the pinned signal-census protocol. Every no-Entry
  record remains in the denominator. Expected fills remain 1,963 and 1,885.
- Raw archive values outside that exact ID whitelist are never deserialized.
  Generic allowlisted archive framing is reused in a standalone helper, not by
  importing the old EXIT module or executing its policies.
- Each arm's expected observation count is computed from its preserved Entry time
  and the scheduled calendar, NOT from available future candles.
- Both arms share the same State/Signal semantics; recognition for the same
  opportunity/NOW can be reused because it is independent of Entry arm.
- Full per-session checkpoint streams and coverage-only summaries are generated
  twice independently. All output file hashes must match; missing/no-Entry values
  are never transformed into profitable or zero-return trades.
- The registry inventory and source hashes are saved. GitHub artifact retention is
  30 days, NOT permanent storage. A final receipt/checkpoint will record actual CI.
- Checkpoint PnL is only a legal historical feature. This census does not publish
  or select a NEW EXIT based on aggregate PnL/High/Low/return outcomes.
- Provider market-data requests, new protected partition opens, model fits,
  candidate policy evaluations and old EXIT policy invocations remain zero.

## 次の方針 / 残り

After actual canonical tests and the full observation census complete, preserve
CI/artifact/hash/coverage receipts, including any failure rather than masking it.
Then finish Pattern-v2 EXIT-time recomputation/admission, NEW EXIT execution and
terminal/missing contracts, and the finite training/evaluation protocol.
R18's Low→strictly-later-High buckets (<1,1–2,2–3,3–4,4–5,>=5%) and realized
Entry→Exit vs available Entry→High capture remain mandatory evaluator outputs.
No NEW EXIT performance exists yet; do not claim the observation census is it.

The Selector upside thesis is a research motivation, not proof that every filled
Entry is in RISE/REBOUND or will reverse. Report actual Entry-time State/quality
counts, and never assume all selected names will rise or use future Low to decide
whether a current DROP is recoverable. Ordered >=5% anatomy is evaluator-only,
not a certification that every such Opportunity can be captured after its Entry.

All Safety9 false: executionAllowed, brokerWriteAllowed, excelOrderWriteAllowed,
rssOrderFunctionAllowed, liveTradingAllowed, paperTradingAllowed,
automaticPromotionAllowed, productionUpdateAllowed, transmitted.
No provider acquisition, Common Holdout/REPORT19/Validation/OOS/Fresh/Prospective
opening, force push, old Evidence overwrite, main merge, live/paper/production.
