# Phase57 LONG-only L1 Early Winner Discovery

Status: **L1 DISCOVERY PASS / L2 DATA APPROVAL REQUIRED**

Evidence date: 2026-09-15 JST  
Branch: `research/phase57-long-only-cash-equity`  
Measurement run: `34930970200`  
Evidence artifact: `10381228403`  
Artifact digest: `sha256:46d799f6fc851e085c043835dd8667414203f9b8cb368233ff758a306d782a04`

## Scope and integrity

- The fixed 20-session Development A discovery contract was used without outcome-based session selection.
- Four earliest sessions were provider-unavailable; the remaining 16 sessions were measured. No substitute sessions were chosen.
- Validation, Validation Replication, Primary OOS, and Contingency OOS remain sealed.
- Existing encrypted Minute shards were reused. This corrected measurement made zero new J-Quants requests.
- Features are causal and physically separated from evaluator-only future labels.
- The first measurement exposed a daily-adjusted versus raw-Minute price-scale mismatch. That result was rejected. The corrected run de-adjusts the prior close to the same raw price scale as Minute bars and adds a regression test.
- The raw data were not committed. Only sanitized aggregate evidence is referenced here.

## Data quality

| Item | Result |
|---|---:|
| Approved sessions | 20 |
| Measured sessions | 16 |
| Provider-unavailable sessions | 4 |
| Raw Minute rows | 6,618,801 |
| Causal feature rows | 576,581 |
| Evaluator-only label rows | 576,581 |
| Eligible symbol-sessions | 59,708 |
| Minute coverage versus PIT-eligible universe | 100% per measured session |
| Non-unit historical adjustment-scale rows | 6,668 |
| Corporate-action exclusions | 63 |
| New requests for corrected measurement | 0 |

## Winner opportunity

| Winner definition | Symbol-sessions |
|---|---:|
| Final return at least +5% | 1,042 |
| Final return at least +10% | 192 |

Every one of the 16 measured sessions contained final +5% winners. The session-level winner rate ranged from 0.529% to 3.948%, so the opportunity is not confined to one session, although regime variation is material.

## Remaining upside by decision time

| Decision time | +5% winners: mean | +5% winners: median | Late detection | +10% winners: mean | +10% winners: median |
|---|---:|---:|---:|---:|---:|
| 09:30 | 5.251% | 4.058% | 8.47% | 9.227% | 7.925% |
| 10:00 | 4.413% | 3.203% | 12.07% | 7.292% | 4.904% |
| 10:30 | 3.740% | 2.551% | 17.82% | 6.212% | 3.465% |
| 11:00 | 3.347% | 2.295% | 22.43% | 5.253% | 3.091% |
| 11:30 | 2.986% | 1.968% | 28.01% | 4.679% | 2.540% |
| 13:00 | 2.296% | 1.411% | 35.67% | 3.659% | 1.581% |
| 14:00 | 1.531% | 0.905% | 52.84% | 2.507% | 1.068% |
| 15:00 | 0.156% | 0.000% | 94.45% | 0.382% | 0.000% |

The economically useful window is concentrated in the morning. Waiting until 14:00 or later converts much of the task into late detection.

## Winner state before the final move

| Current session return bucket | Distinct winner symbol-sessions | Mean remaining upside | Median remaining upside |
|---|---:|---:|---:|
| Below 0% | 73 | 13.248% | 11.134% |
| 0% to +1% | 152 | 9.072% | 6.275% |
| +1% to +2% | 208 | 6.125% | 5.097% |
| +2% to +3% | 328 | 4.898% | 4.140% |
| +3% to +5% | 695 | 2.775% | 2.153% |
| Already at least +5% | 997 | 1.530% | 0.758% |

Distinct counts overlap across buckets because a winner can pass through several states during a session. The important finding is that many winners are observable while only +1% to +3% up and still retain roughly +4% to +6% median/mean upside.

## Winner versus non-winner cohorts

