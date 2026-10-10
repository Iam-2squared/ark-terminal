# Phase57 Replacement Capital — controlling handoff

Status: **NO_SELECTION_STOP**. Experimental, previously outcome-exposed Development only. Frozen Selector/IM/R1 Entry and R50-A EXIT remain unchanged. Neither Capital v3-B nor R50-A became a formal Final selection.

## Immutable chain

| Stage | Identity |
|---|---|
| Prior seven-trade anatomy, 255-feature audit, two-candidate protocol, Gate frozen before new fits | GitHub commit `9277491b5ed37dd020d64da71b6856f12f8034ee`; protocol SHA256 `9ccf9b1a4673f0b63c38c44bdccf9f4096ec3760d461190d26b6c24e4d465d80`; feature audit SHA256 `166bd79694632a25ef93bca89549414d40f57bffaabb9c0b4f2bed7da704c195` |
| Preperformance CI | SUCCESS run `36315018356`, exact tested SHA `81e928c659947c32a95d457fb47b1145ca2a8c72`, 0 new fits in receipt, 69 synthetic and existing tests locally |
| Finite 16-fit/24-session Action | SUCCESS run `36315203748`, SHA `f0d4136cf53a55ef3aa398a259f83dc78342ca23`, exact tested source SHA256 `75f508afd7d81153ebf0a2b1299203cafb0794848d779b84ff11d3e6793574eb` |
| Action artifact | ID `10929589461`; ZIP SHA256 `ec38be66193021419c43638809be6cff6a4f3c7e3c874b39e61770ca9b05d302`; permanent append-only chunk copy in `RESULT/`, reconstruction and SHA in `RESULT/REASSEMBLE.json` |
| Data boundaries | 24 trading sessions, 2025-07-22–2025-08-25; Initial ¥1,000,000; MAX3 concurrent; cash LONG-only; 100-share lot; Safety9 false; provider requests 0; protected openings 0 |

`FAILURE_ANATOMY.json` contains all seven previous same-day early-EXIT replacements, 16 same-timestamp competitors, scores, Selector/State/Signals/Pattern/path features known at Entry, and separately tagged future outcomes. Old seven: 0/7 reached +5%, mean remaining upside 1.934%, median 1.787%. It informed structural hypotheses, never tuned the floor or Gate. `PRECOMMIT.json` and `FEATURE_AUDIT.json` were saved first. The two policies share strictly temporal Ridge magnitude and LogisticRegression P(remaining upside ≥3%) fits; Initial uses the exact saved v3-B prediction; Replacement uses the newly fitted ranking and a fixed P≥0.50 floor.

## Primary IM, same R50-A control

| Metric | Saved v3-B × R50-A | RC_MAG_FLOOR | RC_PROB3_FLOOR |
|---|---:|---:|---:|
| Purchases / confirmed exits | 79 / 79 | 79 / 79 | 79 / 79 |
| Initial / same-day Replacement purchases | 72 / 7 | 72 / 7 | 72 / 7 |
| Replacement ≥5% remaining upside | 0 / 7 | 0 / 7 | 0 / 7 |
| Combined ≥5% / ≥10% | 27 / 15 | 27 / 15 | 27 / 15 |
| ≥5% reach | 27 / 158 = 17.09% | 27 / 158 = 17.09% | same |
| Time-weighted utilization, valid minutes | 76.84% | 76.55% | 76.55% |
| Share of valid time utilization ≥80% | 58.29% | 59.12% | 59.12% |
| Full certified EOD Final Equity | ¥887,131.009125 | ¥889,179.47125 | ¥889,179.47125 |
| Portfolio Return | −11.2869% | −11.0821% | −11.0821% |

New IM Replacement upside: mean **1.901%**, median **1.787%**; <1% **2/7 (28.57%)**; 3–4% **2/7 (28.57%)**; 4–5% **0/7**; ≥5% **0/7**; ≥10% **0/7**. Its realized net mean/median were −6.417%/−8.914%, with confirmed PnL **−¥121,887.20**. The Initial cohort had mean/median 6.144%/4.101% and 27/72 ≥5%, with confirmed PnL +¥11,066.67. Combined 27/79 = 34.18% ≥5% and 15/79 = 18.99% ≥10%; combined <1% = 20/79 = 25.32%. The full Initial/Replacement/Combined ten-bucket tables, including upside mean/median, net mean/median, allocated capital and capital share, are machine-readable in the archived `*_buckets.csv`.

The replacement policies traded **two new identities for two former identities**, not two net new purchases. New identities had future upside 3.895% and 2.913%, and realized PnL +¥8,377.04; the displaced two previously funded identities contributed +¥6,328.58. Their net +¥2,048.46 explains the Final Equity change. Neither new identity was ≥5%, and no additional ≥10% Opportunity was reached. All seven new same-day Replacement purchases still contained zero ≥5% winners.

IM purchases/day were mean 3.29, median 3, p75 4, max 4. MAX3 is simultaneous occupancy; time at MAX3 was 87.86% of 7,800 scheduled minutes, so four daily purchases demonstrate slot reuse. Time-weighted utilization was 76.55% over 7,779 valid minutes (21 invalid), below the aspirational 80% target. Cash remained positive for 7,779 valid minutes; its equity-time share was 23.30% and mean amount ¥227,948. The one-shot idle classification counted 5,959 minutes after a high-quality Entry remained unfunded, 983 after floor rejection, 837 with no remaining Entry event. The first class includes capacity-bound events; it does **not** claim that cash alone could have bought a fourth simultaneous position.

