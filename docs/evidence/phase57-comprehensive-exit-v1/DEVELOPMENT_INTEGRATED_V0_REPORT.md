# Phase57 Development Integrated v0 — terminal-hold benchmark

Saved 2026-09-27 12:46:40 JST. Controlling launch/execution SHA `fdc04c577c518db8b8e854c14d45bdaec811516b`; tested source `4de5a6ed6dbece3bec86582962d49ed2d2160da7`. **Development outcome-exposed benchmark, not Final EXIT, not Fresh/OOS or live estimate.** No integrated Entry/Capacity SELECT is made.

## Exact scope, identity, reproducibility

- Frozen Entry Dual Freeze `4878a1cc53430e816261dea0fb16aeb53b3c238d`; Selector/Entry changed 0. Rank is existing R35 `newEligibleRank ASC → savedV1Score DESC → symbol ASC → entryId ASC`, with rank knownAt ≤ Entry; sizing is R35 equity/MAX_N, 100-share lots, cash-only.
- Controlling pre-performance protocol V2 SHA256 `9b345b3e73214eea0c58caa9509ea0bff8dc6e3c57a9cff646a02566bf4d8fc0`. V1 was corrected **before performance** to restrict to R50 frozen OOF score window, 34 sessions / IM 1,150 fills / R1 1,107 fills. Full frozen Entry population remains 2,155 Opportunities per arm over 58 sessions, but is **not** the measured portfolio window. Do not generalize score-window returns to all 2,155.
- EXIT is R50_B behavioral terminal-hold control, zero model Harvests; auction at exact 15:30 endpoint only. `EXIT STATUS = BENCHMARK / NOT FINAL EXIT`. The five unsuccessful EXIT generations remain NO_SELECTION_STOP; no Final EXIT Freeze exists.
- Required CI run `36292067129` SUCCESS, artifact `10922179082`, ZIP SHA256 `1b0e8971ce796735d85219076115cc2c812e124f47f0ebac520afaa85f94bcfd`: 47 synthetic/regression tests, source support, fit/replay 0. Initial CI run `36291720633` is superseded because its loader decoded beyond allowlists (see exposure below).
- Replay run `36292209627` SUCCESS, attempt 1; artifact `10923055754`, ZIP SHA256 `802ee621a2fb2f6b00c1d4719b5ef193ce76c437793766394f48d86cc642cd68`. Run A/B result SHA256 both `fb1935cc84ba5ebea29fed24d007cec216d7ca0f3f39462157838b257a2bd15c`, byte-identical. Six variants; fits 0; provider 0; protected 0. Independent read-only audit asserts cash and capacity invariants, final-cash conservation, censor ownership, evaluator isolation, score-window support and A/B identity. Full scorecards (including p05/p10/worst, cash, gross exposure, concentration, turnover, 4+ simultaneous event attribution, per-session enrichment and paired counts) are preserved in `DEVELOPMENT_INTEGRATED_V0_FULL_SCORECARD.json.gz` SHA256 `c11d846809755d8d36193f2d7988a1fdc238e08292d97517787799b763757ca3`.

## Causal rank enrichment before portfolio scoring

Top-N is within each simultaneous frozen Entry-time batch, **not** chosen by future outcome or by ranking candidates across later intraday times. `POST_ENTRY_UPSIDE_GE5` is evaluator-only; denominators are IM 1,150 and R1 1,107 filled score-window Entries (supports 222 and 200). Rates are descriptive on reused Development.

| Arm | Top | Selected | ≥5% hits | Hit rate | Baseline | Enrichment | ≥5% reach | Canonical ≥5% reach |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| IM | 1 | 561 | 122 | 21.75% | 19.30% | 1.127× | 54.95% | 52.20% |
| IM | 3 | 1,031 | 203 | 19.69% | 19.30% | 1.020× | 91.44% | 90.44% |
| IM | 5 | 1,150 | 222 | 19.30% | 19.30% | 1.000× | 100% | 100% |
| R1 | 1 | 770 | 154 | 20.00% | 18.07% | 1.107× | 77.00% | 74.54% |
| R1 | 3 | 1,077 | 198 | 18.38% | 18.07% | 1.018× | 99.00% | 98.43% |
| R1 | 5 | 1,107 | 200 | 18.07% | 18.07% | 1.000× | 100% | 100% |

IM has 88 simultaneous batches of at least four candidates, R1 26. Top1 yields only modest enrichment, and Top3 approaches the all-fill baseline. Top5 covers every candidate because the observed batch maximum is ≤5. These are rank diagnostics, **not** capacity-constrained returns or a reason to refit/reweight rank.

