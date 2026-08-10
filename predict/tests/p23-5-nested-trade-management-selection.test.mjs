import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE57_P23_5_SAFETY,
  buildChronologicalSessionFolds,
  selectTradeManagementConfigInner,
  evaluateNestedTradeManagementStateMachine,
} from '../daytrade/phase57-nested-trade-management-selection.js';

const safetyFalse = [
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed',
];

function bar(timestamp, open, high, low, close, volume = 1000) {
  return { timestamp, open, high, low, close, volume };
}

function iso(date, minute) {
  const hh = String(Math.floor(minute / 60)).padStart(2, '0');
  const mm = String(minute % 60).padStart(2, '0');
  return `${date}T${hh}:${mm}:00.000Z`;
}

function rowForSession(date, mode = 'REBOUND') {
  const contextBars = [
    bar(iso(date, 0), 100.0, 100.4, 99.8, 100.2),
    bar(iso(date, 5), 100.2, 100.8, 100.1, 100.7),
    bar(iso(date, 10), 100.7, 101.3, 100.6, 101.2),
    bar(iso(date, 15), 101.2, 101.9, 101.1, 101.8),
  ];
  const futureBars = mode === 'REBOUND'
    ? [
      bar(iso(date, 20), 101.8, 101.9, 97.8, 98.0),
      bar(iso(date, 25), 98.0, 100.5, 97.9, 100.3),
      bar(iso(date, 30), 100.3, 102.8, 100.2, 102.5),
    ]
    : [
      bar(iso(date, 20), 101.8, 101.9, 97.8, 98.0),
      bar(iso(date, 25), 98.0, 98.1, 95.8, 96.0),
      bar(iso(date, 30), 96.0, 96.1, 93.8, 94.0),
    ];
  return {
    id: `${date}-${mode}`,
    sessionDate: date,
    featureCutoff: iso(date, 15),
    entryPrice: 101.8,
    signalDirection: 'LONG',
    contextBars,
    futureBars,
  };
}

const fastExit = {
  id: 'FAST_EXIT',
  config: {
    hardStopAtr: 100,
    profitProtectActivationAtr: 100,
    cautionEnterDamageVotes: 1,
    cautionExitDamageVotes: 1,
    cautionConfirmBars: 1,
    severeBreakdownDamageVotes: 1,
    severeBreakdownConfirmBars: 1,
    minBarsBeforeStateExit: 1,
    maxHoldBars: 1000,
  },
};

const patient = {
  id: 'PATIENT',
  config: {
    hardStopAtr: 100,
    profitProtectActivationAtr: 100,
    cautionEnterDamageVotes: 2,
    cautionExitDamageVotes: 7,
    cautionConfirmBars: 99,
    severeBreakdownDamageVotes: 7,
    severeBreakdownConfirmBars: 99,
    minBarsBeforeStateExit: 99,
    maxHoldBars: 1000,
  },
};

test('P23.5 safety remains fail-closed', () => {
  for (const key of safetyFalse) assert.equal(PHASE57_P23_5_SAFETY[key], false, key);
  assert.equal(PHASE57_P23_5_SAFETY.humanApprovalRequired, true);
});

test('session folds are strictly chronological and non-overlapping', () => {
  const rows = Array.from({ length: 10 }, (_, index) => rowForSession(`2026-07-${String(index + 1).padStart(2, '0')}`));
  const folds = buildChronologicalSessionFolds(rows, { trainFraction: 0.5, testFraction: 0.2, minTrainSessions: 4 });
  assert.ok(folds.length >= 2);
  for (const fold of folds) {
    assert.ok(fold.trainEnd < fold.testStart);
    assert.equal(fold.trainSessions.some(session => fold.testSessions.includes(session)), false);
  }
});

test('inner selection favors a patient state machine on rebound-only training sessions', () => {
  const rows = Array.from({ length: 12 }, (_, index) => rowForSession(`2026-07-${String(index + 1).padStart(2, '0')}`, 'REBOUND'));
  const selection = selectTradeManagementConfigInner(rows, [fastExit, patient], {
    innerTrainFraction: 0.5,
    innerTestFraction: 0.25,
    innerMinTrainSessions: 4,
    minInnerSignals: 2,
  });
  assert.equal(selection.selectedCandidateId, 'PATIENT');
  assert.equal(selection.outerRowsUsedForSelection, false);
});

test('outer decline does not retroactively change the config selected from earlier rebound sessions', () => {
  const rows = [];
  for (let index = 1; index <= 12; index += 1) rows.push(rowForSession(`2026-07-${String(index).padStart(2, '0')}`, 'REBOUND'));
  for (let index = 13; index <= 18; index += 1) rows.push(rowForSession(`2026-07-${String(index).padStart(2, '0')}`, 'DECLINE'));

  const result = evaluateNestedTradeManagementStateMachine(rows, {
    candidates: [fastExit, patient],
    outerTrainFraction: 0.65,
    outerTestFraction: 0.2,
    outerMinTrainSessions: 8,
    innerTrainFraction: 0.5,
    innerTestFraction: 0.25,
    innerMinTrainSessions: 4,
    minInnerSignals: 2,
  });

  assert.ok(result.outerFoldCount >= 1);
  const first = result.foldResults.find(fold => fold.selectedCandidateId);
  assert.ok(first);
  assert.equal(first.selectedCandidateId, 'PATIENT');
  assert.equal(first.outerOutcomesUsedForSelection, false);
  assert.equal(result.selectionIntegrity.outerOutcomesUsedForConfigSelection, false);
  assert.equal(result.selectionIntegrity.postSelectionAcrossOuterResultsAllowed, false);
  assert.equal(result.interpretation.finalUntouchedOosEdgeClaimAllowed, false);
});

test('explicit attempt to select from outer outcomes is rejected', () => {
  assert.throws(() => evaluateNestedTradeManagementStateMachine([
    rowForSession('2026-07-01', 'REBOUND'),
    rowForSession('2026-07-02', 'REBOUND'),
  ], { allowOuterOutcomeSelection: true }), /forbidden/);
});
