# Phase57 Entry: Historical Inventory / Protection Allocation Freeze

As of 2026-09-08. Metadata-only research. **PARTIAL INVENTORY / FINAL ALLOCATION BLOCKED.**

The protection policy is frozen; a complete Historical Inventory and final Entry Development / Validation / Untouched OOS allocation are NOT completed. No sealed data was opened to fill missing governance evidence. No Hybrid→P21 baseline measurement or new Entry model was run.

## Git scope

Main audited: `899d16b808dba0d5b2003228a5f46332b3a3ce09`.
Branch: `research/phase57-hybrid-p21-entry-baseline`, Draft PR #579.
Parent head: `5c4894dc1f742bc08d911047a5df0c05a32dbf0b` (1 ahead / 0 behind main before this commit).
Parent CI: all three successful; new-head CI must be checked separately.
No merge/rebase, main write, Ready transition, auto-merge, Selector change or trading execution.

Legacy Entry #572 remains separate at `435466c49cf2de7915ec9fa530b7d0f98db914ad`.
Selector Closeout governance was read at #578 `63edf641f871be20cbd8518cec44392d12e74b16`.
Frozen Hybrid pins remain model digest `444e296d31b0e59263f268706b4c8a7c7e9e59d6f7c9547e9f90342a24040fc2`, freeze `a744d599e430d23efe4dea6600e418d3410d8a18df5055b35e1cc71432bf64da`.
This audit checks metadata pins; it does not recompute the model or revisit Selector outcomes. The research Selector is not claimed to be deployed on main.

## Evidence domain and counting

The JSON inventory is normalized: each session row joins to its dataset and governance profile. This supplies session identity, source class, source/manifest hashes, research statuses, tri-state usage/view flags, eligibility, seal references, purposes and an information-class cross-research matrix. `null` means unknown, not false. `eligible... = false` means not authorized now, not necessarily permanently unusable.

| Discovered dataset | Enumerated identities | Dates / scope | Governance |
|---|---:|---|---|
| J-Quants Fresh120 Hybrid | 120 + 2 purges | 2024-10-01–2025-04-14; exact lists in source manifest | All three evaluation roles already opened; downstream hypothesis exposure |
| Fresh120 parent Capacity Reserve | 282 | Parent range 2025-04-15–2026-06-11 | 89 opened + 190 protected + 3 purges |
| J-Quants source-validation registry | 8 | 2025-01-06–2025-01-17, specific registered dates only | Permanent source-validation-only exclusion |
| Entry Baseline candidate period | 17 | 2026-08-13–2026-09-04, exact list below | Already outcome-inspected Selector period; Hybrid→P21 measured 0 |
| Earlier Yahoo Selector dataset | Unknown exact session count | 2026-06-12–2026-09-04 | Already inspected; Baseline17 overlaps, do not add twice |
| Old Entry Quality v2 | Reported 16 candidate / 17 raw sessions | Same recent raw-period reference | Legacy regression; exact per-session Entry exposure not attested by reviewed metadata |
| P25 durable captures | 9 | Exact manifest session list, all within Baseline17 | No additional distinct dates |
| P25 pinned history | 190 reported; 38 per each of 5 symbols | Unique session-date list absent | NOT the protected190; do not count symbol-session observations as unique dates |
| EXIT v3/v4/v5, CAR1/Allocation archives | Unknown | Trees and durable references discovered | No complete information-level session exposure ledger found in reviewed metadata |
| Daily warm-up and recent automation reports | Unknown / not counted | Daily observations and artifact/run dates | Not automatically intraday sessions or prospective holdout |

**429 enumerated session identities is a lower-bound identity domain, not a repository-wide total.**
149 identities have explicit dates; 280 Reserve identities have only pinned parent ordinals.
Of the Reserve282, only first/last dates are materialized in the reviewed allocation metadata. Do not manufacture a calendar from weekdays or assume holiday/special-session membership.
The dated subset spans 2024-10-01–2026-09-04. The complete historical date range and total are unresolved.

693 branch names were enumerated to the end of pagination. Focused research and durable data trees were examined; this is not proof that every historical branch/archive has a complete usage ledger. No entire outcome archives were downloaded to obtain session dates.

| Status in the 429-identity domain | Count | Interpretation |
|---|---:|---|
| USED confirmed | 226 | Hybrid120 + Capacity89 + recent Selector-inspected17; includes hypothesis use |
| OPENED confirmed | 226 | Same known exposure groups; not a newly performed measurement |
| SEALED operational | 190 | Remains protected, even when global exposure is unknown |
| NEVER_OPENED globally confirmed | 0 | Zero certified, not proof that zero truly fresh sessions exist |
| UNKNOWN_GOVERNANCE | 203 | Protected190 + source-only8 + purges5 |
| Selector-used confirmed | 226 | Lower bound within enumerated domain |
| Entry-used / EXIT-used / Allocation-used globally | Unknown / Unknown / Unknown | Do not report missing ledgers as zero |
| Hybrid→P21 baseline measured | 0 | Unchanged |

