# Phase57 — NEW EXIT Zero-Base Research Contract R18

Date: 2026-09-25 JST
Repo: Iam-2squared/ark-terminal
Branch: research/phase57-long-only-cash-equity
PR: #587
Parent HEAD at preregistration: `1695e5721072dcad5ced63e74589e118ad363859`

## Controlling user direction

Entry research remains closed. Keep both frozen Entry policies unchanged:

1. `IMMEDIATE`
2. `ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF`

Dual Freeze remains `4878a1cc53430e816261dea0fb16aeb53b3c238d`.

**EXIT is restarted from zero.** `Fixed12` and `NEW_LONG_EXIT_PROTECT_3_TO_1_FIXED12_V1` / Candidate A are historical Evidence only. They are not comparison baselines, promotion gates, model inputs, search anchors, or targets for NEW EXIT. Do not spend future research budget reproducing or beating them. Preserve old files append-only.

R17 remains a factual record of old results, but its instruction to retain Fixed12/Candidate A as comparison baselines is superseded by this R18.

## Research thesis

The Frozen Selector selected opportunities for upside potential. The new EXIT must therefore not treat every post-Entry decline as a failed trade. Entry may occur during rise, reversal/rebound, or shortly before a local bottom/reversal. The EXIT problem is to decide causally, at each NOW, whether the original upside thesis is still alive, recovering, deteriorating, or broken.

Candidate conceptual decision states may include HOLD_CONTINUE, HOLD_RECOVERY, DETERIORATING/PROTECT, and EXIT_THESIS_BROKEN. These names are conceptual research framing, not pre-authorized policy thresholds.

Use only information known by EXIT decision NOW. Entry→NOW closed-prefix price/PnL/path, current State, State history/transitions/dwell/churn, Signal history/transitions/failure, and causally reproducible Pattern-v2 families may be investigated after lineage audit. Future State, future pivot, future High/Low, future MFE/MAE, final PnL, and oracle exit timestamp remain evaluator/label-only and must never enter a decision feature.

## Mandatory EXIT evaluation geometry

Future outcome geometry is evaluator-only. It must not influence an EXIT decision.

For each evaluable Frozen Entry, preserve the canonical ordered opportunity geometry and report:

- Opportunity move: ordered `Low -> strictly-later High`.
- Available post-entry upside: `Entry -> strictly-later High`.
- Realized EXIT move: `Entry -> Exit`.
- Upmove Capture Ratio: realized `Entry->Exit` move divided by available positive `Entry->strictly-later High` move, with denominator-zero/negative cases reported separately rather than coerced.
- Peak-to-Exit Giveback: strictly-later High relative to Exit under the preregistered price convention.
- Also retain net return after the frozen transaction-cost convention separately from raw geometric capture.

Do not credit a High that occurs after the actual EXIT ownership time. If a high-based evaluator metric intentionally describes the full opportunity suffix rather than owned path, label it explicitly as evaluator opportunity and do not call it captured.

### Mandatory opportunity-size buckets

Break results out by the canonical ordered `Low -> strictly-later High` opportunity range:

- <1%
- 1–2%
- 2–3%
- 3–4%
- 4–5%
- >=5%

For every bucket report at least:

- N and evaluable/missing/censored N;
- mean/median Low→High opportunity move;
- mean/median Entry→High available upside;
- mean/median Entry→Exit realized move;
- mean/median Upmove Capture Ratio, with denominator eligibility;
- mean/median High→Exit giveback;
- net-return mean/median, PF, win rate, p05/p10/worst;
- holding time;
- early-exit opportunity cost / late giveback where causally/evaluator-defined.

Report IMMEDIATE and ALL_MATERIAL R1 separately and a valid common-case paired view where identities and evaluator geometry are identical. Never compare different denominators as paired.

The historical Entry evidence recorded an IMMEDIATE ordered Low→strictly-later-High >=5% group of N=666. Preserve the exact canonical definition when reproducing this anatomy; do not assume a newly recomputed N is equivalent until lineage/hash matches.

## EXIT objective decomposition

Evaluate at least three distinct abilities instead of collapsing everything into win rate:

1. Winner continuation — preserve large upside while the rise/reversal thesis remains alive.
2. Profit retention — limit avoidable peak→exit giveback without mechanically clipping large winners.
3. Loss containment — identify genuine thesis failure while avoiding premature exits during a recoverable decline/reversal.

A policy that improves downside by destroying >=5% opportunity capture is not automatically successful. A policy that preserves winners but leaves catastrophic losses unchanged is also not automatically successful. Selection criteria must be preregistered before candidate performance inspection.

## Immediate next work — no candidate performance inspection yet

1. Re-audit canonical State-v3 9-state producer, six Timing Signal producers, Pattern-v2 feature producer/registry, and current 2,155 raw/path substrate.
2. Build `EXIT_FEATURE_AVAILABILITY_CAUSALITY_MATRIX_R18` with feature/family, producer, source, timestamp, knownAt, closed-bar requirement, coverage/missing semantics, post-Entry generation, EXIT-NOW legality, future-suffix dependence, and status `MODEL_ADMITTED / BLOCKED / EVALUATOR_ONLY`.
3. Explicitly distinguish Entry-stage admission from EXIT-NOW admission. A feature blocked at Entry may become legal only if its required observation is already in the past at EXIT NOW and lineage is proven.
4. Do not infer full-2,155 admission from the 3,800-event information exporter or old 277 subset. Current R3 source audit says directly causal prefix evidence exists for range6Pct, lastCloseLocation, lastUpperWickFraction, turnover6Jpy, but exact Frozen-2,155 join/admission was still pending; inherited relativeVolume5/directionalVwapDistancePct and PIT/context families remain blocked until lineage proof.
5. After the matrix, freeze the EXIT evaluation scorecard and finite candidate/model/feature/label/search protocol before inspecting NEW EXIT performance.
6. Then run Development-only temporal/purged/session-grouped research and causal sequential replay for both frozen Entry arms using the same EXIT semantics.

## Data and safety boundary

The 2,155 Opportunities are outcome-exposed Development, not Fresh/OOS. Do not newly open Common Holdout, REPORT19, Validation, OOS, Fresh, or Prospective. Provider new acquisition remains 0 unless separately authorized. No future/backfill interpolation, fabricated fill, outcome-based complete-case filtering, Entry retraining, or result-following unlimited threshold/model search.

Evidence is append-only. Do not overwrite R11–R17 or failed trials. No force push, main merge, production, live or paper trading.

Keep all false:
- executionAllowed
- brokerWriteAllowed
- excelOrderWriteAllowed
- rssOrderFunctionAllowed
- liveTradingAllowed
- paperTradingAllowed
- automaticPromotionAllowed
- productionUpdateAllowed
- transmitted

## Checkpoint discipline

Every GitHub checkpoint must record current HEAD/basis, completed work, numeric results when available, Freeze state, exposure boundary, Safety state, blockers, exact next work, and superseded controlling documents. GitHub alone must be sufficient to reconstruct current state and direction.
