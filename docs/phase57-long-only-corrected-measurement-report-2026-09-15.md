# Phase57 LONG-only Corrected Measurement Report — 2026-09-15 JST

## 1. Executive Verdict

**PROMISING BASELINE / KEEP CURRENT TARGET CANDIDATE, with a material measurement-coverage blocker before Freeze.**

The corrected measurement preserves a strong Ridge top-tail signal. Among Top5 events with a causally fresh decision price, 53.39% subsequently touched +3% and 30.48% touched +5% in the same session. These are 20.79x and 34.61x the unconditional prevalence. Strict wall-clock 30-minute return remains positive at +98.84 bps mean and +25.20 bps median.

The material limitation is coverage: 36.35% of eligible cross-sectional rows and 29.50% of selected events have no accepted price within five wall-clock minutes. They fail closed and are not replaced. This missingness is concentrated in lower-liquidity names and varies by market and decision time, so the result is a strong corrected-measurement Development baseline rather than a Freeze decision.

## 2. Remote HEAD / PR / CI

| Item | Result |
|---|---|
| Repository / branch | `Iam-2squared/ark-terminal` / `research/phase57-long-only-cash-equity` |
| PR | [#587](https://github.com/Iam-2squared/ark-terminal/pull/587), open draft |
| Contract commit | [`20356553ddece7309a6a00654c3b1e276d1a3466`](https://github.com/Iam-2squared/ark-terminal/commit/20356553ddece7309a6a00654c3b1e276d1a3466) |
| Measurement implementation | [`582daf88c2ca1521489b6e5033030afb147e54d3`](https://github.com/Iam-2squared/ark-terminal/commit/582daf88c2ca1521489b6e5033030afb147e54d3) |
| Coverage-report correction | [`09e0cae350d3e1668f4c3c4329a93bff7c7ab4d3`](https://github.com/Iam-2squared/ark-terminal/commit/09e0cae350d3e1668f4c3c4329a93bff7c7ab4d3) |
| Final measurement run | [#34985364169](https://github.com/Iam-2squared/ark-terminal/actions/runs/34985364169), success |
| Aggregate artifact | `10404515279`, ZIP SHA-256 `d57013c55a8a083e369f7ab4129155f52e97cbdecf5a0221a8c2f404b156b2ba` |
| Report self-hash | `b024f2700764097628eb9a1689a2bee3d9ac528fe26a15b2cb78716169c014e3` |

## 3. Workflow Trigger Audit

The contract was committed before diagnostic code. The measurement workflow is path-scoped to the corrected-measurement files, uses saved encrypted Development artifacts, has no provider client or model-library installation, performs no fit, purges private inputs, and uploads aggregate evidence only.

On both measurement commits, the L2 Selector Development, Selector Capacity, Missed Opportunity, and CURRENT Entry/Exit workflows were skipped. Only ordinary CI and the dedicated corrected-measurement workflow ran. Provider requests and fit calls recorded by the report are both zero.

## 4. Measurement Contract and Semantics

Contract `CORRECTED-MEASUREMENT-1` is fixed at commit `20356553ddece7309a6a00654c3b1e276d1a3466`.

| Measure | Fixed definition |
|---|---|
| Decision Price | Latest accepted Minute close causally available at or before the decision timestamp, maximum age 5 wall-clock minutes |
| Missing/stale price | Fail closed; no forward-fill, interpolation, or replacement candidate |
| Primary 30m return | Strict wall-clock `t + 30m`; latest valid observation at the endpoint with maximum endpoint age 5 minutes |
| Lunch / absent endpoint | No bridge or forward-fill; evaluation unavailable |
| Primary opportunity | Future continuous 5m High touches +2%, +3%, or +5% from Decision Price before same-session end |
| Secondary confirmation | Future continuous 5m Close or terminal-auction Close reaches the threshold |
| 30m MFE / MAE | `max(0, max future High / DecisionPrice - 1)` / `min(0, min future Low / DecisionPrice - 1)` through wall-clock 30m |
| Session MFE / MAE | Same clipped definitions through same-session end; no overnight carry |

## 5. Fresh-price Coverage

Across 76 available Development sessions there are 2,758,341 causal candidate rows. A fresh Decision Price exists for 1,755,720 rows (63.65%); 1,002,621 rows (36.35%) fail closed. Price age has median 2 minutes, P75 12, P90 36, P95 63, P99 149, and maximum 359 minutes before applying the five-minute freshness rule.

### Coverage by market

| Market | Rows | Fresh rows | Fresh rate | Unavailable rate |
|---|---:|---:|---:|---:|
| Prime | 1,248,109 | 1,083,996 | 86.85% | 13.15% |
| Standard | 1,079,873 | 437,718 | 40.53% | 59.47% |
| Growth | 430,359 | 234,006 | 54.37% | 45.63% |

### Coverage by liquidity

| Liquidity | Rows | Fresh rows | Fresh rate | Unavailable rate |
|---|---:|---:|---:|---:|
| High | 948,544 | 916,943 | 96.67% | 3.33% |
| Mid | 945,571 | 628,737 | 66.49% | 33.51% |
| Low | 864,226 | 210,040 | 24.30% | 75.70% |

### Coverage by decision time

| Decision time | Rows | Fresh rate | Unavailable rate |
|---|---:|---:|---:|
| 09:30 | 276,633 | 67.85% | 32.15% |
| 10:00 | 278,907 | 62.62% | 37.38% |
| 10:30 | 279,941 | 59.13% | 40.87% |
| 11:00 | 280,353 | 57.50% | 42.50% |
| 11:30 | 280,196 | 71.31% | 28.69% |
| 13:00 | 278,565 | 61.57% | 38.43% |
| 13:30 | 277,054 | 59.15% | 40.85% |
| 14:00 | 274,794 | 60.22% | 39.78% |
| 14:30 | 271,195 | 62.64% | 37.36% |
| 15:00 | 260,703 | 75.23% | 24.77% |

The unavailable rows are composed of 64.05% Standard, 19.58% Growth, and 16.37% Prime; by liquidity they are 65.25% Low, 31.60% Mid, and 3.15% High. The tables above use each group as the denominator and are the relevant bias diagnostic.

## 6. Corrected Wall-clock 30m Coverage

Strict wall-clock 30m is evaluable for 1,214,637 rows, 44.04% of the full causal cross-section. Of these endpoints, 81.65% are continuous 5m closes and 18.35% are terminal-auction closes. Endpoint age is zero minutes through P95 and no more than five minutes.

Across all evaluable rows, the strict-30m mean is +0.018 bps, median 0 bps, 30m MFE +0.323%, and true MAE -0.325%. This near-zero full-universe return supplies the neutral population against which Ridge concentration is judged.

## 7. Future Opportunity Prevalence and Early Composition

Primary opportunity uses future 5m High. Secondary uses a future 5m or auction Close.

| Threshold | High-touch count | High prevalence | Close-confirmed count | Close prevalence | High opportunities with current return <3% |
|---:|---:|---:|---:|---:|---:|
| +2% | 100,010 | 5.708% | 88,850 | 5.061% | 83.53% |
| +3% | 44,991 | 2.568% | 39,053 | 2.224% | 78.28% |
| +5% | 15,429 | 0.881% | 12,788 | 0.728% | 72.12% |

The North-Star opportunities are mostly still early by the fixed diagnostic: 35,217 of the +3% opportunities and 11,128 of the +5% opportunities occur while current return is below +3%. Early +3% opportunities are 38.74% Standard, 37.08% Growth, and 24.18% Prime; early +5% opportunities are 41.17% Standard, 40.79% Growth, and 18.04% Prime. High liquidity accounts for 51.33% of early +3% and 55.58% of early +5%, but Mid and Low together remain substantial.

## 8. Corrected MFE / MAE

| Scope | MFE | True MAE |
|---|---:|---:|
| Full cross-section, wall-clock 30m | +0.323% | -0.325% |
| Ridge Top5, wall-clock 30m | +3.162% | -1.409% |
| Ridge Top5, same-session end | +4.229% | -2.385% |

MAE is clipped at zero whenever price never trades below Decision Price; positive MAE cannot offset adverse excursions. MFE is symmetrically clipped at zero. The former legacy aggregate allowed the positive-MAE distortion and is not used here.

## 9. Corrected-Measurement Ridge Top5

This is `CORRECTED_MEASUREMENT_RIDGE_SAVED_CD`, using the saved C+D Ridge artifact with SHA-256 `994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb`, 1,077,111 training rows, and the fixed 15-feature universe. No fit occurred in this measurement. It is not the unavailable historical C-only v1.

| KPI | Corrected result |
|---|---:|
| Selection events | 3,800 |
| Fresh-price evaluable | 2,679 (70.50%) |
| Strict-30m evaluable | 1,916 (50.42%) |
| Wall-clock 30m mean | +98.84 bps |
| Wall-clock 30m median | +25.20 bps |
| Wall-clock 30m positive rate | 52.56% |
| Positive sessions | 70/76 |
| 30m MFE / true MAE | +3.162% / -1.409% |
| Session MFE / true MAE | +4.229% / -2.385% |
| Previous-close Final +5% precision | 11.42% (reference only) |

## 10. North-Star Precision, Recall, and Capacity-aware Lift

Precision uses the 2,679 Top5 selections with a fresh causal Decision Price. `All selections lower bound` keeps all 3,800 Top5 slots in the denominator and treats unavailable outcomes conservatively. Random expectation is computed within each decision timestamp from `K/N_t`.

| High-touch threshold | Precision@5 | All-selections lower bound | Recall | Random recall | Recall lift | Prevalence | Precision lift |
|---:|---:|---:|---:|---:|---:|---:|---:|
| +2% | 66.08% | 46.45% | 1.765% | 0.1366% | 12.92x | 5.708% | 11.58x |
| **+3%** | **53.39%** | **37.53%** | **3.170%** | **0.1366%** | **23.21x** | **2.568%** | **20.79x** |
| **+5%** | **30.48%** | **21.42%** | **5.276%** | **0.1365%** | **38.64x** | **0.881%** | **34.61x** |

Close-confirmed precision is 61.10% at +2%, 49.31% at +3%, and 28.07% at +5%. Close-confirmed recall lifts are 13.49x, 24.77x, and 43.07x respectively. High touches and close confirmations remain separate measures.

## 11. Time to Opportunity

| Opportunity | P25 | Median | P75 | P90 | <=15m | 16–30m | 31–60m | 61–120m | >120m |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| High +3% | 5m | 15m | 65m | 125m | 738 | 170 | 143 | 220 | 155 |
| High +5% | 5m | 20m | 75m | 170m | 379 | 74 | 95 | 131 | 135 |
| Close +3% | 10m | 20m | 70m | 135m | 602 | 184 | 150 | 234 | 151 |
| Close +5% | 10m | 30m | 90m | 180m | 310 | 92 | 87 | 129 | 134 |

The median selected hit appears quickly, while the long upper tail shows that same-session opportunity is broader than a 30-minute exit target. No time threshold was used to filter or tune selection.

## 12. Target Alignment

Corrected wall-clock 30m return and same-session MFE have Pearson correlation 0.4184 and Spearman correlation 0.5419. Future-opportunity prevalence rises sharply in the upper corrected-30m outcome tail.

| Corrected 30m outcome band | Mean 30m | Future +3% | Future +5% | Session MFE | Session true MAE |
|---|---:|---:|---:|---:|---:|
| Top 1% | +305.02 bps | 65.75% | 32.99% | +5.13% | -0.84% |
| Top 5% | +146.02 bps | 24.76% | 9.92% | +2.68% | -0.56% |
| Top 10% | +103.66 bps | 14.82% | 5.59% | +2.00% | -0.49% |
| Top 20% | +70.40 bps | 8.49% | 3.08% | +1.47% | -0.44% |
| Middle 20–80% | -0.63 bps | 1.11% | 0.35% | +0.52% | -0.54% |
| Bottom 20% | -68.42 bps | 2.05% | 0.80% | +0.43% | -1.41% |

This supports retaining strict wall-clock 30m as a candidate target: its upper tail strongly enriches the North Star. The lower-tail rebound pocket is real but much weaker and has materially worse adverse excursion.

## 13. Earlier-observed A/B Development Diagnostic

A/B is outside the C+D fit but was already observed during prior Development work, so it is an honest stability diagnostic only, not sealed Validation/OOS.

| KPI | A/B result |
|---|---:|
| Sessions | 36 |
| Strict-30m mean / median | +86.56 / +16.08 bps |
| Positive rate / sessions | 50.93% / 33 of 36 |
| High +3% Precision@5 | 47.24% |
| High +3% all-selections lower bound | 32.33% |
| High +3% Recall lift | 21.92x |
| High +5% Precision@5 | 24.03% |
| High +5% all-selections lower bound | 16.44% |
| High +5% Recall lift | 34.19x |

The signal weakens outside the C+D fit, as expected, but remains large relative to same-timestamp random selection and positive in 33/36 sessions. This is supportive Development evidence, not a Validation claim.

## 14. Legacy v1 Difference

The reported historical `+117.21 bps` v1 result used six subsequent closed observations, whose wall-clock horizon had median 45 minutes and maximum 355 minutes. It also used stale reference prices and a non-clipped MAE aggregate. It must remain labeled `Legacy 6-observation Measurement Diagnostic`.

The corrected baseline uses a saved C+D Ridge score because original C-only weights and row scores are unavailable. Its legacy six-observation diagnostic is +122.79 bps mean and +40.40 bps median on 2,806 available selected rows, but that number is not compared directly with corrected strict-30m performance.

## 15. What Ridge Does Well and Fails At

Ridge does well at concentrating future upside from a valid decision-time price. It turns a 2.57% unconditional +3% prevalence into 53.39% among evaluable Top5 selections, and a 0.88% +5% prevalence into 30.48%. The result also remains meaningful on the earlier-observed A/B sessions.

Ridge still misses most opportunities in absolute recall because Top5 capacity is intentionally narrow. More immediately, the current candidate universe permits stale rows to enter ranking: 29.50% of selected slots cannot be evaluated with a five-minute-fresh price, and the implementation correctly does not replace them after seeing availability. This makes coverage and eligibility semantics the main remaining blocker.

## 16. Root-cause Interpretation

1. **Measurement / evaluation coverage:** primary remaining problem. Corrected definitions work, but fresh-price availability is materially incomplete and non-uniform.
2. **Model / ranking:** Ridge has a strong baseline signal but is far from the North Star of nearly all Top5 names reaching +3%; this becomes the next model question after eligibility is made causal and measurable.
3. **Feature:** not established as the current root cause by this measurement-only run.
4. **Target:** strict wall-clock 30m has clear North-Star alignment in its upper tail; target redesign is not presently supported.

Interpretation **A** is supported: corrected Ridge is a useful baseline and clearly enriches both +3% and +5%. It is not Freeze-ready because of the causal price-coverage blocker and because this is Development evidence.

## 17. Recommended Next Research — One Item

Freeze a **causal candidate-eligibility and data-quality contract** that requires a valid <=5-minute Decision Price before ranking, then measure its coverage and selection impact without tuning the freshness threshold on returns. Do not change the model, target, features, Top N, Entry, EXIT, or Allocation in that step.

## Safety and STOP

Provider requests: 0. Fit calls: 0. Validation/OOS remained sealed. Candidate v2 was not rerun. No new model, feature, target, Top N policy, order path, or trading capability was introduced. Lane Y, main, and live circuit were untouched; all execution/write/trading flags remain false.

**STOP: no further research or implementation is authorized by this report.**
