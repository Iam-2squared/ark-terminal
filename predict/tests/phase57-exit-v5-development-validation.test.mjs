import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import {
  PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_CONTRACT,
  PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY,
  PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_SAFETY,
  assertExitV5DevelopmentValidationSafety,
  buildExitV5FrozenRowsFromP21Replay,
  hashExitV5DevelopmentValidationObject,
  reduceExitV5DevelopmentValidationShards,
} from '../daytrade/phase57-exit-v5-development-validation.js';

const FIVE_MINUTES = 5 * 60_000;
const BASE = Date.parse('2026-08-06T00:00:00.000Z');

function bars(changedFutureClose = null) {
  return Array.from({ length: 34 }, (_, index) => {
    const close = changedFutureClose !== null && index === 24 ? changedFutureClose : 100 + index * 0.1;
    return {
      timestamp: new Date(BASE + index * FIVE_MINUTES).toISOString(),
      open: close - 0.05,
      high: close + 0.2,
      low: close - 0.2,
      close,
      volume: 10_000 + index * 100,
    };
  });
}

function signal(overrides = {}) {
  return {
    symbol: '7203.t',
    sessionDate: '2026-08-06',
    featureCutoff: new Date(BASE + 15 * FIVE_MINUTES).toISOString(),
    direction: 0,
    horizonBars: 3,
    selectedFeatureFamily: 'FULL',
    selectedModelType: 'RANDOM_FOREST',
    selectedConfigId: 'RF12',
    selectedThreshold: 0.55,
    signalPointInTimeValid: true,
    selectionSource: 'P21_1_OUTER_OOS_REPLAY',
    ...overrides,
  };
}

function replay(signals = [signal()]) {
  return {
    selectionIntegrity: {
      outerTestNeverUsedForSelection: true,
      outerTestNeverUsedForFit: true,
    },
    signals,
  };
}

function frozenIdentity(row) {
  return {
    symbol: row.symbol,
    sessionDate: row.sessionDate,
    entryTimestamp: row.entryTimestamp,
    entryPrice: row.entryPrice,
    signalDirection: row.signalDirection,
    setup: row.setup,
    selectedModelType: row.selectedModelType,
    selectedConfigId: row.selectedConfigId,
    selectedThreshold: row.selectedThreshold,
    baseHorizonBars: row.baseHorizonBars,
    selectorPolicyId: row.selectorPolicyId,
    entryPolicyId: row.entryPolicyId,
  };
}

test('P21 replay freezes one causal Entry and keeps future bars outside its identity', () => {
  const historicalSessions = [{ symbol: '7203.T', sessionDate: '2026-08-06', bars5m: bars() }];
  const [row] = buildExitV5FrozenRowsFromP21Replay({ historicalSessions, replay: replay() });
  const [futureChanged] = buildExitV5FrozenRowsFromP21Replay({
    historicalSessions: [{ symbol: '7203.T', sessionDate: '2026-08-06', bars5m: bars(140) }],
    replay: replay(),
  });

  assert.equal(row.symbol, '7203.T');
  assert.equal(row.direction, 'SHORT');
  assert.equal(row.signalDirection, 'SHORT');
  assert.equal(row.entryTimestamp, historicalSessions[0].bars5m[15].timestamp);
  assert.equal(row.entryPrice, historicalSessions[0].bars5m[15].close);
  assert.equal(row.contextBars.length, 13);
  assert.equal(row.contextBars.at(-1).timestamp, row.entryTimestamp);
  assert.equal(row.futureBars[0].timestamp, historicalSessions[0].bars5m[16].timestamp);
  assert.ok(row.futureBars.every((bar) => bar.timestamp > row.entryTimestamp));
  assert.deepEqual(frozenIdentity(futureChanged), frozenIdentity(row));
  assert.deepEqual(futureChanged.contextBars, row.contextBars);
  assert.notDeepEqual(futureChanged.futureBars, row.futureBars);
  for (const [key, value] of Object.entries(PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_CONTRACT)) {
    assert.equal(row[key], value, key);
  }
});

test('P21 Frozen Entry conversion fails closed on lineage or duplicate identity drift', () => {
  const historicalSessions = [{ symbol: '7203.T', sessionDate: '2026-08-06', bars5m: bars() }];
  assert.throws(
    () => buildExitV5FrozenRowsFromP21Replay({
      historicalSessions,
      replay: replay([signal({ signalPointInTimeValid: false })]),
    }),
    /lacks point-in-time Entry attestation/,
  );
  assert.throws(
    () => buildExitV5FrozenRowsFromP21Replay({ historicalSessions, replay: replay([signal(), signal()]) }),
    /duplicate P21 Frozen Entry identity/,
  );
  assert.throws(
    () => buildExitV5FrozenRowsFromP21Replay({
      historicalSessions,
      replay: { ...replay(), selectionIntegrity: { outerTestNeverUsedForSelection: false, outerTestNeverUsedForFit: true } },
    }),
    /outer Entry rows untouched/,
  );
});

test('Development Validation policy is byte-frozen, non-OOS, and research-only', () => {
  assert.equal(assertExitV5DevelopmentValidationSafety(), true);
  assert.equal(PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.outerOosReadAllowed, false);
  assert.equal(PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.outerOosEvaluationAllowed, false);
  assert.equal(PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.validationRetuningAllowed, false);
  assert.equal(PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.resultBasedRetuningAllowed, false);
  assert.equal(PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.expectedEntrySetFingerprint.length, 64);
  assert.equal(PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.expectedMarketDataFingerprint.length, 64);
  assert.equal(PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.expectedPairedSubstrateFingerprint.length, 64);
  for (const key of [
    'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
    'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed',
    'transmitted', 'freshHoldoutConsumed',
  ]) assert.equal(PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_SAFETY[key], false, key);
  assert.equal(hashExitV5DevelopmentValidationObject({ b: 2, a: 1 }), hashExitV5DevelopmentValidationObject({ a: 1, b: 2 }));
  assert.throws(() => reduceExitV5DevelopmentValidationShards([]), /validation shards are required/);
});

test('Development Validation workflow has read-only GitHub permissions and no push path', () => {
  const workflow = fs.readFileSync(new URL('../../.github/workflows/phase57-exit-v5-development-validation.yml', import.meta.url), 'utf8');
  assert.match(workflow, /permissions:\n  contents: read\n  actions: read/);
  assert.doesNotMatch(workflow, /contents: write|pull-requests: write|git push/);
  assert.match(workflow, /CANONICAL_SOURCE_RUN_ID: '31785422471'/);
  assert.match(workflow, /formalOos!==false/);
  assert.match(workflow, /strictOuterSplitMembershipEnforced/);
  assert.match(workflow, /freshHoldoutConsumed/);
});
