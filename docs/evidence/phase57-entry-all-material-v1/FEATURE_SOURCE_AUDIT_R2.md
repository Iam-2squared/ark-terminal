# Phase57 All-Material Entry v1 — Feature Source Audit R2

Status: **PRE-PERFORMANCE SOURCE / KNOWN-AT AUDIT CHECKPOINT**

Parent protocol: `PROTOCOL_R2_UPSIDE_ABSTENTION.md`
Branch at start of audit: `research/phase57-long-only-cash-equity`
Parent HEAD after R2 protocol freeze: `276ae1fe144b9e8f91e74822587ca37b3c621b16`

Purpose: prevent field-name presence, downstream analyzer usage, or historical availability from being mistaken for point-in-time eligibility. A feature family may enter the learned Entry candidate only after its producer lineage, source timestamp, `knownAt`, join semantics, missing-value behavior and Development coverage are proven.

## 1. Audit status vocabulary

- `ELIGIBLE_CORE_R1`: carried from the previously frozen R1 causal matrix as a NOW-prefix family. R2 does not reopen its semantic definition.
- `CONDITIONAL_SOURCE_AUDIT_REQUIRED`: candidate material exists or is referenced in the repository, but this checkpoint does not yet prove complete PIT lineage/coverage. It must not enter performance modeling yet.
- `FORBIDDEN_DECISION_INPUT`: evaluator/future/post-entry information that can never be a decision feature in this phase.
- `UNAVAILABLE`: no admissible causal source exists under the current no-new-provider boundary.

A field is never promoted from `CONDITIONAL_SOURCE_AUDIT_REQUIRED` solely because a script contains its name.

## 2. Carried core causal families

These remain eligible only under their R1 prefix/closed-bar semantics:

| Family | R2 status | Required runtime constraint |
|---|---|---|
| closed OHLC path through NOW | ELIGIBLE_CORE_R1 | closed bars only; no suffix |
| causal multi-horizon price returns | ELIGIBLE_CORE_R1 | computed from available prefix only |
| gap / prefix range / realized-volatility transforms | ELIGIBLE_CORE_R1 | no later-day extrema |
| causal bar-shape transforms | ELIGIBLE_CORE_R1 | closed current/prior bars only |
| momentum / mean-reversion prefix transforms | ELIGIBLE_CORE_R1 | no future pivot/Low/High |
| current/prior 9-State, transition, dwell, churn | ELIGIBLE_CORE_R1 | only States already known by NOW |
| existing six Signal current/history | ELIGIBLE_CORE_R1 | only emitted/known Signals by NOW |
| time-of-day / session / lunch phase | ELIGIBLE_CORE_R1 | deterministic timestamp-derived |
| current price level | ELIGIBLE_CORE_R1 | decision-time observable |

This table carries R1 eligibility; it is not a claim that every derived column already has 2,155-row coverage in a new All-Material training table. Dataset construction must still report coverage and missingness.

## 3. Conditional repository materials requiring producer proof

Legacy/research code has referenced names in these families, including candidate fields such as:

- `priorDay20dVol`
- `priorDayTr5`
- `priorDayTr20`
- `priorDayVolumeShock`
- `t0AbnormalTurnover`
- `t0LiquidityLog`
- `marketReturnPct`
- `selectionHour`

`selectionHour` is conceptually timestamp-derived and may ultimately map to the eligible time family, but the concrete field's producer/join path still must be checked before reuse from an existing artifact.

