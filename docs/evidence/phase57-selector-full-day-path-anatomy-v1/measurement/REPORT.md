# Frozen Selector Full-Day Path Anatomy / Null-Control Diagnostic

Development-only descriptive evidence. Fixed frozen Selector, 30-minute cadence, Top5, 76 sessions / 760 timestamps / 3,800 selections per arm. Reference OPEN/CLOSE returns; no guaranteed fills or strategy P&L. All percentage values are percentage points; canonical round-trip cost 0.05pp.

## Primary answers (Q1–Q10)

1. Directionality: COMMON120 multiple-comparison-adjusted positive Selector–Random horizons: []. Relative information and absolute net performance are separate; this is in-sample Development, not validation.
2. Range selection: at COMMON120 / 30m, paired MFE uplift NApp, absolute MAE uplift NApp, balance uplift NApp. Compare the CIs in cluster-bootstrap.json before assigning directionality.
3. +3/+5 economic translation: future-conditioned full-day winner outcomes appear below; they cannot define a trading policy.
4. Giveback: COMMON120 / 30m Selector–Random giveback NApp; 120m NApp.
5. Delayed edge: 120m minus 30m paired advantage NApp, CI [None, None]. Tags: DELAYED_ALPHA_INCONCLUSIVE.
6. Fat-tail dependence: full, top1% and top5% excluded net returns are tabulated below. Exclusions are outcome-conditioned diagnostics, not deployable filters.
7. Price/tick: fixed price-band results are in price-tick-diagnostic.json. Actual dated exchange tick sizes are NOT_EVALUABLE; nominal 1JPY quantities cannot establish tick causality.
8. Score ranking: exact frozen scores reconstructed from the existing PIT contract; deciles are set before future availability. Rank IC against terminal/MFE/absolute MAE appears below.
9. Redesign rationale: range-only association, weak absolute net and tail dependence would support considering an economic-target redesign; a strong common-cohort terminal signal would support retaining the Selector. This report supplies diagnostic evidence only, not unfreeze approval.
10. Recommended next step: review the diagnostic and its power/coverage before an explicit user decision on Selector redesign or additional Development evidence. Do not begin Entry, EXIT, Capital or new acquisition automatically.

Final Path Verdict: **INCONCLUSIVE**. Tags: DELAYED_ALPHA_INCONCLUSIVE.
Final Selector Interpretation: The frozen ranking must be described by its matched terminal advantage together with its upside and downside excursions. Development results alone do not establish deployable absolute LONG alpha.

## Primary common-cohort evidence

| Cohort | Selector rows | Random rows | Momentum rows | Matched Selector–Random timestamps |
|---|---:|---:|---:|---:|
| COMMON60 | 1312 | 1013 | 1365 | 0 |
| COMMON90 | 829 | 613 | 886 | 0 |
| COMMON120 | 431 | 283 | 459 | 0 |
| SESSION_END | 686 | 596 | 580 | 0 |

COMMON120 below uses identical event IDs at every horizon and full original Top5 in each arm at matched timestamps. Independent pair cohorts may differ between Random and Momentum. Session-equal means are primary; row distribution medians/PF are descriptive.

| min | Selector net | Random net | delta | simultaneous 95% CI | MFE delta | absMAE delta | giveback delta | clusters | MDE |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| 5 | NA | NA | NA | [None, None] | NA | NA | NA | 0 | NA |
| 10 | NA | NA | NA | [None, None] | NA | NA | NA | 0 | NA |
| 15 | NA | NA | NA | [None, None] | NA | NA | NA | 0 | NA |
| 30 | NA | NA | NA | [None, None] | NA | NA | NA | 0 | NA |
| 60 | NA | NA | NA | [None, None] | NA | NA | NA | 0 | NA |
| 90 | NA | NA | NA | [None, None] | NA | NA | NA | 0 | NA |
| 120 | NA | NA | NA | [None, None] | NA | NA | NA | 0 | NA |

## Available cohorts and session end (descriptive)

