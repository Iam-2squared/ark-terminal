# Phase57 Entry All-Material v1 — Protocol R0

## Status
PRECOMMITTED BEFORE NEW ALL-MATERIAL PERFORMANCE MEASUREMENT.

This protocol starts a new Entry research version after completion of the bounded 9-State pass. It does not rewrite, erase, or reinterpret prior evidence.

## Immutable starting point
- Repo: `Iam-2squared/ark-terminal`
- Branch: `research/phase57-long-only-cash-equity`
- Draft PR: `#587`
- Prior bounded-pass freeze HEAD: `b446025d5021e69ac3a1e5eee1a2fae294d51414`
- Prior bounded-pass status: `DEVELOPMENT_REVIEW_COMPLETE_WITH_UNRESOLVED_STATES / ENTRY_COMPLETION_GATE_NOT_MET`
- Saved ONE_MINUTE reference: mean EntryPosition about 67.49%, Fill about 81.86%, <=15% about 15.19%, <=25% about 26.73%.
- REBOUND / RISE / DROP / PULLBACK one-shot timing candidates remain REJECTED and MUST NOT be retuned or silently retried.
- SHARP_RISE / DROP_STOP remain performance-insufficient; RISE_STOP remains no-observation; RANGE / SHARP_DROP bounded-pass conclusions remain preserved.

## User-authorized objective change
The 15% mean EntryPosition objective remains the stretch target.

The Development gate for proceeding to EXIT is now:
1. an integrated candidate is frozen before its final measurement;
2. full 2,155 Development Opportunities are replayed under fixed semantics;
3. valid-filled cohort mean EntryPosition is `< 0.25`;
4. common-case paired EntryPosition improves versus the saved reference;
5. Fill / Capture / Opportunity preservation do not suffer a material collapse;
6. causality / leakage / future-suffix / evaluator isolation / timestamp-knownAt / session-lunch / transition / reproducibility / regression checks pass;
7. the result is not driven by a tiny subgroup or a narrow session / symbol concentration.

If mean EntryPosition is `<0.15`, record stretch-target achievement. If it is `<0.25` but `>=0.15`, the candidate may still be frozen as `DEVELOPMENT_ENTRY_CANDIDATE_READY` and the research may proceed to EXIT when all other gates pass. The 25% gate MUST NOT be relaxed after results are observed.

## Research scope now authorized
The new version may use any feature family that is BOTH available in the approved Development substrate/repository AND causally known at the decision timestamp. Authorization is not evidence of availability: lineage, `knownAt`, and coverage must be verified before the family is decision-allowed.

Candidate feature families to inventory include:
- causal OHLC / price path and prefix geometry;
- multi-horizon returns, momentum and mean-reversion descriptors;
- opening gap and prior-close context;
- causal range, ATR-like and realized-volatility descriptors;
- bar-shape / candle-shape descriptors computed only from closed bars;
- original 9-State value plus State transition, dwell, persistence and churn history;
- the existing six Signals plus causal Signal history;
- time-of-day, session boundary, lunch and elapsed-active-minute context;
- market / sector / peer context only when its own point-in-time lineage is verified;
- price level, tick-size, liquidity / tradability descriptors only when known at decision time;
- point-in-time symbol profile fields already present in the repository/substrate;
- volume / turnover only where causal timestamp semantics and coverage are verified;
- Dictionary-derived descriptors only when their source fields and `knownAt` semantics are causal;
- other repository-resident Entry-time features that pass the same availability/causality audit.

New Signal logic, Volume, Dictionary context, market/sector context, liquidity context, learned Entry models and a State-overlay are allowed in this NEW research version. Frozen Selector, original State-v3 / 9-Pattern implementation, original six Signals, saved ONE_MINUTE implementation, and all prior Evidence remain immutable baselines.

## Absolute prohibited inputs
The following MUST NOT be decision features:
- future Low / High / Later High;
- MFE / MAE / Capture metrics;
- realized or future PnL;
- EXIT result or EXIT decision made after the Entry timestamp;
- future State or any state derived from suffix bars;
- post-entry bars or observations unavailable at `knownAt`;
- data filled by future backfill or interpolation.

Future evaluator quantities MAY be used as training labels only when explicitly documented as labels, completely isolated from feature generation, and evaluated through temporal/OOF separation. They MUST NOT enter real-time feature vectors.

