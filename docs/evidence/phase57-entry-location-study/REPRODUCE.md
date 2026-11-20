# Entry Location Study reproduction

This is an evaluator over the seven sources pinned in `protocol.json`, all from
already exposed Historical Development. It does not instantiate Selector,
Entry runtime, EXIT, Capital, Portfolio, a model or a price provider.

From the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest scripts.test_phase57_entry_location_study scripts.test_phase57_entry_location_audit -v
PYTHONDONTWRITEBYTECODE=1 python3 -m scripts.verify_phase57_entry_location_reproduction
node --test predict/tests/phase57-entry-location-study.test.mjs
```

The reproduction command creates a temporary output directory and compares all
11 generated outputs byte for byte with saved evidence. It never overwrites the
saved ledger. The original four-policy statistics remain unchanged; WAIT10 is
the user-requested fixed reference, not a fitted or promoted candidate.

`ledger.json.gz` has all 2,743 anchors, including missing or boundary entries.
`result.json.gz` holds distributions, subgroups, chronology and concentration.
`supplement.json.gz` holds subgroup chronology and symbol macro sensitivity.
The CSVs expose the paired table, all fixed-horizon distributions, original
Opportunity preservation, coverage and the 2D Entry Efficiency counts.

Two denominators must remain distinct:

- Earlier Timing-only capture: immediate reference OPEN winners within the
  common selection+60m window (+3: 267, +5: 123).
- Original Selector Opportunity: Decision Price winners. The common60 subset
  has +3: 296, +5: 141; available same-session observed full-ledger winners are
  +1: 2,055, +2: 1,619, +3: 1,212, +5: 609.

`original-opportunity-preservation.csv` includes both complete common60 and
same-session populations. An observed HIGH touch is known even on an incomplete
path. An incomplete path without a touch stays UNKNOWN. Boundary entries and
known losses are separate. No LOW or HIGH is used for timing decisions.

`denominator-and-window-audit.json.gz` also separates changes to D30 caused by
the purchase price from changes caused by moving the evaluation window. These
are descriptive identities, not a new optimization target. The 1e-10 percent
touch tolerance handles floating-point equality only; it is not an Entry rule.

The audit supplement was added during review of the existing local study. It
does not claim an outcome-blind preregistration or fresh validation. It adds no
policy or tuned threshold. Source pins, the original protocol and original
location aggregates are retained unchanged.

Stop after this evidence package. Claude Architecture Review and architecture
implementation are separate, unperformed next steps.
