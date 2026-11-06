# Phase57 LONG-only Eligibility-Aware Ridge Report — 2026-09-16 JST

## 1. Executive Verdict

**FREEZE CANDIDATE SUPPORTED — user approval required; no automatic Freeze.**

Applying the fixed five-minute Decision Price eligibility rule before ranking removes the post-selection coverage bias and preserves substantial Ridge enrichment. Primary Future +3% Precision@5 is 47.26% and stretch Future +5% Precision@5 is 24.99%, versus unconditional prevalence of 2.57% and 0.88%. Precision lift remains 18.40x and 28.38x. All 3,800 Top5 events have a fresh causal Decision Price; 99.74% have a continuous future 5m High evaluator path and 100% have a future 5m/auction Close path.

The gate materially changes the candidate population toward Prime and High-liquidity names, but the selected Ridge Top5 is still dominated by Standard and Growth, and strong opportunity precision remains in every market and liquidity group. The edge is therefore not explained solely by Prime or High liquidity.

## 2. Remote HEAD / PR / CI

| Item | Result |
|---|---|
| Repository / branch | `Iam-2squared/ark-terminal` / `research/phase57-long-only-cash-equity` |
| PR | [#587](https://github.com/Iam-2squared/ark-terminal/pull/587), open draft |
| Eligibility Contract | [`2998675a217317e4658272129d8759f16d11cc7e`](https://github.com/Iam-2squared/ark-terminal/commit/2998675a217317e4658272129d8759f16d11cc7e) |
| Measurement implementation | [`6930a1682eabf39971269b118486839d9d15ccba`](https://github.com/Iam-2squared/ark-terminal/commit/6930a1682eabf39971269b118486839d9d15ccba) |
| Measurement run | [#34988864742](https://github.com/Iam-2squared/ark-terminal/actions/runs/34988864742), success |
| Artifact | `10405482047`, ZIP SHA-256 `b9aab68806621d270abf8a6985e763eaebd617bd8945c6e24afa1f9dc719ba8c` |
| Report self-hash | `81451600639fd5d257bbfbed2129798d634326e1f61297cb6328d00c1b368a83` |

For the implementation commit, Predict Tests, Phase57 Research Foundation, and Phase52 Daily Dry-Run Persistence all succeeded. The dedicated eligibility measurement succeeded. L2 Selector Development, Selector Capacity, Missed Opportunity, and CURRENT Entry/Exit were skipped.

## 3. Workflow Trigger Audit

The Contract was committed before implementation. Its commit triggered ordinary CI only; every research/refit workflow was skipped. The implementation uses a dedicated path-scoped workflow, saved encrypted Development artifacts, the saved C+D Ridge score, and fixed aggregation libraries. It installs no model library and contains no fit path or provider client.

The report records provider requests `0`, fit calls `0`, Validation/OOS unopened, Candidate v2 not rerun, and no new model, feature, target, Top N, or freshness tuning.

## 4. Eligibility Contract SHA and Freshness Rule

Contract `ELIGIBILITY-MEASUREMENT-1` is frozen at `2998675a217317e4658272129d8759f16d11cc7e` and inherits corrected outcome semantics from `CORRECTED-MEASUREMENT-1` at `20356553ddece7309a6a00654c3b1e276d1a3466`.

Eligibility is decided before Ridge ranking. The latest accepted market price must be causally available at or before the decision timestamp, finite, positive, and no more than five wall-clock minutes old. Older prices, forward-fill, interpolation, and future bars are forbidden. The eligible rows are sorted by the unchanged saved Ridge score descending and symbol ascending, then `K=min(5,N_t)` is selected.

Future-path presence is not used for causal eligibility. Any missing future outcome remains selected and is reported after ranking.

## 5. Pre/Post Eligibility Coverage

| Coverage item | Count | Rate |
|---|---:|---:|
| Pre-eligibility candidate rows | 2,758,341 | 100.00% |
| Fresh-price eligible rows | 1,755,720 | 63.65% |
| Ineligible rows | 1,002,621 | 36.35% |
| Decision timestamps | 760 | — |
| Eligible candidates/timestamp | mean 2,310; min 1,863; median 2,262; max 3,085 | — |
| Top5 events | 3,800 | exactly 5 per timestamp |
| Top5 fresh Decision Price | 3,800 | **100.00%** |
| Top5 session High evaluable | 3,790 | **99.74%** |
| Top5 session Close evaluable | 3,800 | **100.00%** |
| Top5 strict wall-clock 30m evaluable | 2,704 | **71.16%** |

The 10 selected events without a continuous future 5m High remain in Top5 and are unavailable for the High-touch evaluator. No selected event lacks a future 5m/auction Close path. The 1,096 strict-30m unavailable selections have no acceptable wall-clock endpoint; they are not removed from the same-session opportunity population.

## 6. Market and Liquidity Composition Change

### Market

| Market | Pre N / share | Eligible N / share | Eligibility rate | Top5 N / share |
|---|---:|---:|---:|---:|
| Prime | 1,248,109 / 45.25% | 1,083,996 / 61.74% | 86.85% | 268 / 7.05% |
| Standard | 1,079,873 / 39.15% | 437,718 / 24.93% | 40.53% | 1,858 / 48.89% |
| Growth | 430,359 / 15.60% | 234,006 / 13.33% | 54.37% | 1,674 / 44.05% |

### Liquidity

| Liquidity | Pre N / share | Eligible N / share | Eligibility rate | Top5 N / share |
|---|---:|---:|---:|---:|
| Low | 864,226 / 31.33% | 210,040 / 11.96% | 24.30% | 511 / 13.45% |
| Mid | 945,571 / 34.28% | 628,737 / 35.81% | 66.49% | 890 / 23.42% |
| High | 948,544 / 34.39% | 916,943 / 52.23% | 96.67% | 2,399 / 63.13% |

The rule is a fixed causal price-observability condition, but operationally it also acts as a strong liquidity/tradability screen. Prime gains 16.49 percentage points and High liquidity gains 17.84 points in the eligible population; Low liquidity loses 19.37 points. This bias is material and must remain explicit.

Ridge ranking does not simply inherit that composition: 92.95% of selected events are Standard or Growth, even though Prime is 61.74% of the eligible universe.

## 7. Current Return and Volatility Composition

| Distribution | Pre eligibility | Post eligibility |
|---|---:|---:|
| Current Return mean | +0.058% | +0.078% |
| Current Return P25 / median / P75 | -0.702% / 0.000% / +0.728% | -0.820% / 0.000% / +0.871% |
| Decision volatility mean | 0.341% | 0.318% |
| Decision volatility P25 / median / P75 | 0.156% / 0.245% / 0.408% | 0.157% / 0.230% / 0.362% |

Fresh eligibility only modestly changes current-return location and slightly lowers typical volatility. The selected Top5 remains a distinct Ridge population: current-return median -3.16% and decision-volatility median 1.65%.

## 8. Future +2/+3/+5 Precision, Recall, and Lift

Primary opportunity is a same-session future continuous 5m High touch from Decision Price. Random expectation preserves each eligible timestamp and its `K/N_t`.

| High threshold | Precision@5 | Hits | Recall | Random recall | Recall lift | Eligible prevalence | Precision lift |
|---:|---:|---:|---:|---:|---:|---:|---:|
| +2% | 61.29% | 2,323 | 2.323% | 0.2159% | 10.76x | 5.708% | 10.74x |
| **+3%** | **47.26%** | **1,791** | **3.981%** | **0.2159%** | **18.44x** | **2.568%** | **18.40x** |
| **+5%** | **24.99%** | **947** | **6.138%** | **0.2160%** | **28.41x** | **0.881%** | **28.38x** |

Because High-touch coverage is 99.74%, conservative all-selection precision is nearly identical: 47.13% at +3% and 24.92% at +5%.

## 9. 5m Close-confirmed Precision

| Close threshold | Precision@5 | Recall | Random recall | Recall lift | Precision lift |
|---:|---:|---:|---:|---:|---:|
| +2% | 57.00% | 2.438% | 0.2158% | 11.30x | 11.26x |
| **+3%** | **43.58%** | **4.240%** | **0.2158%** | **19.65x** | **19.59x** |
| **+5%** | **22.95%** | **6.819%** | **0.2160%** | **31.58x** | **31.51x** |

Close-confirmed +3/+5 remains close to High-touch performance, so the result is not explained only by brief intrabar threshold touches.

## 10. Strict Wall-clock 30m Result

| KPI | Eligibility-aware Top5 |
|---|---:|
| Evaluable events | 2,704 / 3,800 (71.16%) |
| Mean return | **+83.35 bps** |
| Median return | **+19.07 bps** |
| Positive rate | **51.70%** |
| Positive sessions | **69/76** |
| 30m MFE | +2.757% |
| 30m true MAE | -1.301% |
| Session-end MFE | +3.800% |
| Session-end true MAE | -2.159% |

Strict-30m coverage remains lower because the fixed wall-clock endpoint cannot bridge lunch or use an absent/stale endpoint. The primary same-session +3/+5 evaluator has near-complete coverage.

## 11. Time to +3% / +5%

| High opportunity | P25 | Median | P75 | P90 | <=15m | 16–30m | 31–60m | 61–120m | >120m |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| +3% | 5m | **20m** | 70m | 140m | 862 | 224 | 181 | 298 | 226 |
| +5% | 5m | **30m** | 95m | 182m | 404 | 86 | 113 | 162 | 182 |

Close-confirmed median time is 25 minutes at +3% and 35 minutes at +5%. No time threshold was used for selection.

## 12. Market Robustness

| Market | Eligible N | Top5 N | Future +3% | Future +5% | 30m mean / median | 30m true MAE |
|---|---:|---:|---:|---:|---:|---:|
| Prime | 1,083,996 | 268 | 54.10% | 31.34% | +118.39 / +18.98 bps | -0.819% |
| Standard | 437,718 | 1,858 | 54.75% | 30.51% | +133.76 / +37.40 bps | -1.049% |
| Growth | 234,006 | 1,674 | 37.84% | 17.84% | +26.15 / 0.00 bps | -1.643% |

Growth is clearly weaker, especially on strict 30m return and downside, but it remains far above the full eligible prevalence. Prime does not explain the aggregate edge because it supplies only 7.05% of Top5 selections.

## 13. Liquidity Robustness

| Liquidity | Eligible N | Top5 N | Future +3% | Future +5% | 30m mean / median | 30m true MAE |
|---|---:|---:|---:|---:|---:|---:|
| Low | 210,040 | 511 | 48.12% | 24.16% | +160.43 / +119.23 bps | -0.204% |
| Mid | 628,737 | 890 | 42.74% | 19.57% | +118.71 / +72.24 bps | -0.882% |
| High | 916,943 | 2,399 | 48.75% | 27.17% | +68.24 / 0.00 bps | -1.497% |

The edge is present in Low, Mid, and High. High liquidity contributes the most selections, but it does not have uniquely strong +3% precision. Strict-30m segment estimates have uneven coverage—particularly Low at 175 of 511 selected events—so same-session opportunity precision is the more reliable segment comparison here.

## 14. Earlier-observed A/B Development Stability

A/B is outside the saved C+D fit but was already observed in earlier Development work. It is a stability diagnostic, not sealed Validation/OOS.

| KPI | A/B eligibility-aware result |
|---|---:|
| Sessions / Top5 events | 36 / 1,800 |
| Future +3% Precision | 42.25% |
| Future +3% Recall lift | 18.10x |
| Future +5% Precision | 19.90% |
| Future +5% Recall lift | 26.10x |
| Strict-30m mean / median | +72.10 / +13.16 bps |
| Positive rate / sessions | 50.51% / 32 of 36 |
| Session High coverage | 99.94% |

Every market and liquidity group remains positive on opportunity precision in A/B. The weakest cell is Prime +5% at 9.02% on only 122 selected events; Standard is 25.35% and Growth 15.04%. This supports broad Development stability while showing that group-level estimates remain noisy.

## 15. Previous Corrected Result Comparison

The previous run ranked the full universe first, then evaluated the 2,679 Top5 events that happened to have fresh prices. The new run first restricts to the 1,755,720 causally eligible rows and then selects Top5. Of 3,800 selection events, 2,679 overlap and 1,121 are replaced under the corrected order.

| KPI | Previous post-ranking freshness | Eligibility before ranking | Change |
|---|---:|---:|---:|
| Fresh Top5 coverage | 70.50% | **100.00%** | +29.50 pp |
| Session High coverage | 70.50% effective denominator | **99.74%** | +29.24 pp |
| Strict-30m coverage | 50.42% | **71.16%** | +20.74 pp |
| Future +3% Precision | 53.39% | **47.26%** | -6.13 pp |
| Future +3% hits / recall | 1,426 / 3.170% | **1,791 / 3.981%** | +365 / +0.811 pp |
| Future +5% Precision | 30.48% | **24.99%** | -5.49 pp |
| Future +5% hits / recall | 814 / 5.276% | **947 / 6.138%** | +133 / +0.862 pp |
| 30m mean / median | +98.84 / +25.20 bps | **+83.35 / +19.07 bps** | -15.49 / -6.12 bps |
| Positive sessions | 70/76 | **69/76** | -1 session |

The precision decline is expected when previously unevaluable high-score slots are replaced without looking at outcomes. The key result is that the edge remains very large, every Top5 slot starts from a fresh causal price, and absolute opportunity hits and recall increase.

## 16. Freeze Candidate Decision

**FREEZE CANDIDATE SUPPORTED.**

- Future +3/+5 Precision Lift remains 18.40x / 28.38x after pre-ranking eligibility.
- Same-timestamp Random is exceeded by 18.44x / 28.41x on recall.
- Positive strict-30m sessions remain 69/76; A/B remains 32/36.
- Prime, Standard, Growth, Low, Mid, and High all retain substantial opportunity precision.
- Decision Price coverage is 100% by construction and same-session outcome coverage is 99.74–100%.
- The eligibility rule is causal, fixed before measurement, and was not tuned.
- No outcome, evaluator field, or future-path availability enters ranking.

This is a Freeze-Candidate recommendation on Development evidence. It is not an automatic Freeze and is not a Validation/OOS claim.

## 17. What Remains Material

The freshness gate excludes 36.35% of candidate rows and materially changes population composition. That is acceptable as a causal data-quality/tradability contract only if this narrower observable universe matches the intended operational Selector universe. The result should not be described as full-JPX coverage.

Strict wall-clock 30m coverage remains 71.16% in selected events, mostly because lunch and absent endpoint rules fail closed. This does not impair the near-complete same-session North-Star evaluator, but strict-30m metrics must keep their explicit denominator.

## 18. One Recommended Next Step

Ask the user to approve or reject formal Freeze of **`ELIGIBILITY_AWARE_RIDGE_SAVED_CD` with the exact five-minute pre-ranking eligibility contract and Top5 policy**. If approved, record an immutable Freeze artifact and preregister the later Validation protocol without opening Validation in the Freeze step.

## 19. Safety and STOP

Provider requests: 0. Fit calls: 0. Validation/OOS remained sealed. Candidate v2 was not rerun. No Candidate v3, new model, feature, target, Top N, segment model, Entry/EXIT/Allocation, old-selector comparison, News/Event, or trading path was introduced. Lane Y, `main`, and all live circuits were untouched; all execution/write/trading flags remain false.

**STOP: await the user's Freeze decision.**
