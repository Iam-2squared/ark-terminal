# Phase57 Capital Sizing R35 — Cash-Only MAX3/4/5 Precommit

Date: 2026-09-26 JST  
Scope: Development-only research; no broker/order/paper/live/production action.

## Purpose

Freeze the remaining sizing ambiguity before any Final EXIT-dependent Portfolio
performance or >=5% opportunity allocation score is inspected.

## Reused causal architecture

This adapter reuses the existing Lane-C Max-N slot-budget rule rather than
inventing a new allocation family:

- current portfolio equity = available cash + **fresh known-now** market value
  of open cash-equity LONG positions;
- target slot budget = current portfolio equity / N;
- N is exactly 3, 4, or 5;
- MAX3 is PRIMARY; MAX4/MAX5 are sensitivity references only;
- candidate priority is the already-precommitted causal order:
  `newEligibleRank ASC -> savedV1Score DESC -> symbol ASC`;
- quantity is the largest 100-share lot whose entry notional is no greater than
  both target slot budget and currently available cash.

Unrealized value may change the target slot budget but never becomes reusable
cash. Only a confirmed EXIT releases cash.

## Event order

At each timestamp:

1. ingest only information known by that timestamp;
2. apply confirmed EXITs;
3. release confirmed EXIT cash;
4. refresh current marks for still-open positions;
5. if every open position needed for MTM sizing has a fresh known-now mark,
   compute current equity and slot budget;
6. rank same-time Entry candidates by the frozen causal priority;
7. size/admit in that order subject to cash, 100-share lot and MAX-N capacity;
8. record marks/equity.

If current MTM sizing is incomplete, do not forward-fill or substitute entry
cost/stale/future marks. New Entry sizing for that timestamp is unresolved and
no fictitious quantity is created.

## Cash-equity invariants

- initial cash: JPY 1,000,000;
- LONG-only / CASH-only;
- no margin, leverage, borrowing, shorting or collateral reuse;
- cash must remain >= 0;
- no order may spend unsettled/fictitious cash;
- 100-share lots only;
- no quantity below one lot;
- no capacity above MAX3/MAX4/MAX5;
- no MAX6+ or MAX10 re-search after results.

## Outcome separation

The following are forbidden as rank/sizing inputs:

- realized >=5% bucket;
- future High/Low;
- future return;
- MFE/MAE;
- Final EXIT outcome;
- final PnL;
- capture metrics.

The >=5% bucket is evaluator-only after this sizing contract and Final EXIT are
frozen.

## Final comparison

Compare exactly MAX3 vs MAX4 vs MAX5 under the same Final Frozen Entry, same
Final Frozen EXIT, same cost/event ordering and same causal ranking.

Primary: MAX3.

Required Portfolio outputs include Return, MaxDD, PF, capital
lock/utilization, concentration, turnover, minimum cash, gross exposure,
insufficient-cash rejects and reproducibility. Evaluator-only attribution also
reports >=5% opportunity reach/miss/share/capture without feeding those values
back into allocation.

## Exposure / Safety at precommit

This document contains no Portfolio performance and opens no protected data.
Provider requests remain 0. Safety9 remain false. No main merge, live, paper,
production, broker write, Excel order write or RSS order function is authorized.
