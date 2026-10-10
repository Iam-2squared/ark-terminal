# Phase57 Development Integrated v1 — accounting closure and coverage limit

Saved: 2026-09-27 13:47 JST. Branch: `research/phase57-long-only-cash-equity`; draft PR #587.

## Status and scope

**PARTIAL MARKED CURVES / FULL-PERIOD HARD BLOCKER.** Six frozen IM/R1 × MAX3/4/5 benchmark replays, A/B byte determinism, accounting audit and six CSV exports completed. None has a valid full-period asset curve, Final Equity, Portfolio Return or full-period MaxDD. Do not SELECT an Entry arm/capacity, adopt R50_B as Final EXIT, or interpret realized-only PnL as portfolio performance.

The scope is the same **34 Development sessions** in the R50 OOF score window. IM has 1,150 and R1 1,107 frozen Entry fills. It is outcome-exposed Development, not the 58-session/2,155-Opportunity full Entry period, Fresh/OOS, or a live return estimate. R50_B is the zero-model-exit **terminal-hold control / NOT FINAL EXIT**. Gen1/2/3/R49/R50 remain formal NO_SELECTION_STOP.

## Frozen valuation and cash semantics

The v1 performance-before Freeze is `DEVELOPMENT_INTEGRATED_V1_PRECOMMIT.json`, SHA-256 `cb4ad1f28471cf26c1ddd50453445323f132410d7a7e34cabffdcfaa8c56ad71`, committed at `45ce79aab06aca5a9a17ed50109c6643f7186797`. This new accounting measurement does not revise v0 results.

An owned position may be valued from the latest completed observed 1-minute CLOSE since Entry **in the current uninterrupted morning/afternoon segment**, or from the exact observed Entry OPEN until a later bar is complete. The source time, knownAt and stale minutes remain visible. A recorded 15:30 single-price auction is the only terminal-hold EXIT fill; a mark is never an execution price or released cash. In the missing-auction case the position, 100-share quantity and cost basis remain locked and the sell cost is not charged. Marks do not cross lunch or a session boundary. Between-session corporate-action continuity is unverified, so a censored position cannot use next-day prices even if a new observation appears. Missing mark makes equity/unrealized/exposure null and blocks new R37 equity-based sizing; cash and realized PnL remain exact. At each event confirmed EXIT cash is released before same-time ranked Entry sizing.

## CI, replay and artifact audit

| Check | Frozen evidence |
|---|---|
| Entry dual Freeze | `4878a1cc53430e816261dea0fb16aeb53b3c238d`; Entry/Selector changes 0 |
| Source implementation / required CI | source SHA `7318b7fa3724a6210f9fbf9c8d3d0fb0723794dc`; run `36294851905` SUCCESS; 63 focused/regression PASS |
| CI artifact | ID `10923607126`; ZIP SHA-256 `27bf502aa75afa41ebe800df96c0537367fda38a53a4ce4d6bdac1a88f852234`; 10-file source manifest, zero replays/fits |
| Exact replay | execution SHA `094404eaffaad926fff63c5ae150fc66532b490e`; run `36294959003` SUCCESS, attempt 1 |
| Replay artifact | ID `10922714467`; ZIP SHA-256 `16f40454abc0842e0351071872e08c42fe3024c62de5fb5582aadf181b923905` |
| A/B and accounting | result A/B byte-identical, SHA-256 `597b37cd7b902fbb42347147f8a3c53af32a23cb1e6c421b8d6085e20338d22b`; all position marks, cash, quantities and nulls audited |
| Exposure / safety | provider requests 0; protected opens 0; fits 0; nine trading/write/promotion/transmission flags false |

The CI preflight decoded 1,150 allowlisted raw payloads and skipped 4,225 outside raw payloads before JSON decoding. Earlier R49 loader initially decoded 3,220 outside-allowlist payloads, and superseded v0 preflight decoded 4,225 outside raw and 3,220 outside origin payloads. Those earlier accesses were not used for training/decision/score/tuning. Historical zero-out-of-scope-access is **not** claimed.

## Six finite benchmark replays

Event coverage means valid equity / scheduled event snapshots. The distinct time-weighted coverage is shown separately. All variants begin with ¥1,000,000, LONG/CASH only, 100-share lots, MAX3 primary and MAX4/MAX5 sensitivity.

| Arm | Capacity | Valid events | Priced session minutes | Funded / confirmed exits | Censored end-open | Realized-only PnL | Final Equity / Portfolio Return / full MaxDD |
|---|---:|---:|---:|---:|---:|---:|---|
| IM | MAX3 | 162/629 (25.76%) | 24.20% | 27 / 26 | 1 | −¥217,413.43 | null / null / null |
| IM | MAX4 | 161/629 (25.60%) | 23.30% | 36 / 35 | 1 | −¥121,540.23 | null / null / null |
| IM | MAX5 | 160/629 (25.44%) | 22.40% | 45 / 44 | 1 | −¥57,981.49 | null / null / null |
| R1 | MAX3 | 213/838 (25.42%) | 26.47% | 27 / 26 | 1 | −¥197,554.34 | null / null / null |
| R1 | MAX4 | 213/838 (25.42%) | 26.47% | 36 / 35 | 1 | −¥128,951.06 | null / null / null |
| R1 | MAX5 | 212/838 (25.30%) | 25.72% | 45 / 44 | 1 | −¥150,066.64 | null / null / null |

