import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import test from 'node:test';
import {buildArkTerminalUiReadModel} from './phase57_ui_read_model.mjs';

const NOW = '2026-09-15T13:00:20.000Z';
const canonical = value => Array.isArray(value)
  ? value.map(canonical)
  : value && typeof value === 'object'
    ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])]))
    : value;
const sha256 = value => createHash('sha256').update(JSON.stringify(canonical(value))).digest('hex');

function snapshot(overrides = {}) {
  return {
    schemaId: 'ARK_ACCOUNT_READONLY_SNAPSHOT_V2',
    capturedAt: '2026-09-15T13:00:00.000Z',
    captureCompletedAt: '2026-09-15T13:00:01.000Z',
    source: 'MARKETSPEED_II_RSS',
    mode: 'READ_ONLY',
    positions: [{symbol: '408A', name: 'external fixture', account: '特定', quantity: 180}],
    orders: [],
    executions: [],
    buyingPower: 2605,
    safety: {
      executionAllowed: false,
      brokerWriteAllowed: false,
      excelOrderWriteAllowed: false,
      rssOrderFunctionAllowed: false,
      liveTradingAllowed: false,
      paperTradingAllowed: false,
      automaticPromotionAllowed: false,
      productionUpdateAllowed: false,
      transmitted: false,
    },
    ...overrides,
  };
}

function ownership(overrides = {}) {
  const core = {
    schemaId: 'ARK_CASH_OWNERSHIP_BASELINE_V1',
    capturedAt: '2026-09-15T12:50:00.000Z',
    source: 'TEST_ONLY',
    frozen: true,
    externalPositions: [{symbol: '408A.T', quantity: 180}],
    arkManagedPositions: [],
    ...overrides,
  };
  delete core.baselineSha256;
  return {...core, baselineSha256: sha256(core)};
}

function blockedPipeline() {
  return {
    status: 'BLOCKED',
    stage: 'G9',
    reconciliation: {status: 'RECONCILIATION_PASS', blockers: []},
    draft: {symbol: '7203.T', side: 'BUY', positionEffect: 'OPEN', quantity: 100},
    candidate: {eligible: false, blockers: ['INSUFFICIENT_CASH']},
    upstreamLineage: {
      sourceActionSha256: 'b'.repeat(64),
      sourceCashExecutionIntentSha256: 'c'.repeat(64),
      sourceIntentSha256: 'd'.repeat(64),
      sourceIntentId: 'intent-1',
      strategyId: 'strategy-1',
    },
  };
}

test('fresh real-account-shaped snapshot projects read-only HOME/POSITIONS/SYSTEM without inventing unavailable metrics', () => {
  const model = buildArkTerminalUiReadModel({
    accountSnapshot: snapshot(),
    lockedPipeline: blockedPipeline(),
    ownershipBaseline: ownership(),
    generatedAt: NOW,
  });

  assert.equal(model.schemaId, 'ARK_TERMINAL_UI_READ_MODEL_V1');
  assert.equal(model.readOnly, true);
  assert.equal(model.source.freshness.state, 'FRESH');
  assert.equal(model.home.buyingPower, 2605);
  assert.equal(model.home.totalAssets, null);
  assert.equal(model.home.totalAssetsState, 'UNAVAILABLE');
  assert.equal(model.positions.length, 1);
  assert.equal(model.positions[0].symbol, '408A.T');
  assert.equal(model.positions[0].ownership, 'EXTERNAL');
  assert.equal(model.positions[0].ownershipQuantityMatch, true);
  assert.equal(model.positions[0].marketPrice, null);
  assert.equal(model.system.pipeline.state, 'BLOCKED');
  assert.deepEqual(model.system.pipeline.blockers, ['INSUFFICIENT_CASH']);
  assert.equal(model.system.tradeReadiness, 'BLOCKED');
  assert.equal(model.system.health, 'READ_ONLY_OK');
  assert.equal(model.selector.state, 'UNAVAILABLE');
  assert.equal(model.performance.state, 'UNAVAILABLE');
  assert.equal(model.mutationCapabilities.orderSubmit, false);
  assert.equal(model.mutationCapabilities.orderCancel, false);
  assert.equal(model.mutationCapabilities.killSwitchChange, false);
});

test('stale account snapshot blocks trade readiness instead of displaying healthy synthetic data', () => {
  const model = buildArkTerminalUiReadModel({
    accountSnapshot: snapshot({
      capturedAt: '2026-09-15T12:00:00.000Z',
      captureCompletedAt: '2026-09-15T12:00:01.000Z',
    }),
    generatedAt: NOW,
  });

  assert.equal(model.source.freshness.state, 'STALE');
  assert.equal(model.system.health, 'BLOCKED');
  assert.equal(model.system.tradeReadiness, 'BLOCKED');
  assert.equal(model.home.buyingPowerState, 'STALE');
  assert.equal(model.selector.state, 'UNAVAILABLE');
});

