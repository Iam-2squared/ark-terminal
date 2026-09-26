# Phase57 Gen3 R45 — running controlling handoff

Saved at JST: 2026-09-27T00:17:12+09:00.

This append-only checkpoint records the authorized one-shot Gen3 learning launch. It does not report candidate performance, a selection, or a Final EXIT Freeze.

## Controlling identities

| Item | Value |
|---|---|
| Repository / PR | Iam-2squared/ark-terminal / Draft PR #587 |
| Research branch trigger HEAD | `9cc2e39e9b4b0defc7d6a9a7570701f3fa6c02a8` |
| Implementation closure HEAD | `a6915498f126be6f324adbb6a380f18273b4808c` |
| Exact CI-tested execution SHA | `a65b3530df53a7a28334d7d1d4218d561e38b06b` |
| Entry Dual Freeze | `4878a1cc53430e816261dea0fb16aeb53b3c238d` |
| Protocol SHA-256 | `e7b38e7e6aaf909926852467152fffef2532f58f960a95e6f2d18efd66f5d1b5` |
| Required CI run | `36250723100` — SUCCESS, attempt 1 |
| Required CI artifact | `10908534909`, `phase57-gen3-contract-r45-36250723100` |
| Required CI ZIP digest | `sha256:2f41b3a935334733e4905bd0adff9f092bfd7b68fd9286e38bdde7a7538d44c0` |
| Learning workflow | Phase57 Gen3 Finite Learning R45 |
| Learning run / attempt | `36251316248` / 1 |
| Learning job | `108429755915` (`finite-once`) |
| Run URL | https://github.com/Iam-2squared/ark-terminal/actions/runs/36251316248 |
| Candidate / expected fits | 4 / 24 |

## Gate evidence before launch

Required CI independently recorded 79 focused/inherited tests PASS, 24/24 fold × Entry arm × head support slices PASS, 656,247 checkpoint rows, model fits=0, policy replays=0 and Gen3 performance inspected=false. The CI ZIP, contract receipt, support receipt, focused-test log and all 67 exported source hashes were independently rechecked before launch.

The launch marker is `docs/evidence/phase57-comprehensive-exit-v1/GEN3_LAUNCH_R45.json` at trigger commit `9cc2e39…`. It binds the exact execution SHA, successful CI run/artifact, frozen protocol, four candidates, 24 expected fits, Entry freeze, no retry and Safety9.

## Launch state at save time

The unique run exists and is in progress. Completed steps:

1. trigger checkout and immutable marker capture;
2. required CI artifact restore;
3. checkout exact execution SHA `a65b353…`;
4. Python 3.13 and frozen numerical dependency install;
5. source, CI, support, latest-HEAD, duplicate-run and Safety verification;
6. immutable R35 preparation artifact restore.

Current step: **Prepare causal features and isolated labels without fitting**.

The pre-fit authorization recheck and 24-fit step have not yet started at this checkpoint. Therefore current observed Gen3 model fits remain 0. This Work intentionally does not wait for the long GitHub computation.

## Freeze / Exposure / Safety

- Development cohort: existing outcome-exposed 2,155 Opportunities only.
- Fresh/OOS/Protected/Common Holdout/REPORT19/Validation/Prospective: unopened.
- New provider market-data requests: 0.
- Candidate performance inspected: false.
- Entry, Selector, candidates, thresholds, labels, features, State/Signal semantics and Completion Gate: unchanged.
- Gen1 and Gen2 remain formal NO_SELECTION_STOP.
- No fifth candidate, retry, main merge, force push, live, paper, production, Capital replay or promotion.

Safety9 all false: executionAllowed, brokerWriteAllowed, excelOrderWriteAllowed, rssOrderFunctionAllowed, liveTradingAllowed, paperTradingAllowed, automaticPromotionAllowed, productionUpdateAllowed, transmitted.

## Next action

After run `36251316248` completes, start from independent artifact integrity and lineage audit. Verify exact source/protocol, 24 completed fits, one immutable OOF prediction set, four policy A/B byte identity, two neutral replays, missing-reference handling and `AWAITING_POST_RUN_AUDIT`. Only then build scorecards under the unchanged R31/R45 gates and return SELECT or NO_SELECTION_STOP. Capital MAX3/MAX4/MAX5 remains outside this launch Work.

This handoff supersedes only the prior “ready to launch” status in `GEN3_IMPLEMENTATION_HANDOFF_R45.md`. The R44/R45 architecture, protocol, feature audit, negative Gen1/Gen2 closures and all permanent safety/data boundaries remain controlling.
