# Symbol Profile Coverage — final handoff

Source results: 4929b92aa8e678376b3f4ddb74316e88a5fab428.
Protocol and correction-spec precommit: 57309d22d1685be2f6bfe64297072452716b5056.
Read ci-result-precision-fix/result/REPORT-ja.md and ci-result-precision-fix/ci-receipt.json for measured results.

All 9 lane-USABLE and 23 calibration-only lane-WATCH verdicts receive full symbol coverage diagnostics at 20/60/250 snapshots. Primary window is precommitted 60. Per-symbol rows are in all-symbol-profiles.csv.gz; count distributions include lane, code union and intersection, deduplicating same trait IDs without pooling values. Representatives are selected deterministically by confidence and trait count, not outcomes.

HIGH/MEDIUM/LOW are new descriptive sampling-precision labels only. They neither change v0 Gates nor certify symbol-specific temporal reliability. Unknown peer-prior values are not manufactured. Episodes mean event-bearing sessions only when present; unconditional event-positive sessions are separate. A historical liquidity/price/volatility strata are recovered only from identifiable, held-out-validated linear identities in saved peer fits; any failed reconstruction stays UNKNOWN. Do not present these as current market attributes.

The archive union of daily and minute profiles is not a simultaneous current profile: endpoints differ. Validated Entry/EXIT handoff count remains zero due to time alignment, symbol temporal reliability, and Reader integration blockers. This does not imply all measured traits are useless.

Sparse handoff design: USABLE + HIGH/MEDIUM cells only in a candidate research payload; LOW/INSUFFICIENT abstain; WATCH goes to an explicitly non-dispatch research sidecar. Keep definition hash, units, transform, as-of/availability, reference period, nEff, posterior uncertainty, peer differentiation and drift. A missing/stale/mismatched Reader or endpoint blocks dispatch. Do not invent a dense all-trait vector.

Correction specification was frozen before new coverage results in correction-spec.json:
- new pullback registry candidate, unchanged v0; same contiguous phase/session, upward impulse followed immediately by confirmed downward correction, availability at confirmation, no cross-lunch pairing;
- explicit history adapter, canonical date and barValue schema;
- completed 5m bars only, expected current-phase endpoint equality, maximum 4-minute staleness; no missing-minute fill or stale fallback.
No correction implementation, new registry measurement, calibration fitting or Entry/EXIT development took place.

Next single step: implement/test only the bounded correction specification, then separately establish synchronized profiles and Development temporal confidence calibration. Once Dictionary+Reader become Development-usable, freeze their interface and in the next stage redesign NEW LONG Entry/NEW LONG EXIT, not minor modifications of the old pair. This condition is not currently met.

No new provider acquisition, Common Holdout244/REPORT19/Validation/OOS/Fresh payload opening, old Evidence overwrite, Gate relaxation, production promotion, main merge or trading. Prior exposure incident remains recorded. All nine Safety flags false. STOP after CI/evidence preservation.

Export precision revision: the first ci-result run rounded serialized floats to six decimal places, erasing tiny raw Amihud values in JSON/CSV. It is retained for provenance only. The canonical ci-result-precision-fix preserves native finite float values. Confidence classifications and count distributions are required to match the initial run exactly. Neither the precommitted protocol nor correction specification changed.