| horizon | arm | n | net mean | median | PF | positive rate | session-equal mean | cluster CI |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 5 | FROZEN_SELECTOR | 2707 | +0.0144 | -0.0500 | +1.0390 | +0.4152 | +0.0146 | [-0.032912912830668516, 0.06423594807005241] |
| 10 | FROZEN_SELECTOR | 2450 | +0.0250 | -0.0500 | +1.0491 | +0.4580 | +0.0283 | [-0.04535651090469493, 0.10313739476495754] |
| 15 | FROZEN_SELECTOR | 2321 | +0.0205 | -0.0500 | +1.0335 | +0.4589 | +0.0303 | [-0.052593643617702995, 0.1149160788642281] |
| 30 | FROZEN_SELECTOR | 1953 | +0.0130 | -0.0500 | +1.0167 | +0.4706 | +0.0307 | [-0.09240645392215845, 0.1533481445481354] |
| 60 | FROZEN_SELECTOR | 1312 | -0.2213 | -0.1724 | +0.8116 | +0.4276 | -0.2036 | [-0.41080872240398, 0.01802528019861726] |
| 90 | FROZEN_SELECTOR | 829 | -0.2228 | -0.2181 | +0.8396 | +0.4415 | -0.1893 | [-0.4868715872296665, 0.11683349680500496] |
| 120 | FROZEN_SELECTOR | 431 | -0.1431 | -0.4792 | +0.9052 | +0.4153 | -0.0094 | [-0.47133896861421115, 0.5112821102205731] |
| 5 | MOMENTUM30_TOP5 | 2664 | -0.2309 | -0.0500 | +0.6596 | +0.3547 | -0.2306 | [-0.2988196565945176, -0.16024329364445772] |
| 10 | MOMENTUM30_TOP5 | 2424 | -0.3359 | -0.2719 | +0.6505 | +0.3903 | -0.3324 | [-0.42393930422089826, -0.2376960071175495] |
| 15 | MOMENTUM30_TOP5 | 2294 | -0.3844 | -0.3798 | +0.6684 | +0.3928 | -0.3783 | [-0.48747105046513745, -0.2682384687372581] |
| 30 | MOMENTUM30_TOP5 | 1943 | -0.5570 | -0.6117 | +0.6334 | +0.3649 | -0.5731 | [-0.7219989353587594, -0.4287017012295127] |
| 60 | MOMENTUM30_TOP5 | 1365 | -0.8788 | -0.8145 | +0.5649 | +0.3700 | -0.8985 | [-1.1358741406398691, -0.6621464257382] |
| 90 | MOMENTUM30_TOP5 | 886 | -1.3793 | -1.1356 | +0.4557 | +0.3612 | -1.4379 | [-1.7395240252764421, -1.1398144237395598] |
| 120 | MOMENTUM30_TOP5 | 459 | -2.1800 | -1.3387 | +0.3057 | +0.3333 | -2.2191 | [-2.723455749238265, -1.7251320704962496] |
| 5 | RANDOM_TOP5 | 2587 | -0.0541 | -0.0500 | +0.4450 | +0.2702 | -0.0538 | [-0.06326307341244868, -0.04440512770719414] |
| 10 | RANDOM_TOP5 | 2221 | -0.0622 | -0.0500 | +0.5543 | +0.3494 | -0.0607 | [-0.07679171356409012, -0.045246881137591954] |
| 15 | RANDOM_TOP5 | 2017 | -0.0677 | -0.0500 | +0.5823 | +0.3619 | -0.0638 | [-0.0835652054934753, -0.04467257046536744] |
| 30 | RANDOM_TOP5 | 1608 | -0.0599 | -0.0500 | +0.7034 | +0.4030 | -0.0542 | [-0.08331240305223934, -0.025209487010108764] |
| 60 | RANDOM_TOP5 | 1013 | -0.0723 | -0.0849 | +0.7526 | +0.4215 | -0.0588 | [-0.11499139771484582, -0.0014524554906617524] |
| 90 | RANDOM_TOP5 | 613 | -0.0507 | -0.0996 | +0.8554 | +0.4290 | -0.0208 | [-0.12200787394746988, 0.09150598599705356] |
| 120 | RANDOM_TOP5 | 283 | -0.0748 | -0.1287 | +0.8183 | +0.4276 | -0.0804 | [-0.2305167197159205, 0.1017230369646349] |
| SESSION_END | FROZEN_SELECTOR | 686 | -0.9293 | -0.6355 | +0.5104 | +0.3688 | -0.8195 | [-1.22232326797205, -0.44013222633881094] |
| SESSION_END | MOMENTUM30_TOP5 | 580 | -2.2305 | -1.4393 | +0.2773 | +0.3121 | -2.2831 | [-2.803913856826339, -1.7447316318975448] |
| SESSION_END | RANDOM_TOP5 | 596 | -0.1020 | -0.1006 | +0.7247 | +0.4329 | -0.0866 | [-0.2043636410747674, 0.03478363156573132] |

