# Phase57 9-State Entry Audit — PROGRESS R9 / Low-Centered Attribution + Hypothesis Freeze

2026-09-24 JST / PR #587 / branch `research/phase57-long-only-cash-equity`

## Authoritative correction status

`PROGRESS_R8.md` remains the correction for the erroneous ONE_MINUTE transcription in R7. Authoritative accepted ONE_MINUTE full-population baseline is:

- Fill `1764 / 2155 = 81.85614849187935%`
- valid EntryPosition N `1751`
- mean EntryPosition `0.6748679920277816`
- median `0.4960285714285679`
- <=10% `168 / 1751 = 9.5945%`
- <=15% `266 / 1751 = 15.1913%`
- <=25% `468 / 1751 = 26.7276%`
- <=50% `882 / 1751 = 50.3712%`
- +3 Capture `71.8791%`
- +5 Capture `73.5294%`

## Low-centered causal attribution v1

Dedicated run `35896350202` on HEAD `7e723bcc75b0c6b62377934965c855c3bac67594` completed SUCCESS.

- job `107301109836`
- artifact `10767297879`
- uploaded ZIP digest reported by Actions `058620e1f64abbafa12602df197719881723c9a62b6cfee2f34b1bc771070a47`
- causal State-v3 / frozen-signal witness set frozen before Oracle alignment
- every checked classifier source bar closed before checkpoint
- `stateFutureViolations=0`
- `oracleLowHighDecisionUse=0`
- `futureOutcomeDecisionUse=0`
- provider requests / protected data `0 / 0`
- immutable ONE_MINUTE baseline identity guard PASS

The Oracle Low below is evaluator-only attribution after causal witnesses were frozen. It is not a decision input.

| State | N | Fill | Mean Position | Median | <=15% | <=25% | comparable filled entries before Oracle Low |
|---|---:|---:|---:|---:|---:|---:|---:|
| RISE | 111 | 77.48% | 62.88% | 41.28% | 18.07% | 33.73% | 76.74% |
| DROP | 1403 | 76.76% | 67.77% | 51.71% | 13.26% | 24.93% | 55.15% |
| PULLBACK | 354 | 92.94% | 62.59% | 46.10% | 15.38% | 29.23% | 61.70% |

Among opportunities whose Oracle Low is inside the frozen decision window, earliest existing BUY-state-or-Signal occurrence after that evaluator Low appears within:

| State | <=1 active min | <=3 | <=5 |
|---|---:|---:|---:|
| RISE | 54.13% | 70.64% | 76.15% |
| DROP | 11.84% | 27.87% | 42.09% |
| PULLBACK | 28.05% | 47.03% | 57.51% |

At the evaluator Low itself, BUY-state prevalence is only about 52.29% for RISE, 6.93% for DROP and 13.88% for PULLBACK, then increases after the Low. The current records also show that first-entry timing frequently precedes that Low. The supported causal diagnosis is therefore not a classifier label mismatch; it is instability/prematurity of the current first-trigger semantics on Development paths.

## Precommitted performance hypotheses

Before replaying any new candidate, this commit freezes `CONFIRMED_BUY_PERSISTENCE_HYPOTHESES_R1.md` for exactly three independent State hypotheses:

- `RISE_CONFIRMED_BUY_PERSISTENCE_V1` — RISE hypothesis budget 1/1
- `DROP_CONFIRMED_BUY_PERSISTENCE_V1` — DROP hypothesis budget 1/1
- `PULLBACK_CONFIRMED_BUY_PERSISTENCE_V1` — PULLBACK hypothesis budget 1/1

Shared minimal rule: for the target T0 State only, recompute unchanged State-v3 each active minute and enter at the first checkpoint with either (a) existing Signal + current BUY state, or (b) two consecutive BUY-state observations. No fixed fallback, no new Signal/feature/threshold/model. Each State is scored independently against immutable ONE_MINUTE baseline; failure consumes that State's unattended slot.

Acceptance gate is frozen before measurement: paired EntryPosition and Low→Entry improve; <=15 and <=25 rates improve; Fill/+3/+5 each no worse than -2pp; causality/future-suffix/non-target invariance PASS.

## Current gate

Entry completion is NOT met. Overall accepted ONE_MINUTE mean remains `67.49%` versus aspirational `<15%`. REBOUND 1/1 is already rejected. SHARP_RISE/DROP_STOP remain insufficient; RANGE/SHARP_DROP support-limited; RISE_STOP no observations. EXIT and Capital remain untouched.

## Safety

No new protected partition access, provider request, main merge, broker/Excel/RSS/paper/live/production action. Safety/write/trading flags remain false.
