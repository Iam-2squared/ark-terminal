# Phase57 Execution Layer v1 — transmission locked

PRE-LIVE EXECUTION INFRASTRUCTURE ONLY. NO REAL ORDER TRANSMISSION, NO BROKER WRITE, NO EXCEL ORDER WRITE, NO RSS ORDER FUNCTION, NO LIVE TRADING. This is an independent decision-aftercare layer, not a strategy change. Nine safety flags remain false even when fixture state is ARMED. No environment variable, human flag or adapter injection unlocks the production submission/cancellation methods.

Base inspected on GitHub: #584 and existing `feature/phase57-execution-layer-v1` both at `61cb50b7eea670c8473811a4198f919e7065671b`. There was no Execution PR. Work is isolated in that branch; #583, #584 and their source/freeze/OOS evidence are untouched.

## Reuse audit

The repository search covered execution/order/fill, broker and Excel preparation, reconciliation/cash/buying power, journal/restart/idempotency, emergency/ARM/EXIT_ONLY and semi-auto/pre-live code and tests.

| Classification | Existing implementation | Decision |
|---|---|---|
| REUSE | `scripts/lib/phase57-offline-parity.mjs`: EvidenceLog, timestamp/session/freeze primitives | Same exclusive writer lock, fsync, hash-chain and torn-tail rejection; no modification. |
| REUSE | `scripts/lib/phase57-operational-robustness.mjs`: reconcileState, classifyFreshness, applyExternalCashFlow | Strict quantity/money reconciliation plus buying-power/open-order checks; external flows stay out of PnL. |
| KEEP | `predict/semi-auto/phase51-foundation.js`, `predict/prelive/phase52-safety.js` | Preserve readiness/approval/kill-switch principles and original regressions; their permissive numeric defaults and non-durable ID arrays are unsuitable here. |
| KEEP | `predict/broker/readonly-broker-reconciler.js` | Preserve external-state-is-not-internal-truth semantics and regressions. Its broker schemas are not falsely equated with this fixture schema. |
| KEEP | `predict/broker/execution-bridge.js`, `broker-write-lock.js` | Existing bridge permits PAPER/DRY_RUN adapters. Do not connect it to this stricter always-locked layer. |
| KEEP | `predict/paper/paper-order-book.js`, simulators, shadow audit logs | Preserve tested partial/filled/terminal distinctions; paper trading remains disabled here. In-memory order-book updates alone cannot provide durable atomic fill+position replay. |
| KEEP | `tools/rss_order_preparation.py`, `rss_order_dryrun.py`, approval kill-switch/dry-run | No imports/calls/order-sheet/formula modifications. Existing ARMED label semantics differ; never use them to infer transmission permission. |
| NEW | `scripts/execution/*` | Strict canonical intent, aggregate pending-risk gates, event reducer, fixture-only transitions, locked adapter, manual abandoned-lock recovery and evidence runner. |
| COMMONIZE / DEPRECATE | None in this change | Reuse exported helpers without refactoring protected runtime code. No historical APIs removed. |

## One-command fixture run

From the repository root on Windows or Linux, with Node 22 and Git installed:

```powershell
node scripts/execution/run-fixture.mjs execution-run-001
```

Choose a new output directory for each run; existing directories fail rather than overwrite. No Excel, MSII, account, network or market credentials are used. The runner verifies the actual Frozen Main file digest, runs the failure matrix, then processes a synthetic intent through risk, three fills, replay and emergency stop. `execution.jsonl`, seven categorized evidence files, status, snapshot, tests log and a hash manifest are written. CI also runs the old 150 frozen-runtime tests and 27 selected Phase51/52/broker/order-book regressions. No historical performance is remeasured.

## Interfaces and conservative policies

`orderIntent` requires a known symbol from the configured universe, canonical version identifiers, explicit causal timestamps, source/decision SHA-256 identities, strict positive 100-share order quantity and explicit BUY/SELL + OPEN/CLOSE. EXIT is derived from an existing matching position; no assumed reverse trade. Evidence hashes are provenance identities, not automatic certification of their contents. A future trusted decision bridge must bind them to the originating signed/sealed evidence; no live bridge is present here.

LIMIT and MARKET intent vocabulary is modeled; only DAY is accepted. Unknown order types or time-in-force are rejected. No broker-specific tick-size, order-type, borrowing or trading-halt assumptions are encoded. Those remain external constraints to validate before any future real adapter. Synthetic limit values are illustrative test inputs, not recommended trading limits or new MAX_3 research.

Intent identity excludes arrival time and includes decision/session/version, side/effect, quantity, prices and evidence. A repeated decision returns the original identity without a second candidate; conflicting payloads fail. This v1 deliberately supports one canonical intent per decision, stricter than maxOrdersPerDecision values above one. Event IDs are also durable. Replayed identical callbacks are no-ops; new callbacks reusing a fill ID fail. Invalid reducer events are journaled and revoke readiness, while leaving financial state unchanged.

