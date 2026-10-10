# Phase57 — Nine-State Entry Audit / Bounded Research R0

2026-09-23 JST. Research-only continuation for Draft PR #587.

## Authorization and target

The latest user instruction authorizes automatic continuation through investigation, analysis and justified local research repairs for all nine States. This supersedes the earlier stop-after-each-State requirement only within this scope. It does not authorize unconstrained optimization, changing the nine-pattern vocabulary/meaning, protected-data access, production replacement, main merge or execution.

Target: audit all nine States, resolve supported implementation/timing problems in isolated research candidates, then perform a full-population integration comparison. Development completion, independent validation and live readiness are separate statuses. A State with insufficient empirical evidence must remain INSUFFICIENT, not PASS.

Processing order: REBOUND -> RISE -> SHARP_RISE -> DROP -> PULLBACK -> RANGE -> SHARP_DROP -> DROP_STOP -> RISE_STOP. Classifier/evaluation infrastructure failures affecting the entire pipeline stop dependent work. State-specific insufficiency does not prevent safe independent audits of the other States.

## Starting identity and input provenance

- Branch: research/phase57-long-only-cash-equity
- Source HEAD verified before this documentation-only addition: 0cb54331b7da1021a0244c625245c20b1694ec28
- Original tested implementation HEAD: 8c256ff98d365d01c7150afe193686f020e2026c
- Original dedicated run: 35818555587
- Original artifact: 10732168448
- Downloaded ZIP SHA-256: 74ff0fb4398f9e2659109103ae73e8a6b27423aa0eb5aee7006c84312488aab8
- ZIP size reported by GitHub: 682445 bytes
- Artifact expiration: 2026-12-22T04:29:43Z
- Local ZIP digest verified against the saved CI receipt. All six replay-a/manifest.json member hashes were verified.
- Full artifact remains expiring Actions evidence; downloading a working copy is NOT permanent repository storage.
- Provenance: docs/evidence/phase57-drop-pull-1m-state-recheck-v1/FINAL_REPORT_R1-ja.md and validation/CI_RECEIPT_R1.json.

Only archive member names, schemas, input hashes, unique Opportunity identity counts and initialState counts were inspected during this setup. No new State-level outcome summary was calculated, no case was visually reviewed, and no classification-quality conclusion was made. Loading serialized rows for schema/count validation is not an independent blind holdout: these data were already outcome-exposed Development before this task.

## Initial T0 inventory — NOT performance or classification accuracy

The PATTERNS tuple was read from scripts/phase57_state_v3_9pattern_entry_v1.py at the source HEAD. Counts below were computed from initialState in replay-a/entry-records.json.gz of the verified artifact.

| State | T0 Opportunities | Initial audit disposition |
|---|---:|---|
| REBOUND | 192 | INPUT_INVENTORY_VERIFIED; prefix audit next |
| RISE | 111 | NOT_STARTED |
| SHARP_RISE | 7 | NOT_STARTED; very small T0 cohort |
| DROP | 1403 | NOT_STARTED |
| PULLBACK | 354 | NOT_STARTED |
| RANGE | 57 | NOT_STARTED |
| SHARP_DROP | 26 | NOT_STARTED |
| DROP_STOP | 5 | NOT_STARTED; very small T0 cohort |
| RISE_STOP | 0 | NO_T0_OBSERVATIONS; transition/code audit still required |
| TOTAL | 2155 | 2155 unique Opportunity identities |

T0 inventory is not a census of subsequent WAIT-state transitions. Zero T0 observations does not prove a State never occurs later. Do not fabricate observations, lower support standards or retune classifier thresholds to populate a State.

## Per-State process

1. Read and pin the frozen nine-pattern contract, classifier and available prefix/checkpoint evidence.
2. Audit contract compliance, timestamp ordering, input availability and prefix-only chart shape BEFORE using State-level future outcomes. Record which cases/charts were actually inspected. An implementation matching its own output is not independent semantic validation.
3. Predeclare the case-sampling rule before review; use deterministic outcome-blind sampling and a fixed random seed, include boundary/quality cases using prefix-only criteria, and include masked comparison cases from other States to check missed membership. Hide future suffix, outcome fields and candidate labels in reviewer case packets. Freeze review results before joining evaluator outcomes. Do not claim visual census if only a sample was visually reviewed.
4. Keep original labels fixed for the primary anatomy. Any audit disagreements are separately recorded; do not silently relabel/filter the main cohort after seeing returns.
5. Report N, Fill/Fill rate, Low->Entry price and active-time differences, Entry->Later High, EntryPosition mean/median and <=10/25/50% rates, +3/+5 Capture, and 30m/60m MFE/MAE. Preserve existing evaluator definitions and report valid N, missing/unfilled reasons and every denominator. Separate original T0 State from later transition State.
6. Attribute the issue to implementation, ambiguous contract, Entry timing, data/support insufficiency or no supported issue. Ambiguous contract semantics require human clarification, not an outcome-fitted definition.
7. Where causally justified, precommit ONE minimal research candidate for that State, including rationale, baseline, eligible inputs, target cohort, acceptance/rejection rules and stop conditions BEFORE its comparison. Implement separately from the immutable baseline. If no defensible hypothesis exists, preserve the baseline and report that.
8. Run focused tests, leakage tests, replay/repeatability, same-population/paired comparison and all-State non-target/transition regression. Persist exact hashes and CI identity, then continue to the next safe State. A valid failure is a result, not a reason to weaken the gate.