Realized-only PnL excludes the value and eventual resolution of open censored shares; it cannot rank variants or be divided by initial cash to obtain a portfolio return. The full scorecard contains PF, win rate, trade tail, utilization, concentration, capacity/cash/valuation rejects, evaluator-only funding attribution and IM/R1 common-funded pairs (MAX3 23, MAX4 35, MAX5 42).

## Rank enrichment: reused audited v0 source

Frozen R35 priority is `newEligibleRank ASC → savedV1Score DESC → symbol ASC → entryId ASC`, each rank known no later than frozen Entry. No new rank fit/weight/threshold was used. Evaluator-only `POST_ENTRY_UPSIDE_GE5` is examined after rank order and never enters sizing.

| Arm | Baseline | Top1: hits / selected, rate, × baseline | Top3: hits / selected, rate, × baseline | Top5: hits / selected |
|---|---:|---|---|---|
| IM | 222/1,150 = 19.30% | 122/561, 21.75%, 1.127× | 203/1,031, 19.69%, 1.020× | 222/1,150 |
| R1 | 200/1,107 = 18.07% | 154/770, 20.00%, 1.107× | 198/1,077, 18.38%, 1.018× | 200/1,107 |

The six frozen capital replays funded primary high-upside counts IM MAX3/4/5 = 6/10/15 out of 222 available, R1 = 7/11/14 out of 200. These counts are evaluator attribution, not causal rank inputs. Existing rank's Top3 enrichment is weak; no new ranker is fitted from this exposed result.

## Exact unresolved references and next boundary

The full append-only `DEVELOPMENT_INTEGRATED_V1_MISSING_REFERENCES.json.gz` lists **3,280 distinct variant–timestamp–position missing references**, including input key, quantity, cost basis, last observed knownAt and reason. Of these, 3,255 are cross-session censored `2025-07-17|59050|578`; 25 are same-day afternoon checkpoints with no post-lunch completed owned-symbol bar. The missing terminal auction on 2025-07-17 is never replaced with a 15:20 fill. The last observed 15:20 completed CLOSE became known at 15:21 and can mark 15:30 in v1, but cannot release cash. No allowlisted next-session raw path for 59050 or certified corporate-action continuity exists in the pinned input. The earliest after-auction permanent gap is 2025-07-18 09:00; gaps persist through 2025-08-25 15:30.

To obtain full-period equity, an **independent, causally timestamped, symbol-complete valuation source and verified corporate-action lineage**, plus a pre-performance treatment of missing post-lunch observations, must be available. A new accounting protocol must be frozen before any new replay; do not backfill 15:30 auction, carry stale prices over lunch/overnight, open protected data or change Entry/Selector/rank/EXIT. If no legitimate source exists, retain this hard blocker and avoid any IM/R1 or MAX3/4/5 winner claim.

## Durable assets in this directory

- `DEVELOPMENT_INTEGRATED_V1_FULL_LEDGER.json.gz`: entire six-variant event/position ledger, scorecards, curves, paired positions, SHA-256 `597b37cd7b902fbb42347147f8a3c53af32a23cb1e6c421b8d6085e20338d22b`.
- `DEVELOPMENT_INTEGRATED_V1_FULL_SCORECARD.json.gz`: audited full scorecard, SHA-256 `0ab63f3895e9c7bb270c0e1071a7a42a0b2555ffd6537764463cade1bebad770`.
- `DEVELOPMENT_INTEGRATED_V1_MISSING_REFERENCES.json.gz`: all 3,280 unresolved valuation references, SHA-256 `67b2868fb9a94ca4c9e2716ad7e75813b3380a56f730be798dd5c8a61eaa837c`.
- `DEVELOPMENT_INTEGRATED_V1_SIX_CURVES.zip`: six CSV with timestamp, equity, cash, gross exposure, utilization, drawdown, validity; nulls preserved. SHA-256 `881a1459076478dde8bb09f116d6e1097921835d4ba60f68c967ca38cc33233f`.
- `DEVELOPMENT_INTEGRATED_V1_{im_max345,max3_im_vs_r1,r1_max345}.png`: partial asset curves with explicit null gaps and post-gap shaded region. `DEVELOPMENT_INTEGRATED_V1_PLOT_SOURCE.py` plots the CSV. These are **partial** Development observations, not six complete portfolio histories.

Supersedes v0 controlling Capital status only. R50/R51 formal EXIT limitations and all frozen upstream evidence remain authoritative.
