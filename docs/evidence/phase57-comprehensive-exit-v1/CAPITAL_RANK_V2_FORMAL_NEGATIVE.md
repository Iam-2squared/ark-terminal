# Phase57 Capital Rank v2 — formal negative and Development portfolio closure

Saved: 2026-09-27 JST. Controlling machine records: `CAPITAL_RANK_V2_RESULT_AUDIT.json` and `CAPITAL_RANK_V2_RESULT_HANDOFF.json`. Exact 25 Action outputs are preserved under `CAPITAL_RANK_V2_RESULT/`.

## Identity and exposure

- Entry/Selector freeze: `4878a1cc53430e816261dea0fb16aeb53b3c238d`, unchanged. IMMEDIATE and ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF both retained.
- Rank protocol SHA256: `8b5f9eb1753a2967edd4991fc90bbff6e21898764d1fb13d3693572c72d335de`; 3 enumerated candidates, 4 expanding folds, 2 Entry arms, exactly 24 fits. Feature audit SHA256 `556d5f29e0a54f8878ffb4ae6f87ddd4e79d03a047a5581907c123707501a053`.
- Required CI `36301697160` SUCCESS at tested source `9c09b6451d25ec4d606fa1b2d9ab5cac1274b45e`: 76 tests, 2,257 prefit feature rows, 0 fits, 0 portfolio replays, 0 candidate scores inspected. Superseded CI `36301487370` was not used for launch.
- Finite Action `36302009680` SUCCESS at execution SHA `db5c5f9db7b55be2811e85522c426d0df83f073f`. Artifact `10926311771` ZIP SHA256 `afa814bb189d50d84d1101b0978f2edd208ddc74ab35fcd8348d0e501845169b`, 25 entries. Rank score SHA256 `f4f6e52ee5f9cf9ad5b54278de1d147e1ca55ace58fd947da37af1cac461ea7f`.
- The 2,155 Opportunities are outcome-exposed Development; this 24-session OOF score window runs **2025-07-22 through 2025-08-25** (35 calendar days inclusive). No protected/Fresh/OOS opened and no provider request. Prior R49 and superseded v0 loader out-of-allowlist decodes remain disclosed in the controlling handoff. Safety9 all false.

## Frozen ranking Gate: 0 PASS / NO_SELECTION_STOP

| Arm | 24-session candidate N | Evaluable N | Baseline hit rate | Old rank Top3 hits / N | Old Top3 enrichment | A Top3 | B Top3 | C Top3 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| IM | 819 | 808 | 19.55% | 145 / 731 | 1.028× | 1.014× | 1.016× | 1.030× |
| R1 | 795 | 786 | 18.19% | 142 / 776 | 1.018× | 1.018× | 1.010× | 1.010× |

The frozen minimum was Top3 enrichment **1.15× in both arms**, plus improvement over the same-window old rank and other gates. A/B/C all fail. Top5 admits every candidate (IM 819/819; R1 795/795), so Top5 enrichment is 1.000× for every ordering.

**A precommit design limitation became evident in the artifact audit:** Top3 contains 731/819 IM candidates and 776/795 R1 candidates. Even granting an ideal ordering that selects every known positive and allocates every censored row to Top3, the *loose* upper bounds on enrichment are IM **1.122×**, R1 **1.025×**. The frozen 1.15× Gate cannot pass with this event geometry. This was not caught before Freeze. We do not lower the Gate, add a candidate, or select the best failure. The v2 model family therefore has no formal capital rank selection. This outcome cannot by itself establish that causal features contain no information; the event-capacity/Gate mismatch limits the test.

## Existing rank control: six 24-session terminal benchmark portfolios

No v2 candidate was adopted. The frozen existing R35 causal rank was used for **all six** MAX3/4/5 Development portfolios over exactly the same 24 sessions. EXIT remains a forced-terminal benchmark, **not a selected Final EXIT**.

| Variant | Funded / closed | Unresolved | Realized PnL | Valuation event coverage | Valid equity sessions / 24 | Full return / daily rate |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| IM × MAX3 | 72 / 72 | 0 | −¥129,019 | 99.55% | 23 | null |
| IM × MAX4 | 96 / 96 | 0 | −¥100,769 | 97.51% | 22 | null |
| IM × MAX5 | 120 / 120 | 0 | −¥149,487 | 97.28% | 21 | null |
| R1 × MAX3 | 30 / 29 | 1 | −¥12,397 | 39.93% | 9 | null |
| R1 × MAX4 | 40 / 39 | 1 | −¥26,377 | 39.93% | 9 | null |
| R1 × MAX5 | 120 / 120 | 0 | −¥60,074 | 97.84% | 21 | null |

Realized PnL reflects only confirmed exits and **is not portfolio return**. Exact cash and mark checks passed: no negative cash; 100-share lots; capacity bounds; no future mark; no unresolved-exit cash release. The missing-reference file enumerates **768** per-variant position/timestamp rows: 50 across lunch and 718 uncertified overnight. R1 MAX3/MAX4 funded `2025-08-04|36700|602` with no 15:30 auction; 359 later observations per variant lack certified cross-session valuation. IM variants have same-day lunch gaps. Every full-period equity path has at least one null, so Final Equity, Portfolio Return, full MaxDD, the 24-session arithmetic/median/geometric daily returns, and mechanical 20/60/120/240-session conversions remain **null**. Plots retain gaps; they are partial diagnostic paths, not full asset curves.

The earlier **34-session** v1 blocker (`2025-07-17|59050` missing auction and unproven corporate-action continuity) remains unresolved. This 24-session OOF window must not be presented as its repair or as 34 calendar days. It spans 35 calendar days, 24 trading sessions, with observation events from 09:00 through 15:30 including lunch/reopen events and auction where present.

## Artifact field correction

`report.json` retains `candidatePerformanceInspected=0` and `portfolioReplays=0` from its **pre-fit support receipt** even after the Action. Those fields describe the preflight point, not the end of this Action. The actual Action evaluated three candidate scorecards across both arms and replayed six portfolios; the independent audit explicitly corrects their scope without altering the original artifact, candidate results, or protocol.

## Next boundary

NO_SELECTION_STOP is final for this frozen finite rank search. A new ranking objective/Gate that is mathematically feasible at the actual event size requires a **new performance-blind precommit**. Closing lunch/auction/overnight valuation needs separately justified historical mark and corporate-action provenance before any new performance replay. Never use missing prices as zero PnL, a sale, a cash release, or a backdated fill. Frozen Entry and the five formal negative EXIT generations remain unchanged.
