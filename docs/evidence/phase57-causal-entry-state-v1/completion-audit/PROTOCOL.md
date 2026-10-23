# 2026-09-21 completion audit / strict Daily ablation correction precommit

Audited base: 08e902c4ae8e23971a2b7f671e435fec91af5244, PR #587.
The requested v1 study already exists. Preserve its initial protocol, code, raw evidence,
reports and receipt byte-for-byte; do not retune paths, state thresholds or timing.

## Finding known before this correction
The original diagnostic INTRADAY excludes only keys starting DAILY/.
Six unprefixed features still require prior Daily prices:
dailyHighDistance, dailyLowDistance, dailyCloseDistance, fiveHighDistance,
fiveLowDistance, todayGap. Original ablation is therefore additional explicit
Daily context versus a Daily-contaminated reference, not zero-Daily versus Daily.
This is historical-input contamination of an ablation, not future data leakage.

## Locked additive correction
Use exactly saved measurement/checkpoints.json.gz from the audited base.
Rename the six keys above to DAILY/derived/<original-key> on both paired variants.
Reuse the original diagnostic function unchanged: same chronological 29/29
Development sessions, same five checkpoints, equal-prior nearest centroids,
fit-only imputation/scaling, missing indicators, class labels and tie handling.
No feature, threshold, model or hyperparameter selection; no timing changes.
Exclude all DAILY/ keys from strict INTRADAY and include all in PLUS_DAILY.
Require paired IDs and unchanged PLUS_DAILY predictions; fail if violated.
Write both variants, all checkpoint results and confusions, paired correctness,
majority-class reference, feature provenance audit and deterministic hashes.
Generate twice and compare bytes. Add focused tests for feature exclusion and
immutability. This is a correction after original results were seen; it is not
an untouched initial precommit and not independent OOS.

## Completion verification
Verify the original 714 pinned evidence files and implementation pins; rerun the
143 focused tests; confirm producer Actions run 35553422490 (execution SHA
4bb83f2e7f4cc73106f9cfd7a69cf96efe402b4c) directly. Preserve an additive Japanese
completion report with initial results and correction clearly separated.
Observed base-head Actions: 68 action_required; do not call PR green.

No new market data, Dictionary, Holdout/Fresh/OOS/Prospective, Entry training/freeze,
Selector change, EXIT/Capital/production change, trading or orders.
All nine safety flags remain false. STOP after completion audit.
