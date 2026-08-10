import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE57_P23_1_SAFETY,
  buildSessionWalkForwardFolds,
  evaluateIntradayAnalogOos,
} from '../daytrade/phase57-intraday-analog-oos.js';

function dateString(index) {
  const date = new Date(Date.UTC(2026, 5, 1 + index));
  return date.toISOString().slice(0, 10);
}

function rows(count = 30) {
  return Array.from({ length: count }, (_, index) => {
    const sessionDate = dateString(index);
    const x = ((index % 6) - 2.5) / 10;
    const actualReturnPct = x >= 0 ? 0.7 + x : -0.6 + x;
    return {
      id: `row-${index}`,
      symbol: '8035.T',
      sessionDate,
      outcomeSessionDate: sessionDate,
      featureCutoff: `${sessionDate}T00:00:00.000Z`,
      outcomeAt: `${sessionDate}T00:15:00.000Z`,
      horizonBars: 3,
      features: { x },
      context: { timeBucket: 'OPEN' },
      actualReturnPct,
      absMovePct: Math.abs(actualReturnPct),
      mfePct: Math.max(actualReturnPct, 0) + 0.2,
      maePct: Math.min(actualReturnPct, 0) - 0.2,
      pointInTimeValid: true,
      intradayOnly: true,
    };
  });
}

const options = {
  featureKeys: ['x'],
  topK: 5,
  minimumAnalogs: 5,
  minFeatureFraction: 1,
  roundTripCostPct: 0.05,
  minimumExpectedNetPct: 0,
  initialTrainFraction: 0.6,
  testFraction: 0.2,
  minimumTrainSessions: 12,
};

test('P23.1 safety remains fail-closed and research only', () => {
  for (const key of [
    'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
    'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed',
    'overnightHoldingAllowed',
  ]) assert.equal(PHASE57_P23_1_SAFETY[key], false);
  assert.equal(PHASE57_P23_1_SAFETY.humanApprovalRequired, true);
});

test('session walk-forward folds never mix train and test sessions', () => {
  const folds = buildSessionWalkForwardFolds(rows(), options);
  assert.equal(folds.length, 2);
  for (const fold of folds) {
    const train = new Set(fold.trainRows.map(row => row.sessionDate));
    const testSessions = new Set(fold.testRows.map(row => row.sessionDate));
    assert.equal([...testSessions].some(session => train.has(session)), false);
    assert.ok(fold.trainSessionEnd < fold.testSessionStart);
  }
});

test('P23.1 evaluates a frozen single horizon with train-only analog candidates', () => {
  const result = evaluateIntradayAnalogOos(rows(), options);
  assert.equal(result.status, 'INTRADAY_ANALOG_REAL_OOS_EVALUATED');
  assert.equal(result.horizonBars, 3);
  assert.equal(result.outerFoldCount, 2);
  assert.ok(result.readyQueryCount > 0);
  assert.equal(result.selectionIntegrity.outerOutcomesUsedForPrediction, false);
  assert.equal(result.selectionIntegrity.candidatePoolRestrictedToPreOuterTrainingSessions, true);
  assert.equal(result.selectionIntegrity.postSelectionAcrossHorizonsAllowed, false);
  assert.equal(result.edgeClaimAllowed, false);
  assert.equal(result.executionAllowed, false);
  assert.equal(result.transmitted, false);
});

test('changing final outer outcomes cannot change final-fold analog predictions or neighbor identities', () => {
  const baseRows = rows();
  const first = evaluateIntradayAnalogOos(baseRows, options);
  const finalFold = first.foldResults.at(-1).fold;
  const finalStart = first.foldResults.at(-1).testSessionStart;
  const alteredRows = baseRows.map(row => row.sessionDate >= finalStart
    ? { ...row, actualReturnPct: -Number(row.actualReturnPct) * 9, absMovePct: Math.abs(Number(row.actualReturnPct) * 9) }
    : row);
  const altered = evaluateIntradayAnalogOos(alteredRows, options);
  const fingerprint = result => result.predictionFingerprint
    .filter(row => row.fold === finalFold)
    .map(row => ({ id: row.id, direction: row.direction, predictedNetReturnPct: row.predictedNetReturnPct, analogIds: row.analogIds }));
  assert.deepEqual(fingerprint(altered), fingerprint(first));
});

test('mixed horizons are rejected instead of selecting the best one after OOS', () => {
  const mixed = rows();
  mixed[0] = { ...mixed[0], horizonBars: 6 };
  assert.throws(() => evaluateIntradayAnalogOos(mixed, options), /exactly one predeclared horizon/);
});
