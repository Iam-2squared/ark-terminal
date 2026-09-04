import assert from 'node:assert/strict';
import test from 'node:test';
import {
  PHASE57_EXIT_FAILURE_TAXONOMY_VERSION,
  buildP25ExitFailureTaxonomy,
  aggregateP25ExitFailureTaxonomy,
} from '../daytrade/phase57-exit-research-failure-taxonomy.js';

const DATE = '2026-09-03';
const ENTRY_AT = '2026-09-03T00:30:00.000Z';

function contextBars() {
  return Array.from({ length: 6 }, (_, index) => ({
    timestamp: new Date(Date.parse('2026-09-03T00:00:00.000Z') + index * 5 * 60_000).toISOString(),
    open: 100,
    high: 101,
    low: 99,
    close: 100,
    volume: 10_000,
  }));
}

function futureBars(postExitClose = 102) {
  return [
    { timestamp: '2026-09-03T00:35:00.000Z', open: 100, high: 100.2, low: 99.4, close: 99.5, volume: 10_000 },
    { timestamp: '2026-09-03T00:40:00.000Z', open: 99.5, high: 99.6, low: 98.8, close: 99.0, volume: 11_000 },
    { timestamp: '2026-09-03T00:45:00.000Z', open: 99.0, high: 100.5, low: 98.9, close: 100.2, volume: 12_000 },
    { timestamp: '2026-09-03T00:50:00.000Z', open: 100.2, high: 101.5, low: 100.0, close: 101.0, volume: 13_000 },
    { timestamp: '2026-09-03T00:55:00.000Z', open: 101.0, high: postExitClose + 0.2, low: 100.8, close: postExitClose, volume: 14_000 },
    { timestamp: '2026-09-03T01:00:00.000Z', open: postExitClose, high: postExitClose + 0.2, low: postExitClose - 0.3, close: postExitClose, volume: 14_000 },
    { timestamp: '2026-09-03T01:05:00.000Z', open: postExitClose, high: postExitClose + 0.2, low: postExitClose - 0.3, close: postExitClose, volume: 14_000 },
    { timestamp: '2026-09-03T01:10:00.000Z', open: postExitClose, high: postExitClose + 0.2, low: postExitClose - 0.3, close: postExitClose, volume: 14_000 },
  ];
}

function analogPool(label = -0.5) {
  return Array.from({ length: 40 }, (_, index) => ({
    sessionDate: '2026-08-01',
    symbol: `${1000 + index}.T`,
    direction: 'LONG',
    timestamp: '2026-08-01T00:30:00.000Z',
    fullyRealizedAt: '2026-08-01T01:00:00.000Z',
    state: {
      currentReturnPct: -0.5,
      bestReturnPct: 0,
      givebackPctPoints: 0.5,
      atrPct: 1,
      momentumPct: -0.2,
      bodyPressure: -0.5,
      directionalRangePos: 0.2,
      elapsedBars: 1,
    },
    labels: { 1: label, 3: label, 6: label },
  }));
}

function row(postExitClose = 102) {
  return {
    entryAccepted: true,
    frozenBeforeOutcome: true,
    currentOutcomeUsed: false,
    symbol: '7203.T',
    sessionDate: DATE,
    entryTimestamp: ENTRY_AT,
    entryPrice: 100,
    signalDirection: 1,
    direction: 'LONG',
    contextBars: contextBars(),
    futureBars: futureBars(postExitClose),
  };
}

test('failure taxonomy keeps decision policy frozen and exposes evaluation-only post-exit diagnostics', () => {
  const result = buildP25ExitFailureTaxonomy({
    row: row(102),
    analogPool: analogPool(),
    roundTripCostPct: 0.05,
    evaluationHorizons: [1, 3],
  });

  assert.equal(result.version, PHASE57_EXIT_FAILURE_TAXONOMY_VERSION);
  assert.equal(result.diagnosticOnly, true);
  assert.equal(result.outcomeWindowsNeverUsedByDecisionPolicy, true);
  assert.equal(result.invariant.selectorEntryMarketDataAndAllocationFrozen, true);
  assert.deepEqual(result.evaluationHorizons, [1, 3]);
  assert.equal(result.v3.exitTimestamp, '2026-09-03T00:35:00.000Z');
  assert.equal(result.v4.exitTimestamp, '2026-09-03T00:40:00.000Z');
  assert.ok(result.v3.postExitWindows.length > 0);
  assert.ok(result.v3.flags.includes('EARLY_EXIT_REGRET'));
  assert.ok(Number.isFinite(result.pairedDelta.netReturnPctV4MinusV3));
  assert.equal(result.safety.executionAllowed, false);
  assert.equal(result.safety.brokerWriteAllowed, false);
  assert.equal(result.safety.transmitted, false);
});

test('changing bars strictly after both exits changes evaluation diagnostics but not v3/v4 exit decisions', () => {
  const pool = analogPool();
  const favorable = buildP25ExitFailureTaxonomy({ row: row(105), analogPool: pool, evaluationHorizons: [3] });
  const adverse = buildP25ExitFailureTaxonomy({ row: row(80), analogPool: pool, evaluationHorizons: [3] });

  assert.equal(favorable.v3.exitTimestamp, adverse.v3.exitTimestamp);
  assert.equal(favorable.v4.exitTimestamp, adverse.v4.exitTimestamp);
  assert.equal(favorable.v3.netReturnPct, adverse.v3.netReturnPct);
  assert.equal(favorable.v4.netReturnPct, adverse.v4.netReturnPct);
  assert.notDeepEqual(favorable.v3.postExitWindows, adverse.v3.postExitWindows);
});

test('aggregate diagnostics report model metrics and paired deltas without promotion or execution', () => {
  const pool = analogPool();
  const a = buildP25ExitFailureTaxonomy({ row: row(102), analogPool: pool, evaluationHorizons: [1, 3] });
  const b = buildP25ExitFailureTaxonomy({ row: row(101), analogPool: pool, evaluationHorizons: [1, 3] });
  const aggregate = aggregateP25ExitFailureTaxonomy([a, b]);

  assert.equal(aggregate.count, 2);
  assert.equal(aggregate.v3.count, 2);
  assert.equal(aggregate.v4.count, 2);
  assert.ok(Number.isFinite(aggregate.meanPairedDelta.netReturnPctV4MinusV3));
  assert.equal(aggregate.diagnosticOnly, true);
  for (const key of [
    'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
    'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed', 'transmitted',
  ]) assert.equal(aggregate.safety[key], false, key);
});

test('taxonomy rejects empty or invalid evaluation horizon configuration', () => {
  assert.throws(
    () => buildP25ExitFailureTaxonomy({ row: row(), analogPool: analogPool(), evaluationHorizons: [0, -1, 1.5] }),
    /at least one positive evaluation horizon/,
  );
});