## Bounded trial budget and overfitting protection

Initial unattended pass: at most one NEW performance hypothesis per State, at most nine total. This is a conservative engineering trial budget, not a statistical guarantee. No threshold sweeps, outcome-selected symbols/times, feature/model expansion or keep-trying-until-PASS loop. A rejected hypothesis is recorded and not replaced by another unattended hypothesis for that State. Pure software repairs may rerun the same fixed protocol with every failed attempt retained. New candidates, disagreements and failures are append-only in Trial/Exposure ledgers.

All 2155 Opportunities remain exposed Development. Re-splitting them, hiding future charts during review or showing a confidence interval does not make them Fresh/OOS. Independent generalization and absence of overfitting are NOT established here. Protected data remains closed.

## Baselines and causal boundaries

- Frozen Selector unchanged; Entry must not become another Selector that discards Opportunities.
- Original State-v3 classifier, nine-pattern definitions, six existing Signals, RISE/SHARP_RISE/REBOUND T0 BUY policy and saved DROP/PULLBACK one-minute result remain immutable baselines.
- Local timing candidates may be compared in a new research version; no automatic official replacement.
- Classifier implementation bugs may be repaired only to match the fixed contract in an isolated candidate. Vocabulary/semantic/threshold redefinition, new Signals, Volume, Dictionary or learned models require separate permission.
- Decision inputs are only causally available previous-session and current OPEN->NOW closed-price data. Audit bar-start/bar-end, knownAt, session/lunch, missingness and fill semantics.
- Future ordered Low/strictly later High, MFE/MAE and Capture are evaluator-only. No future pivots, future labels or outcome data in classification, BUY/WAIT or favorable case selection.
- Test future-suffix mutation/deletion invariance, evaluator isolation, timestamp boundaries, non-target record invariance and State transitions.
- No invented fills, interpolation, forward-fill or retrospective data repair.

## Reuse and continuation map

Existing measurement roots (read before recomputation):

- docs/evidence/phase57-entry-timing-signal-census-v1/measurement
- docs/evidence/phase57-state-conditioned-signal-entry-v1/measurement
- docs/evidence/phase57-state-v3-9pattern-entry-v1/measurement
- docs/evidence/phase57-state-v3-9pattern-entry-v1/measurement/state-checkpoints.json.gz

Existing source workflow: .github/workflows/phase57-drop-pull-1m-state-recheck-v1.yml. It documents the approved evaluator substrate artifact 10605887642, ZIP SHA-256 749caf82bbd9d39969f5712ef5a6f2705ac973a2f74483f03307c671586ae05a, and member names substrate/raw-paths-evaluator-only.json.gz, substrate/rows.json.gz and substrate/outcomes.json.gz. These are lineage pointers, not a statement that this new task has downloaded or inspected those members. Never expose a full future path in a classification review packet; use an explicit prefix-only adapter and separate evaluator access.

Each continuation must re-read latest HEAD, new user instructions and the latest append-only progress record, check relevant running/queued jobs, and avoid duplicate runs or overwriting newer work. Use exact returned hashes/paths. No force push. Tool/permission/data blockers are reported honestly.

Original accepted CI: dedicated 35818555587; normal regression 35818556861; foundation 35818555691. Earlier 35818543146 was cancelled, not PASS. Original 35815694968 failed due to a docstring static-audit false positive, repaired without relaxing executed-code checks. Do not represent PR-wide workflows as GREEN or repair/replay unrelated old workflows.

## Final integration and completion

After per-State dispositions, fix the integration candidate before measuring the same full 2155-Opportunity population against Immediate, Entry v1, original State v3 and the saved one-minute version. Separate unmatched fills from common-case paired differences, report State-specific and overall results, and verify transitions, integrity, reproducibility and dedicated CI.

Classifications audited, States changed, States empirically supported, and States unresolved must be separate counts. No requirement that all nine be modified. Do not declare whole Entry complete while material BLOCKED/INSUFFICIENT issues remain. Final status can be DEVELOPMENT_CANDIDATE_READY or DEVELOPMENT_REVIEW_COMPLETE_WITH_UNRESOLVED_STATES; neither means OOS PASS or production readiness. Stop automatic mutation after the bounded pass and final integration report.

## Safety and current checkpoint

LONG-only / cash-equity-only. New provider requests 0. No new Common Holdout/REPORT19/Validation/OOS/Fresh/Prospective access. No EXIT/Capital/Portfolio/main merge/production work. executionAllowed, brokerWriteAllowed, excelOrderWriteAllowed, rssOrderFunctionAllowed, liveTradingAllowed, paperTradingAllowed, automaticPromotionAllowed, productionUpdateAllowed, transmitted all remain false.

R0 setup completed: hourly continuation configured; GitHub source identity read; archive downloaded and verified; 2155 unique T0 identities inventoried; nine implementation names checked. No classifier, Entry, Signal, workflow or executable code changed. No new tests/CI run claimed. No prefix chart audit completed. Next: build/read frozen prefix-only REBOUND review evidence, with the declared outcome-blind review protocol, then join anatomy only after review decisions are saved.
