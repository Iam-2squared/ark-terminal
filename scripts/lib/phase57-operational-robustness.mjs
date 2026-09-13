import assert from 'node:assert/strict';

const finite = x => typeof x === 'number' && Number.isFinite(x);
const nonnegative = x => finite(x) && x >= 0;
const round = (x, d = 6) => Number.isFinite(x) ? Number(x.toFixed(d)) : x;

export const CONNECTION_STATES = Object.freeze([
  'DISCONNECTED',
  'CONNECTING',
  'HEALTHY',
  'STALE',
  'UNKNOWN',
  'HALTED',
]);

const TRANSITIONS = Object.freeze({
  DISCONNECTED: new Set(['CONNECTING', 'HALTED']),
  CONNECTING: new Set(['HEALTHY', 'DISCONNECTED', 'UNKNOWN', 'HALTED']),
  HEALTHY: new Set(['STALE', 'DISCONNECTED', 'UNKNOWN', 'HALTED']),
  STALE: new Set(['HEALTHY', 'DISCONNECTED', 'UNKNOWN', 'HALTED']),
  UNKNOWN: new Set(['HEALTHY', 'DISCONNECTED', 'HALTED']),
  HALTED: new Set([]),
});

export function createConnectionState(initial = 'DISCONNECTED') {
  assert.ok(CONNECTION_STATES.includes(initial), 'INVALID_CONNECTION_STATE');
  let state = initial;
  const history = [{ state, reason: 'INITIAL' }];
  return {
    get state() { return state; },
    transition(next, reason = 'UNSPECIFIED') {
      assert.ok(CONNECTION_STATES.includes(next), 'INVALID_CONNECTION_STATE');
      assert.ok(TRANSITIONS[state].has(next), `INVALID_CONNECTION_TRANSITION:${state}->${next}`);
      state = next;
      history.push({ state, reason });
      return state;
    },
    canEvaluate() { return state === 'HEALTHY'; },
    mustFailClosed() { return state !== 'HEALTHY'; },
    snapshot() { return structuredClone({ state, history }); },
  };
}

export function classifyFreshness({ sourceTimestamp, observedAt, maxAgeMs }) {
  assert.ok(Number.isFinite(Date.parse(sourceTimestamp)), 'INVALID_SOURCE_TIMESTAMP');
  assert.ok(Number.isFinite(Date.parse(observedAt)), 'INVALID_OBSERVED_TIMESTAMP');
  assert.ok(nonnegative(maxAgeMs), 'INVALID_MAX_AGE');
  const ageMs = Date.parse(observedAt) - Date.parse(sourceTimestamp);
  if (ageMs < 0) return { status: 'FUTURE_TIMESTAMP', ageMs, decisionAllowed: false };
  if (ageMs > maxAgeMs) return { status: 'STALE', ageMs, decisionAllowed: false };
  return { status: 'FRESH', ageMs, decisionAllowed: true };
}

export function applyExternalCashFlow(snapshot, event) {
  assert.ok(snapshot && typeof snapshot === 'object', 'SNAPSHOT_REQUIRED');
  assert.ok(event && typeof event === 'object', 'EXTERNAL_CASH_FLOW_REQUIRED');
  assert.ok(['DEPOSIT', 'WITHDRAWAL'].includes(event.type), 'INVALID_EXTERNAL_CASH_FLOW_TYPE');
  assert.ok(finite(event.amountJpy) && event.amountJpy > 0, 'INVALID_EXTERNAL_CASH_FLOW_AMOUNT');
  assert.ok(finite(snapshot.cashJpy) && finite(snapshot.equityJpy), 'INVALID_LEDGER_BALANCE');
  const delta = event.type === 'DEPOSIT' ? event.amountJpy : -event.amountJpy;
  const nextCash = snapshot.cashJpy + delta;
  const nextEquity = snapshot.equityJpy + delta;
  assert.ok(nextCash >= -1e-9, 'EXTERNAL_WITHDRAWAL_EXCEEDS_CASH');
  return {
    ...structuredClone(snapshot),
    cashJpy: round(nextCash),
    equityJpy: round(nextEquity),
    tradingPnlJpy: snapshot.tradingPnlJpy ?? 0,
    externalCashFlowJpy: round((snapshot.externalCashFlowJpy ?? 0) + delta),
    lastExternalCashFlow: structuredClone(event),
  };
}

