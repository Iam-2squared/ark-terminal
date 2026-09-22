# Phase57 Continuity Checkpoint — in-progress preservation
Recorded: 2026-09-22 16:47 JST
Repo: Iam-2squared/ark-terminal
Branch: research/phase57-long-only-cash-equity
PR: #587 — Open / Draft / not merged
Turn Start HEAD: 38c789c39a30618b449435d1fc8ec7410a1b5dc6
Verified implementation code HEAD: 698438c2488c3e1de6b3fef2a9fd8f67538cbc14
Latest work HEAD before this checkpoint: 93da164e0e14b12a5899afac2b59fef8edc8bb88
End HEAD: NOT_FINAL — this is an in-progress preservation checkpoint. See subsequent final checkpoint.

## Completed
- Restored four pinned Development artifacts by exact ID/run/digest; admitted 2,155 fixed Opportunities with all input hashes and Step1 raw parity verified.
- Implemented separate NOW/Future modules and JSON schemas, PIT readers, closed statuses/reasons, per-family attributes/events/context, overlapping H10 censors, and immutable-reference generator.
- Full local generation completed: 77,214 NOW + 77,214 Future records, all original keys/identity fields matched, duplicates/drop/refilter=0.
- All 77,214 Future Structure/Phase values match the immutable mechanical-v1 ORACLE reference after explicit status representation normalization. NOW Direction values match all original rows.
- 93 frozen numerical tests +22 G adapter tests +6 compatibility tests +37 v2 tests (26 Golden Vectors included) pass. Initial handoff said 5 focused tests; actual initial suite had 6.
- Full Draft 2020-12 schema validation completed: 154,428 records checked.
- Attribute tags, fixed-level values/events, and moving VWAP events match v1 on 77,214/77,214 rows each.
- 188 old ORACLE active-Structure rows becoming non-DEFINED in NOW are individually enumerated; no unaccounted semantic transition.
- Dedicated CI installed cleartext source and restored original frozen document bytes successfully; its generation job is still running at this checkpoint.

## Tests / Audits
| Check | Result |
|---|---|
| Fixed input hash / cohort / raw parity | PASS: 2,155 |
| Full NOW/Future generation | PASS: 77,214 each |
| Original reference key conservation | PASS |
| Synthetic suites | PASS: 158 tests |
| Full schema audit | PASS: 154,428 |
| Minimal independent core projection | MATCH: 77,214; not full independent primitive implementation |
| Reverse order / worker variation / suffix mutation replay | IN_PROGRESS; do not call PASS yet |
| Independent cross-day price-basis as-of evidence (A8) | BLOCKED / not established |
| Full independent implementation scope / Future bookkeeping review (A9) | PARTIAL |
| Formal acceptance receipt (A12) | NOT_ACCEPTED |

## Failures retained / repairs
1. Bootstrap run 35696041330 failed on frozen spec bytes before tests.
2. Diagnostic bootstrap run 35696312668 ran 121/121 initial tests successfully but failed closed on two frozen document hash mismatches. Its artifact 10680950149 is preserved.
3. Original Library copies matched existing frozen pins exactly. Each repository copy was missing precisely one terminal LF. Source install restored only that byte; no pin or semantic/numeric rule changed. Receipt: docs/evidence/phase57-state-v2-implementation/SOURCE_INSTALL_35700139842.json.
4. First full generation failed because the transition auditor incorrectly assumed every old-ORACLE vs NOW change requires a newly late-confirmed pivot. Frozen retrospective effective-time replay can itself change historical state. Audit now separately records RETROSPECTIVE_EFFECTIVE_TIME_REPLAY and FUTURE_ASSISTED_TO_CAUSAL_PIVOT_CUTOFF, without altering labels or the frozen engine. Failure log and original runner preserved locally for the final evidence package.
5. Other admission/test/audit runner failures are retained separately and never count as completed output.

## Evidence / hashes
- Dedicated CI run: 35700139842; install job 106655938777 PASS; verify job 106656262560 RUNNING.
- Source package payload SHA256: c765a5f1c808abd11e32a1d8672efb5c1fe6e22ee5f609bb46c73fddd175fb1a.
- Primary working-code set hash: 37b5b0c1eea656c2ae2fcbfebb9eaf1c4e04f2efd8e4d909f69fa08fe13f904e.
- NOW canonical hash: ba57dbe3b6da51df8ad79f00d0eaa756d418c9d7b175ee8453afd7f0a2ae7b5d.
- Future canonical hash: a93aa3e8aad0c2fc17be2239b05cfe0ff969da49a77466384262518284162d34.
- Transition canonical hash: df6df18fbb3d60c54d126d4cbcc623c4b8d5de2a63542b82fa030b7e5593319b.
- Local generation manifest SHA256: a5b6e57141b547540f576b5f7972b90e155e9fb3ec2eaa93eb8a807ee3f0664b.
- Local work root: /mnt/data/phase57-v2-work. Generation-run2 is complete; generation-run3 is the active varied replay.
- Source paths: scripts/phase57_state_v2/{common,now,future,historical,independent}.py; scripts/run_phase57_state_v2.py; scripts/report_phase57_state_v2.py; scripts/audit_phase57_state_v2_{schema,event}_transitions.py.

## Frozen boundaries and safety
Selector, Opportunity Generator, numeric mechanical-v1, State v2 Design, Scale, H10, class/threshold/Phase semantics unchanged.
Safety9 all false: executionAllowed, brokerWriteAllowed, excelOrderWriteAllowed, rssOrderFunctionAllowed, liveTradingAllowed, paperTradingAllowed, automaticPromotionAllowed, productionUpdateAllowed, transmitted.
protectedDataOpened=0; providerRequests=0. No Recognition, Signal, Entry/EXIT/Capital, model fitting, main merge or production update.

## Storage / source limitations
GitHub API reports repository visibility=public. No visibility change was made. New market raw and full reference rows are not added to Git; full generated records use workflow artifact / conversation attachment storage, with code/aggregates/hashes in Git.
Historical knownAt=null is explicitly permitted as HISTORICAL_CLOSED_RECONSTRUCTION by frozen section 9.1. It is not itself a new universal rejection gate. The unresolved A8 issue is section 9.3 cross-day common-price-basis/corporate-action as-of admissibility. Existing limitations remain: inherited raw basis, inherited same-day metadata not independently PIT, current-action raw not reaudited, source-filtered invalid-row causes incompletely recoverable.

## Next
1. Finish the full reverse/worker-variation/suffix perturbation replay and compare canonical hashes.
2. Verify dedicated CI output/artifact and assemble final full-data audit evidence.
3. Deliver a ready A8/A9 independent review package and save a final continuity checkpoint. Do not claim Implementation Accepted before all required gates pass.
