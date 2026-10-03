# Phase57 NEW LONG EXIT Candidate C — Robustness FAIL / KILL

Date: 2026-09-18 JST
Repository: Iam-2squared/ark-terminal
Branch: research/phase57-long-only-cash-equity
PR: #587, Draft / unmerged

## Terminal disposition

**Robustness verdict: FAIL**

**Status: NEW_LONG_EXIT_CANDIDATE_C_KILL**

**Candidate C Freeze: NOT PERMITTED / NOT PERFORMED**

Preserve Candidate A's existing `DEVELOPMENT_CANDIDATE_FROZEN_NOT_OOS_VALIDATED`
artifact as the frozen fallback. This audit does not newly revalidate or promote A.
Stop here: no repaired C, threshold retune, routing change, Candidate D/E, Fresh/OOS,
1m research, model, Capital/Portfolio tuning, runtime integration, or main merge.

The historical Candidate C Development PASS is retained as evidence of the old
implementation and evaluator. It is not a valid final freeze authorization.
This terminal disposition takes precedence over that historical eligibility claim.

## Provenance and execution

- Policy/evidence source HEAD: `52c2a11b3f38b1f3d1e4146a0e42b18a0748beda`.
- Audited code HEAD: `eff1e7badd84d0afb1ac41bc28d14ae4b53571a8`.
- Original Candidate C Development run: `35313475902`, SUCCESS, preserved.
- New audit run: `35317600464`.
- New audit job: `105512584657`.
- New audit workflow: `.github/workflows/phase57-exit-cc-freeze-audit.yml`.
- Audit source: `scripts/audit_phase57_exit_cc_freeze.py`.
- Method: `docs/evidence/phase57-exit-cc-freeze-audit-method-2026-09-18.md`.
- Saved Development only: 76 sessions, 2024-09-17 through 2025-01-09.
- Opportunity identities: INITIAL 1,072 + DIP_REPRICE 397 = 1,469.

The method records that static issues were identified before this new batch audit;
it does not claim independent preregistration, Fresh validation, or OOS validation.
The existing A/B/C sources and contracts were not modified.

## Three failed gates

### 1. DIP +5 preservation fails when OPEN and HIGH ordering is respected

The legacy evaluator uses `exitBar >= firstHighTouchBar`. For a next-OPEN exit,
that can count a HIGH reached after the position has already exited in that bar.
The audit retains the old counts and separately computes time-ordered counts.
An equal-bar touch counts only if the exit OPEN already reaches the milestone.
Fixed12 remains a completed-CLOSE reference and retains its exact semantics.

| Cohort / metric | Legacy count | Time-ordered count | Existing floor |
|---|---:|---:|---:|
| INITIAL +3 | 314/314 = 100% | 314/314 = 100% | 90% |
| INITIAL +5 | 137/145 = 94.4828% | 136/145 = 93.7931% | 90% |
| DIP +3 | 102/106 = 96.2264% | 101/106 = 95.2830% | 90% |
| DIP +5 | 37/41 = 90.2439% | **36/41 = 87.8049%** | **90% — FAIL** |

The DIP overcount is one shared +3/+5 identity:
`2024-10-29|2024-10-29T09:30:00+09:00|55800`.
It signals EARLY_2_TO_0_EXIT on bar 4 and exits at bar 5 OPEN, gross
+0.08354218880535225%. Its first +3 and +5 HIGH touches are in bar 5.
Those later intrabar highs cannot be counted as preserved after the OPEN exit.

This changes no policy parameter and leaves the old Evidence intact.
It corrects the temporal interpretation of a measurement, not the strategy.

### 2. DIP implementation violates the frozen later-bar contract on 14 identities

The frozen Candidate C contract requires a later completed CLOSE after the +2
or +3 milestone is first observed. The reused Candidate B policy changes stage
and tests the CLOSE within the same loop iteration, allowing first-arm-bar exits.

Observed Development violations:
- +2 first-arm-bar signals: 5.
- +3 first-arm/promotion-bar signals: 9.
- Total: **14 DIP identities**.

Example: `2024-09-17|2024-09-17T09:30:00+09:00|40140`, DIP_REPRICE,
first +3 observation bar 8, EXIT signal also bar 8.

Synthetic probes reproduce direct +2, direct +3, and +2-to-+3 promotion cases.
The A control does not signal on its first +3 arm bar. No policy was repaired.
This is a contract-conformance failure; it is not a claim that observing a
completed bar's HIGH and CLOSE at its close necessarily uses future data.

### 3. INITIAL stored EXIT details do not match the selected route on 143 identities

Candidate C copies Candidate B's ledger rows, then changes `candidateCNetPct`
and the route label for INITIAL without replacing the nested `result`.

**143/1,072 INITIAL rows** have a mismatch in signal bar, exit bar, gross return,
or net return compared with the exact Candidate A route. The aggregate selected
route return reproduces the historical summary, but the nested EXIT record does
not consistently describe that return.

The audit creates a separately labelled effective-route projection for analysis.
It does not overwrite or repair the original C ledger or source.

## Statistical robustness results retained, despite final KILL

The original aggregate return values reproduce exactly within the audit's
1e-12 numeric comparison tolerance:

