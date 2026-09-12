# Phase57 EXIT v4 — Stage 1B Existing Tick Evidence Discovery Audit

As of: 2026-09-10 JST  
PR: #581  
Parent head: `2529937379813e89271d88a471c9f63659a33775`  
Gate: `EXISTING_EVIDENCE_PARTIALLY_SUFFICIENT`

This was an existing-evidence discovery audit only. It made no J-Quants API call, no `/v2/bulk/get` call, no new Tick or Minute download, no raw persistence, no protected/fresh access, and no EXIT outcome or future-label access.

The central discovery is a branch-only, sanitized J-Quants Tick-to-Minute reconciliation produced on 2026-09-06. It directly compared 61,923 Tick executions with 1,303 Minute rows and established a start-labelled, half-open Minute interval at every row and all 16 inspected session boundaries. A separate post-contract Minute pilot then verified deterministic, sparse, session-separated 5m aggregation on four source groups. These artifacts were not present on PR #581 when Stage 1 stopped.

Raw Tick rows were not retained in GitHub. The direct reconciliation is therefore Trust Level B, not Level A. It resolves source interval semantics, but it does not provide exact historical provider publication time or row-level Ark golden parity for the three Stage 1 sessions.

## A. Evidence search

| Item | Result |
|---|---:|
| Files searched | 3,298: 3,282 unique repo paths + 16 supplied PDFs |
| Branches searched | 696 fetched remote branch tips, including main |
| Artifacts searched | 4 GitHub Actions artifacts |
| Relevant evidence found | 18 evidence clusters |
| Direct raw/tick evidence | 1 sanitized J-Quants Tick-to-Minute reconciliation; retained raw files = 0 |
| Indirect/supporting evidence | 17 clusters |

The content scan produced 272,775 branch-tip/path hits before deduplication. It included all requested keywords and the current EXIT/Entry branches, both selector J-Quants branches, Phase57 realtime/MarketSpeed/RSS/historical branches, Phase58 Tick/RSSChart/bar-close branches, workflows, scripts, committed evidence, data paths, and handoff PDFs.

## B. Evidence inventory

| ID | Classification | Trust | Evidence | Finding / limitation |
|---|---|---|---|---|
| E01 | DIRECT_TIMESTAMP, SESSION_BOUNDARY | B | Actions artifact `9987982017`, run `34028904298`, job `101474738422`, commit `084a10b6...` | 61,923 Tick and 1,303 Minute rows: start-half-open exact 1,303/1,303, orphan bins 0; end-half-open 0/1,303; all 16 boundaries match start labels; raw absent |
| E02 | DIRECT_TIMESTAMP, SESSION_BOUNDARY | B | Frozen timestamp JSON/SHA on `research/phase57-selector-capacity-v2` | Freezes BAR_START, `[Time,Time+1m)`, JST, terminal-auction and no-fabrication rules |
| E03 | INDIRECT_TIMESTAMP | C | Reconciliation implementation and tests at `084a10b6...` | Reproducible algorithm and fail-closed validation; local combined suite 17/17 PASS |
| E04 | INDIRECT_TIMESTAMP, SESSION_BOUNDARY, MISSING | B | Actions artifact `9987714595`, run `34028131686` | Earlier 1,305-row edge probe rejects uniform BAR_END; cannot independently prove closure or absence cause |
| E05 | INDIRECT_TIMESTAMP, AVAILABLE_AT | C | Timestamp audit report | Separates event time, replay time, publication time and fetch time; publication around 16:30 JST |
| E06 | NOT_USABLE | D | Earlier source-validation failure | Its BAR_END suggestion is superseded and not used |
| E07 | 5M_AGGREGATION, SESSION_BOUNDARY | B | Actions artifact `9988060213`, run `34029285223`, job `101475741713`, commit `5dc743f2...` | Four source groups each produce 65 deterministic regular 5m bars; no fill; terminal rows excluded |
| E08 | 5M_AGGREGATION, SESSION_BOUNDARY | B | Reconstruction pilot JSON/SHA/report | SOURCE_VALIDATION_ONLY PASS; relevant job passed although an unrelated verification job made the overall workflow fail |
| E09 | 5M_AGGREGATION, AVAILABLE_AT, MISSING | C | J-Quants Minute adapter and tests | Encodes T..T+4 bins, replay `availableAt=T+5m`, session restart and sparse no-fill |
| E10 | INDIRECT_TIMESTAMP, 5M_AGGREGATION | B | Stage 0/1 counts and three-session SHA-256 fingerprints | Three exposed sessions have minute/5m/member-set fingerprints, but no retained row-level golden comparison |
| E11 | NOT_USABLE for timestamp proof | B | Current Stage 1 artifact `10130183707`, run `34418970782` | Proves the month-scope stop and zero raw/outcome access; contains no Tick rows |
| E12 | INDIRECT_TIMESTAMP | C | Phase58 P15 causal Tick code/tests | Proves MarketSpeed ordering discipline only; not J-Quants evidence |
| E13 | AVAILABLE_AT, INDIRECT_TIMESTAMP | C | RSS capture and MSII prospective runtime/tests | Separates `capturedAt` and source tick time; not J-Quants publication proof |
| E14 | MISSING | C | Phase57 sparse finalized-5m code/tests | Confirms Ark no-synthetic behavior; does not classify J-Quants absence reasons |
| E15 | AVAILABLE_AT, 5M_AGGREGATION | C | Phase58 P29 source-bar-close tests | Confirms Ark distinguishes bar timestamp and bar close; not provider availability proof |
| E16 | NOT_USABLE | D | 41 committed `data/phase57-realtime-live/.../raw` files | TradingView scanner snapshots, not J-Quants or Tick rows |
| E17 | INDIRECT_TIMESTAMP | C | Supplied MarketSpeed RSS function PDF | Documents RssTickList/RssChart fields only; no J-Quants interval contract |
| E18 | INDIRECT / NOT_USABLE | C | Fifteen supplied Ark handoff/history PDFs | Read-only design/history only; no additional J-Quants timestamp or raw proof |