| Cohort | Symbol-sessions | Mean future MFE | Mean future MAE | Mean MFE/ATR | Mean MAE/ATR |
|---|---:|---:|---:|---:|---:|
| Final +5% winner | 1,042 | 2.683% | -0.922% | 3.738 | -0.782 |
| Near winner, final +3% to +5% | 2,396 | 1.387% | -0.488% | 3.200 | -0.922 |
| Intraday +5%, final below +5% | 567 | 1.833% | -2.095% | 2.866 | -1.891 |
| High-volume non-winner | 21,239 | 0.586% | -0.643% | 1.709 | -1.767 |
| Gap-up failure | 3,186 | 0.635% | -0.890% | 1.211 | -1.742 |
| Ordinary non-winner | 53,409 | 0.491% | -0.558% | 1.604 | -1.740 |

The main hard-negative class is intraday +5% then failure: it has upside, but its adverse excursion is more than twice the winner cohort's. L2 should therefore model continuation and downside jointly rather than rank current return alone.

## Stratification

| Dimension | Bucket | Winner rate |
|---|---|---:|
| Market | Prime | 1.257% |
| Market | Standard | 1.504% |
| Market | Growth | 4.114% |
| Liquidity | High | 3.695% |
| Liquidity | Mid | 1.167% |
| Liquidity | Low | 0.363% |
| Gap | Gap-up | 13.147% |
| Gap | Non-gap | 1.043% |

There is substantial Growth, high-liquidity, and gap-up enrichment. Those variables must be used as causal context, not as a reason to exclude other strata after seeing outcomes. Limit-up touched 87 of 59,708 eligible symbol-sessions at any point, so limit-up names do not dominate the opportunity census.

## Negative controls and single-feature diagnostics

Each diagnostic selects the same number of candidates as the number of winners at that decision time. It is a ranking diagnostic, not a deployable selector or a performance claim.

| Time | Random recall | Label-shift recall | 30m momentum recall | VWAP distance recall | VWAP slope recall |
|---|---:|---:|---:|---:|---:|
| 09:30 | 1.75% | 1.56% | 30.87% | 20.35% | 19.67% |
| 10:00 | 1.25% | 1.16% | 18.15% | 25.77% | 13.71% |
| 10:30 | 2.12% | 1.35% | 16.28% | 27.26% | 10.31% |
| 11:00 | 2.31% | 1.64% | 11.84% | 25.99% | 7.12% |

At 09:30, the top 30m-momentum set retains mean +4.131% remaining upside; the top VWAP-slope set retains +4.548%. Causal ranking signals are far above random and label-shift controls, but univariate selection also exhibits meaningful MAE. L2 needs a small multivariate candidate set and full-cross-section calibration.

## Ark disposition

**GO to L2 data acquisition planning.** L1 answers its discovery question positively: early winners exist in useful quantity, meaningful morning upside remains, winner-like hard negatives exist, and causal features contain ranking information beyond controls.

This is not a Selector Freeze and not a Validation claim. The next permitted step is to acquire Development C and Development D Minute data only after separate operator approval, then compare a small target/model set entirely inside Development.

Proposed acquisition scope:

| Partition | Sessions | Purpose | Estimated requests | Hard ceiling proposal |
|---|---:|---|---:|---:|
| Development C | 20 | fit and feature-family ablation | ~253 | 300 |
| Development D | 20 | target/model selection and threshold choice | ~253 | 300 |
| Total | 40 | L2 development only | ~506 | 600 |

Use four encrypted 10-session checkpoints. Stop when all fixed sessions are accounted for or the ceiling is reached. Do not acquire Validation or OOS.

| Fixed scope | Calendar range | Session-list SHA-256 |
|---|---|---|
| Development C | 2024-11-11 to 2024-12-06 | `91a8ef84391f96c2f0043d9f86fc9def044651b4189138aed135a2ba79750e84` |
| Development D | 2024-12-09 to 2025-01-09 | `138a50f0245b9f2eddf690f6b9fc1e36e8ca92eb6d3efa5319a6270cc5a1cfc9` |
| C + D | 40 fixed sessions | `9abbc28870b8885cab2b68ae2d2f3e6ef4511b5f687dc553ddcd9e0255b0281c` |

---

# Claude Independent Review Request

