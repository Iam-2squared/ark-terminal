# Phase57 LONG-only Cash Equity Research Foundation

## Current status

- 🟢 LONG-only cash-equity contract frozen
- 🟢 L0 daily-only census foundation implemented
- 🟢 Claude independent review received and disposition frozen
- 🟢 J-Quants Light + Tick/OhlcMin entitlement re-attested from user screenshots
- 🟢 Reviewed Data Contract v3 committed
- 🟢 Clean 205-session historical accounting preserved with 15-session reserve
- 🟢 Selector-only data consumption prohibited; Development raw data must remain reusable for Entry / EXIT / Allocation / integrated portfolio replay
- 🟢 Exact clean-205 session identifiers frozen without outcome inspection
- 🟢 Formal L0 acquired exactly 411 approved provider requests (206 Daily, 205 dated Master, 0 Minute)
- 🟢 Causal 1m -> 5m, evaluator-only L1 labels, shared replay interface and four-stage comparison harness implemented
- 🟢 Development-only L1 full-cross-section builder and L2 ridge candidate selection/freeze path implemented
- 🟢 Formal L0 private-cache loader verifies page/aggregate hashes and runs A/B without manual stitching
- 🟢 Development A Formal L0 and fixed-definition Development B replication complete
- 🟡 L1 Development Minute acquisition remains separately unapproved

## Research objective

Build a new independent JPX cash-equity LONG-only system and compare it against the current integrated Ark Selector -> Entry -> EXIT baseline.

Target research path:

`JPX PIT universe -> LONG Momentum / Continuation Selector -> LONG Entry -> EXIT -> Capital Allocation -> Cash Equity Portfolio`

This is not a SHORT-off patch to the current selector. The new line must discover long opportunities independently while keeping existing LONG+SHORT research, Lane Y, main and the live execution circuit unchanged.

## Non-negotiable trading constraints

- cash equity only;
- LONG only;
- no margin buy;
- no short selling;
- no leverage;
- 100-share lot contract;
- quantity cannot exceed available cash;
- no broker, Excel-order or RSS-order writes in research.

## Data strategy

L0 uses only Daily + dated PIT Master. Minute requests remain zero until L1 is explicitly released.

The 205 evaluation sessions require 205 dated Master requests and 206 Daily requests. The one extra Daily request is the non-evaluation `2024-09-09` causal warm-up needed to calculate the adjusted close-to-close return for the first Development A session. Total Formal L0 budget is therefore 411 base requests, with zero Minute requests.

When minute data is authorized, it is not a Selector-only asset. The same immutable raw payload must remain reusable for Selector, Entry, EXIT, Capital Allocation and integrated portfolio replay.

Final L2 fit and performance claims require full point-in-time JPX cross-sections on released dates. Winner / near-winner / control subsets are diagnostic only.

## Historical split v3

| Partition | Sessions |
|---|---:|
| Development A | 25 |
| Development B | 15 |
| Development C | 20 |
| Development D | 20 |
| Validation | 30 |
| Validation Replication | 20 |
| Primary OOS | 30 |
| Contingency OOS | 30 |
| Admission Reserve | 15 |
| **Total** | **205** |

Contingency OOS cannot be opened because performance is poor. Reserve is deterministic replacement data for admission failures only.

## Independent review

Claude returned `CONDITIONAL GO`. Ark adopted the useful controls but did not blindly copy the review. Important corrections include:

- reserve arithmetic is constrained to the actual 205 clean sessions;
- causal past history remains legal across partition boundaries;
- targets may not cross the same-session close;
- future realized volatility is not used as a decision feature normalization;
- Ark's existing timestamp / terminal-auction contract remains authoritative;
- historical example dates from the review are not treated as Fresh dates.

See `docs/phase57-long-only-independent-review-disposition-v1.md`.

## J-Quants entitlement evidence

User screenshots dated 2026-09-15 show:

| Item | Status | End |
|---|---|---|
| Light | active | 2026-10-06 19:02 JST |
| Tick + OhlcMin | active / cancellation scheduled | 2026-10-06 19:07 JST |

No credential value has been read or committed.

## Formal L0 result

The approved plan SHA `2a10ba6f49addaec91251cb5cb45ea1bcd21356b4c1c9d2bccc20f6aace7a258` completed in GitHub Actions run `34916384636`. The repository Actions secret path was reused without revealing the credential. The immutable cache was encrypted, plaintext was removed, and Development B was replicated from the same cache with zero additional provider requests in run `34917676944`.

| Partition | Sessions | Eligible rows | Eligible/input | Mean +3% | Mean +5% | Mean +10% |
|---|---:|---:|---:|---:|---:|---:|
| Development A | 25 | 94,638 | 86.218% | 208.44 | 66.96 | 13.48 |
| Development B | 15 | 56,731 | 86.045% | 200.73 | 69.87 | 17.20 |

Development B reproduced the daily opportunity set without changing the threshold or return definition. L0 therefore passes its market-opportunity purpose and is frozen; further L0 tuning is not warranted. Validation, OOS, Contingency OOS and Reserve outcomes remain unopened.

Official storage/deletion terms remain in force. Daily/Master raw and reversible derivatives must be purged by 2026-10-06 19:02 JST; Minute/causal-5m material by 19:07 JST. The encrypted integrated cache artifact expires on 2026-10-06 and contains no public plaintext raw data.

## This-week completion gate

The research is not considered complete when the Selector looks good. Completion requires a frozen integrated comparison against the current Ark baseline.

| Stage | Required output |
|---|---|
| L0 | daily LONG opportunity census |
| L1 | early-detection / remaining-upside structure |
| L2 | frozen LONG selector candidate |
| Entry | LONG-only entry replay on the new selector |
| EXIT | exit replay on identical LONG entries |
| Allocation | cash-only 100-share constrained allocation |
| Integrated | end-to-end portfolio ledger |
| Comparison | current Ark vs new LONG-only on predeclared metrics |

Before Validation is opened, the comparison metric set and GO/NO-GO rule must be frozen. At minimum the integrated comparison must report after-cost Net, Profit Factor, MaxDD, Return/DD, win rate, trade count, portfolio return, cash utilization, missed opportunity, symbol/sector concentration and SHORT/margin contribution (required to remain exactly zero in the new system).

A Development win is only a candidate-generation result. Validation / OOS decide whether the edge survives. No post-OOS tuning is allowed to force the new system to beat the current Ark baseline.

## Speed objective

Research should move quickly enough to complete the LONG-only integrated candidate and current-Ark comparison this week, without weakening future-leak, PIT, OOS, safety, or data-integrity controls.

## Immediate next action

Obtain separate operator approval for the Development A+B L1 Minute block, reuse the encrypted Daily/Master cache and acquire each released session only once as the integrated Selector/Entry/EXIT/Allocation/Portfolio dataset. The current planning estimate for 40 released sessions is 470 Minute pages and approximately 14.97 million sparse source rows; no Minute request is included in the completed L0 approval.
