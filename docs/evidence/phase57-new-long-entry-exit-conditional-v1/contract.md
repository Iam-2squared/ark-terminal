# Frozen NEW LONG Entry v1 → Existing LONG EXIT conditional diagnostic

Date: 2026-09-18 JST. Historical Development / outcome-exposed only.
This contract is written before this task's EXIT measurements. The new user EXIT
request authorizes this downstream diagnostic; the Entry freeze remains intact.

## Identity and scope

- Remote branch / PR: `research/phase57-long-only-cash-equity`, #587 Draft/open/unmerged.
- Starting HEAD: `efa7efb5235dcb1b711599d5c0ba0a196ec5fab9`; no post-handoff diff.
- Frozen Entry implementation/evidence: `6fabde7dfe208e19d5611e0a290b4df6724e562e`.
- Saved parity run `35250519787`, job `105301441720`, artifact `10508583428`.
- ZIP SHA256: `64721ad1b8f7b348721956bcad41353fbe171d430b153f5d9abc6b6d59a95232`.
- Ledger SHA256: `2286c023f6c53a2c73d67ad16eb51a57c8f2921cae0f749ada75e60af3f10002`.
- Summary SHA256: `48a1dbea20da43f6fd3882e9b8ae26aa8b6403518d3fe533b385c435fa83cba7`.
- Manifest SHA256: `c81dae9c4608373bbda20484034abbedb5362d01c92f08f9cbb9a45273a709f2`.
- Anchor identity SHA256: `985218fd1520bde127a72e9b049dd5a1840d42a928e7e850ea4e3e4d7ed82121`, N=2743.
- Existing EXIT: `LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1`, freeze commit
  `ba0ccdb2aea7e5fc9fee817c0bd95f09427108f8`; Development-selected, not validated.
- Import its exact single-policy research interface and unchanged pure runtime.
  Runtime SHA256 `b3e8f07086cfa65173524f62b78571f606e5d1c372a4cec1c16343c73d8c6c23`;
  interface SHA256 `d7b30e6a4419c10bf7cc2821b70159653af1cf0263d6abac09188c0f47a02a00`.
- Comparator: inherited `FIXED12` from the same runtime. No candidate selection,
  new EXIT implementation, model/analog fit, threshold or horizon search.

## Interface (research assumptions, not executable-fill certification)

| Field | Definition |
|---|---|
| opportunity type | Exact saved `initialEvent.eventType` or `secondaryEvent.eventType` |
| anchor id / symbol / session | Exact saved ledger identity; join saved paths by anchor id |
| opportunity timestamp | Exact saved event timestamp; never synthesize t0+300 seconds |
| reference price | Exact saved `referencePrice`, only `REFERENCE_OPEN` is price-eligible |
| position-start timestamp | Saved INITIAL referenceTimestamp, or saved DIP opportunityTimestamp; must equal the matching scheduled bar start and be no earlier than opportunityTimestamp |
| research fill assumption | Hypothetical unit position at the saved scheduled OPEN reference, zero latency/queue/slippage; optimistic and not proven executable |
| funding | Conditional on that opportunity being funded; no automatic trade, no INITIAL+DIP sum, no sizing/allocation choice |
| exit valuation | Existing completed-CLOSE reference at the decision time; not guaranteed execution |
| cost | Inherited round-trip 0.05 percentage point per unit-position reference trade |
| start state | Fresh EXIT state per conditional position; DIP does not inherit INITIAL state or pre-DIP bars |
| observable horizon | Saved 5m bars only, with post-start timestamps; no raw/1m/provider access |
| missing | Missing reference → ineligible; missing expected bar before exit → censored/NULL; no flat no-trade substitution |
| lunch | EXIT expected trading-slot count skips lunch, elapsed clock time includes it; no new Entry during lunch |
| session cap | Unchanged min(12, saved remaining regular slots); no overnight. Saved post-November 15:25/auction gap remains unresolved/censored, never filled |
| diagnostic session end | Last safe continuous-session cutoff: 15:00 before 2024-11-05, 15:25 thereafter; include all expected afternoon slots and skip lunch. Label SAFE_REGULAR_END, never auction/official close |

The saved reference-availability definition is inherited unchanged. It relies on
the saved bar's availability; sparse underlying minute coverage is not upgraded
to complete tradability. Report observedMinutes=5 sensitivity from saved metadata
only. Provider timestamp, queue, fill and auction limitations remain unresolved.

## Diagnostic populations and metrics

Retain all 2743 INITIAL events including missing/boundary. DIP is the 541 actually
emitted saved opportunities, not the 580 hindsight first-dip labels. Report
reference eligibility, EXIT standalone eligibility, and Fixed12/EXIT common
complete cases separately. The original primary878 and dip328 are labeled
subsets for continuity, not silently substituted for full populations.

For each cohort separately: own-start +5/10/15/20/30/45/60 wall-clock minutes
within one continuous segment, plus SAFE_REGULAR_END. Missing or segment crossing
is NULL with reason. Include entry interval OHLC only after its hypothetical OPEN;
DIP excludes every earlier bar. MFE=max(0,HIGH return), MAE=min(0,LOW return).
Time to extrema is the first containing bar's [start,end] interval (exact intrabar
time unknown); positive/recovery time uses observed completed CLOSE. Recoveries
after an adverse LOW require a strictly later bar CLOSE to avoid intrabar ordering
claims. Threshold hits +1/+2/+3/+5 are evaluation labels only. Giveback=MFE-CLOSE.
Report adverse counts, later-close recovery, deep-adverse winners, and failed Dip
(D30 adverse then negative final diagnostic CLOSE) as retrospective descriptions.

Same paired identities for Fixed12 vs existing EXIT: N, net sum pp, mean/median %,
win rate, PF, worst, p05, worst-5%-mean, entry/exit-order cumulative unit-return DD
proxies (not portfolio MaxDD), MFE capture, giveback, holding bars/time, exit reason,
+3/+5 reference-window winner preservation and final net >= level. Use Fixed12's
own available window for both arms' MFE denominator. Same-bar HIGH touches are
not called premature; intrabar order is UNKNOWN_INTRABAR_ORDER.

Prior risk cohort is EXACT saved primary328 → buyImprovementPct>0 (299) → saved
secondaryD30.downside>=2 (106), >=5 (21). Save every identity, missing status,
existing EXIT action, pre-exit MAE, reference net delta vs Fixed12, whether exit
precedes additional downside, and recovery/winner outcomes. Unknowns stay in the
ledger. No risk-subset membership enters a decision.

## Architecture decision

Choose one of REUSE_EXISTING_EXIT_AS_IS / ADAPT_EXISTING_EXIT_MECHANICALLY /
BUILD_NEW_LONG_EXIT / EXIT_ARCHITECTURE_INCONCLUSIVE after observing evidence.
Mechanical field/rebase adaptation is separate from policy quality. Transfer
quality is descriptive; no newly invented numerical acceptance threshold or OOS
claim. If existing state logic demonstrably cannot meet the requested risk/upside
needs, BUILD_NEW may propose a minimal architecture, without fitting it here.
Otherwise describe evidence/uncertainty rather than forcing a superiority claim.

All trading/order/write/promotion flags remain false. Selector/Entry/Allocation
and legacy lanes unchanged. Fresh/OOS/provider/model/Entry-replay/search counts
are zero; no main merge. No portfolio aggregation or independent validation.
