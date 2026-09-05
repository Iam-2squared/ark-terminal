import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {
  ENTRY_V2_READINESS_PHASE0_POLICY,
  ENTRY_V2_READINESS_PHASE0_SAFETY,
  applyDailyPriceBasisPolicy,
  buildGroupedWalkForwardPrecommit,
  buildLabelMissingnessAudit,
  oneWayClusterAudit,
  quantile,
} from '../daytrade/phase57-entry-quality-v2-readiness-audit.js';

const evidence = JSON.parse(fs.readFileSync(new URL(
  '../daytrade/phase57-entry-quality-v2-dataset-readiness-phase0-2026-09-05.json', import.meta.url,
), 'utf8'));
const falseSafetyKeys = [
  'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
  'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed', 'transmitted',
];

test('unbalanced ICC and design-effect effective n are computed from observed clusters', () => {
  const rows = [
    { session: 'A', value: 1 }, { session: 'A', value: 1 },
    { session: 'B', value: 3 }, { session: 'B', value: 3 },
  ];
  const audit = oneWayClusterAudit(rows, { clusterKey: 'session', valueKey: 'value' });
  assert.equal(audit.nominalN, 4);
  assert.equal(audit.clusterCount, 2);
  assert.equal(audit.icc, 1);
  assert.equal(audit.designEffect, 2);
  assert.equal(audit.approximateEffectiveN, 2);
  assert.equal(quantile([1, 2, 3, 4], 0.5), 2.5);
});

test('Daily price-basis policy does not double-adjust provider quote OHLC', () => {
  const records = [
    { sessionDate: '2026-01-05', open: 100, high: 110, low: 90, close: 105, volume: 1000 },
    { sessionDate: '2026-01-06', open: 104, high: 108, low: 100, close: 106, volume: 1200 },
  ];
  const result = applyDailyPriceBasisPolicy(records, [
    { type: 'SPLIT', sessionDate: '2026-01-06', numerator: 2, denominator: 1 },
    { type: 'SPLIT', sessionDate: '2026-02-01', numerator: 3, denominator: 1 },
  ], '2026-01-06');
  assert.deepEqual(result.records.map(row => row.close), [105, 106]);
  assert.equal(result.lineage.providerQuoteOhlcReAdjusted, false);
  assert.equal(result.lineage.futureSplitEventsExcludedFromFeatureTransformation, 1);
  assert.match(ENTRY_V2_READINESS_PHASE0_POLICY.dailyPriceBasis.splitNormalization, /DO_NOT_REAPPLY/);
});

test('same-session right censoring and grouped split boundaries remain explicit', () => {
  const missingness = buildLabelMissingnessAudit([
    { entryTimestamp: '2026-09-01T00:30:00.000Z', labelCompleteness: { 1: true, 3: true, 6: true, 12: true } },
    { entryTimestamp: '2026-09-01T06:00:00.000Z', labelCompleteness: { 1: true, 3: false, 6: false, 12: false } },
  ]);
  assert.equal(missingness.labelsImputed, false);
  assert.equal(missingness.byTimeOfDay['14:30-15:30'].horizons[12].coverage, 0);
  const split = buildGroupedWalkForwardPrecommit(Array.from({ length: 12 }, (_, index) => `2026-08-${String(index + 1).padStart(2, '0')}`));
  assert.ok(split.folds.length > 0);
  assert.equal(split.embargoSessions, 1);
  assert.equal(split.currentSessionsClaimedUntouchedOos, false);
  for (const fold of split.folds) {
    assert.equal(fold.trainingSessions.some(session => fold.validationSessions.includes(session)), false);
    assert.equal(fold.embargoSessions.some(session => fold.validationSessions.includes(session)), false);
  }
});

test('Phase 0 evidence quantifies dependence and remains a model NO-GO', () => {
  assert.equal(evidence.status, 'PHASE0_AUDIT_COMPLETE_MODEL_NO_GO');
  assert.equal(evidence.datasetSummary.nominalCandidateCount, 445);
  assert.equal(evidence.datasetSummary.sessionCount, 16);
  assert.equal(evidence.goldenMismatchAudit.eventCount, 41);
  assert.equal(evidence.goldenMismatchAudit.exactOhlcvContextCount, 21);
  assert.equal(evidence.goldenMismatchAudit.exactEntryReferenceCount, 13);
  assert.equal(evidence.corporateActionAudit.actionCounts.splits, 81);
  assert.equal(evidence.corporateActionAudit.candidateOverlapCounts.split.prior20Sessions, 0);
  assert.equal(evidence.corporateActionAudit.empiricalSplitContinuity.providerQuoteContinuousBasisCount, 81);
  assert.ok(evidence.effectiveSampleSizeAudit['h6.grossReturnPct'].approximateEffectiveN < 382);
  assert.deepEqual(evidence.sessionRegimeAudit.distribution.direction, { UP: 6, FLAT: 8, DOWN: 2 });
  assert.deepEqual(evidence.sessionRegimeAudit.distribution.volatility, { NORMAL_VOL: 16 });
  assert.equal(evidence.multiHorizonMissingnessAudit.byTimeOfDay['14:30-15:30'].horizons[12].complete, 0);
  assert.equal(evidence.validationPrecommit.currentSessionsClaimedUntouchedOos, false);
  assert.equal(evidence.modelReadinessGate.fiveHundredCandidatesAbsoluteRequirement, false);
  assert.equal(evidence.modelReadinessGate.decision, 'NO_GO');
  assert.equal(evidence.classification.modelFittingPerformed, false);
  for (const key of falseSafetyKeys) assert.equal(evidence.safety[key], false, key);
  for (const key of falseSafetyKeys) assert.equal(ENTRY_V2_READINESS_PHASE0_SAFETY[key], false, key);
});
