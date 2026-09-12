# Phase57 EXIT v4 — J-Quants Historical Data Capacity / Quality / Conservation Audit

Status: `CONDITIONAL_STOP_BEFORE_OUTCOME_ACCESS`  
As of: 2026-09-10 JST  
Scope: metadata, existing quality evidence, replay feasibility, and conservation only.

No EXIT v4 performance, v3/v4 comparison, new MFE/MAE, label generation, protected access, Fresh OOS access, allocation, or promotion was performed.

The machine-readable contract is `predict/research/phase57-exit-v4-jquants-data-capacity-audit-v1.json`.

## A. Contract and retention

| Item | Audit result |
|---|---|
| Light | ACTIVE, user-attested; ¥1,650/month; scheduled end 2026-10-06 19:02 JST |
| Tick + OhlcMin | ACTIVE/cancellation scheduled, user-attested; ¥5,500/month; scheduled end 2026-10-06 19:07 JST |
| Minute/Tick history | Officially past 2 years |
| Add-on limit | 60 requests/min, independent of base-plan rate limit |
| Private archive during subscription | Permitted only for the individual user, with access control/encryption |
| Archive after cancellation | **Not permitted**: delete raw data, copies, and reconstructable derivatives |

The prior idea of permanently sealing a full raw archive after cancellation is rejected by the current official usage guidance. A temporary private archive is possible only while the entitlement remains active and must carry a deletion ledger bounded by 2026-10-06. Non-reconstructable private derivatives may remain under the stated conditions; this audit does not decide which Ark artifacts satisfy that legal/contractual test.

## B. Official source capabilities

| Dimension | Minute OHLC | Tick |
|---|---|---|
| Delivery | API or CSV | CSV only; not direct API |
| Window | Past 2 years | Past 2 years |
| Coverage | TSE issues; regional-only issues excluded | Same stated TSE restriction |
| Time field | `HH:mm` | `HH:MM:SS.ffffff` plus AM/PM session code |
| No-trade interval | No record | No execution row |
| Pagination | `pagination_key`; no total row count | Bulk file flow |
| Adjusted fields | None in minute schema | None stated |

The minute endpoint supports a whole date across listed issues, which is the realistic market-wide acquisition shape. Pagination must continue until the key disappears. The provider warns that pagination is not guaranteed to be a consistent snapshot if data changes during the fetch, so fetch time, page count, canonical hash, and correction-state metadata are mandatory.

## C. Existing Ark quality evidence

Only already-recorded, outcome-free source evidence was inspected. No API call was made because this environment has no `JQUANTS_API_KEY`.

| Session | Eligible JPX symbols | 1m rows | Sparse 5m bars |
|---|---:|---:|---:|
| 2025-08-27 | 3,768 | 466,427 | 167,291 |
| 2025-10-09 | 3,758 | 459,257 | 165,051 |
| 2025-11-25 | 3,765 | 466,095 | 166,978 |
| Mean | 3,763.67 | 463,926.33 | 166,440 |

This three-session sample is sufficient for a planning magnitude, not for a two-year completeness claim. It implies about 44.22 observed 5-minute bins per eligible symbol-session because inactive minutes are absent and no bars are fabricated.

## D. Gross capacity estimate

The official rolling two-year window is estimated at 480–500 TSE sessions pending an authenticated calendar/boundary query. Applying the observed means gives:

| Capacity | Lower | Upper |
|---|---:|---:|
| Sessions | 480 | 500 |
| 1m rows | 222,684,480 | 231,963,000 |
| Sparse 5m bars | 79,891,200 | 83,220,000 |

After protecting 103 sessions, preserving Fresh reservations, avoiding known prior allocations/overlap, and allowing timestamp/corporate-action/parity rejection, a **planning-only** candidate band is 300–360 sessions. This is not an allocation and does not authorize fetching or opening any session.

## E. Independent First ENTER capacity

The known 3.4 First ENTER/session diagnostic is not assumed to transfer unchanged. The estimate uses a 41% haircut for Conservative, a 15% haircut for Base, and no uplift above the known diagnostic for Optimistic.

| | Conservative | Base | Optimistic |
|---|---:|---:|---:|
| First ENTER/session | 2.0 | 2.9 | 3.4 |
| Sessions for 200 | 100 | 69 | 59 |
| Sessions for 500 | 250 | 173 | 148 |
| Sessions for 1000 | 500 | 345 | 295 |
| Sessions for 2000 | 1000 | 690 | 589 |
| Events from candidate 300–360 sessions | 600–720 | 870–1,044 | 1,020–1,224 |

Checkpoint A=200 and B=500 are capacity-feasible if parity passes. C=1000 is conditional and near the conservation boundary. D=2000 is not feasible inside the current two-year window without consuming protected/future data or introducing another defensible source; it must not be forced.

## F. Data quality decision

