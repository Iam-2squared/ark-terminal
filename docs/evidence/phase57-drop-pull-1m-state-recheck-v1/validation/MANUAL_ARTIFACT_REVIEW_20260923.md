# DROP/PULLBACK 1-minute State recheck: verified artifact review

Date: 2026-09-23 JST. Status: MEASUREMENT_VERIFIED_MANUAL_STOP.

## Decision and scope

The saved result is `PASS_CLEAR_IMPROVEMENT`: all seven precommitted gates passed against the frozen five-minute State-v3 Entry baseline. This is a relative Historical/Development improvement, not final Entry acceptance, not superiority to Immediate, not independent validation, and not evidence that mean EntryPosition is at most 0.25.

Only opportunities initially classified DROP/PULLBACK use one-active-minute State rechecks. The nine-pattern classifier, ten-active-minute recent-shape window, T0 BUY states, all six existing signals with OR activation, no-fixed-fallback rule, non-target policy and numerical success thresholds are unchanged. Do not confuse one-minute recheck frequency with a one-minute-return State definition.

## Reacquired GitHub identities and concurrency

- Initial inspected HEAD: `5b47b975b1d833b3992e56ee7dce4010e58e17bb`.
- Verified measurement/repair HEAD: `8c256ff98d365d01c7150afe193686f020e2026c`.
- Initial dedicated failure: run `35815694968`, job `107036623202`. All 81 focused tests passed, then the static causality scanner rejected the explanatory word `outcome` inside the frozen intent function's docstring. This was not a performance verdict.
- A parallel update reached the branch while a repair was being prepared. A non-fast-forward ref update was rejected; it was not forced. The newer branch's AST-based repair and added parity tests were inspected and reused without overwriting them. The separately prepared commit `d1b7055ba467e577e7bb3fd47534f249da73ef92` was not attached to this branch and is not the implementation identity for these results.
- Repair detail: `validation/AUDIT_REPAIR_R1.md`. Executable forbidden keys/names/attributes/string constants and runtime prefix checks remain checked; only documentation is excluded from the static scan. No State/Entry tuning was introduced in the repair.

## Actual CI and downloadable artifact

- Dedicated PR run `35818555587`: SUCCESS, job `107045547187`: SUCCESS.
- Focused policy/frozen-regression tests: SUCCESS.
- Immutable evaluator artifact retrieval/hash verification: SUCCESS; no new market-provider retrieval.
- Replay A and B plus directory byte comparison: SUCCESS.
- Frozen Development/Selector preservation checks: SUCCESS.
- Predict Tests run `35818556861`: SUCCESS.
- LONG-only Research Foundation run `35818555691`: SUCCESS.
- State-v3 Contract run `35818555460`: SUCCESS.
- Push run `35818543146` was cancelled; the later PR run above completed successfully. It is not reported as another scientific failure.
- The whole PR is not claimed GREEN; unrelated legacy workflow failures remain.

Result artifact ID: `10732168448`.
Name: `phase57-drop-pull-1m-state-recheck-v1-8c256ff98d365d01c7150afe193686f020e2026c`.
ZIP bytes: 682445.
ZIP SHA-256: `74ff0fb4398f9e2659109103ae73e8a6b27423aa0eb5aee7006c84312488aab8`.

The archive was downloaded and its SHA-256 independently verified. All six entries in its measurement manifest were checked. No inference from CI color alone was used. The artifact's test text file is empty because the workflow's tee captures stdout while unittest writes to stderr; test execution success is established from the workflow job/log, not that empty file.

### Verified result manifest

| File | SHA-256 |
|---|---|
| causality-audit.json | b569d8d7e25240d359bc1a3c2efbd04f2017136eabac1f4288459559f0cf6cde |
| entry-records.json.gz | de8ee035d2c2949e6ecbd5315d393de8794ca7d0e36ace49a6ccfe720a65a844 |
| gate.json | 7a76b1bcbfe9f35cfde0d3f94b9e12e0e0ad013ede8fce81997288027b2bfc08 |
| summary.json | 8de015aeaf9b80d1d375b409ea597fa6dee24d767a72aeabdd5918faac367ea9 |
| target-paired-vs-state-v3.json.gz | 4e02becf3a49c51e84614cdabebe034f3a42a82a452a5d8013222bde3d14c2e2 |
| trades.json.gz | e731492871f1db795df5a85042f04394c6e6775ecdac6131d2fe68909d09f32e |

This receipt preserves identities and inspected numerical evidence in Git. The original complete measurement files are in the named Actions artifact; this receipt does not claim that those compressed files have also been committed into Git.

## Target cohort: initial DROP/PULLBACK, N=1757

All 2155 unique opportunities remain in the result. The intervention is limited to the 1757 target opportunities.

| Metric | Frozen 5-minute | 1-minute | Difference |
|---|---:|---:|---:|
| Fill | 1323 / 1757 | 1406 / 1757 | +83 |
| Fill rate | 75.298805% | 80.022766% | +4.723961pp |
| NO_ENTRY | 434 | 351 | -83 |
| Delay mean, each policy's own fills | 10.895692m | 8.421764m | -2.473928m |
| Delay median | 10m | 7m | -3m |
| EntryPosition <=0.10 | 85 / 1317 = 6.454062% | 113 / 1396 = 8.094556% | +1.640494pp |
| EntryPosition <=0.25, locked primary | 308 / 1317 = 23.386484% | 362 / 1396 = 25.931232% | +2.544748pp |
| EntryPosition <=0.50 | 650 / 1317 = 49.354594% | 688 / 1396 = 49.283668% | -0.070926pp |
| +3 Capture | 389 / 620 = 62.741935% | 426 / 620 = 68.709677% | +5.967742pp |
| +5 Capture | 211 / 328 = 64.329268% | 232 / 328 = 70.731707% | +6.402439pp |