## Six-variant portfolio scorecard — formally censored

Initial cash ¥1,000,000; current main/R35 slot budget and 100-share lots; MAX3 primary, MAX4/MAX5 sensitivity. Realized PnL is for closed trades **only**, not Portfolio Return. All six have one terminal-unresolved funded position and an unknown final valuation. Thus final equity, Portfolio Return and full-period MaxDD are `null`, not zero. Covered-minute utilization/PF/win/tails are **partial descriptive diagnostics**, not a full-period ranking.

| Arm | Capacity | Funded / closed | Realized PnL | Capacity / cash rejects | Missing-mark rejects | Priced minutes | PF (closed) | Win (closed) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| IM | MAX3 | 27 / 26 | −¥217,413 | 109 / 5 | 1,009 | 9.50% | .080 | 19.23% |
| IM | MAX4 | 36 / 35 | −¥122,662 | 73 / 6 | 1,035 | 7.01% | .487 | 25.71% |
| IM | MAX5 | 44 / 43 | −¥138,453 | 64 / 9 | 1,033 | 7.47% | .389 | 25.58% |
| R1 | MAX3 | 26 / 25 | −¥258,706 | 101 / 1 | 979 | 9.86% | .240 | 16.00% |
| R1 | MAX4 | 34 / 33 | −¥117,711 | 69 / 3 | 1,001 | 6.92% | .553 | 33.33% |
| R1 | MAX5 | 41 / 40 | −¥173,233 | 70 / 5 | 991 | 7.06% | .335 | 27.50% |

Every variant funded `2025-07-17|59050|578`, whose exact terminal auction is missing. The position remains open, retains spent cash/capacity, and has no exact later known-NOW mark from this frozen source. Strict R35 sizing then rejects later opportunities as `MISSING_FRESH_MARK_UNRESOLVED_SIZING`; there is no same-price/future/entry-cost mark substitution or fictional cash release. Time-weighted utilization among *covered* intervals is IM 66.0%/57.8%/58.9% and R1 64.4%/52.0%/47.8% for MAX3/4/5 respectively; only ~7–10% of scheduled-window minutes are fully priced, so these are not whole-window utilization estimates.

Evaluator-only funded POST_ENTRY_UPSIDE_GE5 reach: IM 6/222, 10/222, 14/222 and R1 8/200, 12/200, 14/200 for MAX3/4/5. At simultaneous ≥4-candidate events, MAX3 accepted IM 22 (4 primary hits) and rejected 361 (93 hits); R1 accepted 7 (0 hits) and rejected 101 (20 hits). Most rejects occur after or around valuation/censor constraints, so they cannot be attributed to rank error alone. Valid paired common funded Opportunities: MAX3 20; MAX4 28; MAX5 34. Full evaluator-only capital allocation amounts and terminal capture are in the compact scorecard.

## Disposition and next boundary

We did build and measure the frozen Entry × existing causal Capital × terminal-hold **benchmark**. The dominant observable bottleneck is **missing executable terminal auction followed by unavailable fresh valuation**, not an identified Entry-arm or MAX3/4/5 winner. The simultaneous-batch rank gives only ~1.1× Top1 upside enrichment. Because full-period Portfolio Return/MaxDD are censored, neither IM versus R1 nor MAX3 versus MAX4/5 can be declared economically superior from this run. There is no candidate SELECT, Final EXIT Freeze, post-hoc EXIT/rank adjustment, or portfolio performance claim.

Any new handling of post-terminal unresolved ownership, valuation availability, or a different evaluation window requires a **new prospective benchmark protocol before replay**; do not alter or overwrite this frozen result. Final EXIT research remains separate, with R50 `CAUSAL_SEPARATION_NOT_SUPPORTED`.

## Exposure and Safety

R49's initial allowlist-external 3,220 JSON decodes remain disclosed. This Work's **initial local preflight and superseded first CI** decoded all 5,375 raw payloads (4,225 outside this 1,150-opportunity score-window allowlist) and all 5,375 origin payloads (3,220 outside the full 2,155-entry allowlist). None was used for ranking, sizing, scoring, display, tuning or performance; before accepted CI/replay, the loader was repaired to decode only 1,150 raw and 2,155 origin payloads. Never claim historical out-of-scope access 0. No Fresh/OOS/Protected opens, no new provider acquisition. Safety9 all false; no main merge, broker, Excel, RSS, live, paper, production or transmission.
