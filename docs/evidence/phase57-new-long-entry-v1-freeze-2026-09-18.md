# Phase57 NEW LONG Entry v1 — User-Authorized Freeze / Stop Record

Date: 2026-09-18 JST

Status: **TIMING_LOCATION_FROZEN_NOT_VALIDATED**

## 1. Decision and scope

The user explicitly requested that the current Entry be frozen and that only the freeze be performed. This record accepts the existing two-opportunity timing/location candidate as **NEW LONG Entry v1** and stops further work at that boundary.

This is a documentation-only acknowledgment of the already-frozen contract and completed parity evidence. It does not introduce a new architecture, change an implementation identifier, authorize downstream integration, or upgrade the candidate to independently validated or production-ready status.

Repository: `Iam-2squared/ark-terminal`  
Branch: `research/phase57-long-only-cash-equity`  
PR: **#587 — Draft / unmerged**

## 2. Immutable frozen snapshot

**Frozen implementation / evidence source commit:**

`6fabde7dfe208e19d5611e0a290b4df6724e562e`

The implementation, tests, evaluators, contracts and evidence at this exact commit are the v1 baseline. The commit introducing this acknowledgment adds documentation only; it does not replace the frozen implementation snapshot.

Authoritative records at the frozen source commit:

- Contract: `docs/evidence/phase57-new-long-entry-two-opportunity-contract-2026-09-18.md`
- Parity and artifact hashes: `docs/evidence/phase57-new-long-entry-two-opportunity-parity-2026-09-18.md`
- Source Entry Location Study commit: `a0a263ddc6abd83c9dca0b9f4bc2c86b9753b2bb`
- Recorded parity workflow input commit: `63eadbd661e7959d0a96af46c38c69db80736250`
- Recorded successful parity workflow run: `35250519787`
- Recorded parity artifact ID: `10508583428`

The existing parity record contains the full-ledger, summary, manifest and artifact ZIP hashes. Those records are retained unchanged. No test, replay, acquisition or evaluation is rerun for this acknowledgment, and no new CI result is claimed here.

## 3. Fixed Entry behavior

1. Preserve the Frozen LONG Selector without modification.
2. At t0, expose `INITIAL_ENTRY_OPPORTUNITY` using the existing causal reference semantics, independently of future dip/no-dip outcomes. This is an opportunity event, not an automatic order or fill.
3. Observe exactly the first completed 5-minute CLOSE against the pinned Selector Decision Price.
4. When that CLOSE is below Decision Price, expose at most one `DIP_REPRICE_OPPORTUNITY` using the next regular 5-minute OPEN reference only when that reference is causally observable. A dip CLOSE alone does not establish an available priced opportunity.
5. Otherwise terminate with continuation, unknown or boundary-expiration semantics as defined by the existing contract and implementation. Do not fabricate prices or add t10/t15/t20 retries or recovery-confirmation loops.

This is not a blanket instruction to wait five minutes for every candidate. `FIRST_CLOSED_DIP` is not known at t0. Future HIGH/LOW, later bars and evaluator outcomes remain excluded from decision inputs.

## 4. Responsibility and evidence limits

Entry owns opportunity timing/location, causal state and the audit trail. Capital Allocation owns whether an available opportunity is funded and its quantity/notional; no fixed tranche fraction, including 50/50, is introduced. EXIT owns management after an actual fill.

The retained evidence is Historical Development / outcome-exposed descriptive and parity evidence only. Better dip-cohort reference locations do not establish whole-system profitability, independent generalization, or actual opportunity capture after funding. `DIP_REPRICE_OPPORTUNITY` does not mean the bottom is confirmed; further downside remains possible. The contract's known limitations and killed hypotheses remain in force.

## 5. Stop boundary

After this freeze acknowledgment, stop. No downstream connection or additional research is authorized by this record.

Do not mutate Selector, Entry architecture, thresholds, EXIT, Capital Allocation or Portfolio. Do not reopen 1-minute research, Fresh/OOS, new price-provider acquisition, model fitting, or timing searches. Do not use EXIT/PF/Portfolio as Entry acceptance gates. Do not promote production behavior or merge main.

All existing trading/order/write/promotion safety flags remain false and unmodified. This documentation commit authorizes no live or paper execution.

Further work requires a new explicit user instruction and must preserve this frozen v1 snapshot and its evidence rather than silently overwriting them.
