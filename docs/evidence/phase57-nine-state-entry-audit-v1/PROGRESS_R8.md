# Phase57 9-State Entry Audit — PROGRESS R8 / Anatomy Correction

2026-09-24 JST / PR #587 / branch `research/phase57-long-only-cash-equity`

## Scope

`PROTOCOL_R0.md` remains controlling. This append-only correction supersedes only the erroneous ONE_MINUTE anatomy numbers written manually in `PROGRESS_R7.md`. It does not overwrite R7, alter any frozen policy, consume a performance-hypothesis slot, or change protected-data exposure.

## Why this correction is required

The authoritative job log for Nine-State Anatomy v2 run `35865844490` was re-read directly. Its emitted values agree with the previously accepted DROP/PULLBACK one-minute final report and do **not** agree with several ONE_MINUTE values copied into `PROGRESS_R7.md`.

This is an evidence-transcription problem in R7, not an evaluator calculation change.

Authoritative run identity:

- workflow: `Phase57 Nine-State Anatomy v2`
- run: `35865844490`
- job: `107197078203`
- measured HEAD: `bb44dfaf149b801c4f1af0acd7f78bd557303676`
- artifact: `10751543293`
- artifact ZIP digest reported by Actions: `803fad7291f1689f53169237d2b2013539e2f14b4ff0ddfebb7fd1b013643cc7`
- source one-minute artifact: `10732168448`
- source ZIP SHA256: `74ff0fb4398f9e2659109103ae73e8a6b27423aa0eb5aee7006c84312488aab8`

## Correct authoritative ONE_MINUTE baseline

The run log reports:

- fills: `1764 / 2155`
- fill rate: `81.85614849187935%`
- mean EntryPosition: `0.6748679920277816`

These agree with `docs/evidence/phase57-drop-pull-1m-state-recheck-v1/FINAL_REPORT_R1-ja.md`.

The R7 values `1846 / 2155 = 85.6613%` and the R7 State-level ONE_MINUTE table must not be used for subsequent hypothesis selection or completion claims.

Correct ONE_MINUTE State-level values emitted by run `35865844490`:

| State | N | Fill rate | Mean EntryPosition |
|---|---:|---:|---:|
| REBOUND | 192 | 95.8333% | 0.743672 |
| RISE | 111 | 77.4775% | 0.628843 |
| SHARP_RISE | 7 | 100.0000% | 0.578227 |
| DROP | 1403 | 76.7641% | 0.677651 |
| PULLBACK | 354 | 92.9379% | 0.625865 |
| RANGE | 57 | 96.4912% | 0.731042 |
| SHARP_DROP | 26 | 84.6154% | 0.721125 |
| DROP_STOP | 5 | 80.0000% | 0.843613 |
| RISE_STOP | 0 | n/a | n/a |

Because the v2 log did not print every ONE_MINUTE threshold rate directly, <=10/15/25/50 values must be read from a generated summary or recomputed from the immutable records before being cited. Do not preserve R7's unverified ONE_MINUTE threshold rates merely because they were written to a progress note.

## Research consequence

The broad conclusion is unchanged: mean EntryPosition remains about `67.49%`, far from the aspirational `<15%` target. However, State prioritization must use the corrected State-level values above.

REBOUND hypothesis 1/1 remains rejected on its own dedicated run and is unaffected by this correction. Semantic blind reviews and sealed-map exact-match results are unaffected.

## Next diagnostic

A new evaluator-only Low-centered attribution lane is introduced with this commit for the three highest-support unresolved States: `RISE`, `DROP`, `PULLBACK`.

The diagnostic must:

1. build all causal State-v3 / frozen-signal witness rows before opening Oracle Low;
2. verify every classifier source bar is closed before each checkpoint;
3. only after causal witness freeze, align those witnesses to already-exposed Development Oracle Low;
4. report State/signal prevalence around Low and delays from Low to the first causal BUY-state / frozen signal;
5. re-read the immutable one-minute records and assert the authoritative `1764 / 2155`, `81.85614849187935%`, `0.6748679920277816` baseline before its output is accepted.

This is diagnostic only and consumes no RISE/DROP/PULLBACK performance-hypothesis slot.

## Safety / exposure

Provider requests 0. No Common Holdout / REPORT19 / Validation / OOS / Fresh / Prospective access is authorized. EXIT and Capital remain untouched because Entry completion is not met. No broker/Excel/RSS/paper/live/production action is authorized; all safety/write/trading flags remain false.