Do not read this changing-N table as a longitudinal path. Session end crosses lunch using actual regular bars; fixed horizons never cross lunch.

## Winner translation and tails

| arm | full-day reach | complete winners | end net mean | end gross positive rate | end gross negative rate | end giveback mean |
|---|---|---:|---:|---:|---:|---:|
| FROZEN_SELECTOR | +3% | 243 | +1.1013 | +0.6091 | +0.3704 | +5.6395 |
| FROZEN_SELECTOR | +5% | 128 | +2.6892 | +0.6953 | +0.2891 | +6.6588 |
| RANDOM_TOP5 | +3% | 9 | +3.0342 | +1.0000 | +0.0000 | +1.4261 |
| RANDOM_TOP5 | +5% | 2 | +4.2483 | +1.0000 | +0.0000 | +2.8224 |
| MOMENTUM30_TOP5 | +3% | 226 | -0.4911 | +0.4912 | +0.4779 | +7.4065 |
| MOMENTUM30_TOP5 | +5% | 142 | +0.3081 | +0.5704 | +0.3944 | +8.4370 |

| COMMON120 arm / 30m | full net | top1 excluded | top5 excluded | worst1 excluded | worst5 excluded | winsorized |
|---|---:|---:|---:|---:|---:|---:|
| FROZEN_SELECTOR | +0.2348 | +0.0439 | -0.2293 | +0.3522 | +0.5589 | +0.1788 |
| RANDOM_TOP5 | -0.1053 | -0.1258 | -0.1704 | -0.0841 | -0.0369 | -0.1016 |
| MOMENTUM30_TOP5 | -0.8723 | -1.0231 | -1.3752 | -0.7114 | -0.4198 | -0.8512 |

## Score economic monotonicity

| horizon | n | terminal rank IC | MFE rank IC | absolute MAE rank IC | monotone net deciles |
|---|---:|---:|---:|---:|---|
| 15 | 900553 | +0.0112 | -0.0244 | -0.0371 | False |
| 30 | 710656 | +0.0031 | -0.0371 | -0.0409 | False |
| 60 | 449655 | -0.0123 | -0.0448 | -0.0366 | False |
| 90 | 273721 | -0.0263 | -0.0461 | -0.0239 | False |
| 120 | 129921 | -0.0335 | -0.0448 | -0.0114 | False |

## Integrity and limits

Primary: common-cohort terminal, Random null, excursion balance, giveback, tails, fixed price/volatility strata, score analysis. Descriptive supporting work: timing buckets, AM/PM, concentration, conditional winners/deep losers. No additional path archetypes or optimized filters.
Common cohort manifests include full event IDs and hashes. Selection membership and projected paths must exactly match the prior Economic Census. Missing bars fail closed without interpolation or zero imputation. Sparse observed-minute 5m bars are counted. Time-to-hit/peak/trough are 5m intervals, not precise event times; same-bar ordering is unknown.
Session bootstrap: deterministic seed 20260919, 10,000 replicates. Seven COMMON120 Random contrasts use simultaneous Bonferroni intervals; all other CIs are pointwise descriptive. 0m is a zero gross reference only; no net/PF at zero duration. PF is return-sum ratio, not a capital-weighted portfolio statistic.
Selector / Entry / EXIT / Capital unchanged. DEV TEST / Fresh / OOS sealed. New provider requests 0; fit calls 0. All nine safety flags false. No merge, promotion, paper or live execution. STOP after diagnostic.