USED and OPENED overlap. SEALED and UNKNOWN_GOVERNANCE overlap. These columns are not meant to sum to429. The mutually exclusive primary classification is226 USED_OPENED +203 UNKNOWN_GOVERNANCE.

## The actual protected190

Source: `predict/research/phase57-selector-closeout-data-use-manifest.json`, Git blob `b2542b627c14ac0ba3d3d960b164e6c7aaaa8da3`, at the pinned #578 head above.
Parent allocation SHA-256: `d92ce2c29daaacd419979847d62d093df9f7375c12483ab9c4d51130ac6efd41`.
Seal IDs in this inventory are references to the existing manifest groups, not newly minted cryptographic seals.

| Parent Reserve ordinal IDs | Sessions | Existing assignment | Current protection |
|---|---:|---|---|
| R092–R120 | 29 | Original Capacity v2 OOS | SEALED_QUARANTINED |
| R121–R149 | 29 | v2.1/v2.2 fresh Validation | SEALED_UNRELEASED |
| R151–R179 | 29 | v2.1/v2.2 fresh OOS | SEALED_UNRELEASED |
| R180–R282 | 103 | Remaining Reserve | SEALED in Selector/Capacity lineage |
| Total | 190 | No ownership transfer or release | All preserved |

Exact dates for each protected group are unresolved; they are contained within the parent 2025-04-15–2026-06-11 range. R282 is explicitly 2026-06-11. Do not label2025-04-15 as the first protected date: it is R001, in opened Development.
Original v2 Validation R062–R090 was already opened, then reused for Development; the sealed Validation is the different R121–R149 group.

The disjoint answer requested for protected190 is:

| Entry classification now | Sessions |
|---|---:|
| X: Development assigned/available | 0 |
| Y: Validation assigned/available | 0 |
| Z: Certified Entry Untouched OOS | 0 |
| W: Unavailable under existing Selector reservations, absent an authorized transfer | 87 |
| U: Remaining Reserve with unresolved cross-research governance | 103 |
| X+Y+Z+W+U | 190 |

W is not a claim of permanent unavailability. All190 lack a complete cross-research freshness attestation; W takes precedence over U only for this disjoint operational partition.
103 is a priority-conservation subset, not103 certified Entry OOS sessions. Nothing in this freeze releases any of the190.

## Cross-research contamination matrix

| Dataset group | Selector features / market | Selector outcomes | Entry information | EXIT information | Allocation information |
|---|---|---|---|---|---|
| Hybrid120 | Detailed exposure not separately attested | OPENED, reused for downstream hypotheses | Unknown | Unknown | Unknown |
| Capacity89 | Detailed exposure not separately attested | OPENED Development/Validation | Unknown | Unknown | Unknown |
| Protected original OOS29 | Unknown | Not opened in Selector/Capacity scope | Unknown | Unknown | Unknown |
| Fresh Validation29 + OOS29 | Structural admission already performed; exact information classes unresolved | Not opened in Selector/Capacity scope | Unknown | Unknown | Unknown |
| Remaining Reserve103 | Unknown | Not opened in Selector/Capacity scope | Unknown | Unknown | Unknown |
| Baseline17 | Legacy/reconstructed sources; exact exposure unresolved | Already inspected period | Hybrid-P21 0; old Entry use unresolved per date | Unknown | Unknown |

The inventory distinguishes MARKET_DATA, SELECTOR_OUTPUT, ENTRY_OUTPUT, FUTURE_LABEL, REALIZED_OUTCOME, SESSION_SUMMARY and separately known OUTCOME_SUMMARY exposure. A known aggregate outcome exposure does not establish that every feature/label file was viewed. Conversely, a statement that outcomes stayed sealed does not prove market data was never accessed during structural admission.

## Frozen role policy (no release)

A. **Baseline Diagnostic17** is reserved as `ENTRY_BASELINE_DEVELOPMENT_DIAGNOSTIC`, explicitly separate from model Development. It is not admitted for execution. The old precommit is preserved byte-for-byte; the new manifest clarifies only its allocation role and stronger no-measurement hold.

Exact A dates:

`2026-08-13, 2026-08-14, 2026-08-17, 2026-08-18, 2026-08-19, 2026-08-20, 2026-08-21, 2026-08-24, 2026-08-25, 2026-08-26, 2026-08-27, 2026-08-28, 2026-08-31, 2026-09-01, 2026-09-02, 2026-09-03, 2026-09-04`.

B. **Entry Development: 0 assigned, IDs `[]`.** Already-opened Hybrid120/Capacity89 may be considered later, but are not fresh evidence, nor automatically causally usable with the current P21 prior. No model-fitting permission.

