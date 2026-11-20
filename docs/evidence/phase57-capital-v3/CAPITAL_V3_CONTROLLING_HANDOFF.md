# Phase57 Capital v3 — controlling handoff / cash-aware funded allocation

Saved JST: 2026-09-27T18:07:12.083353+09:00. Basis research SHA: `89ab75d7665818c3533963c486a6388d417067c2`. PR #587 Draft; no merge.

## Final disposition

**0/2 PASS; NO_SELECTION_STOP.** The existing R35 causal control remains the fallback, but is not renamed Capital v3. No Capital v3 Freeze, six-variant v3 portfolio, v3 daily return or newly selected Final EXIT exists. The R50_B forced-terminal hold is only a reproducible benchmark. The 2,155 Development Opportunities are outcome-exposed, not Fresh/OOS validation.

## Frozen identity and sequence

- Entry Dual Freeze: `4878a1cc53430e816261dea0fb16aeb53b3c238d`. Selector/Entry/candidate sets and thresholds unchanged.
- Performance-blind v3 pregeometry contract: `CAPITAL_V3_PREGEOMETRY_PRECOMMIT.json`. Geometry, 254-feature audit, exact numerical Gate were committed at `597752ccee71e8fefd7b2f15b8ccf3ae69ac7e34` before fits.
- CI preflight at tested SHA `404293f674f1c796f9204abcfec73ec69740e5dd`: run `36307624818` SUCCESS, artifact `10928320706`; 52 focused tests locally, CI source/feature checks, 0 fits and 0 funded performance.
- One finite launch at SHA `89ab75d7665818c3533963c486a6388d417067c2`: run `36307805922` SUCCESS; artifact `10927778687` ZIP SHA256 `d9c0731560fe8e63039dc563ec8c3af279b0e2a08df39745b9bcd63b677c0de7`.
- Exactly A logistic +5% probability and B ridge clipped 0–20% remaining upside, 2 arms × 4 expanding whole-session folds with 2-session purge: **16 fits**. Candidate C was dropped before performance because no independent causal utility contract was available. Models, imputing and feature names were fixed.
- `CAPITAL_V3_RESULT_MANIFEST.json` pins the complete CI result files, OOF predictions, four cash ledgers and independent attribution audit. The separate R1/R50 immutable source artifacts and their ZIP hashes are recorded there.

## Outcome-blind cash geometry

| Arm | Frozen candidates | Existing MAX3 funded | Funded share | True ranking contests | Known +5% support | Optimistic control-count enrichment ceiling |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| IM | 819 | 72 | 8.79% | 21 | 158 | 5.11× |
| R1 | 795 | 30 | 3.77% | 9 | 143 | 5.50× |

R1 control funded 18 and 12 positions in folds 1/2, and zero in folds 3/4 after an unresolved auction. The frozen fold Gate compares only the two control-informative R1 folds and reports the other two as unavailable. The terminal-hold benchmark returns cash at scheduled terminal, so it does not establish successful intraday recycling from a newly selected EXIT.

## Actual funded MAX3 results (24 sessions, 2025-07-22 to 2025-08-25; 35 calendar days)

| Arm | Rank | Funded / known | +5% hits | Hit rate | Enrichment vs all known Entry | Reach | ≥7.5% rate | ≥10% rate | +5% capital share |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| IM | Control | 72 / 72 | 26 | 36.11% | 1.847× | 16.46% | 20.83% | 19.44% | 34.64% |
| IM | CAPITAL_V3_A | 72 / 72 | 25 | 34.72% | 1.776× | 15.82% | 19.44% | 18.06% | 33.15% |
| IM | CAPITAL_V3_B | 72 / 72 | 27 | 37.50% | 1.918× | 17.09% | 20.83% | 20.83% | 36.60% |
| R1 | Control | 30 / 29 | 9 | 31.03% | 1.706× | 6.29% | 24.14% | 20.69% | 28.51% |
| R1 | CAPITAL_V3_A | 30 / 29 | 11 | 37.93% | 2.085× | 7.69% | 27.59% | 24.14% | 36.16% |
| R1 | CAPITAL_V3_B | 30 / 29 | 11 | 37.93% | 2.085× | 7.69% | 27.59% | 24.14% | 36.85% |

The +5% labels use the observed strictly later same-session best High relative to the frozen effective Entry price. Censored rows are excluded from the hit denominator. These future labels are evaluator-only; they never sized or bought a position. Both arms share underlying Opportunities and are not independent replications.

## Frozen Gate failures

- **CAPITAL_V3_A**: IMMEDIATE:hit_delta, IMMEDIATE:enrichment, IMMEDIATE:reach, IMMEDIATE:capital_share, IMMEDIATE:fold_noninferior, IMMEDIATE:fold_strict.
- **CAPITAL_V3_B**: IMMEDIATE:hit_delta, IMMEDIATE:enrichment.