| Cohort | n | Candidate C mean | PF | p05 |
|---|---:|---:|---:|---:|
| INITIAL | 1,072 | -0.2632201808% | 0.7938803795 | -5.6078210265% |
| DIP_REPRICE | 397 | -0.1863755922% | 0.8198904263 | -4.5333906071% |

Both remain negative-mean and PF<1. These are not profitability or portfolio claims.

Chronological mean delta vs Fixed12, using the same 19-session blocks as A:

| Cohort | Block 1 | Block 2 | Block 3 | Block 4 | Nonnegative |
|---|---:|---:|---:|---:|---:|
| INITIAL | +0.017784pp | +0.108921pp | +0.180892pp | -0.057226pp | 3/4 PASS |
| DIP | -0.129198pp | +0.268567pp | +0.161393pp | +0.279429pp | 3/4 PASS |

DIP incremental mean delta vs A is positive in all four blocks:
+0.029404 / +0.099550 / +0.144804 / +0.056875pp.
INITIAL is exactly A at the effective-route level.

Top-three-frequency-symbol exclusion:
- INITIAL: exclude 67400 (21), 57590 (19), 89180 (18); n=1,014 remains.
  Mean delta vs Fixed12 +0.0282516912pp, vs A 0; PASS.
- DIP: exclude 48830 (6), 88940 (6), 218A0 (5); n=380 remains.
  Mean delta vs Fixed12 +0.1320230736pp, vs A +0.0658930698pp; PASS.
- Top-three frequency shares: INITIAL 5.41045%, DIP 4.28212%.
- Symbol HHI: INITIAL 0.0047738221, DIP 0.0050695075.

Evaluator-only adverse subsets, identity verified:

| Subset | n | A mean | C mean | Delta vs A |
|---|---:|---:|---:|---:|
| Additional drop >=2% | 106 | -1.4170068748% | -1.1697326613% | +0.2472742135pp |
| Additional drop >=5% | 21 | -3.6847352366% | -3.0618351345% | +0.6229001022pp |

All original Development numeric gates reproduce as PASS. The final KILL is
caused by the three integrity/causal-measurement gates, not failed chronological
or symbol-exclusion statistics. Numeric gains do not override these failures.

## Tests / CI

- New audit detector regression tests: **12/12 PASS** on repository sources.
- New audit executes twice into separate temporary directories.
- Summary JSON, detailed audit ledger gzip, and manifest: **byte-identical**.
- `git diff --exit-code` after audit: PASS; tracked inputs unchanged.
- Source blob/SHA256 pins and anchor/cohort identity checks: PASS.
- Fill-bar future H/L/C perturbation mismatches: **0**.
- Evidence upload: SUCCESS.
- Freeze gate: **FAIL**, intentionally enforcing the actual KILL verdict.
  Therefore audit workflow conclusion is FAILURE, not a green freeze result.
- Predict Tests run `35317600444`: SUCCESS, including offline regression and
  original Development artifact hash-preservation verification.

PR synchronization automatically triggered existing repository CI workflows;
none of the old research workflows was manually dispatched or rerun. The final
report/decision commit is documentation only and uses `[skip ci]` to avoid another
unnecessary replay. The audited code HEAD above remains the CI evidence anchor.

## Evidence

GitHub artifact ID: `10536065025`.
Artifact name: `phase57-exit-cc-freeze-audit-eff1e7badd84d0afb1ac41bc28d14ae4b53571a8`.
Artifact expiry reported by GitHub: 2026-10-18T07:03:28Z.
Archive contains the complete per-block mean/PF/p05 summary, all 1,469 audit rows,
all temporal/ledger findings, input/output pins, and the audit output log.

SHA256:
- ZIP: `d96114e05d4ba68f482caa643b5fb09546254e45e6a2432231a812ceb8f95cea`.
- Original summary.json: `3d8fde89ceb6560c7f1d7fca3bb180a464ed1252b14f5c1d9b33334d5bed94a4`.
- ledger.audit.json.gz: `590af2646ffbe14e49aed220da4894568fa047e88f1113c039bf3ce9c8ffb6ea`.
- Original manifest.json: `3e4b1fcd9526db7377ef7d978a04a6a5aef1633c2a1b70653226e31075b495d5`.

The downloaded archive digest and extracted output digests were verified locally.
A durable extracted decision receipt is stored separately at
`docs/evidence/phase57-exit-cc-freeze-audit/decision.json`; it is not mislabelled as
the byte-identical original summary. The audit is deterministically regenerable
from the pinned source/data and the audited code HEAD.

## Safety and stop

This audit changed no Selector, NEW Entry, A/B/C policy, existing EXIT runtime,
or pre-existing evidence. Fresh/OOS access, provider requests, model fit/prediction,
1m research, Capital/Portfolio tuning, main merge, and runtime promotion: **0**.

All nine reported trading/write/promotion flags remain **false**:
executionAllowed, brokerWriteAllowed, excelOrderWriteAllowed,
rssOrderFunctionAllowed, liveTradingAllowed, paperTradingAllowed,
automaticPromotionAllowed, productionUpdateAllowed, transmitted.

Candidate A's prior freeze artifact is preserved byte-for-byte, SHA256
`ba4ea0f8aa3a3c897f05936beb379e7388fba464665ac4b44edc12e36c2a2223`.
Its historical evidence is not silently amended and this report grants no new
validation or deployment approval to A.

**STOP. Candidate C KILL; Candidate A existing frozen fallback retained.**
