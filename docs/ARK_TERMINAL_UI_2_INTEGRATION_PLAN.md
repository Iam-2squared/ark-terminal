# Ark Terminal UI 2.0 — verified data integration plan

Status: **READ-ONLY INTEGRATION CONTRACT / NO ORDER AUTHORIZATION**  
Scope: Japan cash equities, LONG-only  
UI source snapshot: `ui/ark-terminal-2-standalone` @ `48c647e5b4cd6f865818565814c71ff14ca8470d`  
Execution source branch: `research/phase57-msii-realtime-parity-shadow-v1`

## 1. Non-negotiable boundary

The approved six-screen UI is a presentation layer. It does not become an execution authority.

The UI integration MUST NOT:

- change Selector / Entry / EXIT / Capital Allocation research logic, thresholds, weights, or frozen specifications;
- enable margin, short selling, margin fallback, paper trading, live trading, broker writes, Excel order writes, or RSS order calls;
- convert a UI button into an order transmission path;
- classify broker positions as Ark-managed without a validated ownership baseline;
- display dummy healthy values when a source is missing, stale, invalid, or not connected.

The initial UI data contract is `ARK_TERMINAL_UI_READ_MODEL_V1`, built by `tools/phase57_ui_read_model.mjs`.
All mutation capabilities in that contract are fixed `false`.

## 2. Verified source contracts

### A. Current live-account execution snapshot — authoritative for this integration

`tools/Start-ArkCashLocked.ps1` captures `ARK_ACCOUNT_READONLY_SNAPSHOT_V2` from the dedicated workbook/account sheet and contains:

- `capturedAt`, `captureCompletedAt`, `source`, `mode`;
- `positions[]`: symbol, name, account, quantity;
- `orders[]`: orderNumber, status, symbol, quantity, filledQty;
- `executions[]`: executionDate, symbol, account, side, quantity, price;
- `buyingPower`;
- all execution/write/transmission safety flags fixed false.

This snapshot is the first source used by the UI read model because it is the same account boundary exercised by the G6-G10 locked launcher.

### B. Locked G6-G10 pipeline result

`tools/phase57_cash_locked_pipeline.py` supplies read-only inspection state:

- `status`: `BLOCKED` or `LOCKED_READY`;
- `stage`: G6 / G9 / G10 / EXCEL_ADAPTER;
- reconciliation status/blockers;
- locked order draft;
- cash-only unlock candidate;
- micro-live preflight;
- upstream lineage when the request originated from the frozen strategy path.

`LOCKED_READY` is **not** equivalent to live execution permission. The UI must render it as a locked/preflight state only.

### C. Private ownership baseline

`ARK_CASH_OWNERSHIP_BASELINE_V1` is the only accepted source for distinguishing:

- `EXTERNAL` personal holdings;
- `ARK_MANAGED` holdings;
- otherwise `UNKNOWN`.

The UI read model verifies the baseline SHA-256 before assigning ownership. Missing or invalid ownership input never auto-claims a broker position.

### D. Existing `/api/broker-readonly` endpoint — not a live-account source yet

The current server endpoint is a read-only stub:

- `account` returns `null`;
- `positions` returns `[]`;
- `orders` returns `[]`;
- `health` confirms read-only / liveTrading false.

Therefore UI 2.0 must **not** treat the hosted `/api/broker-readonly` responses as proof that the live brokerage account is empty or healthy.

### E. Existing local `tools/rss_bridge.py` — separate contract, do not silently mix

The local bridge can expose MARKETSPEED II / Excel read-only account data, but its account reader currently targets the `ArkAccount` and `ArkPositions` sheet contract. The proven locked launcher reads the dedicated `ARK_ACCOUNT_READONLY` sheet directly.

Until those contracts are deliberately normalized and tested against the same workbook, UI 2.0 must not combine them as though they were the same authoritative source.

## 3. Screen-by-screen mapping