| Family | Candidate fields/examples | Producer proven? | source timestamp / knownAt proven? | coverage proven? | missing/backfill semantics proven? | Status |
|---|---|---:|---:|---:|---:|---|
| prior-day volatility / TR | `priorDay20dVol`, `priorDayTr5`, `priorDayTr20` | NO | NO | NO | NO | CONDITIONAL_SOURCE_AUDIT_REQUIRED |
| volume / turnover shock | `priorDayVolumeShock`, `t0AbnormalTurnover` | NO | NO | NO | NO | CONDITIONAL_SOURCE_AUDIT_REQUIRED |
| liquidity proxy | `t0LiquidityLog` | NO | NO | NO | NO | CONDITIONAL_SOURCE_AUDIT_REQUIRED |
| market context | `marketReturnPct` | NO | NO | NO | NO | CONDITIONAL_SOURCE_AUDIT_REQUIRED |
| sector context | sector-relative/context fields, if present | NO | NO | NO | NO | CONDITIONAL_SOURCE_AUDIT_REQUIRED |
| tick size / tradability | PIT tick/tradability fields, if present | NO | NO | NO | NO | CONDITIONAL_SOURCE_AUDIT_REQUIRED |
| PIT symbol profile | prior profile / symbol metadata fields, if present | NO | NO | NO | NO | CONDITIONAL_SOURCE_AUDIT_REQUIRED |
| Dictionary descriptors | PIT Dictionary-derived descriptors, if present | NO | NO | NO | NO | CONDITIONAL_SOURCE_AUDIT_REQUIRED |
| existing artifact `selectionHour` | `selectionHour` | NO | deterministic concept only | NO | NO | CONDITIONAL_SOURCE_AUDIT_REQUIRED |

The conservative `NO` values mean **not yet proven in this R2 checkpoint**, not that the repository lacks the source.

## 4. Required promotion evidence for each conditional family

Before a conditional family becomes model-eligible, record all of:

1. producer script/module and immutable source artifact lineage;
2. raw source field(s) and source capture timestamp;
3. exact `knownAt` rule proving the value existed before the corresponding Entry decision;
4. as-of/session/symbol join logic, including lunch and cross-day boundaries;
5. no future interpolation/backfill and no use of final-day aggregates not known at NOW;
6. Development 2,155 coverage count/rate;
7. missing reason distribution and deterministic missing handling;
8. a future-suffix mutation or equivalent causality test for derived intraday fields;
9. confirmation that no sealed Fresh/OOS/Validation/Common Holdout/REPORT19/Prospective payload was opened to obtain it.

If any item fails, status stays conditional or becomes unavailable. Missing values must not be repaired with future information.

## 5. Forbidden decision inputs

The following are permanently evaluator/training-label-only or forbidden in the live decision feature vector:

| Field/family | Status | Reason |
|---|---|---|
| ordered future Low | FORBIDDEN_DECISION_INPUT | future evaluator / label only |
| strictly-later High | FORBIDDEN_DECISION_INPUT | future evaluator / label only |
| future MFE/MAE | FORBIDDEN_DECISION_INPUT | future evaluator only |
| +1/+2/+3/+4/+5 Capture outcome | FORBIDDEN_DECISION_INPUT | future evaluator only |
| realized/future PnL | FORBIDDEN_DECISION_INPUT | outcome leakage |
| EXIT result/reason | FORBIDDEN_DECISION_INPUT | downstream future outcome |
| future State / post-NOW State transition | FORBIDDEN_DECISION_INPUT | future path leakage |
| bars not closed by NOW | FORBIDDEN_DECISION_INPUT | timestamp leakage |
| backfilled/interpolated future values | FORBIDDEN_DECISION_INPUT | future repair leakage |

Future Low/high-derived labels may be used only as explicitly isolated training labels under the nested/OOF contract; they never enter X/features or causal abstention logic.

## 6. All-Material dataset admission table

Implementation must emit a machine-readable table with at least:

`family, field, producer, sourceArtifact, sourceTimestampRule, knownAtRule, joinKey, coverageN, coverageRate, missingN, missingReason, missingPolicy, futureSuffixTest, admitted`

No performance runner may silently admit a field not present with `admitted=true` in that frozen table.

## 7. Current disposition

- Core R1 causal prefix families may proceed to dataset implementation under their frozen semantics.
- Conditional volume/turnover/liquidity/market/sector/tick/profile/Dictionary families **remain blocked from model input until source proof is completed**.
- This audit does not consume any new Entry performance.
- No provider request or protected validation/OOS/Fresh payload is authorized.

Next research step: trace concrete producer/source paths for the conditional fields, then freeze a machine-readable admission matrix before learned-model performance is run.