IM +5% misses stayed **131**: 116 CAPACITY_FULL, 11 QUALITY_FLOOR, 2 RANK_LOSS, 1 INSUFFICIENT_CASH, 1 OTHER_CAUSAL. Previous v3-B × R50-A had 123 CAPACITY_FULL, 6 RANK_LOSS, 1 INSUFFICIENT_CASH and 1 OTHER_CAUSAL. Thus capacity-full decreased by 7 but the floor itself rejected 11 ex-post +5% opportunities; reach did not improve. Future outcomes are evaluator-only and do not enter the floor, rank, sizing or EXIT.

`REPLACEMENT_COMPETITION.json` records each eligible same-day post-EXIT event, all predicted scores, the funded identity and evaluator-only remaining upside. IM had 40 events with multiple candidates; post-replay pair ordering accuracy was 61.45% for magnitude ranking, 63.86% for P(≥3%) ranking. Nine missed +5% Entry events coincided with a Replacement position being held; this is a capacity co-occurrence diagnostic, **not** a unique causal estimate of opportunity cost.

IM Portfolio: 24/24 certified EOD, Final Equity ¥889,179.47, return −11.082%, EOD MaxDD −16.086%, PF 0.818, win rate 44.30%. Arithmetic daily return −0.3834%, median −1.2265%, geometric −0.4882%, positive days 37.5%; cumulative −11.082%. Full intraday MaxDD stays **null** due invalid intraday marks; 446/448 snapshots had valid equity. Potential mean remaining upside 5.768% → mean realized EXIT net −0.289% (diagnostic gap 6.056 percentage points); loser drag −¥607,770, confirmed sell costs ¥11,063, Replacement PnL −¥121,887, gross cash turnover ¥44.141m or 44.14× initial cash. Upstream buy-side costs are embedded in the frozen effective Entry price; no extra cost was invented. Potential/realized means are trade-weighted diagnostics and not an additive portfolio-return decomposition.

## Secondary R1 and null boundary

Both candidates bought 33 positions, 30 Initial plus 3 Replacement, with 32 confirmed exits and one unresolved terminal auction. Twelve funded positions reached ≥5%; 8 reached ≥10%; reach was 12/143 = 8.39%. Replacement mean/median upside 6.825%/3.652%, with 1/3 ≥5%, but realized Replacement PnL −¥11,663.02. Time-weighted utilization was 70.25% over only 3,232 valid active minutes of 7,800; 4,568 minutes lacked valid full-portfolio marks. Exactly 9/24 EOD sessions were certified; 15 remain null. Therefore full-period R1 Final Equity, Portfolio Return, full EOD MaxDD and aggregate daily mean/median/geometric return remain **null**. The 2025-08-04 unresolved auction cannot generate a sell fill, cash release or missing mark by assumption.

Independent attribution found one evaluator reporting bug: the original finite scorecard assigned 95 R1 misses to OTHER_CAUSAL even though an earlier unresolved position locked cash and the frozen protocol prioritizes UNRESOLVED_CASH_LOCK. `INDEPENDENT_AUDIT.json` preserves every archived reason and supplies the frozen-priority correction: R1 95 UNRESOLVED_CASH_LOCK, 33 CAPACITY_FULL, 2 QUALITY_FLOOR, 1 RANK_LOSS. This changes no purchase, prediction, cost, valuation or selection Gate.

## Reproducibility and selection

Two same-environment runs on the same source and input hashes had **byte-identical feature matrices, predictions, four ledgers and scorecards**. CI Action versus local Python builds had different feature/prediction bytes: maximal Ridge prediction deltas IM 1.07e−11/R1 1.76e−11, P(≥3%) deltas IM 0.00339/R1 0.01034. CI used Python 3.12.14 GCC, local used Python 3.12.14 Clang; NumPy 2.3.5 and sklearn 1.8.0 matched. The root cause of the feature-level delta is **not proven**. No event rank order, quality-floor membership, funded metadata, closed trade, scorecard or selection decision changed across environments. The raw ledgers differ because they include unrounded floating predictions. `INDEPENDENT_AUDIT.json` contains numeric deltas and identity checks; no rounding was used to pass Gate.

Both candidates failed frozen gates for Replacement ≥5% quality, Replacement median relative to Initial, High-Upside reach, time-weighted utilization gain, and added-trade ≥5% rate. **NO_SELECTION_STOP** regardless of their modest equity gain; 80% utilization was precommitted as a diagnostic target. No fourth candidate, re-fit, threshold change, Entry/Selector/EXIT change or fallback arm was introduced. Final EXIT remains unselected. The next research cycle needs a new performance-blind Capital precommit; the present 24-session Development results are already exposed and cannot support an independent confirmation claim.

## Reconstruct from GitHub

1. Checkout the controlling branch and inspect `PRECOMMIT.json`, `FEATURE_AUDIT.json`, `FAILURE_ANATOMY.json`, both Action runs and `FINITE_LAUNCH.json`.
2. Verify `RESULT/REASSEMBLE.json` and concatenate the three listed `.zip.partXX` files in order. Verify the full ZIP SHA256, then extract the complete finite Action scorecard, predictions, fold manifests, four ledgers, bucket CSVs, daily CSVs, curves JSON/CSV and PNGs.
3. Read `RESULT_ANALYSIS.json`, `REPLACEMENT_COMPETITION.json`, `INDEPENDENT_AUDIT.json` and this handoff. `scripts/phase57_replacement_capital_independent_audit.py` reproduces source/ledger integrity, fold hashes, cash/lot/slot, category reconciliation, and the frozen-priority R1 correction.

Safety9 remains false; provider requests 0; Protected/Fresh/OOS/Validation/REPORT19 remain unopened. Draft PR #587 only; no main merge, force push, live/paper trading, broker/Excel/RSS order write or production update. Historical R49/v0 allowlist decode exposure remains preserved in its original Evidence.
