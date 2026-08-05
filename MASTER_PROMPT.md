# Ark Terminal Development Constitution

## Project
Ark Terminal is an AI investment platform for Japanese equities. Version 1.0 focuses on analysis, discovery, market intelligence, backtesting, paper trading, trade memory, accuracy monitoring, and approval-gated learning.

## Design principles
- Reuse and connect existing engines before adding new ones.
- Avoid duplicate logic and future data leakage.
- Keep live broker execution disabled in v1.0.
- Require explicit human approval before model promotion.
- Keep safety, auditability, and reproducibility ahead of feature count.

## Working branch policy
- Confirm the current branch from Git before work.
- Never hard-code a permanent working branch in this document.
- Start each new Phase from the latest `main` on a dedicated branch.
- Never commit directly to `main`.

## Definition of Done
A change is complete only when requirements are met, existing behavior is preserved, type and lint checks pass where configured, unit/integration/regression tests pass, relevant documentation is updated, CI is green, and the PR summary is complete.

## v1.0 safety boundary
- Live trading: disabled
- Broker connection: disabled
- Automatic model promotion: disabled
- Human approval: required

## Release flow
Candidate -> Walk Forward -> Comparison -> Human Approval -> Production
