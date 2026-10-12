# REBOUND Entry Hypothesis Lock R1

2026-09-23 JST / Development-only / precommitted before candidate replay.

## Evidence available before this lock

1. Prefix-only blind semantic review was frozen for 34 masked cases before sealed scoring.
2. Sealed score subsequently showed 34/34 exact agreement with the frozen REBOUND/RISE baseline labels. This supports contract implementation consistency on the stress sample; it does not make every shape visually strong.
3. The blind annotations identified many `WEAK_REBOUND` / boundary / degraded-data shapes, suggesting that the semantic category `partial rebound` is weaker than the operational claim `sufficient reversal confirmation to BUY immediately`.
4. After the semantic review was frozen, the original fixed T0 REBOUND cohort anatomy was inspected. Original State-v3 is identical to Immediate for T0 REBOUND and is far from the user's aspirational Low→Later-High EntryPosition mean < 0.15 target.

No candidate performance has been measured before this lock.

## Single unattended REBOUND hypothesis

ID: `REBOUND_CONFIRM_EXISTING_EVIDENCE_V1`

For opportunities whose original frozen T0 State is exactly `REBOUND`:

- suppress only the current `INITIAL_STATE_BUY` at T0;
- do not add a Signal, feature, learned model, price threshold, recovery threshold, volume input or fixed-time fallback;
- retain the existing six frozen Signals unchanged;
- retain the existing 5-active-minute State-v3 checkpoints unchanged;
- after T0, allow Entry at the earliest of:
  1. first existing frozen Signal trigger, or
  2. first later State-v3 checkpoint classified `RISE` or `SHARP_RISE`;
- a later `REBOUND` by itself is not a confirmation trigger for this candidate;
- if neither event occurs within the already frozen Entry window, record NO ENTRY.

All non-REBOUND T0 opportunities must remain byte/field-equivalent to the original State-v3 Entry baseline (apart from an experiment identifier stored outside the baseline record comparison).

This is an Entry-timing candidate only. The 9-Pattern classifier and its thresholds remain unchanged.

## Why this is causal

The decision uses only already frozen inputs available by NOW: State-v3 prefix classifications and existing six causal Signal outputs. Future Low/High, Later High, MFE/MAE, Capture, return labels and future suffix are evaluator-only and unavailable to the decision function.

## Precommitted comparison

Population: original 2,155 Development Opportunities, with the original T0 REBOUND cohort (N=192) as the target cohort. Compare candidate against original State-v3, Immediate and Entry v1. No post-result resampling or symbol/time filtering.

Required reporting for REBOUND target cohort:

- Fill / Fill rate / no-entry reasons
- EntryPosition mean, median and <=10/15/25/50% rates
- Low→Entry distance and active delay
- Entry→Later High remaining upside
- +3 / +5 Capture
- 30m / 60m MFE and MAE
- common-case paired EntryPosition, Low→Entry, price, delay and remaining-upside differences
- session/symbol concentration if the candidate appears favorable

## Acceptance / rejection rules fixed before measurement

The candidate can be retained as a provisional REBOUND component only if all of the following hold:

1. common-case paired EntryPosition mean improves versus original State-v3 (`candidate - baseline < 0`);
2. common-case paired Low→Entry distance improves (`candidate - baseline < 0`);
3. the <=15% EntryPosition rate improves versus original State-v3;
4. the <=25% EntryPosition rate improves versus original State-v3;
5. Fill-rate degradation is no worse than 2 percentage points;
6. +3 Capture degradation is no worse than 2 percentage points;
7. +5 Capture degradation is no worse than 2 percentage points;
8. causality / leakage / non-target invariance checks PASS.

The -2pp preservation tolerance is not chosen from this REBOUND outcome. It is inherited unchanged from the previously precommitted and accepted DROP/PULLBACK one-minute Development gate, to avoid inventing a new post-exposure tolerance.

The user's EntryPosition mean <0.15 remains an aspirational whole-Entry completion target, not a REBOUND-specific tune-until-pass gate. This single candidate is not allowed to mutate after results are observed. If it fails, REBOUND's unattended performance-hypothesis budget is consumed and the candidate is rejected/HOLD; do not try a second REBOUND performance rule automatically.

## Safety

Provider requests 0. Protected data opened 0. No Fresh/OOS/Validation/Prospective. No EXIT/Capital/Portfolio work. All trading/write/promotion flags remain false.
