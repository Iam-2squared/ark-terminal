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
- 🟢 Formal L0 acquisition/admission/census path implemented and tested with zero provider requests
- 🟢 Causal 1m -> 5m, evaluator-only L1 labels, shared replay interface and four-stage comparison harness implemented
- 🔴 New J-Quants Historical acquisition remains blocked

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

## Remaining acquisition blockers

- confirm a private user-only cache outside the public GitHub repository;
- pass the mandatory cancellation purge dry-run;
- confirm API credential availability in the intended runtime without exposing it;
- explicit operator acquisition approval outside the committed plan.

Official storage/deletion terms were verified on 2026-09-15. Daily/Master raw and reversible derivatives must be purged by 2026-10-06 19:02 JST; Minute/causal-5m material by 19:07 JST. The current Work process has no J-Quants credential, and no value was requested or observed.

Fresh prospective selection is already frozen by rule. Exact future dates are recorded mechanically as sessions occur and do not block historical Daily/Master cache acquisition.

Until then acquisition remains fail-closed.

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

Clear the four remaining gates (private cache destination, tested purge dry-run, credential presence and plan-SHA-bound operator approval), acquire Daily + dated Master once into private immutable cache, mount Development A only, and run Formal L0. Minute acquisition remains zero until L1 block release.
