# Phase57 All-Material Entry v1 — Evaluator Extension R3

2026-09-24 JST / PR #587 / Development-only

## Purpose

All-Material Entry の model-selection 結果を見る前に、Entry 品質 evaluator を additive に拡張する。
この変更は Entry decision を一切生成・変更しない。Frozen Selector、original State-v3/9Pattern、
existing six Signals、accepted ONE_MINUTE の decision semantics は immutable baseline のまま。

## Canonical contract preservation

Canonical source is `scripts/phase57_state_conditioned_signal_entry_v1.py`.

Existing Capture semantics are preserved exactly for `+1/+2/+3/+5`:

- denominator: `selectorOutcome.mfeEnd >= k`
- entered candidate with `labels.mfeEnd >= k`: captured
- no Entry: `noEntry`
- entered but candidate outcome unavailable: `unknownEntered`
- entered below k: `belowThreshold`

`+4` is added using the same contract. The new evaluator asserts byte-structure equality of the
computed `+1/+2/+3/+5` Capture dictionaries against the frozen canonical `base.capture()` result.
A mismatch fails closed.

## Added evaluator-only views

For every evaluated policy:

- population / Fill / no-entry / Fill rate
- EntryPosition mean / median / distribution
- EntryPosition `<=10% / <=15% / <=25% / <=50%`
- Low->Entry absolute distance in `%` and `bps`
- Entry->strictly-later-High remaining upside in `%` and `bps`
- 30m / 60m MFE, MAE, returnNet
- `+1/+2/+3/+4/+5` Capture
- State split
- session / symbol / entry-clock concentration
- sector concentration only if sector exists in the record schema; otherwise explicit `UNAVAILABLE_IN_RECORD_SCHEMA`

Two future-evaluator-only stratifications are added:

1. cumulative selector-upside thresholds `>=1/2/3/4/5%`;
2. mutually exclusive selector MFE buckets `<1`, `[1,2)`, `[2,3)`, `[3,4)`, `[4,5)`, `>=5%`.

These strata may describe results only. They are forbidden as Entry decision inputs, learned online
features, ABSTAIN inputs, or post-hoc opportunity deletion rules.

## Why this is required

A normalized EntryPosition can look poor when total future opportunity range is small.
For example, Low=100, LaterHigh=101, Entry=100.5 produces EntryPosition=50%, despite only
50 bps Low-to-Entry distance. The extension therefore reports normalized position and absolute
distance side by side; it does not delete the `<25%` primary gate.

## Baseline replay targets

Dedicated CI re-evaluates, without provider calls:

- Immediate
- Entry v1
- original State-v3
- accepted ONE_MINUTE

The accepted ONE_MINUTE record file is restored from run `35818555587`, artifact `10732168448`.
Before use, all six recorded artifact file SHA-256 identities are checked, including
`entry-records.json.gz = de8ee035d2c2949e6ecbd5315d393de8794ca7d0e36ace49a6ccfe720a65a844`.

The ONE_MINUTE evaluator is executed twice and the deterministic JSON outputs must diff equal.

## Safety / interpretation

This is Development evaluator infrastructure, not a new Entry candidate and not Fresh/OOS evidence.
No provider acquisition, model fit, threshold selection, ABSTAIN selection, EXIT/Capital change,
main merge, paper/live execution, or production update is authorized by this file.

Safety flags remain all false.