The IM control is 26/72 (36.11%); A is 25/72 and B 27/72 (37.50%). B gains only 1/72 = 1.39 percentage points and 0.071× enrichment; frozen minima are +3 percentage points and +0.10×. R1 improves from 9/29 to 11/29 for both candidates but cannot override IM Gate failure. No fourth candidate, Gate relaxation or rescore was introduced.

## Causal miss anatomy and accounting

- IM Control: miss 132 of 158 known +5% candidates; exclusive reasons {"CAPACITY_FULL": 128, "LOT_INFEASIBLE": 1, "OTHER_CAUSAL": 1, "RANK_LOSS": 2}; unresolved at end 0.
- IM CAPITAL_V3_A: miss 133 of 158 known +5% candidates; exclusive reasons {"CAPACITY_FULL": 128, "OTHER_CAUSAL": 1, "RANK_LOSS": 4}; unresolved at end 0.
- IM CAPITAL_V3_B: miss 131 of 158 known +5% candidates; exclusive reasons {"CAPACITY_FULL": 128, "OTHER_CAUSAL": 1, "RANK_LOSS": 2}; unresolved at end 0.
- R1 Control: miss 134 of 143 known +5% candidates; exclusive reasons {"CAPACITY_FULL": 36, "LOT_INFEASIBLE": 1, "RANK_LOSS": 2, "UNRESOLVED_CASH_LOCK": 95}; unresolved at end 1.
- R1 CAPITAL_V3_A: miss 132 of 143 known +5% candidates; exclusive reasons {"CAPACITY_FULL": 36, "LOT_INFEASIBLE": 1, "UNRESOLVED_CASH_LOCK": 95}; unresolved at end 1.
- R1 CAPITAL_V3_B: miss 132 of 143 known +5% candidates; exclusive reasons {"CAPACITY_FULL": 36, "LOT_INFEASIBLE": 1, "UNRESOLVED_CASH_LOCK": 95}; unresolved at end 1.

Cash ≥0, 100-share lots and MAX3 were checked from the saved ledgers. The old control was reproduced byte-for-byte before candidate replay. R1 continues to carry `2025-08-04|36700|602` unresolved; no fictitious cash was released and no cross-session mark was inserted. The prior 24-session control endpoint audit still certifies 4 of 6 flat EOD curves; R1 MAX3/4 remain null after the unresolved position. Since v3 was not selected, no new six-way v3 asset curve, daily-return claim or funded Final EXIT analysis is authorized.

## Reproducibility qualification

CI versus local fixed-code 16-fit rerun produced different feature matrix and prediction byte hashes; cause has not been established. Maximum prediction deviation was 2.69×10⁻⁷ for A and 8.17×10⁻¹² for B. The **four funded MAX3 cash ledgers were byte-identical**, every funded identity and funded hit count matched, and both runs returned NO_SELECTION_STOP. Prediction-byte reproducibility remains **unproven**; this is an additional reason against selection, not permission to alter frozen rounding, features, targets or thresholds. Full per-arm differences are in `CAPITAL_V3_REPRODUCIBILITY_AUDIT.json`.

## Exposure, Safety and next action

Provider new requests 0. Common Holdout / REPORT19 / Validation / OOS / Fresh / Prospective / Protected newly opened 0. Existing R49 and superseded v0 allowlist-external decode history remains disclosed. Safety9 all false. No main merge, force push, paper, live, production, broker order, Excel order write or RSS order call.

Before a new Capital proposal, address numerical byte reproducibility and the R1 unresolved auction/valuation provenance without borrowing future marks. A future model/Gate or Final EXIT architecture requires a new performance-blind contract and data that have not already been used for this Development choice. Preserve this 0/2 negative result and its files append-only.

### Rebuild from pinned GitHub artifacts

```bash
python -m unittest scripts.test_phase57_capital_v3 scripts.test_phase57_cash_capital_r34 scripts.test_phase57_cash_portfolio_r37 scripts.test_phase57_capital_rank_v2
python -m scripts.phase57_capital_v3 --mode preflight --r1-records <R1 pinned entry-records.json.gz> --benchmark-ledger <R50 pinned R50_B_FAILED_RECOVERY-run-a.jsonl.gz> --out /tmp/v3-prefit.json
python -m scripts.phase57_capital_v3_audit --source docs/evidence/phase57-capital-v3/RESULT --r1-records <R1 pinned entry-records.json.gz> --benchmark-ledger <R50 pinned R50_B_FAILED_RECOVERY-run-a.jsonl.gz> --out /tmp/v3-audit.json
```
