# Phase57 — Comprehensive EXIT Intelligence v1 pre-design handoff R27

Date: 2026-09-25 JST  
Latest implemented/tested HEAD: `21bbf931786e293ebe12cdf331c03052d317d05a`  
PR: #587 Open / Draft / unmerged  
Overall status: **FOUNDATION_IMPLEMENTED_AND_CI_PASS / CLAUDE_RESPONSE_PENDING / COMPLETION_GATE_NOT_YET_PASS**

## Current position

All requested technical pre-design work through feature admission, sequential
geometry, execution/evaluator contracts, full scorecard and finite research
protocol is implemented and tested. No NEW EXIT candidate was fitted, replayed,
ranked or inspected. The only unmet Completion Gate item is a genuine external
Claude response and its evidence-backed disposition; it is not replaced by an
internal review.

## Completion Gate ledger

| Gate | Status | Evidence |
|---|---|---|
| R20 full observation census complete/audited | PASS | R22; run `36128852207`, artifact `10862675162` |
| R20 Run A/B reproducibility | PASS | all 61 manifested files byte-identical |
| State-v3 EXIT-NOW contract | PASS | R20/R22/R23 |
| Six Signals EXIT-NOW contract | PASS | R20/R22/R23; UNKNOWN preserved |
| Pattern-v2 476 inventory/admission | PASS | R23; 446 admitted / 30 blocked / 187 finite subset |
| Entry→NOW path feature contract | PASS | R20/R23 |
| Feature Availability & Causality Matrix | PASS | R23 + executable generator |
| Decision/execution/terminal/missing contract | PASS | R24 + executable module |
| R21 evaluator kernel isolation and CI | PASS | R21 run `36130452793`; integrated tests on latest HEAD |
| Six Low→High buckets | PASS | R24; exact source/hash reproduces 158/391/361/289/188/666 |
| Full EXIT scorecard | PASS | R24 + deterministic JSON generator |
| Finite candidate/model/search protocol | PASS | R25; exactly 24 configurations |
| Claude independent review | **PENDING/BLOCKER** | R26 request; PR comments `5832544386`, `5832590346` |
| Claude disposition | **PENDING/BLOCKER** | no response, therefore no fabricated disposition |
| Focused tests | PASS | 61 tests |
| Relevant latest CI | PASS | run `36136774921`, job `108076613448` |
| Final pre-design handoff | PASS | this R27 document |

Because the two Claude rows are not complete, the user-defined overall Completion
Gate is not called PASS. Candidate fitting/performance inspection remains blocked.

## R20 receipt

- Artifact ZIP: `phase57-exit-checkpoints-r20-36128852207`, 195,826,846 bytes.
- ZIP SHA-256: `6019809ca4ac9793c5a34ec1c894580c52ffea5074b6ee0ee8e593d10ef12b40`.
- Manifest SHA-256: `98036d1133b0d93aa4c6e47d598ffd4a60d1f7021474f569c3a2ba24021e2b3b`.
- Cohort: 2,155 IDs/arm, exact shared ID hash
  `ff2d0ea4f8ee03337e10910e908d41e48321c7d335c834ab1f9aa4de60255a60`.
- Fills/no Entry: IMMEDIATE 1,963/192; ALL_MATERIAL R1 1,885/270.
- Checkpoints: 345,893 + 310,354 = 656,247.
- Fresh/missing current close: IMMEDIATE 220,364/125,529; R1
  198,591/111,763.
- Complete owned prefix: IMMEDIATE 65,266; R1 55,672.
- Provider requests, protected opens, model fits, candidate evaluations and legacy
  EXIT invocations: all zero.

Entry State distributions and all six Signal UNKNOWN counts are preserved in R22.
All 34 R20 tests passed, including actual canonical producer parity, knownAt,
suffix mutation, lunch/ownership and tri-state behavior.

## Feature and sequential foundation

R23 pins the exact 476-column registry SHA-256
`efcbcaf4c4024679dc5f6e7881dcccc7c0186361b6bd469b7d3a5e6a5421e8eb`.
Exactly 446 columns are causally legal at EXIT NOW; 24 `RECENT/*` and six
prior-daily PDH/PDL Signal columns are blocked. The finite search can use only
the exact 187-column curated subset. Selector-origin join is 2,155/2,155 with
sanitized projection SHA-256
`cac2eeeda308ffdff20fe09331aec3cb7b18da311cc2c753bb78978b43581761`.

State/Signal/path histories are generated only from known prefixes. DROP or a
negative mark cannot mechanically mean SELL. Signal UNKNOWN is not FALSE.
Incomplete owned paths retain explicit coverage and cannot certify giveback.

## Execution/evaluation foundation

