# Phase57 LONG-only Ridge Top5 Hit Distribution — Final Diagnostic

Date: 2026-09-16 JST  
PR: #587  
Branch: `research/phase57-long-only-cash-equity`  
Diagnostic contract: `ELIGIBILITY-TOP5-HIT-DISTRIBUTION-1`  
Contract commit: `4cd58726eeeb5f34ae8bb75570589e07261f6100`  
Implementation commit: `ebc64571017d1bacf12446c231cdc77ecd5058b4`  
Measurement run: `35027741312`

## 1. Executive verdict

**FREEZE READINESS CONFIRMED.**

With the already-fixed 5-minute freshness eligibility applied before ranking, the saved Corrected-Measurement Ridge Top5 repeatedly contains future upward opportunities at each decision timestamp:

- at least one future `+1%` high-touch in **98.55%** of decisions;
- at least one future `+2%` high-touch in **97.24%**;
- at least one future `+3%` high-touch in **92.50%**;
- at least one future `+5%` high-touch in **72.50%**.

Median hit counts per Top5 are respectively **4, 3, 2, and 1**. The signal remains after requiring a future 5-minute close: at least one close-confirmed `+3%` opportunity occurs in **90.92%** of decisions and at least one close-confirmed `+5%` opportunity in **70.00%**.

This diagnostic does not formally freeze the Selector. It supports presenting the exact saved Ridge plus eligibility contract as a Freeze Candidate for user approval. Validation/OOS remain sealed.

## 2. Remote, PR, CI, workflow safety

The remote state was checked before the diagnostic. PR #587 was open and draft on the requested branch. The implementation HEAD was `ebc64571017d1bacf12446c231cdc77ecd5058b4`.

Normal CI on that HEAD:

| Workflow | Result |
|---|---:|
| Predict Tests | SUCCESS |
| Phase52 Daily Dry-Run Persistence | SUCCESS |
| Phase57 LONG-only Research Foundation | SUCCESS |
| L2 Selector Development | SKIPPED |
| Capacity Diagnostic | SKIPPED |
| Missed Opportunity Diagnostic | SKIPPED |
| CURRENT Entry/Exit integration | SKIPPED |

The dedicated measurement-only run completed successfully. It reused saved encrypted Development inputs and saved C+D Ridge weights, reconstructed evaluator-only rows, performed no fit, made no provider request, removed private inputs, and uploaded aggregate evidence only.

Safety audit:

- fit/refit calls: **0**
- provider requests: **0**
- Validation opened: **false**
- OOS opened: **false**
- model/feature/target/Top-N/freshness changes: **false**
- threshold tuning: **false**
- trading and broker-write flags: **false**

## 3. Evidence identity and population

| Item | Value |
|---|---:|
| Saved Development sessions | 76 |
| Full reconstructed population rows | 2,758,341 |
| Fresh-price eligible rows | 1,755,720 |
| Decision timestamps | 760 |
| Top5 selection events | 3,800 |
| Top5 events per decision | exactly 5 |
| High-path evaluable events | 3,790 / 3,800 (99.7368%) |
| Close-path evaluable events | 3,800 / 3,800 (100%) |

Ten selected events had no continuous future high path. They remain selected and count as non-hits in the decision-distribution lower bound; they were not replaced with lower-ranked candidates.

Artifact identity:

- artifact ID: `10419919267`
- artifact name: `phase57-long-only-top5-hit-distribution-35027741312`
- artifact ZIP SHA-256: `c766f0e79813aa6e04c812c157b34e5467c480f3f34e93bbdefd9dc00095b100`
- report self-hash: `6bee3d44cbf6664886ccc9fd2de0624d1b3936e7e787187887fb912c78a5ae65` (recomputed match)

## 4. Threshold precision, recall, and lift

Primary opportunity definition is same-session future 5-minute High relative to the valid Decision Price. Precision uses evaluable selected events; the lower-bound precision uses all 3,800 selected events.

