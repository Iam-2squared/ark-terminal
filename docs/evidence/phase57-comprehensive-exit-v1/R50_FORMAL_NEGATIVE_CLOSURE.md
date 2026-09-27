# Phase57 R50 formal negative closure

Saved: 2026-09-27 11:19:52 JST  
Marker HEAD: `da000c3d75b42e8bb02eadd97e12187e1a2dc145`  
Exact tested/execution SHA: `cc7d6c6e836b913607def00c0eeb1c155b2ab600`

## Frozen identity and artifact

- Protocol SHA256: `011b4959bf7cd343694f44e2986d13d87c07b6fa238dc326f5273e86885afe18`
- Required CI: run `36287866189`, SUCCESS; artifact `10921575990`; digest `sha256:5bc9ac527045d61a28258b7714291da7450d531191098941fd5708828d2e1d16`
- Finite replay: run `36287943625`, SUCCESS, attempt 3; artifact `10921995049`; digest `sha256:1868b407b4650144c45b5d0b3bf0a9a59a93179614e0b1c856fe0b4a26c2adaa`
- Result JSON SHA256: `e320c1cb2e234a00fc1b671ab70b07ec52e0e0f3f4207a615df73ef3430d9a55`
- A ledger SHA256: `2fbf1df2d7ddfbd5f07fbe87da8daeb37b80cb96bb6bfab60a3aa2496f7ae185`
- B ledger SHA256: `770f02612cdd97ed2420f14a2fe6ab6ed1f50a96f222afa9b3c376982c8ea476`
- Both candidate run-A/run-B gzip ledgers are byte-identical.
- Candidate count 2; model fits 0; prediction refits 0.

## Frozen-gate scorecard

Primary is evaluator-only `POST_ENTRY_UPSIDE_GE5` (IM 222, R1 200).

| Candidate / Entry | Mean Net | Median Net | PF | Win | Median Capture | Premature | Negative Capture | Median High→Exit gap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A / IM | 4.881% | 3.459% | 5.780 | 74.32% | 44.163% | 4.50% | 24.77% | 4.635pp |
| A / R1 | 4.418% | 3.323% | 4.459 | 74.50% | 39.693% | 4.50% | 25.00% | 4.929pp |
| B / IM | 4.372% | 3.524% | 3.879 | 68.92% | 48.757% | 0.00% | 30.18% | 4.590pp |
| B / R1 | 4.044% | 3.310% | 3.346 | 67.50% | 39.810% | 0.00% | 32.00% | 5.017pp |

Both candidates pass support, mean net, median net, and premature gates in both Entry arms. Both fail the frozen median-capture >=50% gate in both arms. Therefore:

**0 PASS — NO_SELECTION_STOP**

Candidate A made 97 model exits over the complete replay (65 in Primary). Candidate B made zero and is behaviorally the terminal-hold control. Relative to B on the common Primary set, A changed 32/222 IM exits (23 better, 9 worse) and 32/200 R1 exits (21 better, 11 worse). A improved left-tail/mean economics but reduced median capture.

Cost stress remained positive in Primary: A mean net at 0.20pp sell cost was 4.731% IM and 4.268% R1; B was 4.222% IM and 3.894% R1. A harvest concentration was not dominant: all-row top-symbol share 6.19% and top-session share 8.25%; Primary top-symbol share 9.23% and top-session share 7.69%.

## Recovery history

- Initial workflow YAML parse failure: jobs 0, replay 0.
- Attempt 1 run `36287340967`: direct-script import failure before decision loop/performance.
- Attempt 2 run `36287541385`: arm/Entry identity collision guard before scorecard.
- Mechanical corrections only: module invocation, arm-qualified identity, unresolved non-Primary terminal representation, filename-neutral deterministic gzip, and dependency-free regression test placement. No candidate, feature, threshold, state, execution, cost, gate, or selection rule changed.
- Attempt 3 is the only completed formal replay.

## Capital disposition

No Final EXIT Freeze exists because selection is null. Portfolio performance, MAX3 primary, and MAX4/MAX5 sensitivity were therefore not run. Existing causal R35 rank lineage and performance-free R37 cash/lot interface remain preparation only. Capital cannot be connected to an unselected EXIT.

## Exposure and safety

Development only (2,155 outcome-exposed opportunities). Common Holdout, REPORT19, Validation, OOS, Fresh, Prospective, and Protected remained unopened. Provider requests 0. Entry/Selector changes 0. The recorded R49 initial decode of 3,220 allowlist-external payloads remains disclosed; R50 used allowlist-first inputs.

Safety9: all false. No live, paper, production, broker, Excel, RSS, transmission, or automatic promotion action occurred.

## Controlling next rule

R50_A/R50_B may not be relaxed, retuned, or adopted as best-of-failing. No third/fourth R50 candidate may be added. Any further EXIT research requires a new failure anatomy and a new performance-blind Precommit.