| Item | Status | Finding |
|---|---|---|
| Historical range | PASS | Minute and Tick: past 2 years |
| TSE coverage | CONDITIONAL PASS | Regional-only listings excluded |
| PIT universe | CONDITIONAL PASS | Dated master replay exists and three sessions were observed; delisted/code-change linkage remains unproven |
| Timestamp boundary | **FAIL** | Official endpoint defines `HH:mm`, but not bar-start vs bar-end |
| Timezone / `availableAt` | **FAIL / CONDITIONAL** | No provider `availableAt`; causal derivation depends on unresolved boundary and explicit JST proof |
| Lunch/session handling | CONDITIONAL PASS | Current TSE is 09:00–11:30 and 12:30–15:30; the two-year window crosses the historical close-time change and needs a dated schedule |
| No trade | PASS | Officially omitted rather than emitted as zero |
| Missing reason | **FAIL** | Absence alone cannot distinguish no-trade, suspension, provider failure, not-listed, or out-of-universe |
| Adjustment | **FAIL** | Minute schema has no adjustment factor |
| Corporate actions | **FAIL** | Dated daily adjustment/action join and cross-session state policy are not frozen |
| Revision/reproducibility | CONDITIONAL PASS | Canonical raw SHA/fetch time/page count/correction snapshot required |
| Archive after cancellation | **FAIL** | Contract requires deletion of reconstructable material |
| 5m causal aggregation | CONDITIONAL PASS | Existing no-fill segment aggregator is structurally suitable only after timestamp and dated-session proof |

The repository has a specific inconsistency that must fail closed: the aggregation path requires `BAR_START_HALF_OPEN_INCLUDING_TERMINAL_AUCTION_MINUTES`, while `fetchJquantsMinuteRows()` records `sourceMinuteTimestampMeaningVerifiedByOperator:false`. The requirement string is not itself proof. A predeclared minimal Tick/minute/golden overlap must establish the boundary before any FULL replay classification.

## G. 5-minute candidate contract

Subject to the missing timestamp proof:

- 09:00–09:05 means source minutes with `09:00 <= t < 09:05`.
- The output timestamp is 09:00 and can become available no earlier than 09:05 JST.
- Never aggregate across the 11:30–12:30 lunch break.
- Keep closing-auction minutes separate from continuous 5-minute inputs.
- Never fill absent minutes. Record observed-minute count and an externally supported reason.
- An absent bin remains `NO_OBSERVATION / NO_FINALIZED_BAR`; EXIT state, streak, and MFE/MAE do not advance.
- Session close must be date-aware; a single modern 15:30 rule cannot silently govern the whole rolling window.

This contract remains `NOT_FROZEN_TIMESTAMP_PROOF_REQUIRED`.

## H. Replay and dataset classification

| Class | Current count/status |
|---|---|
| `FULL_REPLAY_ELIGIBLE` | 0 confirmed; blocked |
| `EXIT_DEVELOPMENT_SUBSTRATE` | 0 confirmed; 300–360 planning candidates only |
| `DIAGNOSTIC_ONLY` | 3 existing quality-evidence sessions |
| `SEALED_RESERVE` | Protected 180–282 = 103; Fresh reservations = 25; new access = 0 |
| `NOT_USABLE` | 0 confirmed; assign only after Stage 1 |

Frozen Hybrid and MSH-Entry replay are at most candidate Tier 2 until dated universe, timestamp, corporate actions, reference price, feature parity, and golden overlap all pass. No session is promoted to Tier 1 by this audit.

## I. Conservation decision and STOP

Current stage remains Stage 0. Do not bulk-fetch, allocate, calculate EXIT outcomes, or unlock Development.

Before a result-blind allocation can be frozen:

1. confirm exact API date boundary and exact TSE session list;
2. prove minute boundary/timezone with a minimal predeclared Tick overlap;
3. make session-end semantics historically date-aware;
4. join dated issue master and corporate-action metadata;
5. distinguish missing reasons using independent evidence;
6. run a small predeclared Ark golden parity pilot;
7. freeze deletion-ledger requirements for all reconstructable J-Quants material by cancellation;
8. then freeze a result-blind Development/Validation/Holdout/OOS/Future allocation.

Only Stage 1 may be proposed next. EXIT outcome measurement remains prohibited.

## Official references

- https://jpx-jquants.com/en
- https://jpx-jquants.com/en/spec/data-spec
- https://jpx-jquants.com/en/spec/eq-bars-minute
- https://jpx-jquants.com/en/spec/eq-trades
- https://jpx-jquants.com/en/spec/pagination
- https://jpx-jquants.com/en/spec/rate-limits
- https://jpx-jquants.com/en/spec/eq-bars-daily/adj
- https://jpx-jquants.com/en/help/usage
- https://www.jpx.co.jp/english/equities/trading/domestic/01.html
