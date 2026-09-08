# Phase57 Selector Research Closeout — Frozen Minimal Hybrid v1

Status: **CLOSED / FROZEN**. Current Phase57 Selector: **Frozen Minimal Hybrid v1**, unchanged. This is the user's current research-reference decision, not a main deployment or a claim that Hybrid dominates every objective.

Model digest: `444e296d31b0e59263f268706b4c8a7c7e9e59d6f7c9547e9f90342a24040fc2`.
Freeze SHA: `a744d599e430d23efe4dea6600e418d3410d8a18df5055b35e1cc71432bf64da`.
Both internal digests were recomputed and matched. Source file bytes were matched to PR #578's pinned remote Git blobs; existing model, Freeze, dataset ancestry and OOS report remain unmodified.

## Frozen Hybrid evidence

| Measure | Stored result |
|---|---:|
| Fresh Validation primary Utility | 213.91 bps |
| Untouched-at-evaluation OOS primary Utility | 223.14 bps |
| OOS same-capacity Utility | 226.03 bps |
| OOS median session | 224.21 bps |
| OOS positive opportunity sessions | 24 / 24 |
| OOS selected count mean / median / min / max | 5.195833 / 5 / 0 / 12 |
| OOS pre-selection movement | 798.39 bps |
| OOS late-detection rate | 95.5133% |

Hybrid is the Opportunity leader; V3 is the Early Detection specialist. Preserve this limitation. The original report explicitly records an opportunity/early-detection tradeoff and no single overall winner; this closeout does not rewrite it. Utility is a cost-adjusted two-sided excursion proxy, not actual profit, hit rate, or production readiness.

The user-supplied post-hoc rank-layer opportunities (204.93 / 150.76 / 116.65 / 93.48 / 64.03 bps for ranks 1–5 / 6–10 / 11–15 / 16–20 / 21–30) are retained with their provenance qualification in the JSON. Their originating diagnostic artifact was not independently reloaded here. They do not authorize capacity-rule changes.

## Capacity closeout

- v2: already failed its 29-session Validation; preserve that evidence and the sealed original OOS.
- v2.1: DEVELOPMENT NO-GO. 64 tuples, eligible 0. Count-qualified best increases 6.1625→8.33522727 (+35.2572%, +2.17272727), but Utility 244.55035503→233.72092414 bps gives -10.82943089 bps and worst fold -14.45976362 bps against the unchanged -10 floor. New Validation/OOS were not evaluated.
- v2.2: DEVELOPMENT NO-GO after target/baseline and forward-CV corrections. Count 6.1625→5.0000 (-1.1625, -18.86%); Utility 299.20→248.28 bps (-50.92); worst block -61.71; jumps 0%; all 880 held-out decisions Top5. No Freeze created. All original evidence remains.
- v2.1/v2.2 absolute Utilities are not directly comparable after the baseline semantics correction. Missing-label/top20-scope limitations remain.
- v2.3+: NOT STARTED. No more Capacity learning, threshold/grid searches, feature engineering, model iterations, gate relaxation or Development reoptimization. Existing workflows are historical evidence, not authorization to dispatch them. Related monitors are already paused; no active Capacity runs were observed.

## Correct data-use manifest

The request's blanket “Capacity v2 Validation = SEALED” is not historically true. Original v2 Validation was already opened, then incorporated into v2.1/v2.2 Development. Do not reclassify it as fresh.

| Reserve ordinals (original 282) | Role / present state |
|---|---|
| 1–60 | Opened Development |
| 61 | Excluded purge |
| 62–90 | Opened v2 Validation, now Development-only |
| 91 | Excluded purge |
| 92–120 | Original v2 OOS: SEALED / QUARANTINED |
| 121–149 | New v2.1/v2.2 Validation: outcomes SEALED; structural admission already performed |
| 150 | Excluded purge |
| 151–179 | New v2.1/v2.2 OOS: outcomes SEALED; structural admission already performed |
| 180–282 | 103-session remaining reserve: SEALED / UNTOUCHED in this research line |

Totals: 89 outcome-opened sessions, 190 protected non-purge sessions, 3 purges. Do not label structurally admitted periods as never accessed. Dates already published in Hybrid's earlier allocation remain in the machine-readable manifest; no new calendar/data query was made. Freshness must be cross-checked against other research lines before downstream use.

## Downstream responsibility

Next research chain: Frozen Hybrid v1 → Frozen Entry → selected EXIT → selected Capital Allocation. The selector ranks promising remaining-opportunity candidates. Cash utilization and sizing belong to Capital Allocation; do not weaken selection merely to fill capital.

End-to-end performance needs a separate ancestry/freshness contract. Previously evaluated Selector Validation/OOS cannot silently become untouched downstream data. The existing OOS evidence also records the identical Frozen J-Quants input adapter as pending. No downstream implementation, tuning or evaluation starts in this closeout.

PR #577 remains unchanged. PR #578 stays Draft as the Capacity evidence archive. No main merge/promotion, Lane Y, Entry, EXIT, Allocation, V3, Hybrid features, coefficients, ranking, or capacity-rule changes. All nine safety flags remain false.
