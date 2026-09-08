# Capacity v2.2 pre-training semantics audit

Source audit run: 34214657195. Reused Development: 89 sessions / 1,780 decisions. No training, Validation, OOS, or new reserve labels were opened by this audit.

## Confirmed findings

The Frozen selector computes qualified = ranked.filter(remainingOpportunityScore >= minimum), then selected = qualified.slice(0, maximum). Qualified membership need not be a contiguous prefix of the Hybrid-score ranking. The v2.1 metric instead substituted Utility(Top frozenSelectedCount). This is a baseline identity bug in the capacity comparison, not a reason to rewrite the preserved v2.1 NO-GO.

Among 1,771 paired active decisions, 1,769 differ. Session-equal stored Frozen-selected Utility is 294.98333425 bps vs 240.27603043 bps for the same-count prefix (difference -54.70730382 bps).

| Layer | Absolute marginal mean (bps) | Prefix delta mean (bps) | Positive marginal but negative delta |
|---|---:|---:|---:|
| 6–10 | 193.46076163 | -25.85336657 | 1200 / 1777 |
| 11–15 | 155.72493060 | -21.04468716 | 1344 / 1777 |
| 16–20 | 113.85827794 | -21.04767062 | 1510 / 1777 |

These demonstrate target semantics mismatch: positive absolute opportunity does not imply quality-preserving expansion. Use D_K = U_K - stored Frozen-selected U for K=5,10,15,20. This includes the Top5 offset missing from simple telescoping layers when the baseline is not a Top5 prefix. Differences between adjacent D_K exactly recover adjacent prefix deltas; train direct D_K to match the actual comparison field. Four linear outputs replace three marginal outputs; inputs remain unchanged.

## Missing-label scope and costs

The source builder calculates per-symbol labels only for ranked.slice(0,20); its Frozen-selected mean also drops unavailable/outside-Top20 labels. Therefore the stored field is the available-case selected subset within that scope, NOT a verified full-selected-candidate mean. This limitation cannot be repaired from these checkpoints and is retained explicitly. Per-symbol denominator counts are not stored; equal-count weighted reconstruction identities fail on 246/274/298 decisions. Do not substitute algebra based on nominal layer sizes. Direct stored prefix differences are exact for the stored metric.

Labels use the next six available bars in the same session/AM-or-PM segment, maximum up/down excursion, minus 10 bps once per available candidate. The same cost cancels from relative targets. This is not executable trading return. Use common paired timestamp support, then equal session weighting. There are 3 Frozen ABSTAIN decisions, 6 additional active baseline-missing decisions, 1,771 complete paired decisions, and no missing features. Minimum rankedCount=24.

## Causality correction

v2.1 selected lambda from all three outer-held-out periods before making earlier-fold predictions. v2.2 nests lambda selection wholly inside each past training window. Each scale/coefficient fit is past-only. Mapping floor is fixed before all training (-10 bps); no future threshold selection, no expanded grid. Whole-session boundaries prevent the same-session +6 label horizon from crossing train/test. Preserve the original purge gap.

Algorithmic forward-only evaluation is not a fresh-data claim: the entire Development set has already informed research. Validation/OOS remain sealed even if Development passes. All old numerical gates remain unchanged and apply against the corrected cached baseline; every outer block must also preserve -10 bps.