Trust B is the highest available level because no raw J-Quants Tick row is retained. The Actions ZIP SHA-256 values independently match GitHub metadata: `9104f8f...`, `0171e722...`, and `c199de00...`. Each embedded `report.sha256` also verifies.

## C. Timestamp contract

| Item | Result |
|---|---|
| Minute semantics | PASS — BAR_START |
| Evidence level | B |
| Timezone | PASS — Asia/Tokyo / JST exchange-local time |
| First minute | 09:00 |
| 09:00 row interval | `[09:00:00,09:01:00)` |
| 09:05 relation | Starts `[09:05:00,09:06:00)`; it is not part of the 09:00–09:05 5m bar |
| barStart | PASS — source `Time` |
| barEnd | PASS — source `Time + 1 minute` |
| 11:30 / 15:30 | Separate terminal-auction Minute events, excluded from regular continuous 5m input |
| Tick proof | FOUND — sanitized direct reconciliation, raw not retained |
| availableAt | CONDITIONAL — reconstructed event-time bound is safe; exact provider publication is unknown |

`sourceTimestamp`, `barStart`, `barEnd`, replay `availableAt`, provider publication time, and fetch time remain separate fields. For later-fetched causal replay, a regular 5m bar is not available before its `barEnd`; the adapter assigns replay `availableAt=barEnd`. This does not claim that J-Quants delivered the row intraday. Existing provider evidence only states daily publication around 16:30 JST, not an exact per-row or per-session delivery instant.

## D. 5m aggregation contract

| Item | Result |
|---|---|
| Included minute rows | CONFIRMED — observed rows T, T+1, T+2, T+3, T+4 |
| First 5m bar | CONFIRMED — `barStart=09:00`, `barEnd=decisionTimestamp=replay availableAt=09:05` |
| Morning | PASS — regular bins are within `[09:00,11:30)` |
| Lunch | PASS — no bin crosses 11:30–12:30; 11:30 terminal event is separate |
| Afternoon restart | PASS — independent bins restart at 12:30 |
| Afternoon regular end | `[12:30,15:30)`; 15:30 terminal event is separate |
| Missing minutes | No forward/back fill and no synthetic OHLCV; aggregate only observed Minute rows |
| Golden 5m parity | NOT RUN for 2025-08-27, 2025-10-09, 2025-11-25 |
| Causal aggregation | PASS as later-fetched event-time reconstruction |

The four-group reconstruction evidence reports 1,290 regular Minute rows, eight terminal-auction rows, 260 generated regular 5m bars, deterministic repeatability, zero fabricated minutes, and terminal-auction exclusion. It is source-semantic evidence, not Ark Lane Y golden parity.

## E. Data semantics

| Item | Result | Reason |
|---|---|---|
| Missing reason | FAIL | Minute absence still cannot uniquely distinguish no trade, suspension, provider omission, not listed or out of universe |
| Canonical sparse treatment | PASS | Any unresolved absence remains `UNKNOWN` and yields `NO_OBSERVATION / NO_FINALIZED_BAR`; state and streak do not advance |
| Adjusted/unadjusted | PASS for intraday basis | Exact Minute OHLCV/turnover equality to executions establishes raw execution-price semantics |
| Corporate actions | PARTIAL | Same-session raw basis is known; merger/code/delisting lineage and event-crossing rules remain incomplete |
| Historical universe | PARTIAL | Dated issue master exists; exact lineage and suspension completeness are not proven |

An unresolved corporate-action symbol/session must be blocked. No historical back-adjustment may be introduced after candidate selection.

## F. Replay eligibility

