# Frozen Hybrid v1 + Existing P21: preflight and measurement foundation

Status: **NOT MEASURED / admission blocked**. Unit-test results are synthetic, never Entry performance.

## Impact audit (2026-09-08)

Latest main at inspection: `899d16b808dba0d5b2003228a5f46332b3a3ce09`.
Entry #572 remains Draft at `435466c49cf2de7915ec9fa530b7d0f98db914ad`, 36 ahead / 29 behind main, with GitHub reporting not mergeable. Preserve it for legacy infrastructure regression. Do not merge/rebase it.
Use a separate `research/phase57-hybrid-p21-entry-baseline` branch from the inspected main. It contains only new offline helpers, contract, documentation and tests. No Hybrid or P21 implementation is re-created or copied into runtime.

Selector closeout is on #578 at `63edf641f871be20cbd8518cec44392d12e74b16`, not deployed on main. #577 remains Draft/unmerged at `c70cb168358b1aedd9785a18ca76fde1832d7a53`. The closeout is a research-reference designation, not production promotion.
Both supplied Hybrid core digests were independently recomputed from the pinned model and Freeze JSON, omitting only the respective digest property, using the original JSON property order. Both match. File-byte hashes differ from internal object digests; Git blob pins are retained in the contract. No model inference, fitting or mutation was performed.

## Dataset allocation

The closeout manifest reports Hybrid's original 72 Development / 24 Validation / 24 OOS sessions as already opened. Original Capacity Validation is also USED, not sealed. Capacity has 89 opened sessions, 190 protected non-purge sessions and three purges. None is released by this work.

Precommit the already-inspected 17-session raw-market window 2026-08-13 through 2026-09-04 for **Entry Development diagnostics only**, subject to source admission. Include 2026-08-14; do not remove a session because old P21 produced no candidates. These are not yet 17 measured Hybrid sessions. Rebuild all Hybrid selections from the market-wide archive; the old 445 P21 candidates and 397-symbol selector scope are not the input universe. Original Hybrid Validation/OOS and Capacity datasets are not allocated to this measurement.

The 2025 Hybrid OOS cannot use the current 2026-08-12-ended P21 history pack. Prior filtering must never be bypassed. A genuinely date-appropriate reconstructed P21 methodology is a separate baseline class and would need a separate contract, not a relabeling of this baseline.

Historical bars fetched in 2026 may support causal replay but are not prospectively captured evidence. Preserve original source classifications in ancestry; downstream later-fetched data remain non-prospective and are not untouched OOS. Date-specific master and provider revision limitations must carry forward.

## Implemented foundation

- Recompute and check exact Hybrid model/Freeze internal digests.
- Fail-closed admission assertions for raw/source rights, fingerprints, source adapters, prior pack, corporate-action basis and cost contract.
- Event ledger separating ENTER, ABSTAIN and BLOCKED. Invalid input is not an abstention.
- First ENTER per symbol-session as a stateful opportunity, without hypothetical fills, EXIT or state resets. Repeated same-direction and opposite-direction events remain in the event ledger.
- Feature-prefix fingerprint; completed bars and future-field rejection; separate future-only LONG/SHORT labels for +1/+3/+6/+12.
- Positive-return gross hits and positive-after-cost rates are separate; zero gross return is not a hit. Complete-label denominators and censoring counts are explicit.
- Directional return, MFE/MAE and first extremum bar-close time summaries.

This is not an end-to-end executable baseline. The ledger accepts already scored P21 rows; it does not call or simulate P21. Features passed to the helper require schema parity with existing PIT-safe feature builders before admission. Never pass outcome data as selector inputs.

Future-label grid semantics must be verified against the provider/session-calendar adapter, especially terminal auction bars and exchange schedule changes. Missing trading minutes must not be replaced by invented bars. Standard scheduled lunch is not a missing trading bar; labels may cross lunch within the same JST session. Extremum timing is bar-close resolution, not exact tick time. A final selection with no later observed event has unknown next-selection status, not a fabricated rejection.

## Costs and unresolved work

Existing P21 inner selection uses 0.05% = 5 bps; stored Selector utility uses 10 bps. Neither is silently adopted as the downstream Entry-outcome cost. The helper requires an explicit cost, and real admission stays blocked until the correct existing downstream cost source is pinned. No cost assumptions were changed.

Late-entry/continuation definitions, paired WAIT diagnostics, rank/time/session breakdowns, session regimes and ICC/effective n remain to implement and freeze before outcome reads. Conditional delayed-entry comparisons will be descriptive, not proof that a WAIT policy causally improves results. MFE is available opportunity, not realized capture. First-entry opportunities are not independent trades.

## Access and next step

This execution environment has no configured J-Quants key and no raw OHLCV/prior pack. This does **not** establish that the user's subscription or GitHub Actions secret is absent: the inspected Selector workflow references `secrets.JQUANTS_API_KEY`, and prior manifests record verified entitlement. Do not rerun old Selector/Capacity workflows: they include fitting or reserved-data evaluation outside this request.

Highest-value continuation: locate an authorized immutable market-wide archive and the exact existing P21 prior pack for the allocated window, or configure an Entry-only read-only acquisition route for those dates. Then verify unchanged Hybrid and P21 source adapters plus outcome-cost provenance before running all selection events. No sealed data access, new Entry model, real/paper orders, main merge, Ready conversion or automatic promotion is authorized.

All requested real baseline metrics are currently null/unknown, not zero accuracy. See the machine-readable precommit for the full blocked-state report. Main, #572, #577 and #578 are unchanged by this Entry foundation.