export function reconcileState(expected, observed, tolerances = {}) {
  assert.ok(expected && observed, 'RECONCILIATION_INPUT_REQUIRED');
  const moneyTolerance = tolerances.moneyJpy ?? 0.01;
  const quantityTolerance = tolerances.quantity ?? 1e-9;
  const mismatches = [];
  const compareMoney = key => {
    if (!finite(expected[key]) || !finite(observed[key])) return;
    if (Math.abs(expected[key] - observed[key]) > moneyTolerance) mismatches.push({ field: key, expected: expected[key], observed: observed[key] });
  };
  for (const key of ['cashJpy', 'equityJpy', 'grossExposureJpy', 'absoluteNetExposureJpy']) compareMoney(key);
  const expPositions = new Map((expected.positions ?? []).map(p => [p.symbol, p]));
  const obsPositions = new Map((observed.positions ?? []).map(p => [p.symbol, p]));
  const symbols = [...new Set([...expPositions.keys(), ...obsPositions.keys()])].sort();
  for (const symbol of symbols) {
    const a = expPositions.get(symbol), b = obsPositions.get(symbol);
    if (!a || !b) { mismatches.push({ field: 'positionPresence', symbol, expected: Boolean(a), observed: Boolean(b) }); continue; }
    if (a.direction !== b.direction) mismatches.push({ field: 'direction', symbol, expected: a.direction, observed: b.direction });
    if (!finite(a.quantity) || !finite(b.quantity) || Math.abs(a.quantity - b.quantity) > quantityTolerance) mismatches.push({ field: 'quantity', symbol, expected: a.quantity, observed: b.quantity });
  }
  return {
    reconciled: mismatches.length === 0,
    decisionAllowed: mismatches.length === 0,
    nextState: mismatches.length === 0 ? 'HEALTHY' : 'UNKNOWN',
    mismatches,
  };
}

export function constrainQuantity({ desiredQuantity, priceJpy, lotSize = 100, maxQuantity = Infinity, maxNotionalJpy = Infinity, availableCashJpy = Infinity }) {
  assert.ok(nonnegative(desiredQuantity), 'INVALID_DESIRED_QUANTITY');
  assert.ok(finite(priceJpy) && priceJpy > 0, 'INVALID_PRICE');
  assert.ok(Number.isInteger(lotSize) && lotSize > 0, 'INVALID_LOT_SIZE');
  for (const [name, value] of Object.entries({ maxQuantity, maxNotionalJpy, availableCashJpy })) assert.ok(value === Infinity || nonnegative(value), `INVALID_${name.toUpperCase()}`);
  const byDesired = Math.floor(desiredQuantity / lotSize) * lotSize;
  const byQuantity = maxQuantity === Infinity ? byDesired : Math.floor(maxQuantity / lotSize) * lotSize;
  const byNotional = maxNotionalJpy === Infinity ? byDesired : Math.floor(maxNotionalJpy / priceJpy / lotSize) * lotSize;
  const byCash = availableCashJpy === Infinity ? byDesired : Math.floor(availableCashJpy / priceJpy / lotSize) * lotSize;
  const finalQuantity = Math.max(0, Math.min(byDesired, byQuantity, byNotional, byCash));
  const reasons = [];
  if (finalQuantity < byDesired) {
    if (finalQuantity === byQuantity && byQuantity < byDesired) reasons.push('MAX_QUANTITY');
    if (finalQuantity === byNotional && byNotional < byDesired) reasons.push('MAX_NOTIONAL');
    if (finalQuantity === byCash && byCash < byDesired) reasons.push('AVAILABLE_CASH');
  }
  return {
    desiredQuantity: byDesired,
    finalQuantity,
    finalNotionalJpy: round(finalQuantity * priceJpy),
    constrained: finalQuantity < byDesired,
    reasons,
  };
}

export function createOperationalGate({ connectionState = 'DISCONNECTED', reconciliationRequired = true } = {}) {
  const connection = createConnectionState(connectionState);
  let reconciliation = reconciliationRequired ? 'PENDING' : 'NOT_REQUIRED';
  let halted = false;
  return {
    connection,
    markReconciled(ok) { reconciliation = ok ? 'PASS' : 'FAIL'; if (!ok) connection.transition('UNKNOWN', 'RECONCILIATION_FAILED'); },
    halt(reason = 'MANUAL_HALT') { if (connection.state !== 'HALTED') connection.transition('HALTED', reason); halted = true; },
    decisionAllowed() { return !halted && connection.state === 'HEALTHY' && ['PASS', 'NOT_REQUIRED'].includes(reconciliation); },
    snapshot() { return { connection: connection.snapshot(), reconciliation, halted, decisionAllowed: this.decisionAllowed() }; },
  };
}