Risk checks run at validation AND submission request. They require all explicit hard limits, healthy causal feed/account context and exact account/position/open-order reconciliation. Pending OPEN quantities reserve buying power and symbol/gross exposure; worst-case net exposure assumes either side may fill first, never that opposing pending orders cancel out. Pending CLOSE quantities reserve position inventory. Realized plus marked unrealized loss, excluding external flows, is checked against session-opening equity and absolute loss limits. Orders, counts and loss counters are session-bound; crossing sessions requires a separately initialized and reconciled run, never an automatic reset. CLOSE orders remain subject to operational safety and configured limits; EXIT_ONLY does not override unknown accounts or limits.

The simulation position ledger is separate from the Frozen historical ledger. BUY OPEN purchases LONG; SELL OPEN reserves full cash collateral and records nonreusable short proceeds. CLOSE releases the exact position and collateral portion. Partial fills may be smaller than an order lot because they represent execution observations, not newly sized orders. Average fill price is quantity-weighted; fees are applied once; overfill, invalid fee and incompatible limit fill are rejected. Trading PnL and DEPOSIT/WITHDRAWAL/MANUAL_ADJUSTMENT are distinct. All balance changes invalidate account readiness until a new matching snapshot. This layer never recomputes strategy sizing: any future MAX_3 decision must use a newly reconciled equity input upstream.

## Modes, order state and recovery

Modes: DISARMED, SHADOW, ARM_REQUESTED, ARMED, EXIT_ONLY, EMERGENCY_STOP. A named manual operator is required for ARM changes/clearing emergency; fixture preflight must pass to reach ARMED. The production mode always adds TRANSMISSION_LOCKED. Operator identity here is an audit field, not a production authentication mechanism. No Excel permission button is polled or trusted.

Order states: CREATED → VALIDATED → READY or BLOCKED; fixture READY → SUBMISSION_REQUESTED → SUBMITTED → ACCEPTED → PARTIALLY_FILLED / FILLED. Explicit REJECTED, CANCEL_REQUESTED, CANCELLED, UNKNOWN and RECONCILIATION_REQUIRED branches are checked. Terminal orders cannot resurrect. Cancellation does not manufacture an exit or fill. Fills arriving while CANCEL_REQUESTED can still be recorded; cancellation confirmation alone never changes position quantity. No external adapter call occurs inside the reducer.

`TransmissionLockedAdapter.submitOrder()` and `.cancelOrder()`, and the public runtime methods of the same names, always return blocked/transmitted=false. `MockExecutionAdapter` only manufactures fixture response values. Runtime fixture event processing cannot dispatch an arbitrary injected adapter. SUBMISSION_REQUESTED and subsequent execution observations are accepted only in SYNTHETIC_FIXTURE mode. Production schema mode cannot submit, accept or fill a real order. Both modes currently admit only exposed fixture dates and cannot consume future/reserved sessions.

COMMIT contains the event and derived-result hash in one fsynced record. Financial state is assigned only after successful append. Replay verifies the existing hash chain, exact config identity and deterministic result hashes. On restart, context becomes unknown and mode DISARMED (or persistent EMERGENCY_STOP); in-flight submitted/accepted/partial/cancel requests become UNKNOWN without resubmission. A known complete FILLED state remains complete. UNKNOWN resolution requires explicit operator, evidence, matching account snapshot and matching cumulative fill quantity; it cannot invent missing fill history or return to READY. Duplicate/conflicting events are never auto-retried through an adapter.

Emergency stop blocks unsubmitted intents and prevents new requests; already observed fills remain accounting facts and may be processed in fixture mode. Clear requires explicit confirmation and evidence and leaves the system DISARMED/unreconciled. Connection loss never implies a position closed.

A hard process crash leaves EvidenceLog's writer lock. It is intentionally not auto-deleted. After manually stopping **every writer**, `recoverStoppedWriter` requires operator, `confirmAllWritersStopped=true`, exact journal SHA-256 and the original config; it verifies replay on a temporary copy, rechecks the original hash, quarantines the lock and writes a manual recovery record. The operator's stopped-writer confirmation is essential; this function is not a distributed lease. Torn/corrupt journals are preserved and rejected; v1 does not truncate them or silently discard uncertain fills. Their recovery requires independently reconciled evidence and a new audited run. This is a remaining operational procedure, not an automatic repair claim.

## Remaining gates

- #584 normal-bar finalization semantics and prospective Realtime Shadow remain unverified.
- No live decision-to-execution bridge, real account snapshot provider, broker rule inventory or RSS order adapter is connected.
- Future integration must bind real evidence, identities, timestamps, broker constraints and user authentication; mutable local audit hashes are tamper-evident chains, not signatures against a privileged attacker.
- Full-session handover, broker-specific late fills/corrections and recovery of corrupt original journals require explicit external reconciliation policies before live use.
- Future transmission release requires a separate reviewed code change and authorization. No runtime flag can accomplish it in v1.

Current status is **TRANSMISSION_DISABLED_FIXTURE_PASS / PRE_LIVE_INFRASTRUCTURE_ONLY**, not operational live readiness, Realtime Shadow PASS, finalization PASS, OOS PASS or production readiness. Research PR remains Draft/unmerged.
