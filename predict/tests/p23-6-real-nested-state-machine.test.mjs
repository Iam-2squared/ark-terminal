import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE57_P23_6_SAFETY,
  evaluateRealNestedStateMachine,
} from '../daytrade/phase57-real-nested-state-machine.js';

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

function rowForSession(date, mode = 'REBOUND', index = 0) {
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
    id: `TEST|${date}|${index}`,
    symbol: 'TEST.T',
    sessionDate: date,
    outcomeSessionDate: date,
    featureCutoff: iso(date, 15),
    pointInTimeValid: true,
    signalPointInTimeValid: true,
    entryPrice: 101.8,
    signalDirection: 1,
    baseHorizonBars: 1,
    baseOuterFold: index,
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

test('P23.6 safety remains fail-closed', () => {
  for (const key of safetyFalse) assert.equal(PHASE57_P23_6_SAFETY[key], false, key);
  assert.equal(PHASE57_P23_6_SAFETY.humanApprovalRequired, true);
});

test('real nested evaluator compares exact outer rows without using comparator results for selection', () => {
  const rows = [];
  for (let index = 1; index <= 12; index += 1) rows.push(rowForSession(`2026-07-${String(index).padStart(2, '0')}`, 'REBOUND', index));
  for (let index = 13; index <= 18; index += 1) rows.push(rowForSession(`2026-07-${String(index).padStart(2, '0')}`, 'DECLINE', index));

  const result = evaluateRealNestedStateMachine(rows, {
    candidates: [fastExit, patient],
    outerTrainFraction: 0.65,
    outerTestFraction: 0.2,
    outerMinTrainSessions: 8,
    innerTrainFraction: 0.5,
    innerTestFraction: 0.25,
    innerMinTrainSessions: 4,
    minInnerSignals: 2,
    minInnerSignalBearingFolds: 1,
    roundTripCostPct: 0.05,
  });

  assert.ok(result.matchedOuterTestRowCount > 0);
  assert.equal(result.matchedOuterTestRowCount, result.stateMachine.outerOutcomes.length);
  assert.equal(result.matchedComparators.pairedSignalCount, result.matchedOuterTestRowCount);
  assert.equal(result.selectionIntegrity.matchedComparatorUsesExactNestedOuterRows, true);
  assert.equal(result.selectionIntegrity.comparatorsUsedForStateMachineConfigSelection, false);
  assert.equal(result.selectionIntegrity.priorP23_3ResultsUsedToPostSelectP23_6OuterOutcomes, false);
  assert.equal(result.interpretation.finalUntouchedOosEdgeClaimAllowed, false);
  assert.equal(result.interpretation.reusedRecentResearchWindow, true);
  assert.equal(result.edgeClaimAllowed, false);
  assert.equal(result.executionAllowed, false);
  assert.equal(result.transmitted, false);
});

test('outer-outcome selection attempt is rejected', () => {
  assert.throws(() => evaluateRealNestedStateMachine([], { allowOuterOutcomeSelection: true }), /forbidden/);
});
