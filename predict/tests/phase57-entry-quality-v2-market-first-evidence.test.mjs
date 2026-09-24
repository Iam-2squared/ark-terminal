import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import { fingerprintEntryV2SelectionScope } from '../daytrade/phase57-entry-quality-v2-historical-market-data.js';

const integrityPath = new URL(
  '../daytrade/phase57-entry-quality-v2-market-first-integrity-2026-09-05.json',
  import.meta.url,
);
const scopePath = new URL(
  '../daytrade/phase57-entry-quality-v2-market-first-selection-symbols-2026-09-05.json',
  import.meta.url,
);
const integrity = JSON.parse(fs.readFileSync(integrityPath, 'utf8'));
const scope = JSON.parse(fs.readFileSync(scopePath, 'utf8'));
const sha256 = value => createHash('sha256').update(value).digest('hex');
const falseSafetyKeys = [
  'executionAllowed',
  'brokerWriteAllowed',
  'excelOrderWriteAllowed',
  'rssOrderFunctionAllowed',
  'liveTradingAllowed',
  'paperTradingAllowed',
  'automaticPromotionAllowed',
  'productionUpdateAllowed',
  'transmitted',
];

test('market-first evidence reaches Checkpoint A without counting golden events twice', () => {
  assert.equal(integrity.status, 'CHECKPOINT_A_200_REACHED');
  assert.equal(integrity.checkpoints.checkpoint200Reached, true);
  assert.equal(integrity.checkpoints.checkpoint500Reached, false);
  assert.equal(integrity.marketDataset.totalMarketBars, 2_512_365);
  assert.equal(integrity.marketDataset.readySnapshots, 1_074);
  assert.equal(integrity.eventDataset.totalSelectedEvents, 41_232);
  assert.equal(integrity.eventDataset.totalP21CandidateEvents, 445);
  assert.equal(integrity.eventDataset.independentCandidateEvents, 445);
  assert.equal(integrity.eventDataset.duplicateCandidateEvents, 0);
  assert.equal(integrity.parityAndLeakageAudit.existingGoldenRowsExcludedFromDevelopmentAggregation, true);
  assert.equal(integrity.parityAndLeakageAudit.goldenBarAuditCount, 41);
  assert.equal(integrity.parityAndLeakageAudit.pitViolationCount, 0);
  assert.equal(integrity.classification.modelFittingPerformed, false);
  assert.equal(integrity.modelReadiness.modelFittingAllowed, false);
});

test('labels, strict Daily Context, missing optional contexts, source class, and safety remain explicit', () => {
  for (const stats of Object.values(integrity.eventDataset.labelCompletenessByHorizon)) {
    assert.equal(stats.complete + stats.incomplete, 445);
  }
  assert.deepEqual(integrity.eventDataset.sourceClassBreakdown, {
    HISTORICAL_RECONSTRUCTION_LATER_FETCHED: 445,
  });
  assert.equal(integrity.classification.prospective, false);
  assert.equal(integrity.classification.formalOos, false);
  assert.equal(integrity.eventDataset.dailyContextCoverage.covered, 445);
  assert.equal(integrity.eventDataset.dailyContextCoverage.missingOrBlocked, 0);
  assert.equal(integrity.eventDataset.dailyContextCoverage.archiveDailyRecordCount, 189_735);
  assert.equal(integrity.eventDataset.dailyContextCoverage.availablePriorSessionsPerCandidate.min, 111);
  assert.equal(integrity.eventDataset.dailyContextCoverage.availablePriorSessionsPerCandidate.median, 479);
  assert.equal(integrity.eventDataset.dailyContextCoverage.corporateActionAudit.adjustedCloseUsedAsFeature, false);
  assert.equal(integrity.eventDataset.dailyContextCoverage.corporateActionAudit.providerQuoteCorporateActionSemanticsResolved, false);
  assert.match(integrity.eventDataset.dailyContextCoverage.status, /STRICT_PRIOR_SESSION/);
  assert.equal(integrity.eventDataset.marketContextCoverage.marketWideBreadthCovered, 445);
  assert.equal(integrity.eventDataset.marketContextCoverage.benchmarkIndexCovered, 0);
  assert.equal(integrity.eventDataset.marketContextCoverage.topixCovered, 0);
  assert.equal(integrity.eventDataset.marketContextCoverage.nikkei225Covered, 0);
  assert.match(integrity.eventDataset.tickToPriceCoverage.status, /NO_VALUE_FABRICATED/);
  assert.equal(integrity.marketDataset.universeAudit.claimedAsCompleteHistoricalJpxUniverse, false);
  assert.equal(integrity.riskAudit.historicalUniverseClaimedComplete, false);
  assert.match(integrity.riskAudit.checkpoint500PhysicalConstraint, /OLDER_FROZEN_P21_HISTORY_OR_A_NEW_PROVIDER/);
  assert.ok(integrity.modelReadiness.reasons.includes('DATASET_READINESS_PHASE0_REQUIRED_BEFORE_MODEL_FITTING'));
  for (const key of falseSafetyKeys) assert.equal(integrity.safety[key], false, key);
});

test('daily acquisition scope is bound to all Current Dynamic5m selected symbols', () => {
  assert.equal(fingerprintEntryV2SelectionScope(scope), scope.selectionScopeContentSha256);
  assert.equal(
    fingerprintEntryV2SelectionScope({ ...scope, generatedAt: '2099-01-01T00:00:00.000Z' }),
    scope.selectionScopeContentSha256,
  );
  assert.equal(scope.sourceClass, 'HISTORICAL_RECONSTRUCTION_LATER_FETCHED');
  assert.equal(scope.symbolCount, 397);
  assert.equal(new Set(scope.symbols).size, scope.symbolCount);
  assert.deepEqual(scope.symbols, [...scope.symbols].sort());
  assert.equal(scope.candidateOutcomeUsedToChooseSymbols, false);
  assert.equal(scope.dailyDataMayInfluenceHistoricalSelectorReplay, false);
  assert.equal(integrity.selectionScopeContentSha256, scope.selectionScopeContentSha256);
  for (const key of falseSafetyKeys) assert.equal(scope.safety[key], false, key);
});
