# Validation Dataset Pre-Registration — BLOCKED

Date: 2026-09-16 JST. Repo: Iam-2squared/ark-terminal. Branch: research/phase57-long-only-cash-equity. PR: #587.

**MSH_ENTRY_LONG_V1_VALIDATION_DATASET_FREEZE_BLOCKED**

Blocker: **EXIT_DEVELOPMENT_ALLOCATION_CONFLICT**. No Validation dataset is frozen or released by this audit.

## Finding

The existing LONG-only allocation v3 designates 30 Validation sessions, 2025-01-10 through 2025-02-25. This is the original calendar-based allocation, not a period chosen from Candidate scores/outcomes. Its session-list SHA-256 is `2be49f69be8178b09ca2f3d00b7690222d7481637529d781070a348522adb364` (compact JSON ordered array, UTF-8, no newline).

The EXIT Stage2 allocation at remote `ea15a594103bd6c9146f19a4aebafb83067d869b` is also FROZEN_RESULT_BLIND. It reserves the first10 of these dates for EXIT DEV-B, and the remaining20 for EXIT Validation. The current user explicitly prohibits silently transferring EXIT Development reservations into Entry Validation. No explicit release/supersession record was found in the reviewed LONG-only allocation, data plan or independent-review disposition. The newer LONG-only plan's integrated raw-data reuse requirement does not explicitly release the other Frozen EXIT contract.

| Proposed Entry Validation dates | Sessions | Existing EXIT role | Result |
|---|---:|---|---|
| 2025-01-10, 01-14, 01-15, 01-16, 01-17, 01-20, 01-21, 01-22, 01-23, 01-24 | 10 | DEV_B_LOCKED | Blocking allocation conflict |
| 2025-01-27 through 2025-02-25, exact dates in audit.json | 20 | VALIDATION_LOCKED | Separate EXIT reservation; not silently released |

The30 sessions have no overlap with the LONG-only76-session Development (last2025-01-09), the inspected legacy Entry Development allocation, Historical Holdout29 identifiers, or legacy Fresh reservation identifiers. The2026-09-10 metadata inventory records each as METADATA_ONLY_OUTCOME_UNTOUCHED. This is dated metadata evidence, not a universal proof that every research branch has never exposed an outcome. A final exposure attestation remains required after allocation ownership is reconciled. Per-session status, metadata lineage and exact source Git blob identifiers are in audit.json.

We did not shorten30 to20, append dates, deploy a reserve, take OOS dates, or choose a new Fresh window to evade the conflict. Existing calendar allocation excludes non-session dates; no calendar or market-data request was made.

## Confirmed without outcomes

- Candidate SHA: `4a2f52cd6f25f480fe6d7de9db525860ddf3c1600abed06b6222c0990c055a23` — unchanged.
- Final model SHA: `b053a858edda22bee7b9939162648740507964cc5ed8d613c2d778d15534589e` — unchanged.
- Final scaler SHA: `1e4865915a2ad1ec51dd4ebf2116d48b9f89b9b884f8dc732fdb2861dbf4fe4b` — unchanged.
- Selector payload SHA: `3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59` — unchanged.
- Fit Contract SHA: `64c20d785be5f23b0a9103f419726b191a12a58fd5d3a7ad5185c69f9644a938` — unchanged.
- Development Evidence SHA: `68d2a02c988a05b3178e903d628a53662b01bb704fa0700ebcb98e3b32547ead` — unchanged.
- Frozen Selector ranking and Candidate cadence agree: 09:30,10:00,10:30,11:00,11:30,13:00,13:30,14:00,14:30,15:00 JST. Ten decisions/session, approximately30m. No5mSelector experiment is authorized.

## Evaluation draft, not dataset freeze

`evaluation-draft.json` preserves the existing HIGH ordinal label, completed CLOSE diagnostic, strict30m signed LOW-based trueMAE and HIGH-based MFE, separate entry-time remaining opportunity, latency and consumed-return semantics. Primary/path metrics are gross reference-price diagnostics; no new fee/slippage number or cost-adjusted P&L is introduced. Missing30m LOW/path stays MISSING; sessionMAE substitution is forbidden. Integrity failure stops the run rather than replacing a session. This draft cannot authorize Validation prediction or acquisition.

The data source remains the existing J-Quants v2 dated-master/daily/minute contract, private immutable cache first; same PIT Prime/Standard/Growth common-equity universe, no new filters. Cache price payloads, candidate events, labelability and outcome availability were not opened to select dates.

## Access / changes

Validation predictions, scores, ENTER/SKIP, outcome reads/aggregates, Development fits, scaler refits, OOF regeneration, threshold evaluation, OOS data/event-count previews, EXIT outcomes and SHORT evaluation: all0. Yahoo/J-Quants/other market-data requests: all0. Only allocation/reservation metadata (including protected-set identifiers needed for overlap checks), source contracts and artifact hashes were inspected. All safety flags remain false.

Only additive audit/report/draft files were created. No Selector, Entry, Fit Contract, Candidate, Development evidence or allocation file was changed. Metadata consistency and source-hash checks were performed; no local full regression or training runner was needed for these documentation-only additions.

Source remote head: `0f6274e8605a2d5e9ec7c51193625491c1a055af`. Latest main observed: `6b6c4d522cd1863132185463a0aed74bc819be01`.

## Exact next action

**STOP.** Resolve the cross-research allocation ownership explicitly using metadata only: whether the Frozen EXIT reservations are retained, or an authorized allocation amendment releases/reassigns them. Do not treat this blocked report as such an amendment. After that, complete the current prior-exposure attestation and rerun Dataset Identity Freeze. Candidate2.0, its model/scaler and all sealed data remain unchanged.