You are the independent, adversarial reviewer for Ark Terminal Phase57 LONG-only Cash Equity research. Do not endorse the plan by default. Look for explanations that would invalidate, weaken, or narrow the conclusions.

## Research question

Can final same-day +5%/+10% JPX winners be identified early enough that meaningful upside remains, using only information causally available at the decision time? This L1 stage is discovery, not model selection. The eventual system must be cash-equity LONG-only with zero SHORT, margin, or leverage.

## Data and isolation

- Fixed Development A discovery list: first 20 calendar-ordered sessions, chosen before Minute outcomes.
- Four earliest sessions were unavailable from the provider; 16 were measured without replacement.
- 6,618,801 raw sparse Minute rows; 59,708 PIT-eligible symbol-sessions; 576,581 decision-time rows.
- 100% PIT-eligible Minute-symbol coverage in every measured session.
- 63 same-session corporate-action rows excluded.
- 6,668 historical rows required a non-unit daily adjustment scale. Minute bars are raw; previous daily close was de-adjusted to the same raw scale.
- Feature rows and evaluator-only future labels are physically separate. Timestamp contract is causal 1m to 5m, bar available at bar end, with lunch and closing auction separated.
- Validation, Validation Replication, Primary OOS, and Contingency OOS remain sealed.

## Results to challenge

1. There were 1,042 final +5% and 192 final +10% winner symbol-sessions over 16 measured sessions.
2. At 09:30, final +5% winners retained mean/median +5.251%/+4.058%; at 10:00, +4.413%/+3.203%; at 11:00, +3.347%/+2.295%.
3. Winners observed at current return +1% to +2% retained mean/median +6.125%/+5.097%; at +2% to +3%, +4.898%/+4.140%.
4. Intraday +5% then failure is a hard-negative cohort: future MFE +1.833% but MAE -2.095%, versus winner MFE +2.683% and MAE -0.922% when pooled over decision times.
5. At 09:30, same-count ranking recall was 1.75% random, 1.56% label-shift, 30.87% for 30m momentum, 20.35% for VWAP distance, and 19.67% for VWAP slope. These are diagnostics, not Selector performance.
6. Winner rates are enriched in Growth (4.114%), high-liquidity (3.695%), and gap-up (13.147%) strata.
7. Limit-up touched only 87 of 59,708 eligible symbol-sessions, so it does not numerically dominate the opportunity set.

## Questions requiring an explicit answer

1. Does the daily-adjusted/raw-Minute scale correction described above fully resolve corporate-action scale risk? What concrete falsification check should run before L2 without building new infrastructure?
2. Does losing the first four calendar sessions to provider availability introduce a meaningful selection or regime bias? Is keeping the remaining fixed 16 without replacement the least-biased response?
3. Are the winner-time and return-bucket conclusions genuinely about early opportunity, or can they still be tautological conditioning on final winners?
4. Which comparisons against near winners, intraday-failures, gap-up failures, and ordinary non-winners most strongly support or refute learnability?
5. Which two or three evaluator targets should L2 compare? Consider continuation probability, expected future return, and a downside-aware objective such as MFE minus lambda times absolute MAE or ATR-normalized opportunity. Reject an unnecessary target zoo.
6. Which compact causal feature families should be admitted first, and which should be held for ablation? Explicitly address momentum, VWAP, gap, liquidity, market/sector breadth, pullback quality, and trend efficiency.
7. Should Growth/gap/liquidity be features, stratified calibrators, or separate models? Identify the highest leakage and overfitting risk.
8. Are the random and label-shift controls sufficient for L1? Name the minimum additional negative control, if any, required before Selector Freeze.
9. Is Development C=20 sessions for fit/ablation and Development D=20 sessions for target/model/threshold selection statistically defensible given the L1 effect sizes and session instability? If not, propose a data-efficient alternative without opening Validation/OOS.
10. Give a verdict: `GO`, `CONDITIONAL GO`, or `NO-GO` for the proposed 40-session Development C+D full-cross-section Minute acquisition. List only critical preconditions that protect future-leak, OOS isolation, security, or result validity.

Return findings in severity order. Separate confirmed defects, plausible risks, and optional improvements. Do not suggest hiding already-observed results or creating a new holdout retroactively.