| Threshold | Opportunity N | Selected hits | Precision@5 | All-slot lower bound | Prevalence | Precision lift | Recall | Random expected recall | Recall lift |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| +1% | 321,894 | 2,895 | 76.39% | 76.18% | 18.37% | 4.16x | 0.899% | 0.2165% | 4.15x |
| +2% | 100,010 | 2,323 | 61.29% | 61.13% | 5.71% | 10.74x | 2.323% | 0.2159% | 10.76x |
| +3% | 44,991 | 1,791 | 47.26% | 47.13% | 2.57% | 18.40x | 3.981% | 0.2159% | 18.44x |
| +5% | 15,429 | 947 | 24.99% | 24.92% | 0.88% | 28.38x | 6.138% | 0.2160% | 28.41x |

Random expectation is computed within the same eligible universe at each decision timestamp with the same `K=5`. It is not calculated as total slots divided by total opportunities.

## 5. Per-decision Top5 hit distribution — future High

### Distribution of 0/5 through 5/5

| Hits in Top5 | +1% decisions | +2% decisions | +3% decisions | +5% decisions |
|---:|---:|---:|---:|---:|
| 0/5 | 11 (1.45%) | 21 (2.76%) | 57 (7.50%) | 209 (27.50%) |
| 1/5 | 17 (2.24%) | 68 (8.95%) | 131 (17.24%) | 274 (36.05%) |
| 2/5 | 65 (8.55%) | 145 (19.08%) | 228 (30.00%) | 183 (24.08%) |
| 3/5 | 164 (21.58%) | 225 (29.61%) | 197 (25.92%) | 70 (9.21%) |
| 4/5 | 259 (34.08%) | 215 (28.29%) | 122 (16.05%) | 23 (3.03%) |
| 5/5 | 244 (32.11%) | 86 (11.32%) | 25 (3.29%) | 1 (0.13%) |

### Decision-level summary

| Metric | +1% | +2% | +3% | +5% |
|---|---:|---:|---:|---:|
| Mean hits / Top5 | 3.809 | 3.057 | 2.357 | 1.246 |
| Median hits / Top5 | 4 | 3 | 2 | 1 |
| P(at least 1) | 98.55% | 97.24% | 92.50% | 72.50% |
| P(at least 2) | 96.32% | 88.29% | 75.26% | 36.45% |
| P(at least 3) | 87.76% | 69.21% | 45.26% | 12.37% |
| P(at least 4) | 66.18% | 39.61% | 19.34% | 3.16% |
| P(5/5) | 32.11% | 11.32% | 3.29% | 0.13% |

## 6. Close-confirmed hit distribution

Requiring a future 5-minute Close at or above each threshold reduces the hit rate but preserves substantial enrichment.

| Threshold | Precision@5 | Mean hits / Top5 | P(>=1) | P(>=2) | P(>=3) | P(>=4) | P(5/5) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| +1% | 71.82% | 3.591 | 98.55% | 95.39% | 83.03% | 57.24% | 24.87% |
| +2% | 57.00% | 2.850 | 96.32% | 85.79% | 61.58% | 33.95% | 7.37% |
| +3% | 43.58% | 2.179 | 90.92% | 71.45% | 38.55% | 15.00% | 1.97% |
| +5% | 22.95% | 1.147 | 70.00% | 32.37% | 10.00% | 2.24% | 0.13% |

Close-confirmed recall lifts are 4.30x, 11.30x, 19.65x, and 31.58x for +1%, +2%, +3%, and +5% respectively.

## 7. Time to first hit

### Future High, primary

| Threshold | Hit N | P25 | Median | P75 | P90 | <=15m | 16–30m | 31–60m | 61–120m | >120m |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| +1% | 2,895 | 5m | 10m | 35m | 90m | 1,780 | 362 | 202 | 383 | 168 |
| +2% | 2,323 | 5m | 15m | 65m | 115m | 1,217 | 297 | 227 | 367 | 215 |
| +3% | 1,791 | 5m | 20m | 70m | 140m | 862 | 224 | 181 | 298 | 226 |
| +5% | 947 | 5m | 30m | 95m | 182m | 404 | 86 | 113 | 162 | 182 |

### Future Close, secondary

| Threshold | Hit N | P25 | Median | P75 | P90 |
|---:|---:|---:|---:|---:|---:|
| +1% | 2,729 | 5m | 15m | 55m | 100m |
| +2% | 2,166 | 10m | 22.5m | 70m | 135m |
| +3% | 1,656 | 10m | 25m | 75m | 152.5m |
| +5% | 872 | 10m | 35m | 101.25m | 190m |

