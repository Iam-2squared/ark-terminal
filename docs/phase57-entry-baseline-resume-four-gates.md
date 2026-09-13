# Entry baseline resumption: four gates, no protected190 consumption

Audit date: 2026-09-09 JST. Audited main: `899d16b808dba0d5b2003228a5f46332b3a3ce09`.
Audited #579 head: `a95aca96c4d2c74f359e99b7228c9418997c8f19`.

**NO-GO for historical measurement.** The user explicitly decoupled the protected190 access-ledger issue from the separate 17-session diagnostic. This amendment permits admission work on the already-reserved diagnostic dates; it does not release a reserve session or erase old governance evidence. All190 stay SEALED/PROTECTED/UNKNOWN across research; confirmed CLEAN remains0. The original allocation and inventory files are immutable historical evidence.

The new role is `ENTRY_BASELINE_DEVELOPMENT_DIAGNOSTIC`, an explicit refinement of the original `ENTRY_DEVELOPMENT_DIAGNOSTIC`. Its exact17 IDs are copied from the original precommit, not generated from a calendar: August13,14,17–21,24–28,31 and September1–4,2026. They are already-inspected diagnostic dates, never new OOS or Prospective evidence. Legacy445 events are not the new population. No diagnostic date has been marked `BASELINE_DIAGNOSTIC_USED`.

| Gate | Finding | Admission |
|---|---|---|
| Market-wide archive |18 raw-file paths on4 dates in the examined automation branch;13 diagnostic dates have no raw path there. Contents were not opened. Other archive locations are not ruled out. Universe, bar availability, coverage and session/auction semantics remain unverified. |NO-GO|
| Exact causal prior |Canonical artifact9213298657 still exists and is unexpired; its archive digest and expected snapshot hash are separately pinned. No exact prior pack bytes, actual time bounds, horizon rows or selection/refit have been admitted and verified. |NO-GO|
| Hybrid→P21 adapter |20 synthetic contract tests pass. Uses unchanged feature feed; direct/mapped output-stage LONG,SHORT,ABSTAIN and missing-prior BLOCKED are identical. Eligible output tests use an explicitly synthetic cached bundle; they do not prove actual prior selection/refit or market-wide Selector replay parity. |PARTIAL, not full GO|
| Cost |Frozen before outcomes: existing EXIT v4 gross-minus0.05pct diagnostic convention; Entry and Capital contracts corroborate the5bps round-trip rate. |GO for contract only|

Machine-readable per-session findings, archive path/blob metadata, source identities and policy amendment are in `predict/research/phase57-entry-baseline-resume-four-gates-2026-09-09.json`. Null coverage means unmeasured, not zero market coverage. Date-boundary eligibility is17; fully admitted sessions and verified causal sessions are0; all17 are currently BLOCKED.

## Adapter boundary

`buildHybridP21Input` only maps validated input. It does not fetch data, execute the Selector, fit a model, call P21 scoring or generate labels. It requires exact symbol membership in the supplied frozen Hybrid selection, the pinned model/Freeze digests, matching selection/decision time, rank/score lineage, matching last-close price reference and a completed observed prefix. Missing volume, duplicate/unsorted bars, cross-session/symbol bars, outcome-bearing input and unavailable/incomplete bars fail closed. No interpolation or price adjustment is introduced.

P21 receives the existing feature feed's rows and unchanged options: horizons1/3/6/12/24,200 minimum training rows,50 minimum signals and the existing prior-only search space. Rank/Hybrid score stay outside Entry features. The adapter does not authorize source access; historical scoring remains subject to the original source-rights, PIT, corporate-action and coverage guards plus all four gates.

The existing P21 feed uses the last completed bar's **open timestamp** as its internal `featureCutoff`. The adapter retains that legacy key and exposes outer decisionT and actual context availability separately. It checks `bar.timestamp+5min<=T` and `availableAt<=T`; it does not claim that a completed bar's features were known at its open. Existing prior filtering remains at the earlier legacy cutoff. The legacy row string `prospective_completed_5m_ohlcv_prefix` is preserved for input parity and explicitly does not classify these later-fetched diagnostic data as Prospective evidence.

The synthetic output cache is confined to tests and clearly labeled `SYNTHETIC_NO_FIT`; no synthetic bundle is a production or historical prior pack. Actual prior-pack parity remains a gate, not inferred from these tests.

## Cost freeze

`ENTRY_BASELINE_COST_CONTRACT_V1` sets net directional return in bps to gross directional return minus5, once per available horizon label. Primary provenance is the unchanged EXIT v4 fixed-return subtraction. Capital uses half-rate on entry and exit notionals; that portfolio cash accounting is not asserted equivalent or copied. InternalP21 selection retains5bps independently. Selector utility10bps and paper per-fill slippage10bps are different contracts and excluded. There is no zero-cost default, no actual-fill/portfolio-return claim and no extra cost subtraction.

Gross>0 is hit; zero is neutral and stays in the observed denominator; gross<0 is miss. Cost-adjusted>0 is reported separately. Missing labels remain missing, never zero-filled. Event-level and first-entry opportunity metrics are separate; horizons are not additive trades. Cost selection used only existing source contracts, with no baseline outcomes inspected.

## Access audit and result status

This resumption pass read GitHub refs/PR/CI metadata, trees, existing governance JSON and implementation source. It did not download the canonical archive or open marketwide.ndjson/measurement.json contents. Protected190 newly opened0, new protected outcomes viewed0, new protected performance computed0. Historical17 raw contents/outcomes newly opened0, historicalP21 events scored0, labels generated0, measured sessions0. Only invented test inputs were used. Nine safety flags remain false.

All requested historical event counts, coverage, hit/positive rates, returns, MFE/MAE, timing, late/continuation/WAIT diagnostics, LONG/SHORT/time/rank breakdowns, label completeness, PIT, duplicates, regimes and ICC/effective n are **not measured**. In particular synthetic passing tests are not a historical PIT=0 certificate. Existing P21's accuracy and largest empirical weakness cannot yet be concluded. New Entry model research remains NO-GO.

Next highest-value step: obtain a metadata-only index for an isolated17-session market-wide archive and the exact pre-Aug13 prior pack, including actual member/date bounds, required/available universe, availability semantics and hashes. Validate scope first, then inspect only admitted inputs to finish raw/prior and real adapter parity. Do not request protected190 release or treat the earlier cross-research ledger search as a prerequisite. Run the baseline once only after all gates pass.

## Verification

Run `node --test scripts/tests/phase57-hybrid-p21-baseline.test.mjs scripts/tests/phase57-entry-allocation-governance.test.mjs scripts/tests/phase57-protected190-cross-research.test.mjs scripts/tests/phase57-hybrid-p21-adapter.test.mjs scripts/tests/phase57-entry-baseline-resume-gates.test.mjs`.

The tests exercise synthetic adapter parity and rejection cases, pin unchanged P21/cost source blobs, preserve original17 IDs and protected190 reservations, and verify immutable audit/cost hashes. CI performs these offline checks with no secrets, provider requests or historical measurement. Only #579 research files/workflow are changed; main, #572, Selector, Existing P21, EXIT and Capital implementations remain unchanged.
