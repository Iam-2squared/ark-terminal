# Phase57 NEW EXIT Pre-Design OFFICIAL PASS R32

Date: 2026-09-26 JST
Basis HEAD: `1dab62f1619835ad400a74d126b41859e9944ce5`
Status: **PREDESIGN OFFICIAL PASS**

## Current state
R28 required pre-fit findings are machine-closed by R30. R29's +2.00% primary objective and R31's finite bucket anatomy/completion expectations were frozen before any NEW EXIT fit or candidate-performance inspection.

## Evidence
- Entry Dual Freeze remains `4878a1cc53430e816261dea0fb16aeb53b3c238d`.
- R30 focused CI: run `36199796765`, SUCCESS at `84d839d838483cb16458f54e89e3aabcdbfdb5d4`; artifact `10891970429`, digest `sha256:2ba4cab53f0a017bcc6e6478f0f25b8975027850baf4b75c0874abdfffbfc169`.
- R31 precommit: `NEW_EXIT_BUCKET_COMPLETION_GATE_R31.json`, commit `1dab62f1619835ad400a74d126b41859e9944ce5`.
- R31 focused CI: run `36213722965`, SUCCESS; artifact `10895959156`, digest `sha256:2625cb775f887a6d8b309ee7adcf2d5a60b702d060886430a174358448e4d0e9`.
- At PASS: NEW EXIT fits=0; candidate performance inspected=false; winner selected=false; protected opens=0; provider requests=0.

## Authorized Development work
Proceed now with exactly R25's 24 configurations, four fixed expanding walk-forward folds, the two registered feature sets, Ridge/HGB families, and registered threshold/persistence values. Complete all 24 before winner declaration. No 25th configuration, result-driven feature/model/threshold change, bucket-conditioned training, or protected-data opening.

## Freeze / safety
R25 and R31 gates remain immutable during this finite run. Fixed12/Candidate A remain historical only. Safety9 remain false. No main merge, live/paper/production, force push, or provider acquisition.

## Next plan
Implement/reuse only the plumbing needed for the frozen R25 run, execute the 24 Development configurations, generate the R24/R31 full scorecard, and apply only precommitted gates. Outcome is SELECT or NO_SELECTION_STOP. If SELECT, freeze EXIT and move directly to Capital and Portfolio integration.

This R32 supersedes R27 as the controlling pre-design handoff; R18-R31 remain supporting immutable evidence.
