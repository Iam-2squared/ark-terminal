# Phase57 — Generation 1 formal closure and Claude review disposition R40

Saved at: 2026-09-26 17:59:18 JST  
Reviewed basis HEAD: `43b91e50ba9c14277ed51961e132485ed1f0b42e`  
Status: **GEN1 CLOSED / NO_SELECTION_STOP; GEN2 AUTHORIZED THROUGH FINITE ACTIONS LAUNCH ONLY**

## Authority and work actually performed

This append-only record reuses the completed R38 correction and R39 formal closure.
It does not reopen, tune, refit or replay the R25/R33/R36 experiment. The current
user instruction explicitly authorizes a separately bounded Generation 2 design,
precommit, implementation, focused tests, necessary pre-performance CI and finite
GitHub Actions launch. This satisfies R39's requirement for a user decision before
new research; it does not change R39's negative Generation 1 outcome.

New work in this document is a source-qualified, finding-level disposition of the
user-relayed Claude R36 review, with the two required PARTIAL corrections and an
explicit Gen2 stopping boundary. R36 computation, R38 evaluator repair and their
CI/hashes below are reused evidence, not newly performed work. Comprehensive
failure anatomy and the Gen2 protocol are separate downstream deliverables and
are not claimed complete here.

## Generation 1 closure reused without recomputation

Controlling historical references:

- [R39 final no-selection handoff](DEVELOPMENT_NO_SELECTION_HANDOFF_R39.md).
- [R38 bounded evaluator erratum](RESULT_AUDIT_ERRATUM_SCOPE_R38.md).
- [Original receipt](r38-result/original-receipt.json) and [original fit receipt](r38-result/original-fit-receipt.json).
- [R38 correction audit](r38-result/audit.json).
- [Original selection](r38-result/original-selection.json) and [corrected selection](r38-result/corrected-selection.json).
- Original and corrected scorecards remain side by side in `r38-result/original-scorecards/` and `r38-result/corrected-scorecards/`.

