# Phase57 EXIT v4 — Stage 1E Controlled ZIP Acquisition / Allowlisted Extraction

## Outcome

Stage 1E completed the explicitly authorized temporary whole-ZIP acquisition and extracted only the three pre-exposed sessions. The acquisition/extraction guards passed, all three container digests matched GitHub metadata, unapproved member content reads were **0**, and all three temporary ZIP copies were deleted after subset hashing and parity.

The final gate is **CONTROLLED_EXTRACTION_PARITY_PARTIAL**. The allowed Golden input proves exact MSH feature and state reconstruction with zero PIT violations, but it does not contain model-applied Entry decisions and it does not permit an independent full-universe Hybrid rerun. Consequently, `FULL_REPLAY_ELIGIBLE=0`, confirmed Tier 2 sessions remain `0`, and Stage 2 allocation remains locked.

No EXIT outcome, future label, protected session, Fresh Validation/OOS, or new J-Quants historical session was accessed.

## A. Governance change

| Item | Stage 1D | Stage 1E |
|---|---|---|
| Whole ZIP acquisition | Forbidden | Temporary `ACQUIRED_UNINSPECTED` permitted |
| Research inspection | None | Exact three-session allowlist only |
| Physical acquisition equals research access | Yes under old boundary | No; states are mechanically separated |
| Unapproved member content | Not acquired | Read/parse/extract/summarize = 0 |
| Temporary ZIP | N/A | Deleted after hash and parity |

This is an explicit governance change. It does not authorize research use of the other sessions physically present in the artifact containers.

## B. Frozen extractor and pre-download dry run

| Item | Result |
|---|---|
| Freeze commit | `cdfcf0e566e8edf98294f1a5ae8ae817ee21f57e` |
| Extractor SHA-256 | `73e5c0a67bcfe335fa72e0a48c8f41965f6d6e41d2709b0b8032940b6d87e019` |
| Config SHA-256 | `b5117c4c3115a564414c3cf53948d19e8f284bedbd5642c35628b5d00bd3e475` |
| Extractor test SHA-256 | `38724164b70e2d595619025115a14fa07c3fb4a7d2f9b307f9c6c2aa6523f43a` |
| Freeze record SHA-256 | `d9db8d2c9243e2928923af52824f41cd81f0e5eb409a99fa1f990e962d55cc69` |
| Synthetic ZIP dry run | 8/8 PASS before real download |
| Default deny / traversal / duplicate / nested archive | PASS |
| Synthetic unapproved content reads | 0 |
| EXIT import/invocation | 0 |

## C. Source artifacts

| Session | Run ID | Artifact ID | Container SHA-256 | Match |
|---|---:|---:|---|---|
| 2025-08-27 | 34355199082 | 10106663226 | `803b33bcc8f26acd4afbcea090215ef7e58214ad833206baf79cbaa367d18173` | PASS |
| 2025-10-09 | 34292703804 | 10082689099 | `a38749885f36f63a48d4b8b5b47f02aedc4b5b5a5c9ee10b83744c7ebedb1b3b` | PASS |
| 2025-11-25 | 34292703804 | 10084152060 | `72a9b97a913fe2b94aad4ef292bd6fcf172401d4b5252c7e7ddc7a379c425d03` | PASS |

Only these three artifacts were downloaded. No J-Quants endpoint or bulk endpoint was called.

## D. Allowlisted extraction

| Session | Approved members read | Unapproved content reads | Golden rows | Subset SHA-256 |
|---|---:|---:|---:|---|
| 2025-08-27 | 3 | 0 | 236 | `c0cdc56897ef8a22698949befea45a9019d8eccdc009f2ccd537796dfea27f89` |
| 2025-10-09 | 3 | 0 | 226 | `4c1934e78a169879b18718ea67b16f9adbb8c717b61418971a69c8a008cfe140` |
| 2025-11-25 | 3 | 0 | 325 | `98841946ab40fd7a3d1e6ba3f66b6d8cabf690736e7bcd82bda7bc601c787d08` |
| **Total** | **9** | **0** | **787** | 3 fixed hashes |

