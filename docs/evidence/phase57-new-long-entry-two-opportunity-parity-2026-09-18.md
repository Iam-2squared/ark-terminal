# Phase57 NEW LONG Entry — Two-Opportunity Kernel Parity

Date: 2026-09-18 JST

Verdict: **NEW_LONG_ENTRY_TWO_OPPORTUNITY_KERNEL_PARITY_PASS**  
Architecture status: **TIMING_LOCATION_FROZEN_NOT_VALIDATED**

This is Historical Development / outcome-exposed parity evidence only. It is not Fresh/OOS validation and does not authorize production, execution, sizing, EXIT, Capital Allocation, Portfolio changes, 1m research, provider acquisition, or main merge.

## 1. Scope

Frozen candidate:

`Frozen LONG Selector -> INITIAL_ENTRY_OPPORTUNITY -> observe first completed 5m CLOSE -> [FIRST_BAR_CONTINUATION | DIP_REPRICE_OPPORTUNITY | UNKNOWN/BOUNDARY]`

No t10/t15/t20 recovery loop exists. Entry owns opportunity timing/location only. Quantity/notional remains outside Entry.

Source Entry Location Study: `a0a263ddc6abd83c9dca0b9f4bc2c86b9753b2bb`  
Frozen two-opportunity contract: `docs/evidence/phase57-new-long-entry-two-opportunity-contract-2026-09-18.md`  
Parity workflow input head: `63eadbd661e7959d0a96af46c38c69db80736250`

## 2. Implementation correction before parity

The first kernel draft could emit `DIP_REPRICE_OPPORTUNITY` after observing a dip close even when the next regular 5m OPEN reference was unavailable. That was stricter in the contract than in the implementation.

The kernel was corrected before parity:

- FIRST_CLOSED_DIP alone is not enough to emit a priced secondary opportunity;
- the causally contemporaneous next regular 5m OPEN reference must be observable;
- missing reference -> `SECONDARY_UNKNOWN`;
- session boundary -> `SECONDARY_EXPIRED_BOUNDARY`;
- secondary event now carries `referenceStatus=REFERENCE_OPEN` and `referencePrice`;
- HIGH/LOW, later bars and evaluator outcomes cannot alter the decision event.

This keeps the implementation aligned with the frozen contract rather than weakening the contract to fit code.

## 3. Deterministic parity run

GitHub Actions workflow:

`Phase57 NEW LONG Entry Two-Opportunity Parity`

Run: `35250519787`  
Job: `105301441720`  
Conclusion: **SUCCESS**

Focused kernel + replay tests:

- **15 / 15 PASS**

The full replay was generated twice independently in the same job. The following files were byte-identical between run A and run B:

- `summary.json`
- `ledger.ndjson.gz`
- `manifest.json`
- stdout summary

Saved artifact:

`phase57-new-long-entry-two-opportunity-parity-35250519787`

Artifact ID: `10508583428`

## 4. Identity / population parity

- Full first-anchor ledger: **2,743**
- Anchor identity SHA-256: `985218fd1520bde127a72e9b049dd5a1840d42a928e7e850ea4e3e4d7ed82121`
- Primary common 60m panel: **878**
- Symbols: **430**
- Sessions: **76**
- FIRST_CLOSED_DIP: **328**
- NO_FIRST_CLOSED_DIP: **550**
- Primary secondary reprice resolved: **328 / 328**

Primary state counts:

- `DIP_REPRICE_EMITTED`: 328
- `FIRST_BAR_CONTINUATION`: 550

Full first-close census also reproduces the Entry Location Study:

- FIRST_CLOSED_DIP: 580
- NO_FIRST_CLOSED_DIP: 1,327
- UNKNOWN: 836

Full kernel terminal states reflect missing/boundary semantics rather than imputing them:

- `DIP_REPRICE_EMITTED`: 541
- `FIRST_BAR_CONTINUATION`: 1,327
- `SECONDARY_EXPIRED_BOUNDARY`: 353
- `SECONDARY_UNKNOWN`: 522

Initial reference states:

- `REFERENCE_OPEN`: 1,907
- `UNKNOWN_REFERENCE_OPEN`: 483
- `EXPIRED_BOUNDARY`: 353

## 5. Dip-reprice parity

The kernel reproduces the already-exposed Entry Location evidence on the 328 primary FIRST_CLOSED_DIP anchors.

| Metric | Initial opportunity | Dip-reprice opportunity |
|---|---:|---:|
| Mean D30 downside | 2.8979566% | 1.8911423% |
| Common60 mean Remaining Upside | 1.6876404% | 2.4290977% |

Reprice buy improvement vs initial:

- mean: **+1.1184108%**
- median: **+0.8002433%**

Immediate-winner opportunity preservation:

- +3: **56 / 59 = 94.9153%**
- +5: **21 / 21 = 100%**

These numbers are parity reproduction, not new validation.

## 6. Artifact hashes

- `ledger.ndjson.gz`: `2286c023f6c53a2c73d67ad16eb51a57c8f2921cae0f749ada75e60af3f10002`
- `summary.json`: `48a1dbea20da43f6fd3882e9b8ae26aa8b6403518d3fe533b385c435fa83cba7`
- `manifest.json`: `c81dae9c4608373bbda20484034abbedb5362d01c92f08f9cbb9a45273a709f2`
- uploaded artifact ZIP digest: `64721ad1b8f7b348721956bcad41353fbe171d430b153f5d9abc6b6d59a95232`

## 7. Causality / responsibility audit

Decision inputs remain limited to:

- t0: Selector anchor identity, decision timestamp, Decision Price;
- secondary transition: first completed 5m CLOSE;
- priced secondary opportunity: next regular 5m OPEN reference plus missing/boundary status.

Confirmed zero:

- future HIGH/LOW in decision payloads;
- outcome use in decisions;
- Entry-owned quantity/notional;
- new model fit/prediction;
- Fresh/OOS access;
- provider requests;
- 1m research runs;
- EXIT evaluation;
- Capital Allocation evaluation;
- Portfolio evaluation;
- main merge.

All trading/write/promotion safety flags remain false.

## 8. Architecture disposition

The Entry timing/location research candidate now satisfies the frozen kernel parity gate:

1. full 2,743 anchor identity preserved;
2. primary 878 population reproduced;
3. 328 dip / 550 no-dip reproduced;
4. t0 output is future-independent;
5. one and only one first-bar secondary transition exists;
6. secondary opportunity requires an observable causal reference;
7. missing/boundary states remain UNKNOWN/EXPIRED rather than imputed;
8. no sizing, model, EXIT, Capital, Portfolio, Fresh/OOS or 1m leakage;
9. deterministic full ledger retained as a CI artifact;
10. dip-reprice metrics reproduce the frozen Entry Location Study exactly within the predeclared tolerances.

Therefore **do not mutate Entry timing/location further on the same exposed Development evidence**. The failed extra recovery-confirmation idea remains killed. The current architecture is frozen as a Development-supported candidate, not independently validated.

The next architectural question belongs to a separate downstream contract: whether Capital Allocation can consume the two available opportunity types under cash constraints without moving sizing responsibility back into Entry.

## 9. STOP boundary

For Entry timing/location itself:

**TIMING_LOCATION_FROZEN_NOT_VALIDATED**

No third timing rule, threshold search, recovery loop, 1m reopening, Fresh/OOS opening, EXIT tuning, Capital tuning, Portfolio tuning, Selector change, production promotion, or main merge is authorized by this parity result.
