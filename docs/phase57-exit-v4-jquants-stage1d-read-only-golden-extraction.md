# Phase57 EXIT v4 - Stage 1D Read-Only Golden Extraction Audit

As of: 2026-09-10 JST  
PR: #581  
Parent head: `e22e2716f785ce658f61eb672f22b2026b74d299`  
Final gate: `READ_ONLY_EXTRACTION_NOT_SUPPORTED`

Stage 1D stopped before artifact download, extraction, or parity. The three pre-outcome candidate artifacts are present and unexpired, but the documented GitHub Actions artifact interface exposes metadata and an archive-level ZIP download redirect. It does not expose server-side member listing, session filtering, or individual member download. Downloading the ZIP and filtering locally would violate the fixed physical-acquisition boundary.

Official API evidence: [GitHub REST Actions artifact endpoints](https://docs.github.com/en/rest/actions/artifacts?apiVersion=2022-11-28#download-an-artifact) document a `302` redirect for downloading one ZIP archive. Artifact listing can filter by artifact name, not by a file or session inside the archive.

No undocumented byte-range workaround was treated as a supported research control. A technique that happens to work against a temporary storage redirect would not establish a stable, documented, reproducible member-level access boundary.

## A. Source artifact inventory

| Authorized session | Run | Artifact | Size | Artifact SHA-256 | Sessions / denied | State |
|---|---:|---:|---:|---|---:|---|
| 2025-08-27 | `34355199082` | `10106663226` | 1,197,793 B | `803b33bc...d18173` | 10 / 9 | ACTIVE; metadata only |
| 2025-10-09 | `34292703804` | `10082689099` | 1,095,885 B | `a3874988...edb1b3b` | 10 / 9 | ACTIVE; metadata only |
| 2025-11-25 | `34292703804` | `10084152060` | 1,089,747 B | `72a9b97a...425d03` | 9 / 8 | ACTIVE; metadata only |

The artifact digests and expiry timestamps were obtained from artifact metadata. No archive bytes or member bytes were requested. Measurement/outcome artifacts were not inspected.

## B. Extraction feasibility

| Candidate route | Member-level? | Whole ZIP acquired? | Reproducible support | Verdict |
|---|---|---|---|---|
| GitHub REST artifact metadata | NO | NO | Official | Metadata only |
| GitHub REST archive download | NO | YES | Official | FORBIDDEN |
| `actions/download-artifact` | NO | YES | Official | FORBIDDEN |
| Committed manifest/index | NO row-level subset | NO | Verified | Golden C only |
| Temporary redirect byte ranges | Unproven | Unknown contract | Undocumented | NOT ADOPTED |

Server-side/session-only filtering is therefore **not supported by the current documented interface**. The extraction gate fails closed.

## C. Precommitted filter contract

| Item | Contract |
|---|---|
| Filter key | `sessionDate` exact match |
| Allowlist | 2025-08-27 / 2025-10-09 / 2025-11-25 |
| Unknown date | DENY |
| Outcome-dependent filter | FORBIDDEN |
| Required transport | Documented server-side member filter |
| Download then filter | FORBIDDEN |
| Full archive materialization | FORBIDDEN |
| Lineage | run ID + artifact ID/name/digest required |
| Outcome fields | Strip recursively before output |
| Subset fingerprint | Canonical deterministic SHA-256 required |
| Source mutation | FORBIDDEN; read-only |

The pure contract module is testable but is **not an extractor**. `extractorSha256` and `subsetSha256` remain null because no supported extraction occurred.

Contract module SHA-256: `07a7fd3bd80d8ceacbee78633f662abd70303258a138239f3a8a17f50d8ea7b7`.

## D. Golden and parity status

| Layer | Result | Reason |
|---|---|---|
| Golden B subset | NOT EXTRACTED | No member-level API |
| Data-bar parity | NOT RUN | Gate 1 blocked |
| Hybrid input parity | NOT RUN | Zero Golden B rows |
| Hybrid output parity | NOT RUN | Zero Golden B rows |
| MSH ten-feature parity | NOT RUN | Zero Golden B rows |
| MSH state parity | NOT RUN | Zero Golden B rows |
| Entry-event parity | NOT RUN | Zero Golden B rows |
| PIT violations | 0 observed | No parity executed; not full proof |
| FULL_REPLAY_ELIGIBLE | 0 | Unchanged |
| Tier 2 confirmed | 0 | Unchanged |

## E. Data protection ledger

| Item | Count |
|---|---:|
| Full artifact downloads | 0 |
| Artifact member downloads | 0 |
| Allowed sessions extracted | 0 |
| Unapproved sessions materialized | 0 |
| New J-Quants calls | 0 |
| New Tick/raw/SEALED sessions | 0 |
| Protected 180-282 access | 0 |
| Fresh Validation/OOS access | 0 |
| EXIT outcome access | 0 |
| Future labels generated | 0 |
| EXIT v3/v4 invocations | 0 |
| Raw persistence | 0 |

All nine safety flags remain false. PR #581 remains Draft; main and the base branch were not changed.

## F. Required final report

| Category | Result |
|---|---|
| PR | #581 |
| Parent head | `e22e2716f785ce658f61eb672f22b2026b74d299` |
| Draft | YES |
| main changed | NO |
| Source artifacts found | 3 |
| Source runs | 2 |
| Server-side filter supported | NO |
| Full artifact downloaded | 0 |
| Allowed sessions extracted | 0 |
| Unapproved sessions materialized | 0 |
| Golden B rows | 0 |
| Hybrid parity | NOT RUN |
| MSH feature parity | NOT RUN |
| State parity | NOT RUN |
| Entry parity | NOT RUN |
| PIT violations | 0 observed; not full proof |
| FULL_REPLAY_ELIGIBLE | 0 |
| Tier 2 confirmed | 0 |
| New raw/SEALED/Protected/Fresh access | 0 / 0 / 0 / 0 |
| EXIT outcome/future labels | 0 / 0 |
| Stage 1D contract tests | 8/8 PASS |
| Full Predict tests | 2,615/2,615 PASS |
| GitHub CI | Verify on committed head and report externally |
| Final Gate | `READ_ONLY_EXTRACTION_NOT_SUPPORTED` |
| HARD STOP | ACTIVE |

## G. Direct answers

1. Three-session extraction without whole-artifact download: **No**.
2. Source lineage/hash: **Yes for source artifacts**; subset lineage/hash: **not generated**.
3. Golden B validity: **Candidate source is pre-outcome and lineage-qualified, but no authorized subset was extracted; not usable yet**.
4. Hybrid input/output parity: **Not run**.
5. MSH feature/state parity: **Not run**.
6. Entry-event parity: **Not run**.
7. PIT violations: **0 observed**, because no parity ran; not complete proof.
8. FULL or Tier 2 evidence: **No; both remain 0**.
9. Whole artifact download needed under the current API: **Yes for access, but it remains forbidden and was not performed**.
10. Highest-value action: **create session-isolated, pre-outcome artifacts at generation time (or obtain a documented member-filter endpoint), then explicitly reauthorize Stage 1D**.

HARD STOP: Stage 2 allocation, Development, EXIT measurement, Validation, OOS, and Prospective work remain locked.