test('missing or permissive source safety flags fail closed in the projection', () => {
  const missing = buildArkTerminalUiReadModel({accountSnapshot: snapshot({safety: undefined}), generatedAt: NOW});
  assert.equal(missing.safety.state, 'BLOCKED');
  assert.ok(missing.safety.violations.includes('SOURCE_SAFETY_FLAGS_MISSING'));
  assert.equal(missing.system.tradeReadiness, 'BLOCKED');

  const permissive = buildArkTerminalUiReadModel({
    accountSnapshot: snapshot({safety: {...snapshot().safety, executionAllowed: true}}),
    generatedAt: NOW,
  });
  assert.equal(permissive.safety.state, 'BLOCKED');
  assert.ok(permissive.safety.violations.includes('SOURCE_SAFETY_executionAllowed_NOT_FALSE'));
  assert.equal(permissive.safety.executionAllowed, false);
});

test('ownership is UNKNOWN without an explicit baseline and INVALID baselines never auto-claim broker positions', () => {
  const absent = buildArkTerminalUiReadModel({accountSnapshot: snapshot(), generatedAt: NOW});
  assert.equal(absent.system.ownership.state, 'UNAVAILABLE');
  assert.equal(absent.positions[0].ownership, 'UNKNOWN');

  const invalid = buildArkTerminalUiReadModel({
    accountSnapshot: snapshot(),
    ownershipBaseline: ownership({frozen: false}),
    generatedAt: NOW,
  });
  assert.equal(invalid.system.ownership.state, 'INVALID');
  assert.equal(invalid.positions[0].ownership, 'UNKNOWN');
});

test('tampered ownership hash never assigns an owner', () => {
  const valid = ownership();
  const tampered = {...valid, externalPositions: [{symbol: '408A.T', quantity: 999}]};
  const model = buildArkTerminalUiReadModel({accountSnapshot: snapshot(), ownershipBaseline: tampered, generatedAt: NOW});
  assert.equal(model.system.ownership.state, 'INVALID');
  assert.equal(model.positions[0].ownership, 'UNKNOWN');
});

test('LOCKED_READY requires explicit clear runtime safety and remains non-executable', () => {
  const pipeline = {
    status: 'LOCKED_READY',
    stage: 'EXCEL_ADAPTER',
    reconciliation: {status: 'RECONCILIATION_PASS', blockers: []},
    draft: {symbol: '7203.T', side: 'BUY', positionEffect: 'OPEN', quantity: 100},
    candidate: {eligible: true, blockers: []},
    preflight: {readyForPhysicalUnlock: true, blockers: []},
  };

  const unknownRuntime = buildArkTerminalUiReadModel({
    accountSnapshot: snapshot({buyingPower: 1_000_000}),
    ownershipBaseline: ownership(),
    lockedPipeline: pipeline,
    generatedAt: NOW,
  });
  assert.equal(unknownRuntime.system.tradeReadiness, 'BLOCKED');
  assert.equal(unknownRuntime.system.runtimeSafety.state, 'UNKNOWN');

  const model = buildArkTerminalUiReadModel({
    accountSnapshot: snapshot({buyingPower: 1_000_000}),
    ownershipBaseline: ownership(),
    lockedPipeline: pipeline,
    runtimeSafety: {killSwitchLatched: false, faults: []},
    generatedAt: NOW,
  });

  assert.equal(model.system.tradeReadiness, 'LOCKED_READY');
  assert.equal(model.home.activeIntent.symbol, '7203.T');
  assert.equal(model.mutationCapabilities.orderSubmit, false);
  assert.equal(model.safety.executionAllowed, false);
  assert.equal(model.safety.transmitted, false);
});

test('runtime kill switch blocks readiness without turning the UI into a mutation surface', () => {
  const model = buildArkTerminalUiReadModel({
    accountSnapshot: snapshot(),
    ownershipBaseline: ownership(),
    runtimeSafety: {killSwitchLatched: true, faults: ['RSS_DISCONNECTED']},
    generatedAt: NOW,
  });

  assert.equal(model.system.runtimeSafety.state, 'BLOCKED');
  assert.equal(model.system.runtimeSafety.killSwitchLatched, true);
  assert.equal(model.system.tradeReadiness, 'BLOCKED');
  assert.equal(model.mutationCapabilities.killSwitchChange, false);
});
