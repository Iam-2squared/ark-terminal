import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE57_P23_8_SAFETY,
  assertNoEntryExitOutcomeLeakage,
  evaluateEntryExitQualityOutcome,
  evaluateNestedEntryExitQuality,
} from '../daytrade/phase57-entry-exit-quality.js';

const safetyFalse = [
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed',
];

const bar = (timestamp, open, high, low, close, volume = 1000) => ({ timestamp, open, high, low, close, volume });

function row(sessionDate, symbol, featureCutoff, direction = 'LONG') {
  const prefix = `${sessionDate}T`;
  return {
    symbol,
    sessionDate,
    featureCutoff,
    entryPrice: 100,
    signalDirection: direction,
    contextBars: [
      bar(`${prefix}00:00:00.000Z`, 99.5, 100.2, 99.3, 100.0),
      bar(`${prefix}00:05:00.000Z`, 100.0, 100.4, 99.8, 100.2),
      bar(`${prefix}00:10:00.000Z`, 100.2, 100.6, 100.0, 100.4),
      bar(`${prefix}00:15:00.000Z`, 100.4, 100.8, 100.2, 100.6),
    ],
    futureBars: direction === 'LONG' ? [
      bar(`${prefix}00:20:00.000Z`, 100.6, 101.5, 100.4, 101.2),
      bar(`${prefix}00:25:00.000Z`, 101.2, 102.5, 101.0, 102.2),
    ] : [
      bar(`${prefix}00:20:00.000Z`, 100.6, 100.8, 99.0, 99.3),
      bar(`${prefix}00:25:00.000Z`, 99.3, 99.5, 97.8, 98.2),
    ],
  };
}

test('P23.8 remains evaluation-only and fail-closed', () => {
  for (const key of safetyFalse) assert.equal(PHASE57_P23_8_SAFETY[key], false, key);
  assert.equal(PHASE57_P23_8_SAFETY.humanApprovalRequired, true);
});

test('P23.8 long quality measures entry distance, MFE, MAE and giveback', () => {
  const quality = evaluateEntryExitQualityOutcome({
    symbol: 'TEST.T',
    sessionDate: '2026-08-10',
    featureCutoff: '2026-08-10T00:15:00.000Z',
    entryPrice: 100,
    signalDirection: 'LONG',
    futureBars: [
      bar('2026-08-10T00:20:00.000Z', 100, 110, 98, 105),
    ],
  }, {
    grossReturnPct: 5,
    netReturnPct: 4.95,
    barsHeld: 1,
    exitReason: 'TEST_EXIT',
    outcomeAt: '2026-08-10T00:20:00.000Z',
    intrabarExit: false,
  });

  assert.ok(Math.abs(quality.mfePct - 10) < 1e-12);
  assert.ok(Math.abs(quality.maePct - (-2)) < 1e-12);
  assert.ok(Math.abs(quality.entryLocalExtremaDistancePct - 2) < 1e-12);
  assert.ok(Math.abs(quality.profitGivebackPctPoints - 5) < 1e-12);
  assert.ok(Math.abs(quality.mfeCaptureRatio - 0.5) < 1e-12);
  assert.ok(Math.abs(quality.bottomToTopCaptureRatio - (5 / 12)) < 1e-12);
  assert.equal(quality.evaluationOnly, true);
  assert.equal(quality.futureExtremaUsedForDecision, false);
  assert.equal(quality.eligibleForModelFeatures, false);
});

test('P23.8 short quality uses the same directional excursion convention', () => {
  const quality = evaluateEntryExitQualityOutcome({
    entryPrice: 100,
    signalDirection: 'SHORT',
    futureBars: [bar('2026-08-10T00:20:00.000Z', 100, 103, 90, 95)],
  }, {
    grossReturnPct: 5,
    netReturnPct: 4.95,
    outcomeAt: '2026-08-10T00:20:00.000Z',
    exitReason: 'TEST_EXIT',
  });
  assert.ok(Math.abs(quality.mfePct - 10) < 1e-12);
  assert.ok(Math.abs(quality.maePct - (-3)) < 1e-12);
  assert.ok(Math.abs(quality.entryLocalExtremaDistancePct - 3) < 1e-12);
});

test('intrabar exit fallback excludes ambiguous exit-bar extrema', () => {
  const quality = evaluateEntryExitQualityOutcome({
    entryPrice: 100,
    signalDirection: 'LONG',
    futureBars: [
      bar('2026-08-10T00:20:00.000Z', 100, 101, 99, 100.5),
      bar('2026-08-10T00:25:00.000Z', 100.5, 120, 80, 99),
    ],
  }, {
    grossReturnPct: -1,
    netReturnPct: -1.05,
    outcomeAt: '2026-08-10T00:25:00.000Z',
    exitReason: 'ATR_HARD_STOP',
    intrabarExit: true,
  });
  assert.equal(quality.intrabarExtremaConservative, true);
  assert.ok(quality.mfePct <= 1.000000000001);
  assert.ok(quality.maePct >= -1.000000000001);
});

test('future/extrema diagnostics cannot be smuggled into decision features', () => {
  assert.equal(assertNoEntryExitOutcomeLeakage({ rsi14: 52, vwapDistancePct: 0.2 }), true);
  assert.throws(() => assertNoEntryExitOutcomeLeakage({ rsi14: 52, mfePct: 1.4 }), /leakage guard/);
  assert.throws(() => assertNoEntryExitOutcomeLeakage({ entryBottomCapture: 0.9 }), /leakage guard/);
});

test('nested quality replays only outer-test folds and reconciles trade counts', () => {
  const rows = [
    row('2026-08-01', 'AAA.T', '2026-08-01T00:15:00.000Z'),
    row('2026-08-02', 'BBB.T', '2026-08-02T00:15:00.000Z'),
    row('2026-08-03', 'CCC.T', '2026-08-03T00:15:00.000Z', 'SHORT'),
  ];
  const config = {
    hardStopAtr: 100,
    profitProtectActivationAtr: 100,
    minBarsBeforeStateExit: 99,
    severeBreakdownConfirmBars: 99,
    cautionExitDamageVotes: 99,
    maxHoldBars: 1000,
    roundTripCostPct: 0.05,
  };
  const nestedResult = {
    candidateUniverse: [{ id: 'PATIENT_TEST', config }],
    foldResults: [
      { fold: 0, testStart: '2026-08-02', testEnd: '2026-08-02', selectedCandidateId: 'PATIENT_TEST', testSignalCount: 1 },
      { fold: 1, testStart: '2026-08-03', testEnd: '2026-08-03', selectedCandidateId: 'PATIENT_TEST', testSignalCount: 1 },
    ],
    outerOutcomes: [{}, {}],
  };
  const quality = evaluateNestedEntryExitQuality({ rows, nestedResult });
  assert.equal(quality.evaluatedTradeCount, 2);
  assert.equal(quality.expectedOuterOutcomeCount, 2);
  assert.equal(quality.countReconciled, true);
  assert.equal(quality.records.some(record => record.symbol === 'AAA.T'), false);
  assert.equal(quality.records.some(record => record.symbol === 'BBB.T'), true);
  assert.equal(quality.records.some(record => record.symbol === 'CCC.T'), true);
  assert.equal(quality.interpretation.futureExtremaUsedForEntrySelection, false);
  assert.equal(quality.interpretation.futureExtremaEligibleAsModelFeatures, false);
  assert.equal(quality.edgeClaimAllowed, false);
  assert.equal(quality.executionAllowed, false);
});