R24 fixes one decision per completed continuous 1-minute endpoint and the exact
next scheduled OPEN execution reference. Lunch maps 11:30 decision to 12:30 OPEN.
Missing exact references do not fill or queue. Overnight is forbidden; unresolved
positions use the exact minute-930 auction or stay censored. Of 2,155 paths, 2,092
have a single-price auction reference and 63 do not.

The primary explicit sell cost is 0.05 pp with 0.10/0.20 pp stresses; frozen Entry
cost is not charged twice. Owned extrema stop before the Exit OPEN candle. Regular
High is known at bar-start+1, while endpoint-stamped auction High is known at 930.
This latest R24 correction prevents terminal auction simultaneity from being
misclassified as a post-Exit High.

The canonical ordered-geometry source SHA-256 is
`4b9afd72ccfff0b557fb4a5e067ac122ace90ae501d15a79627a89af9554a01e`.
It yields 2,053 evaluable and 102 not-evaluable Opportunities; the exact >=5%
bucket N=666 is reproduced. Ordered High, post-Entry best High, evaluator gap and
certified owned giveback remain separate.

## Finite next research — frozen but not run

R25 freezes four expanding session-grouped folds with two purge sessions and 34
disjoint OOF score sessions. Labels are incremental exact-reference HOLD5,
HOLD15 and terminal value, future only on the target side. Two feature sets and
two model families produce exactly 24 configurations: 16 three-head Ridge and
8 three-head Histogram Gradient Boosting configurations. All must complete before
selection. Three capability gates, paired neutral-reference comparisons, cost,
concentration, robustness, byte reproducibility and `NO_SELECTION_STOP` are fixed.

No adaptive feature/model/threshold addition is allowed after results. Fixed12
and Candidate A are absent from reference, target, fallback and selection logic.

## Latest focused CI and artifact audit

Dedicated run `36136774921` on HEAD `21bbf931...` completed SUCCESS. Job
`108076613448` passed dependency setup, 61 focused tests, two deterministic
contract generations, recursive Run A/B diff and artifact upload.

- Artifact ID: `10864896673`.
- Name: `phase57-exit-predesign-r25-36136774921`.
- Size: 25,799 bytes.
- GitHub digest and independently downloaded ZIP SHA-256:
  `6e06e2c039d9d63ca6f67b9c48c421f72f3567ae923fd5fd4b91848ac84c7961`.
- Artifact Run A/B four contract files: byte-identical.
- Tests log: `Ran 61 tests ... OK`.

Contract hashes from the artifact:

| Contract | SHA-256 |
|---|---|
| feature | `14296be99970bb95bcb22361db819272181de82013a12d3e337f38857893d3d1` |
| execution | `ce64767891f446368e7a33ec2a40fa3699e809fc81ea433896d533a29d729ea6` |
| evaluator/scorecard | `4a8557407fdcc4adaf545d92b6293af14c3269e6ca92df336fea5b336bdf2094` |
| finite research | `d6633e97e5ef548075a0f52d71d955208630b59e085bd4cc1ba3b76c77749931` |

## Claude review status and required continuation

Direct Claude.ai access was blocked by a site-served Cloudflare verification loop
after one permitted retry. No configured CLI/API credential was present. The same
review request was posted to `@claude` on PR #587 and remains unanswered at this
checkpoint. Details and exact requested scope are in R26.

Next action is only:

1. obtain a genuine Claude response against HEAD `21bbf931...` or its unchanged
   successor;
2. preserve each finding and GitHub Evidence;
3. disposition every finding ACCEPT/PARTIAL/REJECT/DEFER with reasons;
4. make only pre-performance contract corrections, rerun focused CI, and update
   this gate; or, if no changes are required, record the review verdict;
5. only after the user-defined Completion Gate is fully PASS begin the fixed
   24-configuration Development research.

Do not begin candidate fit, replay, performance inspection, EXIT Freeze, Capital,
Portfolio, Fresh/OOS, paper/live or production work while R26 is pending.

## Freeze, exposure, safety and limitations

Entry Dual Freeze `4878a1cc53430e816261dea0fb16aeb53b3c238d` is unchanged.
The 2,155 remain outcome-exposed Development. Common Holdout, REPORT19,
Validation, OOS, Fresh and Prospective were not newly opened. Provider requests
remain zero. Historical bar-end proxy does not prove live receipt latency.
Thirty Pattern columns remain blocked, terminal reference is missing for 63, and
owned-prefix completeness is low; all remain explicit rather than imputed.

All nine safety flags remain false: executionAllowed, brokerWriteAllowed,
excelOrderWriteAllowed, rssOrderFunctionAllowed, liveTradingAllowed,
paperTradingAllowed, automaticPromotionAllowed, productionUpdateAllowed and
transmitted. No main merge, force push, order transmission or production update
occurred.