## 8. Time-of-day diagnostic

No time-of-day rule was added. The fixed groups were committed before measurement.

### Future High

| Period | Decisions | +1% Precision / P>=1 | +2% Precision / P>=1 | +3% Precision / P>=1 | +5% Precision / P>=1 |
|---|---:|---:|---:|---:|---:|
| Morning | 152 | 85.38% / 100.00% | 69.96% / 98.68% | 55.47% / 97.37% | 33.47% / 82.89% |
| Late Morning | 228 | 78.86% / 99.56% | 65.26% / 98.68% | 51.75% / 95.18% | 28.95% / 79.82% |
| Afternoon | 380 | 71.29% / 97.37% | 55.42% / 95.79% | 41.25% / 88.95% | 19.20% / 63.95% |

The signal weakens in the afternoon but remains materially enriched. This is a known characteristic, not a new filtering rule.

## 9. Market and liquidity diagnostics

### Future High precision by market

| Segment | Selected / evaluable | +1% | +2% | +3% | +5% |
|---|---:|---:|---:|---:|---:|
| Prime | 268 / 268 | 76.12% | 63.81% | 54.10% | 31.34% |
| Standard | 1,858 / 1,852 | 78.83% | 66.47% | 54.75% | 30.51% |
| Growth | 1,674 / 1,670 | 73.71% | 55.15% | 37.84% | 17.84% |

### Future High precision by liquidity

| Liquidity | Selected / evaluable | +1% | +2% | +3% | +5% |
|---|---:|---:|---:|---:|---:|
| Low | 511 / 505 | 72.08% | 60.40% | 48.12% | 24.16% |
| Mid | 890 / 889 | 74.13% | 58.27% | 42.74% | 19.57% |
| High | 2,399 / 2,396 | 78.13% | 62.60% | 48.75% | 27.17% |

The edge is not explained solely by Prime or High Liquidity. Growth and Mid Liquidity are weaker at the +3/+5 thresholds, but all reported segments retain substantial opportunity concentration. No segment model, exclusion, or threshold was introduced.

## 10. Freeze-readiness interpretation

1. **Future +1% stability:** very high. The Top5 contains at least one hit at 98.55% of decision timestamps; the median is four hits.
2. **Future +2% stability:** high. At least one hit occurs at 97.24%; the median is three hits.
3. **Primary Future +3%:** strong. At least one hit occurs at 92.50%; the median is two hits, with 18.40x precision lift and 18.44x recall lift.
4. **Stretch Future +5%:** meaningful but incomplete. At least one hit occurs at 72.50%; the median is one hit, with 28.38x precision lift and 28.41x recall lift.
5. **Touch versus close:** the edge remains when requiring a 5-minute close. The primary +3% and stretch +5% P(>=1) decline only from 92.50% to 90.92% and from 72.50% to 70.00%.
6. **Concentration risk:** results are weaker in the afternoon and Growth segment, but the edge exists across every fixed time, market, and liquidity group. It is not explained by one segment alone.

## 11. Known weaknesses and scope limits

- At +5%, 27.50% of decision timestamps have no High-based hit; 5/5 occurs only once (0.13%).
- Afternoon +5% precision is 19.20%, versus 33.47% in Morning.
- Growth +5% precision is 17.84%, below Prime and Standard.
- High touch is an opportunity evaluator, not proof of executable fill. Close confirmation mitigates but does not eliminate this distinction.
- This is Development evidence only. It is not a Validation or OOS claim.
- The saved C+D Ridge is evaluated partly on its fit partitions; A/B provide previously observed outside-C+D-fit diagnostic evidence. This limits performance inference but does not invalidate the requested freeze-readiness diagnostic.
- Ten High paths were unavailable; treating them as non-hits changes aggregate precision by only about 0.07–0.20 percentage point depending on threshold.

## 12. Recommendation and STOP

The single next action is: **ask the user to approve or reject formal freezing of the exact saved C+D Ridge score, 5-minute causal freshness eligibility, and per-decision Top5 policy.**

No formal Freeze was performed. No Validation/OOS, Entry/EXIT/Allocation, model/feature/target/Top-N change, retraining, or provider acquisition was started.