## Data boundary
- Reuse the existing approved Development substrate. Provider requests remain 0.
- Do not open Common Holdout / REPORT19 / Validation / OOS / Fresh / Prospective data in this research stage.
- The 2,155 Opportunity set is outcome-exposed Development. It MUST NOT be described as Fresh, untouched OOS, or independent generalization evidence.
- Approved one-minute artifact lineage remains anchored to artifact `10732168448`, run `35818555587`, ZIP SHA256 `74ff0fb4398f9e2659109103ae73e8a6b27423aa0eb5aee7006c84312488aab8`; its stated expiry is 2026-12-22 and it MUST NOT be called permanent storage.

## Stage A — Feature Availability & Causality Matrix
Before any new all-material performance candidate is measured, construct and save a matrix with at least:
- family;
- concrete feature/source field;
- source script/file/artifact;
- source-stage lineage;
- decision timestamp / `knownAt` rule;
- required lookback;
- point-in-time coverage and missingness;
- decisionAllowed = YES / NO / UNKNOWN;
- leakage-risk reason;
- notes.

`UNKNOWN` stays blocked until evidence resolves it. Absence of evidence is not permission.

## Stage B — frozen transformations and finite search protocol
After Stage A, freeze a separate model-selection protocol BEFORE viewing new candidate performance. It must define:
- decision timestamps and candidate WAIT/ENTER decision grid;
- exact causal transforms per approved family;
- label definitions, with future evaluator labels isolated from features;
- finite model families;
- finite hyperparameter grids or fixed defaults;
- fold construction;
- candidate-selection rule;
- final integrated-candidate freeze rule;
- stop conditions.

Manual, result-following threshold sweeps or repeated feature-family additions until success are prohibited.

## Allowed finite model classes
Subject to repository/runtime support, the finite precommitted model protocol may include simple interpretable and regularized models such as:
- regularized linear / logistic models;
- fixed ranking or discrete-time hazard-style formulations;
- compact tree-based models with predeclared capacity constraints.

The model list, feature groups and hyperparameters must be fixed before new performance results are inspected. Learned models use causal features only.

## Development evaluation design
Prefer time-ordered / purged and session-grouped folds. When feasible use nested or otherwise selection-separated OOF predictions so model/HP/feature selection and evaluation are not performed on the same observations. If the Development history cannot support the intended split, record that limitation rather than weakening the split after seeing outcomes.

## Mandatory measurement
For the full 2,155 set and State slices report:
- N, Fill and Fill rate;
- Low→Entry price distance and active-time distance;
- Entry→strictly-later High;
- EntryPosition mean and median;
- <=10%, <=15%, <=25%, <=50% case rates;
- +3 / +5 Capture;
- 30m / 60m MFE and MAE;
- valid-N / unfilled / missing reasons;
- session / symbol / sector / time concentration.

Compare under identical semantics against Immediate, Entry v1, original State v3, and saved ONE_MINUTE. Separate aggregate effects from common-case paired effects. Keep costs and next-fill semantics fixed.

## Opportunity-preservation rule
Entry must not become a second Selector. WAIT is allowed; discarding Opportunities to manufacture a low EntryPosition is not. Any improvement accompanied by a material Fill/Capture/Opportunity collapse fails regardless of mean EntryPosition.

## Causality and integrity tests
A promotable Development candidate requires, at minimum:
- future-suffix mutation invariance;
- evaluator-feature isolation;
- timestamp / `knownAt` correctness;
- session / lunch boundary correctness;
- no future pivot / bottom / top dependence;
- no interpolation / future backfill;
- non-target / transition invariance as applicable;
- deterministic replay twice;
- focused tests + normal regression + dedicated CI.

## Progression rule
- Entry remains the only active component until the new Entry gate passes.
- If the gate passes, freeze the Entry candidate and only then re-read the latest accepted/Frozen EXIT baseline, contract and evidence before integrating EXIT.
- EXIT completion must be evidenced before Capital Allocation changes.
- Capital Allocation must use only causal sizing inputs, preserve LONG-only cash accounting / lot / cost / event-ordering contracts, and must not receive future Entry/EXIT outcomes.
- Final research chain: Frozen Selector → frozen new Entry → accepted EXIT → accepted Capital Allocation → Cash Equity Portfolio.
- No main merge, automatic promotion, paper/live trading or production update.

## Safety locks
`executionAllowed=false`
`brokerWriteAllowed=false`
`excelOrderWriteAllowed=false`
`rssOrderFunctionAllowed=false`
`liveTradingAllowed=false`
`paperTradingAllowed=false`
`automaticPromotionAllowed=false`
`productionUpdateAllowed=false`
`transmitted=false`

## Immediate next step
Build and freeze the Feature Availability & Causality Matrix from repository code and the approved Development substrate. Do NOT run a new all-material performance candidate before that matrix and the separate finite model-selection protocol are committed.