The extractor read only each date's `features.json.gz`, `bars.json.gz`, and `manifest.json`. It used ZIP central-directory metadata to identify members and did not manually unzip or scan archive contents. No prohibited outcome/future-label field was present or stripped in the allowed source members.

## E. Golden B trust

| Requirement | Result |
|---|---|
| Pre-outcome source | PASS — each manifest declares `labelsGenerated=false` |
| Source parity declaration | PASS — `sourceParity=true` |
| Artifact/run lineage | PASS |
| Container digest | PASS 3/3 |
| Extractor/config frozen before download | PASS |
| Exact allowlist | PASS |
| Unapproved content inspection | PASS — 0 |
| Subset/member hashes | PASS |
| Classification | **Golden B input subset**; not an Entry-event Golden |

## F. Parity layers

| Layer | Result | Evidence / limitation |
|---|---|---|
| 1. Data bar | PASS for allowed Golden prefixes | 6,545 sparse 5m rows; timestamp violations 0; `availableAt=barEnd`; PIT violations 0 |
| 2. Hybrid input | PASS at event level | Frozen selector identifiers, price reference, timestamp and event inputs preserved |
| 3. Hybrid output | PARTIAL | 198 point membership-count comparisons, 0 mismatch; ranks valid; no independent full-universe rerun or selection-digest recomputation |
| 4. MSH feature | PASS | 1,260/1,260 fixed-feature numeric values exact, tolerance 0 |
| 5. MSH state | PASS | 787/787 chronological state comparisons exact |
| 6. Entry event | NOT RECOVERABLE | Source bundle was generated pre-fit with `MODEL_UNAVAILABLE`; model-applied rows 0 |

The first feature comparison used `Object.is`, which treats `0` and `-0` as different. Diagnostic classification proved all 124 field-level differences were JSON negative-zero normalization in short-direction momentum fields. JSON serialization already normalizes both to `0`, the stored feature hashes matched, and strict finite numeric equality with tolerance 0 yielded zero mismatches. This comparator correction does not alter any feature, threshold, upstream model, or tolerance.

## G. Per-session parity

| Session | Data bars | Hybrid | MSH features | MSH state | Entry event | PIT violations |
|---|---|---|---|---|---|---:|
| 2025-08-27 | PASS (2,057 rows) | PARTIAL | PASS 324/324 | PASS 236/236 | NOT RECOVERABLE | 0 |
| 2025-10-09 | PASS (2,428 rows) | PARTIAL | PASS 342/342 | PASS 226/226 | NOT RECOVERABLE | 0 |
| 2025-11-25 | PASS (2,060 rows) | PARTIAL | PASS 594/594 | PASS 325/325 | NOT RECOVERABLE | 0 |

## H. Stage 1 semantics retained

| Item | Result | Treatment |
|---|---|---|
| Minute timestamp | PASS, Trust B from Stage 1B | Start-labelled half-open minute interval |
| 1m→5m aggregation | PASS from Stage 1B contract | Completed sparse bars only; no lunch crossing or fill |
| Historical provider `availableAt` | CONDITIONAL | Replay bound is `barEnd`; not a claim of provider publication time |
| Missing reason | FAIL | Unknown absence remains `UNKNOWN -> NO_OBSERVATION/NO_FINALIZED_BAR` |
| Corporate actions | PARTIAL | Any unresolved conflict must block the symbol/session |
| Historical universe | PARTIAL | No FULL replay claim |

Golden parity does not upgrade these separate source limitations.

## I. Eligibility

| Classification | Sessions | Status |
|---|---:|---|
| Golden B input subset | 3 | CONFIRMED |
| FULL_REPLAY_ELIGIBLE | 0 | NOT CONFIRMED |
| Tier 2 EXIT Development Substrate | 0 | NOT CONFIRMED |
| Diagnostic Golden input sessions | 3 | CONFIRMED |
| Stage 2 allocation | 0 | LOCKED |

Tier 2 remains at zero because the Stage 1E minimum requires sufficient Hybrid and Entry-event Golden parity. We have exact MSH input/state parity, but not an independent full-universe Hybrid replay and not a model-applied Entry-event reference.

## J. Data protection and deletion ledger