R36 executed on `a10b3f25f79f8221c9a71c1b3ede245777bce058`, run
[36222151340](https://github.com/Iam-2squared/ark-terminal/actions/runs/36222151340).
It completed exactly 144 estimator fits and 24 policy replays. Original Run A/B
replay/evaluator outputs from shared immutable OOF predictions were byte-identical;
this is not a claim of two independently repeated estimator fits. R38 verified all
144 model bundle hashes and all 50 original Run A/B files. There are zero passing
candidates and no selected/frozen EXIT.

R38 repaired only `metrics.ownedPeakGivebackPp`: NumPy float32 values returned by
`_position` had been rejected by `numeric`. It restored the original scalar at the
recoverable original decision endpoint under the existing R20/R21 ownership rules.
Incomplete prefixes remain uncertified; exit-candle High/Low remain excluded.
Predictions, decision actions, fills, costs, net returns and all 24 configurations
are unchanged. Additional fits = 0; additional policy replays = 0; Portfolio
replays = 0. The original defective results remain preserved.

R38 CI [36227400437](https://github.com/Iam-2squared/ark-terminal/actions/runs/36227400437)
passed 71 tests. Its correction passes were byte-identical and each local corrected
result matched the independently executed CI output, as recorded by R39. These
successful checks are reused; they are not rerun merely to recreate this document.

| Identity | Value |
|---|---|
| Original R36 artifact ID | `10901042535` |
| Original R36 ZIP SHA256 | `1c574848c6106d34c1d53e902b339e1be2f43b7b5c615e40a7010c29332d997a` |
| Corrected R38 artifact ID | `10901355944` |
| Corrected R38 ZIP SHA256 | `993c3a744b971ae8ccada9784a2c26180beb2abfd3c9c46e8b854ba28ce2f510` |
| Unchanged OOF predictions SHA256 | `1c24a5ff04ba759c00b5cdc517f1a0ab037357658dca95f5497ed8af149d8ca8` |
| Original `selection.json` SHA256 | `35b61fbf7ba1de8e1d706d5c2d3c78324042bb5a05806aac565a7197e037a713` |
| Corrected `selection.json` SHA256 | `ef6d47ad5884fb011d308dbde23cbbce9c9250fe4ae813471209437102d0f17f` |
| Corrected `candidate-summary.json` SHA256 | `6741d85a905672128666def264bfcb8b66940aebf20b75ad2053dc97065f29a9` |

Full per-file hashes are retained in the original receipt and correction audit.
Different selection-file hashes reflect corrected retention evidence, not a
changed selection outcome. Both outcomes are `NO_SELECTION_STOP`.

R39 records primary mean-net gate passes 0/24 and Winner Continuation passes 0/24
for each Entry arm, versus corrected Profit Retention 24/24 and Loss Containment
24/24 for each arm. All-gate passes remain 0/24. The Generation 1 OOF population
is 1,267 Opportunities over 34 score sessions; its >=5% population is 393. The
full exposed Development cohort remains 2,155 Opportunities over 58 sessions,
with canonical >=5% N=666. Neither is fresh/OOS evidence. No best-looking failed
candidate is adopted, and no 25th Generation 1 candidate is added.

## Claude review source and provenance

Source type: **USER_RELAYED_REVIEW_SUMMARY**. The current attached handoff states
that Claude independently reviewed the R36 result and returned `CONDITIONAL GO`.
The summary is in `貼り付けたテキスト（1）.txt`, lines 435–506, SHA256:

`4abd6237fc2c4a66273259c57e9124b6f02ca80ad74d9b86b070a63d3796e13b`.

This document preserves the material findings from that supplied summary. It does
not claim to contain Claude's complete raw response, a direct authenticated Claude
session, a new external review or a GitHub-authored Claude response. PR #587's
retrieved discussion timeline contained 23 entries, all authored by
`Iam-2squared`, and the submitted-review query returned zero reviews. The latest
retrieved review-request comments were `5832544386` / `5832590346`; the historical
blocker comment was `5832681191`. Those old comments neither contradict nor
independently authenticate the later review the user relayed.

[R28](CLAUDE_INDEPENDENT_REVIEW_DISPOSITION_R28.md) is the earlier pre-design
review, with verdict `PASS WITH REQUIRED FIXES`; it is not the R36 result review
and is not used as a substitute for it.

## Finding-level disposition

IDs below identify normalized findings from the user's supplied summary; they
are not invented original Claude finding numbers. Statements in quotation marks
are short exact excerpts from the supplied handoff. Other wording is a qualified
paraphrase/disposition, not a claim of verbatim Claude output.

| ID | Relayed finding / concern | Disposition | Reason and required treatment |
|---|---|---|---|
| G1-C01 | R36 is an informative negative result. | **ACCEPT** | Preserve 144 fits, 24 policies, 0/24 passes and `NO_SELECTION_STOP`. Do not turn technical CI success into strategy success. |
| G1-C02 | Keep Frozen Entry unchanged and do not open Fresh/OOS. | **ACCEPT** | Both frozen Entry arms and all protected partitions remain unchanged/sealed. |
| G1-C03 | Architecture may matter more than small threshold changes. | **PARTIAL** | A defensible research hypothesis, not an identified sole causal explanation. Failure anatomy must distinguish labels, aggregation, calibration, State/Signal/Pattern, missingness and execution effects. No Generation 1 threshold rescue. |
| G1-C04 | Separate Winner Continuation and Loss Containment through Continuation / Failure heads. | **ACCEPT AS GEN2 DESIGN HYPOTHESIS** | Define separate targets and action roles before performance. Neither improved performance nor the suitability of a full survival estimator is established by the review alone. Exact architecture belongs to the Gen2 precommit. |
| G1-C05 | "HGB+Patternが一貫してRidgeより優位" | **PARTIAL** | The best candidate came from HGB+Pattern, but universal HGB+Pattern superiority is not proved by R36; it did not beat Ridge in every corresponding condition. Do not claim model-family dominance or choose extra tuning from this statement. |
| G1-C06 | "MAXだからWinnerを早く切る" | **PARTIAL** | MAX holds when any head remains above the policy boundary. MAX alone cannot explain an early Winner exit. Analyze when and why all three heads lost continuation value, including persistence and data availability. A single optimistic head can plausibly delay loss containment; this is a separate hypothesis, not a proven explanation. |
| G1-C07 | Repair the evaluator bug without retraining. | **ACCEPT / ALREADY RESOLVED** | R38/R39 already supply the narrow correction and reproducibility evidence. Reuse them; keep predictions/actions/returns unchanged. |
| G1-C08 | Freeze a new finite protocol before Generation 2 performance, preserving failed R36 evidence. | **ACCEPT** | Gen2 is a separately authorized experiment. Freeze labels, feature admission, candidates, fit accounting, selection rules, completion gates and stopping rules before any Gen2 performance inspection. |

`CONDITIONAL GO` authorizes no shortcuts. All required conditions must be
implemented and verified before the Gen2 learning workflow starts. No reviewer
claim overrides the frozen execution semantics, causal input boundary or user
stopping instructions.

## Current authorized next work and stopping point

1. Reuse the completed formal closure/erratum and finish comprehensive Generation 1
   failure anatomy using existing immutable ledgers/predictions and approved
   Development substrate only. Future path and bucket diagnostics remain evaluator-only.
2. Define and audit separate Continuation / Failure labels, architecture, causal
   feature interface, knownAt/missingness rules and leakage isolation. Record
   uncertainty where the anatomy does not identify the cause.
3. Freeze a finite Gen2 candidate/search space, exact expected fit count, selection
   rules and Completion Gate in GitHub before any Gen2 performance inspection.
4. Implement that frozen design, run synthetic/focused tests and required
   pre-performance CI. Do not launch learning with an unfinished prerequisite.
5. Recheck latest remote HEAD, commits, controlling evidence and queued/running
   jobs immediately before writes and important computation. Launch one finite
   workflow only, without duplicating an existing job.
6. Once heavy fitting/causal replay has normally started and the exact execution
   SHA, run ID, protocol/hash, candidate count, expected fit count, artifact plan
   and Safety/Exposure are confirmed, save the controlling handoff and stop this
   Work session. Do not consume the session waiting for heavy computation.

Artifact audit, scorecard, `SELECT` / `NO_SELECTION_STOP`, any Final EXIT Freeze
and Capital MAX3/MAX4/MAX5 historical integration are reserved for the next Work
session after GitHub Actions completes. Nothing here authorizes a pre-Freeze
Portfolio comparison with a provisional EXIT.

## Freeze / exposure / Safety / supersession

Entry Dual Freeze remains `4878a1cc53430e816261dea0fb16aeb53b3c238d`:
`IMMEDIATE` and `ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF`. Old Fixed12/Candidate A stay
historical only, never comparison baseline, fallback, search anchor or target.
The 2,155 Opportunities are outcome-exposed Development. Common Holdout, REPORT19,
Validation, OOS, Fresh and Prospective remain sealed. New provider requests = 0;
protected opens = 0. This document performs no fits, policy replays or Portfolio
replays and reports no new Gen2 performance.

Safety9 are all false: executionAllowed, brokerWriteAllowed,
excelOrderWriteAllowed, rssOrderFunctionAllowed, liveTradingAllowed,
paperTradingAllowed, automaticPromotionAllowed, productionUpdateAllowed,
transmitted. No main merge, force push, live/paper/production operation.

R38 continues to supersede only the erroneous original owned-giveback reporting.
R39 continues to control the final Generation 1 negative outcome. The new user
instruction supersedes only R39's pause pending separately bounded research
authorization, and only through the Gen2 launch boundary above. No existing
Evidence file is overwritten or reinterpreted as a Generation 2 result.
