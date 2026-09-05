import assert from 'node:assert/strict';
import test from 'node:test';
import { buildPurgedExitV5Split } from '../daytrade/phase57-exit-v5-continuation-dataset.js';
import {
  PHASE57_EXIT_V5_AUDITED_SPLIT_POLICY,
  PHASE57_EXIT_V5_AUDITED_SPLIT_SAFETY,
  assertExitV5AuditedSplitSafety,
  assertExitV5AuditedEvaluationRows,
  runExitV5AuditedSplitPairedEvaluation,
} from '../daytrade/phase57-exit-v5-audited-split-evaluator.js';

const BOUNDARIES = Object.freeze({
  developmentEnd: '2026-09-01T23:59:59.000Z',
  validationEnd: '2026-09-02T23:59:59.000Z',
  oosEnd: '2026-09-03T23:59:59.000Z',
});

function sample(featureAt, labelThrough, sessionDate) {
  return Object.freeze({
    features: Object.freeze({ featureAt }),
    labels: Object.freeze({ labelThrough }),
    provenance: Object.freeze({ sessionDate }),
  });
}

function auditedSplit() {
  return buildPurgedExitV5Split([
    sample('2026-09-01T10:00:00.000Z', '2026-09-01T10:15:00.000Z', '2026-09-01'),
    sample('2026-09-02T10:00:00.000Z', '2026-09-02T10:15:00.000Z', '2026-09-02'),
    sample('2026-09-03T10:00:00.000Z', '2026-09-03T10:15:00.000Z', '2026-09-03'),
    sample('2026-09-04T10:00:00.000Z', '2026-09-04T10:15:00.000Z', '2026-09-04'),
  ], BOUNDARIES);
}

function bar(timestamp, close = 100) {
  return { timestamp, open: close, high: close + 0.2, low: close - 0.2, close, volume: 1000 };
}

function row({ entryTimestamp, sessionDate, futureTimestamps }) {
  return {
    entryAccepted: true,
    frozenBeforeOutcome: true,
    currentOutcomeUsed: false,
    entryTimestamp,
    sessionDate,
    entryPrice: 100,
    symbol: '7203.T',
    direction: 'LONG',
    signalDirection: 1,
    futureBars: futureTimestamps.map((timestamp, index) => bar(timestamp, 100 + index * 0.1)),
  };
}

const VALIDATION_ROW = Object.freeze(row({
  entryTimestamp: '2026-09-02T10:00:00.000Z',
  sessionDate: '2026-09-02',
  futureTimestamps: ['2026-09-02T10:05:00.000Z', '2026-09-02T10:10:00.000Z'],
}));
const OOS_ROW = Object.freeze(row({
  entryTimestamp: '2026-09-03T10:00:00.000Z',
  sessionDate: '2026-09-03',
  futureTimestamps: ['2026-09-03T10:05:00.000Z', '2026-09-03T10:10:00.000Z'],
}));
const PROSPECTIVE_ROW = Object.freeze(row({
  entryTimestamp: '2026-09-04T10:00:00.000Z',
  sessionDate: '2026-09-04',
  futureTimestamps: ['2026-09-04T10:05:00.000Z', '2026-09-04T10:10:00.000Z'],
}));

test('strict split guard accepts only rows inside the requested audited outer window', () => {
  const split = auditedSplit();
  assert.equal(assertExitV5AuditedEvaluationRows({ evaluationRows: [VALIDATION_ROW], purgedSplit: split, splitName: 'validation' }).status, 'EXIT_V5_AUDITED_SPLIT_ROWS_CONFIRMED');
  assert.equal(assertExitV5AuditedEvaluationRows({ evaluationRows: [OOS_ROW], purgedSplit: split, splitName: 'oos' }).fullTradeTrajectoryContained, true);
  assert.equal(assertExitV5AuditedEvaluationRows({ evaluationRows: [PROSPECTIVE_ROW], purgedSplit: split, splitName: 'prospective' }).purgedBoundarySessionsExcluded, true);

  assert.throws(
    () => assertExitV5AuditedEvaluationRows({ evaluationRows: [VALIDATION_ROW], purgedSplit: split, splitName: 'oos' }),
    /strictly after its lower split boundary/,
  );
  assert.throws(
    () => assertExitV5AuditedEvaluationRows({ evaluationRows: [OOS_ROW], purgedSplit: split, splitName: 'validation' }),
    /starts after its upper split boundary/,
  );
  assert.throws(
    () => assertExitV5AuditedEvaluationRows({ evaluationRows: [OOS_ROW], purgedSplit: split, splitName: 'prospective' }),
    /strictly after its lower split boundary/,
  );
});

test('validation and OOS trades may not carry realized trajectories across the next boundary', () => {
  const split = auditedSplit();
  const crossingValidation = row({
    entryTimestamp: '2026-09-02T23:55:00.000Z',
    sessionDate: '2026-09-02',
    futureTimestamps: ['2026-09-02T23:58:00.000Z', '2026-09-03T00:03:00.000Z'],
  });
  assert.throws(
    () => assertExitV5AuditedEvaluationRows({ evaluationRows: [crossingValidation], purgedSplit: split, splitName: 'validation' }),
    /trade trajectory crosses its upper split boundary/,
  );

  const crossingOos = row({
    entryTimestamp: '2026-09-03T23:55:00.000Z',
    sessionDate: '2026-09-03',
    futureTimestamps: ['2026-09-03T23:58:00.000Z', '2026-09-04T00:03:00.000Z'],
  });
  assert.throws(
    () => assertExitV5AuditedEvaluationRows({ evaluationRows: [crossingOos], purgedSplit: split, splitName: 'oos' }),
    /trade trajectory crosses its upper split boundary/,
  );
});

test('rows from sessions marked as boundary-purged are rejected even when timestamps fit', () => {
  const split = auditedSplit();
  const marked = Object.freeze({
    ...split,
    splitPolicy: Object.freeze({
      ...split.splitPolicy,
      purgedSessionKeys: Object.freeze(['2026-09-02']),
    }),
  });
  assert.throws(
    () => assertExitV5AuditedEvaluationRows({ evaluationRows: [VALIDATION_ROW], purgedSplit: marked, splitName: 'validation' }),
    /belongs to a purged boundary session/,
  );
});

test('strict paired entrypoint binds fitted development boundary to the audited split before evaluation', () => {
  const split = auditedSplit();
  assert.throws(
    () => runExitV5AuditedSplitPairedEvaluation({
      evaluationRows: [VALIDATION_ROW],
      purgedSplit: split,
      fittedModels: { developmentEnd: '2026-08-31T23:59:59.000Z' },
      splitName: 'validation',
    }),
    /development boundary does not match audited split/,
  );
});

test('audited split evaluator remains research-only and has no promotion or execution path', () => {
  assert.equal(assertExitV5AuditedSplitSafety(), true);
  assert.equal(PHASE57_EXIT_V5_AUDITED_SPLIT_POLICY.outerOosRetuningAllowed, false);
  assert.equal(PHASE57_EXIT_V5_AUDITED_SPLIT_POLICY.prospectiveRetuningAllowed, false);
  assert.equal(PHASE57_EXIT_V5_AUDITED_SPLIT_POLICY.evaluationLabelsUsedByDecision, false);
  for (const key of [
    'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
    'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed', 'transmitted',
  ]) assert.equal(PHASE57_EXIT_V5_AUDITED_SPLIT_SAFETY[key], false, key);
});
