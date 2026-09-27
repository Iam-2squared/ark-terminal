# Phase57 R51 — R50 changed-exit Failure Anatomy and separation verdict

Saved: 2026-09-27 11:37:41 JST. Basis: research HEAD `7db166457a07399225784e0447618168662d11ad` (PR #587, Draft). This is Development-only post-result diagnosis, **not** an EXIT Precommit, replay, candidate, or selection.

## Source identity and scope

- R50 frozen protocol SHA256: `011b4959bf7cd343694f44e2986d13d87c07b6fa238dc326f5273e86885afe18`; execution SHA `cc7d6c6e836b913607def00c0eeb1c155b2ab600`.
- Required CI run `36287866189` SUCCESS (37 tests); replay run `36287943625` SUCCESS; artifact `10921995049`, ZIP SHA256 `1868b407b4650144c45b5d0b3bf0a9a59a93179614e0b1c856fe0b4a26c2adaa`.
- The case extractor verifies the A/B byte-identical candidate ledgers and R45 feature/prediction hashes before joining by **Entry arm + Entry ID + exact decision NOW**. R45 decision feature matrix contains 656,247 rows; joined here only at 64 selected checkpoints. No future suffix or evaluator field was passed into an EXIT decision.
- Selection of cases by `POST_ENTRY_UPSIDE_GE5` and positive/negative delta is strictly evaluator-only. Primary support remains IM 222 / R1 200. `CANONICAL_L2H_GE5` IM 387 / R1 381 is distinct.
- Changed economic exits: A versus terminal-control B at a different executable price, not merely a different clock time with identical price. The full reproducible case-level output is in `R51_POST_R50_CHANGED_EXIT_ANATOMY.json.gz`, produced by `scripts/phase57_r50_changed_exit_anatomy_r51.py`. Outcome columns in that output are evaluator-only and explicitly denied to any subsequent decision module.

## Paired result

| Arm | Changed | A improves B | A worsens B | A premature among changed | Median delta net |
|---|---:|---:|---:|---:|---:|
| IMMEDIATE | 32 | 23 | 9 | 10 | +4.056pp |
| R1 | 32 | 21 | 11 | 9 | +3.465pp |

The two arms share 22 changed Opportunities (15 improve in both, 7 worsen in both, 0 discordant); 14 of those share the exact decision minute. There are only 42 unique changed Opportunities, so the arms are **not independent replications**.

## NOW-known features at the Harvest checkpoint

All 64 checkpoints were fresh with complete owned prefix and non-null certified MFE/giveback. This removes incomplete-prefix/missingness as an observed separator in this selected set. The listed extrema and return values are known only through NOW; later best High and post-exit outcomes appear only in evaluator fields.

| NOW fact | IM improve / worsen median | R1 improve / worsen median |
|---|---:|---:|
| Current return | +2.274% / +1.539% | +2.449% / +3.128% |
| Certified MFE | 6.600% / 4.876% | 6.961% / 8.157% |
| Certified giveback | 5.782pp / 4.720pp | 5.583pp / 5.352pp |
| Time since owned peak | 23 / 26 active bars | 27 / 34 active bars |
| Bars held | 57 / 66 | 66 / 59 |
| Momentum5 | -1.357% / -1.898% | -1.205% / -1.058% |
| C score (diagnostic) | .316 / .313 | .304 / .297 |
| D score (diagnostic) | .354 / .360 | .368 / .355 |

The directions for current return, MFE, bars held, and momentum differ by arm or overlap strongly. C/D are uncalibrated diagnostics, not Harvest authorities. `failedRecovery`, `stateRecovery`, `newPeak`, and `signalRecoveryN` are zero at all 64 triggers by the existing lifecycle priority. `signalTrueN` has median zero, `signalFalseN` median five, and CONTINUATION/RECLAIM FALSE history medians three/five/ten on both outcomes; UNKNOWN remains distinct from FALSE.

State transitions overlap: `DROP→DROP` is 14 improve/5 worsen (IM), 12/5 (R1); `PULLBACK→PULLBACK` is 6/3 (IM), 5/4 (R1). DROP or negative PnL alone therefore cannot separate or authorize SELL.

The strongest descriptive Pattern association was already admitted causal `STRUCT/Hrising`: value 1 at 12 improve/1 worsen IM and 13 improve/3 worsen R1; value 0 at 11 improve/7 worsen IM and 8 improve/8 worsen R1 (one IM worsen has null). This is not a clean separator: an `Hrising==1` Harvest condition would leave many successful Harvests unacted upon while retaining failures. Among the 22 common paired Opportunities, the IM-side values are 10 improve/1 worsen at 1, and 5 improve/5 worsen at 0 (one null worsen). Fold cells are small, and the two arms reuse much of the same underlying path. These are observed associations, not a validated causal decision rule.

## Gate-relevant bound, evaluator-only

The following **non-executable diagnostic** takes the higher observed Capture of the *two already frozen R50 policies* per case. It is not an oracle EXIT candidate and must never be implemented as a decision rule:

| Arm | Primary n | R50_A cases at Capture ≥50% | R50_B cases at ≥50% | Either A or B at ≥50% | Median of per-case higher A/B Capture |
|---|---:|---:|---:|---:|---:|
| IM | 222 | 104 | 111 | 111 | 49.191% |
| R1 | 200 | 82 | 90 | 91 | 43.005% |

Even perfect ex-post gating *between these two fixed exits* does not reach the frozen 50% median-capture Gate. A new architecture would have to create causally supported exits in opportunities where A and B currently coincide, not merely veto failed A Harvests. The 64 changed-case comparisons do not establish a stable rule for those untouched terminal paths.

## Verdict and stop condition

**CAUSAL_SEPARATION_NOT_SUPPORTED** for a new, performance-blind, finite EXIT architecture from the present evidence. This does **not** assert that useful NOW information is absent, or that the descriptive Pattern association is zero. It means no reproducible, sufficiently discriminating, independently supported transition rule has been established that justifies promoting that association to an authority and addresses the frozen Gate. This is an evidence/identifiability limitation, not permission to relax R50 thresholds.

Accordingly no R51 EXIT Precommit, new candidate, implementation, required performance CI, finite replay, Final EXIT Freeze, or Capital performance replay is authorized in this Work. R50 remains 0 PASS / NO_SELECTION_STOP. The next research direction requires a new user decision and new performance-blind Precommit; no Fresh/OOS/Protected opening to resolve this.

## Exposure / Safety

The 2,155 Development Opportunities are outcome-exposed. R49's initial decode of 3,220 allowlist-external payloads remains disclosed (not used for training, decision, score, display, or tuning); this anatomy used allowlist-first R50 ledgers and R45 feature/prediction arrays only. New provider requests 0; Common Holdout/REPORT19/Validation/OOS/Fresh/Prospective/Protected opens 0; Entry and Selector unchanged. Safety9 all false. No main merge, force push, live, paper, production, or transmission.