| Item | Result |
|---|---:|
| GitHub artifact ZIP downloads | 3 temporary |
| New J-Quants API calls | 0 |
| New J-Quants bulk downloads | 0 |
| New J-Quants raw sessions | 0 |
| Allowed existing sessions inspected | 3 |
| Unapproved session content inspected | 0 |
| Protected 180–282 access | 0 |
| Fresh Validation/OOS access | 0 |
| EXIT outcome access | 0 |
| Future labels | 0 |
| EXIT invocation | 0 |
| Temporary ZIPs deleted | 3/3 PASS |
| Temporary subsets deleted after evidence capture | 3/3 PASS |
| Raw ZIP committed | NO |
| Extracted subset committed | NO |

Stage 1E focused tests: **13/13 PASS**. Full Predict regression: **2,628/2,628 PASS**. The full regression suite includes pre-existing synthetic/fixture research tests; it did not read these three Stage 1E sessions beyond the allowlisted parity path.

The three local ZIP copies were deleted through the frozen deletion function and non-existence was verified. After the non-raw evidence record was fixed, all three temporary subset directories and the isolated acquisition directory were also deleted. GitHub Actions source artifacts were unchanged.

## K. Safety

All fixed safety flags remain false: `executionAllowed`, `brokerWriteAllowed`, `excelOrderWriteAllowed`, `rssOrderFunctionAllowed`, `liveTradingAllowed`, `paperTradingAllowed`, `automaticPromotionAllowed`, `productionUpdateAllowed`, and `transmitted`.

## L. Final summary

| Item | Result |
|---|---|
| PR | #581 |
| Draft | YES |
| main changed | NO |
| Source artifacts / runs | 3 / 2 |
| ZIPs downloaded | 3 temporary |
| Container SHA count | 3/3 matched |
| Allowlisted sessions | 3 |
| Unapproved member content reads | 0 |
| Allowed sessions extracted | 3 |
| Golden B rows | 787 |
| Subset SHA | 3 fixed |
| Hybrid parity | PARTIAL |
| MSH feature/state parity | PASS / PASS |
| Entry-event parity | NOT RECOVERABLE |
| PIT violations | 0 |
| FULL_REPLAY_ELIGIBLE | 0 |
| Tier 2 confirmed | 0 |
| New J-Quants raw session access | 0 |
| Protected/Fresh access | 0 / 0 |
| EXIT outcome/future labels | 0 / 0 |
| Temporary ZIP deleted | 3/3 |
| Tests | Stage 1E 13/13; full Predict 2,628/2,628 PASS |
| Final Gate | **CONTROLLED_EXTRACTION_PARITY_PARTIAL** |
| HARD STOP | ACTIVE |

## M. Required answers

1. **Yes.** Whole-ZIP physical acquisition was mechanically separated as `ACQUIRED_UNINSPECTED` from three-session research inspection.
2. **Yes.** Instrumentation recorded unapproved member content reads = 0 in both synthetic and real extraction.
3. **Yes.** Exactly the three authorized sessions were extracted.
4. **Yes.** Source artifact/run IDs, three container hashes, frozen extractor/config hashes, all selected-member hashes, and three subset hashes are fixed.
5. **Yes, as Golden B input subsets only.** They are not model-applied Entry-event Golden references.
6. **Partially.** Event-level identifiers, membership counts, ranks, and price inputs are consistent; independent full-universe Hybrid output replay was not performed.
7. **MSH feature and state parity passed exactly. Entry-event parity was not recoverable** because all source decisions are pre-fit `MODEL_UNAVAILABLE`.
8. **Yes.** PIT violations = 0 across 6,545 allowed Golden bars.
9. **No FULL or confirmed Tier 2 basis yet.** FULL remains 0 and Tier 2 remains 0.
10. **Highest-value next action:** freeze a non-outcome, model-applied Entry-event Golden reference (or a reproducible frozen-model decision contract) and a separately authorized full-universe Hybrid replay reference, then rerun only the missing Hybrid-output and Entry-event parity layers. Do not open additional SEALED sessions for this.

## N. Hard stop

Stage 1E stops here. Do not proceed automatically to Stage 2 allocation, Development, EXIT performance, Validation, OOS, or Prospective work.