| Item | Result |
|---|---|
| Frozen Hybrid | PARTIAL |
| MSH-Entry v1 | PARTIAL; threshold remains strictly `> 0.60` |
| Golden input parity | NOT RUN / still blocked without row-level input materialization |
| FULL_REPLAY_ELIGIBLE | 0 |
| Tier 2 confirmed | 0 |
| DIAGNOSTIC_ONLY | 3 existing exposed sessions |
| PIT violations | 0 observed; not complete proof because no new raw was opened |

Timestamp and aggregation are no longer blockers. FULL and confirmed Tier 2 remain unavailable because the three exposed sessions lack row-level Hybrid/MSH golden parity and complete universe/corporate-action lineage. A matching 5m fingerprint alone is insufficient to claim feature, state, membership or Entry parity.

## G. Monthly Tick decision

| Question | Decision |
|---|---|
| Required to resolve Minute interval semantics? | NO |
| Required to freeze the causal 5m reconstruction contract? | NO |
| Would it resolve exact provider `availableAt`? | NO |
| Would it resolve PIT universe/corporate-action lineage? | NO |
| Required now? | NO |

Another monthly Tick download would duplicate the strongest solved part while physically acquiring unallocated sessions. The remaining blockers need date-scoped Minute-only input parity on the same already exposed sessions, a dated master join, and a corporate-action/event blocklist.

If acquisition is ever separately authorized, its state must be explicit and monotonic:

`NOT_ACQUIRED → ACQUIRED_UNINSPECTED → QUALITY_PILOT_ALLOWED → DEVELOPMENT_LOCKED / VALIDATION_LOCKED / OOS_SEALED / PROTECTED`.

Physical possession does not authorize research access, and J-Quants cancellation/retention limits still apply.

## H. Data protection

| Item | Result |
|---|---:|
| New J-Quants bulk downloads | 0 |
| New `/v2/bulk/get` calls | 0 |
| New J-Quants API calls | 0 |
| New raw sessions accessed | 0 |
| New SEALED sessions accessed | 0 |
| Protected 180–282 access | 0 |
| Fresh Validation/OOS access | 0 |
| EXIT outcome access | 0 |
| Future labels generated | 0 |
| Raw persistence | 0 |

Downloaded files in this audit were existing sanitized GitHub Actions evidence ZIPs, not J-Quants raw/bulk archives.

## I. Tests and integrity

- The historical evidence implementations were re-run at `5dc743f2...`: 17/17 Tick reconciliation, Minute reconstruction and aggregation tests passed.
- The Stage 1B contract test validates evidence categories/trust values, interval and 5m rules, the partial gate, zero access counters, locked Stage 2, and all nine safety flags.
- The machine artifact is `predict/research/phase57-exit-v4-jquants-stage1b-existing-tick-evidence-audit-v1.json` with an adjacent SHA-256 file.
- `main` is unchanged. PR #581 remains Draft. No merge, auto-merge, Ready conversion, promotion or production update is authorized.

## J. Final gate

`EXISTING_EVIDENCE_PARTIALLY_SUFFICIENT`

Existing evidence is sufficient to replace the Stage 1 timestamp FAIL with PASS, freeze the source Minute interval, identify terminal-auction rows, establish raw execution-price basis, and freeze the causal sparse 1m→5m reconstruction contract. It is not sufficient to claim exact J-Quants provider `availableAt`, Ark golden input parity, complete missing reasons, full historical universe, FULL replay, or confirmed Tier 2 sessions.

Stage 2 allocation remains blocked. The highest-value next action is a separately precommitted, date-scoped Minute-only input-parity run on the same three already exposed sessions, using the proven timestamp contract, dated issue master, corporate-action blocklist, no outcomes and no new sealed sessions.

## K. Direct answers

1. Existing Ark evidence resolves J-Quants Minute timestamp semantics: **Yes, Trust Level B**.
2. Exact `availableAt`: **No**. A safe reconstructed event-time lower bound is defined; provider publication remains exact-unknown and daily around 16:30 JST.
3. 1m→5m contract: **Yes for causal later-fetched reconstruction**, with explicit terminal-auction exclusion and no fill.
4. Golden parity without new raw acquisition: **No**. The retained evidence has hashes/counts, not row-level Hybrid/MSH inputs.
5. FULL_REPLAY_ELIGIBLE ≥1: **No; 0**.
6. Confirmed Tier 2: **No; 0**. It remains a candidate until golden input parity and PIT/event guards pass.
7. Monthly Tick required: **No for timestamp/aggregation and not useful for the other principal blockers**.
8. Remaining blockers include exact provider availability, golden parity, missing reason, PIT universe and corporate-action lineage; they are not timestamp-only.
9. New SEALED session needed: **No**.
10. Next action: **precommit a Minute-only, input-only parity run on the same three exposed sessions; then stop again before any allocation or outcome access**.

HARD STOP: no monthly Tick download, Stage 2 allocation, Development, EXIT measurement, Validation or OOS follows from this audit.