Position-rate denominators are fills with evaluable EntryPosition, not all opportunities. NO_ENTRY and unavailable metrics remain recorded and are not silently discarded from population counts. The new candidate has 1406 target fills but 1396 evaluable positions; the baseline has 1323 fills but 1317 evaluable positions.

## Matched target comparisons, candidate minus five-minute baseline

| Metric | Paired N | Mean difference |
|---|---:|---:|
| Price improvement, positive means cheaper | 1323 | +0.047218643% |
| Delay | 1323 | -2.747543462 active minutes |
| EntryPosition | 1317 | -0.007470077 |
| Low-to-Entry distance | 1317 | -0.051221020pp |
| Entry-to-Later-High upside | 1243 | +0.058358335pp |
| Range Retention | 1243 | +0.900442760pp |
| 30m MFE | 982 | +0.062213391pp |
| 30m MAE | 982 | +0.005506411pp |
| 60m MFE | 791 | +0.065618203pp |
| 60m MAE | 791 | -0.045905805pp |

The underlying record and pair files were independently recomputed for price, delay, EntryPosition, Low-to-Entry and Range Retention; counts and means matched summary.json within 1e-12. On the common 1317 evaluable-position pairs, mean EntryPosition changes from 0.662445107 to 0.654975031. The common-pair <=25% count changes from 308 to 351, i.e. 23.386484% to 26.651481% (+3.264996pp). This common-pair rate is a supplementary descriptive calculation, not a replacement for the precommitted primary denominator or threshold.

Matched fill categories: BOTH_FILLED 1323; CANDIDATE_ONLY 83; BASE_ONLY 0; NEITHER 351. Earlier State checks recovered fills rather than selecting a smaller favorable target population.

## All-population context and limitations

| Metric, all 2155 | Immediate | Entry v1 | Frozen State-v3 5m | Target-only 1m |
|---|---:|---:|---:|---:|
| Fill | 1963 | 1857 | 1681 | 1764 |
| Fill rate | 91.0905% | 86.1717% | 78.0046% | 81.8561% |
| NO_ENTRY | 192 | 298 | 474 | 391 |
| Mean delay | 1.4529m | 9.1255m | 9.2623m | 7.3673m |
| Mean EntryPosition, own evaluable fills | 0.653993 | 0.643536 | 0.672825 | 0.674868 |
| +3 Capture | 85.2825% | 71.2221% | 67.0171% | 71.8791% |
| +5 Capture | 87.5000% | 75.2451% | 68.3824% | 73.5294% |

The own-sample average EntryPosition did not improve: in the target cohort 0.662445 to 0.665595, and in the full population 0.672825 to 0.674868. This does not contradict the matched-pair improvement; additional fills change the averaging population. Report both instead of subtracting a paired delta from an unrelated baseline average.

Within the target cohort, Immediate achieves <=25% in 578 / 1569 = 36.838751%, versus 25.931232% for the 1m candidate. Immediate target Fill is 1598 / 1757 = 90.950484%, +3 Capture 525 / 620 = 84.677419%, and +5 Capture 288 / 328 = 87.804878%.

The 1m candidate also remains worse than Immediate in full-population paired comparisons: price improvement -0.145929841%, EntryPosition +0.038008502, Low-to-Entry +0.135313177pp, remaining upside -0.129043976pp, Range Retention -3.265668191pp. Full-population Capture deficits are -13.403417pp at +3 and -13.970588pp at +5; Fill remains 199 lower.

Therefore 25.931232% is the share of evaluable fills that achieve EntryPosition <=0.25. It does NOT mean mean EntryPosition=0.2593, or mean position<=0.25. The target own-sample mean is still about 66.56% of the evaluator's range; common-pair mean about 65.50%. Stored EntryPosition is not clipped to [0,1]. Oracle Low/High are evaluator-only; their timing is not known when an entry is decided.

## Gate and causality

All seven precommitted gates are true: primary rate increase at least 2pp; paired EntryPosition improves; paired Low-to-Entry improves; Fill/+3/+5 each not worse than -2pp; causality PASS. This supports a modest cadence-related improvement on reused Development data, not an exhaustive explanation of every WAIT failure.

- Target State decisions: 53712; source-time violations: 0.
- Signal closed-bar checks: 65910 / 65910 PASS.
- Target T0 State exact parity: 1757.
- Non-target record exact parity: 398.
- T0 BUY states: 310 intents / 277 fills, unchanged.
- Forbidden executable decision tokens: none.
- Causal-intent SHA-256 before opening evaluators: `8e9f1bfaf10884dc140d0cf6243cab7149b64490baa9124b33a64a433e238878`.
- Oracle Low/High decision use: 0; future Outcome decision use: 0.
- Provider requests: 0; protected data opened: 0.
- Safety9: executionAllowed, brokerWriteAllowed, excelOrderWriteAllowed, rssOrderFunctionAllowed, liveTradingAllowed, paperTradingAllowed, automaticPromotionAllowed, productionUpdateAllowed, transmitted all false.

## Manual STOP

Do not start the next hypothesis, retune State/Signal/Entry thresholds, add Volume/Dictionary, open Holdout/Fresh/OOS/Prospective, change EXIT/Capital, merge main, promote this trial to production, or enable live/paper execution. Hourly automation remains disabled. A human decision is required for the next step. Preserve the original five-minute evidence and this one-minute relative-improvement result side by side.
