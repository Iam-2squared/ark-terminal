# NEW_LONG_EXIT_LOSS_DEFENSE_FAST_FAIL_KILL

Date: 2026-09-18 JST

Frozen contract: `phase57-new-long-exit-v0-loss-defense-contract-2026-09-18.md`

Workflow run: `35302812435`  
Job: `105468817706`  
Artifact: `phase57-new-long-exit-loss-defense-fast-fail` / ID `10529524968`  
Artifact ZIP SHA-256: `6b2039272faeb8a1c234a15591f6ed897e42d8c62cb33991f805dea6a6a0209c`

## Verdict

**NEW_LONG_EXIT_LOSS_DEFENSE_FAST_FAIL_KILL**

The threshold-free rule was implemented and replayed exactly once:

`HOLD -> first negative completed CLOSE -> DEFENSIVE -> while still below Entry, a lower completed CLOSE than the prior DEFENSIVE CLOSE -> EXIT at next regular 5m OPEN; Entry reclaim -> HOLD.`

No threshold was adjusted after measurement.

## Gate result

| Gate | Result |
|---|---|
| INITIAL +3 preservation >=90% | FAIL — 87.6404% |
| INITIAL +5 preservation >=90% | PASS — 91.0569% |
| DIP +3 preservation >=90% | FAIL — 86.9565% |
| DIP +5 preservation >=90% | FAIL — 85.1852% |
| 106 continued-drop mean-loss reduction >=10% | FAIL — **-2.1221%** relative improvement (worse) |
| 21 deep-drop mean non-worse | PASS |
| INITIAL own60 mean non-worse | PASS |
| DIP own60 mean non-worse | PASS |
| identity / safety | PASS |

## Overall own60 price-path result

| Cohort | n | Endpoint baseline mean | Policy mean |
|---|---:|---:|---:|
| INITIAL | 878 | -0.21556% | **-0.17083%** |
| DIP_REPRICE | 264 | -0.17896% | **-0.12113%** |

The rule improves the overall 60-minute mean price-path endpoint, but it does so while prematurely removing too many later +3/+5 opportunities. Overall mean improvement is therefore not sufficient for adoption.

## Continued deterioration — 106 identities

Frozen Fixed12 mean:
- **-1.48489%**

New policy mean:
- **-1.51640%**

Relative mean-loss reduction:
- **-2.1221%** (worse)

Signals:
- 93 / 106 = 87.74%

The rule fires frequently but does not solve the broader 2% continued-deterioration cohort.

## Deep drop — 21 identities

Frozen Fixed12 mean:
- **-4.00144%**

New policy mean:
- **-3.54656%**

Relative mean-loss reduction:
- **+11.3679%**

Signals:
- 20 / 21 = 95.24%

This is useful retained evidence: persistence of adverse completed CLOSEs contains information for the deepest deterioration cases. However, the same rule is too blunt for the broader population and kills too many winners. The 21-case improvement cannot rescue the architecture.

## Retained design lesson

Keep:

- stateful Loss Defense rather than `negative -> EXIT`;
- completed-bar persistence as a useful deterioration concept;
- Entry reclaim as recovery evidence;
- next-regular-OPEN causal reference;
- same rule across INITIAL/DIP for the first test;
- separate evaluator-only 106/21 cohorts.

Kill:

- **lower completed CLOSE vs previous DEFENSIVE CLOSE** as sufficient deterioration confirmation;
- any threshold tweak intended to rescue this exact rule.

The next Loss Defense architecture, if attempted, must be structurally more selective rather than a numerical retune. A natural next minimal hypothesis is a stronger **prior-bar range breakdown** condition: while DEFENSIVE and unreclaimed, require the current completed CLOSE to break below the prior completed bar LOW before signalling EXIT. This is a new structural condition, not a threshold adjustment, and remains PIT-safe. It is not yet contracted or measured here.

## Verification

- dedicated workflow: SUCCESS;
- causal/frozen-lineage tests: SUCCESS;
- evaluator generated twice with byte-identical summary, ledger and manifest;
- Selector changes: 0;
- NEW Entry changes: 0;
- existing EXIT runtime changes: 0;
- model fit/prediction: 0;
- Fresh/OOS: 0;
- provider requests: 0;
- 1m research: 0;
- Capital/Portfolio tuning: 0;
- main merge: 0;
- all trading/write/promotion flags: false.

This exact v0 Loss Defense rule is closed and must not be revived by threshold tuning.