C. **Entry Validation: 0 assigned, IDs `[]`.** No transfer from the existing sealed reservations.

D. **Entry Untouched OOS: 0 certified, IDs `[]`.** Preserve all190; prioritize conservation of R180–R282 for possible final holdout, conditional on governance and chronology. This is not a final OOS allocation.

E. **Prospective: policy only.** New sessions strictly after2026-09-08 default to protected candidates in this Entry line, pending an explicit dated allocation before outcomes. The policy does not stop existing autonomous pipelines or guarantee that their outputs stay unknown. Cross-research exposure must be checked. Final Entry design freeze and separate one-time release authorization are required before any OOS evaluation. No capture or automation was started or modified here.

Reusing the17-session Baseline for unlimited result-driven Entry tuning is not authorized. After eventual admission, retain one immutable descriptive report and append-only use history; never turn used sessions back into OOS.

## Chronology prevents an automatic historical-OOS claim

Reserve ends2026-06-11. The current Frozen P21 prior ends2026-08-12; Baseline17 begins2026-08-13. The current prior cannot causally be applied to the older Reserve. Historically reconstructed P21 methodology would be a different baseline class and is not authorized by this contract.

Further, later historical periods have already informed the research program. Even a truly unviewed older Reserve is not automatically a chronological future OOS for research performed on later dates. Protect it, but resolve the design chronology before calling it Untouched OOS. Prospective evidence may be needed; no sufficiency claim is made now.

## Metadata-only dataset value assessment

The J-Quants Fresh120 source manifest asserts PIT master lineage, sparse deterministic1m→5m reconstruction, raw unadjusted same-session intraday semantics and hashes. These are source assertions, not a new parity audit. They make it a potentially strong source reference, not fresh Entry test evidence after Selector use.
Remaining Reserve103 has high conservation priority due to its never-released Selector status; raw completeness, global exposure, regimes and Entry causal usability remain unverified. No raw request or regime computation was made.
Baseline17 is useful for limited diagnosis and infrastructure regression, not untouched testing. Durable9 has source lineage but narrow/partial capture coverage and overlaps17; it does not increase independent session count. Source-validation8 stays permanently excluded irrespective of quality. No performance-informed ranking of datasets was performed.

## Required next metadata and stop condition

1. Obtain the pinned Reserve282 ordinal-to-date mapping as a standalone metadata artifact, not by opening a market/outcome archive.
2. Obtain complete session/information-class exposure ledgers for Selector, Entry, EXIT and Allocation, including prior packs and externally retained archives; missing negative evidence remains UNKNOWN.
3. Resolve exact old Selector and Entry572 session membership, source fingerprints and permitted reuse without rereading outcome values.
4. Resolve ownership of the87 reserved sessions and chronological OOS feasibility. A future assignment must be outcome-independent and does not itself authorize opening.
5. Only then finalize B/C/D IDs and re-audit inventory completeness. Baseline execution still requires the previously recorded raw archive, prior-pack, adapter, cost and diagnostic blockers to be resolved.

**Do not measure the17-session Baseline next.** The highest-value next step is a metadata-only date/exposure ledger completion, not more candidates, fitting or performance computation.

## Audit, fingerprints and verification

SEALED content opened: **no**. Outcome newly viewed: **no**. Performance newly computed: **no**. Reserve sessions consumed: **0**. Hybrid/P21/model runs: **0**. Main changes: **0**.
This is an audit of this task's access, not a claim that unrelated external jobs made no reads concurrently.

All nine flags are false: executionAllowed, brokerWriteAllowed, excelOrderWriteAllowed, rssOrderFunctionAllowed, liveTradingAllowed, paperTradingAllowed, automaticPromotionAllowed, productionUpdateAllowed, transmitted.

Inventory SHA-256: `4287faa36ea9c35e649fb912c20119dcd6a2f2e4c4be65ec9aeca494362bcdb0`.
Allocation protection-freeze SHA-256: `288d723c9efcd334b571e6950dfb2e569423a11525071e928a2c575323f85d97`.
The companion checksum file pins exact JSON bytes. Do not rewrite these dated snapshots; correct them through a new, explicitly superseding artifact.

Offline checks: `node --test scripts/tests/phase57-entry-allocation-governance.test.mjs scripts/tests/phase57-hybrid-p21-baseline.test.mjs`.
The new governance tests read only the committed metadata snapshots, previous precommit and checksum file. Existing baseline tests remain synthetic regression tests, not historical measurements. CI is extended only to run these offline checks.

Bottom line: **historical ammo confirmed freely usable for Entry Development/Validation:0; certified Untouched OOS:0; protected and unconsumed:190, including103 priority-conservation Reserve.** Actual globally usable/fresh totals remain unknown. This preserves the data without pretending that the requested complete allocation has succeeded.