| Screen | UI field | Verified source | V1 state |
|---|---|---|---|
| HOME | Buying Power | `ARK_ACCOUNT_READONLY_SNAPSHOT_V2.buyingPower` | CONNECTABLE |
| HOME | Positions count | snapshot `positions.length` | CONNECTABLE |
| HOME | Open orders count | snapshot `orders.length` | CONNECTABLE |
| HOME | Execution count | snapshot `executions.length` | CONNECTABLE |
| HOME | Active intent | locked pipeline draft + upstream lineage | CONNECTABLE when an intent exists |
| HOME | Total assets / equity | not present in the locked launcher snapshot | `UNAVAILABLE` — do not infer from Buying Power |
| HOME | Asset trend | no verified source in current locked contract | `UNAVAILABLE` |
| SELECTOR | Rank / Score / reasons / candidates | final LONG-only Selector output contract not connected here | `UNAVAILABLE` |
| SELECTOR | Current intent lineage | locked pipeline `upstreamLineage` | CONNECTABLE |
| POSITIONS | Symbol / name / account / quantity | snapshot `positions[]` | CONNECTABLE |
| POSITIONS | Ark-managed vs personal | validated ownership baseline | CONNECTABLE; otherwise `UNKNOWN` |
| POSITIONS | avg price / current price / PnL / holding time | not present in current locked launcher snapshot | `UNAVAILABLE` until normalized source is verified |
| POSITIONS | EXIT state | no explicit verified position-state feed connected yet | `UNAVAILABLE` |
| ORDERS | order no. / status / symbol / qty / filled qty | snapshot `orders[]` | CONNECTABLE, read-only |
| ORDERS | executions | snapshot `executions[]` | CONNECTABLE, read-only |
| ORDERS | accept / cancel | no UI write authority | DISABLED |
| PERFORMANCE | daily/weekly/monthly PnL, win rate, PF, averages | no verified performance read model connected yet | `UNAVAILABLE` |
| SYSTEM | snapshot freshness | `captureCompletedAt` / `capturedAt` | CONNECTABLE |
| SYSTEM | source safety flags | snapshot `safety` | CONNECTABLE |
| SYSTEM | reconciliation | locked pipeline G6 result | CONNECTABLE when pipeline evaluated |
| SYSTEM | cash-only preflight | locked pipeline G9/G10 result | CONNECTABLE when pipeline evaluated |
| SYSTEM | ownership baseline status | validated ownership input | CONNECTABLE |
| SYSTEM | Kill Switch | only when an explicit `runtimeSafety` source is supplied | otherwise `UNKNOWN` |

## 4. Missing / stale / invalid display semantics

These states are semantic, not cosmetic:

- `FRESH`: capture age is within the configured maximum (default 30 seconds).
- `STALE`: source exists but is older than the maximum. Trade readiness is `BLOCKED`.
- `UNAVAILABLE`: source was not supplied. Display `--` / unavailable, never zero or healthy.
- `INVALID`: schema, timestamp, pipeline, or ownership input failed validation. Trade readiness is `BLOCKED` when critical.
- `BLOCKED`: a critical source, runtime safety state, or locked pipeline prevents readiness.
- `LOCKED_NO_INTENT`: account source is healthy but no inspected order intent exists.
- `LOCKED_READY`: G6-G10 inspection passed. It remains non-executable and non-transmitted.

A stale or invalid source must never fall back to synthetic demo values.

## 5. Migration order

1. **SYSTEM** — freshness, source integrity, read-only safety, reconciliation, pipeline stage, ownership status. No interactive safety mutations.
2. **HOME** — Buying Power, counts, active locked intent; unsupported metrics remain unavailable.
3. **POSITIONS** — broker positions plus explicit ownership classification. Add price/PnL only after a normalized verified source is approved.
4. **ORDERS** — read-only orders/executions. Keep accept/cancel controls disabled or visually non-operational.
5. **SELECTOR** — connect only after the final LONG-only Selector/Entry/Allocation output contract is frozen and explicitly mapped.
6. **PERFORMANCE** — connect to a dedicated performance read model after trade lineage / realized PnL persistence is authoritative.

## 6. Rollback / deployment plan

- Keep `ui/ark-terminal-2-standalone` and the existing runtime separate during read-only integration.
- Do not change the existing production Vercel root or production branch for the prototype.
- Introduce the real-data UI through a separate route/project or feature flag first.
- Maintain the existing UI as the immediate rollback path until read-only parity is demonstrated on the real Windows/MSII machine.
- UI integration completion, real-data connection completion, and order-unlock completion remain separate gates.

## 7. Next engineering gate

Before the approved HTML is modified, prove `ARK_TERMINAL_UI_READ_MODEL_V1` with synthetic regression and then with a private real-machine snapshot. The first real-machine gate should verify only:

- Buying Power matches the locked launcher;
- position count and ownership classification match;
- order/execution counts match;
- snapshot freshness changes to `STALE` when capture stops;
- G9 `INSUFFICIENT_CASH` renders as a blocked readiness state;
- every mutation capability remains false.

No broker/Excel/RSS write is required or permitted for this gate.
