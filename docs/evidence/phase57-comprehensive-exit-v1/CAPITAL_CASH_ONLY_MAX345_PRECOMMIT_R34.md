# Phase57 R34 Capital Cash-Only Precommit (connector retry)

Date: 2026-09-26 JST
Repo: Iam-2squared/ark-terminal
Branch: research/phase57-long-only-cash-equity
PR: #587
Basis HEAD: 64cfdc669dac0b4801d4c4222d6cfbc41615a0a0

## Purpose

Preserve the Capital preparation contract before any final EXIT-dependent portfolio performance is inspected.

## Frozen Capital boundaries

- Cash equity only.
- LONG-only.
- No margin, leverage, borrowing, shorting, or negative cash.
- Initial cash: JPY 1,000,000.
- Lot size: 100 shares.
- Confirmed same-time EXIT cash release occurs before same-time Entry sizing.
- Missing/unresolved EXIT never fabricates released cash.
- Orders requiring more than available cash are skipped.
- Comparison set is exactly MAX3 / MAX4 / MAX5.
- MAX3 is PRIMARY; MAX4 and MAX5 are sensitivity references only.
- Do not reopen MAX10 or add MAX6+ after seeing results.

## Causal priority inputs

Use only already-known causal rank/score inputs from the Frozen Selector / Frozen Entry lineage.

Primary existing inputs to reuse where available:
- newEligibleRank (ascending)
- savedV1Score (descending)
- stable symbol tie-break

No future outcome may enter Capital ranking or sizing:
- realized >=5% bucket
- future High/Low
- future return
- future MFE/MAE
- EXIT outcome
- final PnL

The >=5% opportunity bucket is evaluator-only after allocation.

## Pre-Freeze preparation allowed

Before Final EXIT Freeze:
- ledger interface
- event ordering
- cash accounting
- 100-share lot sizing
- MAX3/MAX4/MAX5 capacity handling
- rank-to-priority adapter
- cash-only/no-margin invariants
- future-feature denylist
- evaluator-only bucket attribution
- scorecard/reproducibility helpers
- synthetic tests

Before Final EXIT Freeze it is forbidden to:
- run final Portfolio performance using a hypothetical EXIT
- tune rank/sizing from future >=5% labels
- change Capital thresholds after observing EXIT candidate performance
- reuse old 277-trade performance as final evidence

## Post-EXIT comparison

Once Final EXIT is frozen, compare only:
- MAX3 PRIMARY
- MAX4 sensitivity
- MAX5 sensitivity

Required outputs:
- Portfolio Return
- Max Drawdown
- Profit Factor
- capital lock/utilization
- concentration
- turnover
- reproducibility
- minimum cash
- gross exposure
- rejected-for-insufficient-cash count
- evaluator-only Low-to-High bucket acceptance/allocation
- >=5% opportunity capital reach / miss / share / realized capture

## Safety / exposure

Entry Dual Freeze remains unchanged.
No protected partition is opened.
Provider new acquisition remains 0.
Safety9 remain false.
No main merge, live, paper, production, broker write, Excel order write or RSS order function.

## Current status

This document is a contract/precommit only. It does not contain final EXIT-dependent Capital performance.
