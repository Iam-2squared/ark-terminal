# No.1.1 MSII Cash-only Integration — Gate 0 (read-only boundary)

Status: CONTRACT_ADMISSION_ONLY / NOT_PRODUCTION_READY
Frozen source commit: 10c94c92c4bd2a59a22744667fd0210252602df4
Source: research/ark-integrated-no1-1-freeze-20261008/INTEGRATED_NO1_1_FREEZE.json

## Scope
- Recover *only* audited MarketSpeed II RSS/Excel account read-only and locked execution infrastructure from PR #584 and UI read-only from PR #588.
- No blanket merge of old research branches; no Selector/Entry/EXIT/Rank/Capital code changes.
- No live/paper order, no broker write, no Excel order write, no RSS order function invocation, no automatic production promotion.
- No automatic RegisterXLL. Excel add-in is enabled through Excel itself.
- All unknown, stale, missing, duplicate, partial-fill, ownership mismatch, COM exhaustion, restart-unverified conditions fail closed.

## Frozen event semantics that must survive mechanical mapping
1. PULLBACK and SHARP_DROP formal State9 primary are excluded from *all* Entry admissions; unknown state must preserve frozen unavailable-state semantics.
2. First legal broker SELL fill of the trading session sets a persistent no-new-BUY latch for the remainder of that session; SELL_INTENT or unfilled/cancelled orders do not set it.
3. Same timestamp: legal SELL fill and cash/slot release precede BUY admission, but the latch prevents that BUY; reset only on verified next trading session.
4. Existing EXIT decisions continue after latch; no forced liquidation or fabricated fill.
5. Cash-only LONG, MAX3, 100-share lot, 15:20 Entry cutoff; frozen V5 ranking, reserve, quantity and ordering never recalculated by adapter.
6. Historical next-bar reference fills are not broker fills; cash release requires verified broker execution and reconciliation.

## Adapter admission contract — do not guess missing fields
- Inputs: frozen version and source hash, immutable decision/event identity, session and decision timestamp, causal source receipt timestamp, symbol, side, effect, quantity, order type, SOR, account type, strategy intent lineage, and explicit broker execution evidence for SELL-fill latch.
- Symbol mapping (e.g. five-character exchange code to four-character .T) requires independently verified symbol identity and collision tests; no blind truncation.
- Reject missing/ambiguous fields rather than filling from old SHADOW_ORDER_INTENT placeholders.
- No rank/reselection, quantity modification, fabricated order ID or fallback to margin/short.
- Emit non-executable, hashed cash intent only after contract validation.

## Outstanding infrastructure gates
- One authoritative RSS Fresh Snapshot, 30-second freshness, explicit source-health status.
- Local private frozen Ownership baseline and current broker/Ark/external reconciliation.
- Bounded Excel COM retries, recoverable automatic fault halt, restart recovery. Existing ledger has a manual reset primitive; simplify it before live so it does not become an additional user authorization gate.
- Persistent unique RSS order-ID and intent-to-broker-order-to-fill mapping, idempotency and partial fills.
- Runtime safety, ownership and pipeline connected into UI Read Model; six-page local UI read-only E2E.
- Synthetic adversarial tests, then real account SHADOW/LOCKED tests with zero order transmissions.
- **One user-operated live authorization only: Excel's MarketSpeed II RSS order-enable setting.** No additional Ark manual unlock/independent-review approval. Offline/Windows verification are engineering acceptance checks, not user-facing permission toggles. See ONE_MANUAL_PERMISSION_POLICY-ja.md.

## Evidence required before moving to Gate 1
- Read exact No.1.1 and No.1 immutable hashes and runtime event schema.
- Compare PR #584/#588 code against this branch; select only necessary modules.
- Record exact account/RSS order parameters from official MSII specification.
- Record every unknown as BLOCKED, not PASS.
