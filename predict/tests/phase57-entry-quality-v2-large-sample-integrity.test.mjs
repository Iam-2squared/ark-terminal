import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const substratePath = fileURLToPath(new URL(
  '../daytrade/phase57-entry-quality-v2-development-candidate-substrate-2026-09-05.json',
  import.meta.url,
));
const reportPath = fileURLToPath(new URL(
  '../daytrade/phase57-entry-quality-v2-large-sample-integrity-2026-09-05.json',
  import.meta.url,
));
const substrateBytes = readFileSync(substratePath);
const substrate = JSON.parse(substrateBytes);
const report = JSON.parse(readFileSync(reportPath));

const FALSE_SAFETY_KEYS = [
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
const LABEL_HORIZONS = [1, 2, 3, 6, 12];

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])]));
  }
  return value;
}

function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

function assertSafety(safety) {
  for (const key of FALSE_SAFETY_KEYS) assert.equal(safety?.[key], false, key);
}

function jstSessionDate(timestamp) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date(timestamp)).map(part => [part.type, part.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}

test('freezes 41 independent candidates with strict source-class separation and no model', () => {
  assert.equal(substrate.status, 'ENTRY_V2_CANDIDATE_SUBSTRATE_READY_BELOW_200_NO_MODEL');
  assert.equal(substrate.rowCount, 41);
  assert.equal(substrate.rows.length, 41);
  assert.equal(new Set(substrate.rows.map(row => row.candidateEventId)).size, 41);
  assert.deepEqual(substrate.sourceClassBreakdown, {
    ACTUAL_DURABLE: 6,
    HISTORICAL_REPLAY_ARCHIVED_PIT: 0,
    HISTORICAL_RECONSTRUCTION_LATER_FETCHED: 35,
  });
  assert.equal(substrate.datasetSha256, sha256(JSON.stringify(canonical(substrate.rows))));
  assert.equal(substrate.classification.entryQualityModelFitted, false);
  assert.equal(substrate.classification.modelFittingAllowed, false);
  assert.equal(substrate.classification.newEntrySignalProduced, false);
  assert.equal(substrate.classification.signalEligible, null);
  assert.equal(substrate.classification.direction, null);
  assert.equal(substrate.fixedExperimentBoundary.selectorChanged, false);
  assert.equal(substrate.fixedExperimentBoundary.entryPolicyChanged, false);
  assert.equal(substrate.fixedExperimentBoundary.exitChanged, false);
  assert.equal(substrate.fixedExperimentBoundary.capitalAllocationChanged, false);
  assert.equal(substrate.fixedExperimentBoundary.costAssumptionsChanged, false);
  assertSafety(substrate.safety);

  const actual = substrate.rows.filter(row => row.sourceClass === 'ACTUAL_DURABLE');
  const reconstructed = substrate.rows.filter(
    row => row.sourceClass === 'HISTORICAL_RECONSTRUCTION_LATER_FETCHED',
  );
  assert.equal(actual.length, 6);
  assert.equal(reconstructed.length, 35);
  for (const row of actual) {
    assert.equal(row.datasetRole, 'ACTUAL_DURABLE_DIAGNOSTIC_SOURCE_CLASS_PRESERVED');
    assert.equal(row.formalOos, false);
    assert.equal(row.completeSessionEvidence, false);
    assert.equal(row.prospectivePerformanceEligible, false);
    assert.equal(row.sourceSessionClassification.formalOos, false);
    assert.equal(row.sourceSessionClassification.completeSessionEvidence, false);
  }
  for (const row of reconstructed) {
    assert.equal(row.datasetRole, 'DEVELOPMENT_ONLY');
    assert.equal(row.prospective, false);
    assert.equal(row.formalOos, false);
    assert.equal(row.sourceLineage.sourceClass, 'HISTORICAL_RECONSTRUCTION_LATER_FETCHED');
    assert.equal(row.sourceLineage.reconstructionFetchedAfterDecision, true);
    assert.equal(row.sourceLineage.prospective, false);
    assert.equal(row.sourceLineage.formalOos, false);
    assert.match(row.sourceLineage.sourceArtifactSha256, /^[0-9a-f]{64}$/);
  }
});

test('candidate substrate keeps completed-bar PIT and future labels separated', () => {
  for (const row of substrate.rows) {
    assert.equal(row.pointInTimeValid, true, row.candidateEventId);
    assert.equal(row.pitViolationCount, 0, row.candidateEventId);
    assert.equal(row.featureFrozenBeforeOfflineLabels, true, row.candidateEventId);
    assert.equal(row.currentOutcomeUsed, false, row.candidateEventId);
    assert.equal(row.frozenBeforeOutcome, true, row.candidateEventId);
    assert.equal(row.selectionTimestamp, row.entryTimestamp, row.candidateEventId);
    assert.ok(Date.parse(row.featureCutoff) <= Date.parse(row.entryTimestamp), row.candidateEventId);
    assert.equal(row.contextBars.length, row.contextBarCount, row.candidateEventId);
    assert.equal(row.contextBarsHashEncoding, 'CANONICAL_JSON_SHA256', row.candidateEventId);
    assert.match(row.sourceContextBarsSha256, /^[0-9a-f]{64}$/, row.candidateEventId);
    assert.equal(row.contextBarsSha256, sha256(JSON.stringify(canonical(row.contextBars))), row.candidateEventId);
    assert.equal(row.contextBars.at(-1).timestamp, row.featureCutoff, row.candidateEventId);
    let previous = -Infinity;
    for (const bar of row.contextBars) {
      const timestamp = Date.parse(bar.timestamp);
      assert.ok(timestamp > previous, row.candidateEventId);
      assert.ok(timestamp + 5 * 60_000 <= Date.parse(row.entryTimestamp), row.candidateEventId);
      assert.equal(jstSessionDate(bar.timestamp), row.sessionDate, row.candidateEventId);
      previous = timestamp;
    }

    assert.deepEqual(row.qualityLabels.map(label => label.horizonBars), LABEL_HORIZONS);
    for (const label of row.qualityLabels) {
      assert.equal(label.complete, row.labelCompleteness[String(label.horizonBars)]);
      if (!label.complete) {
        assert.equal(label.long, null);
        assert.equal(label.short, null);
        continue;
      }
      for (const side of ['long', 'short']) {
        for (const key of [
          'grossReturnPct', 'costAdjustedReturnPct', 'mfePct', 'maePct',
          'timeToMfeBars', 'timeToMaeBars',
        ]) {
          assert.equal(Number.isFinite(label[side][key]), true, `${row.candidateEventId}:${side}:${key}`);
        }
        for (const key of ['mfeTimestamp', 'maeTimestamp']) {
          assert.equal(jstSessionDate(label[side][key]), row.sessionDate, row.candidateEventId);
          assert.ok(Date.parse(label[side][key]) > Date.parse(row.entryTimestamp), row.candidateEventId);
        }
      }
    }
  }
});

test('integrity report binds the substrate and preserves recovery blockers', () => {
  assert.equal(report.status, 'ENTRY_V2_DEVELOPMENT_DATASET_BELOW_200_CHECKPOINT');
  assert.equal(report.classification.developmentOnly, true);
  assert.equal(report.classification.prospective, false);
  assert.equal(report.classification.formalOos, false);
  assert.equal(report.classification.modelFittingAllowed, false);
  assert.equal(report.checkpoints.checkpoint200Reached, false);
  assert.equal(report.checkpoints.checkpoint500Reached, false);
  assert.equal(report.checkpoints.checkpoint1000Reached, false);
  assert.equal(report.checkpoints.currentIndependentCandidateEvents, 41);
  assertSafety(report.safety);

  const dataset = report.candidateDataset;
  assert.equal(dataset.totalIndependentCandidateEvents, 41);
  assert.equal(dataset.actualDurableIndependentCandidates, 6);
  assert.equal(dataset.archivedHistoricalIndependentCandidates, 0);
  assert.equal(dataset.laterFetchedReconstructionIndependentCandidates, 35);
  assert.equal(dataset.uniqueSymbolCount, 8);
  assert.equal(dataset.sessionCount, 5);
  assert.deepEqual(dataset.countsByDirection, { LONG: 27, SHORT: 14 });
  assert.deepEqual(dataset.countsByMembership, { V1_AND_V2: 27, V1_ONLY: 14 });
  assert.equal(dataset.duplicateRowsWithinSource, 0);
  assert.equal(dataset.crossSourceReplayOverlapExcluded, 6);
  assert.equal(dataset.pitViolationCount, 0);
  assert.equal(dataset.candidateSubstrateFileSha256, sha256(substrateBytes));
  assert.deepEqual(dataset.labelCompletenessByHorizon, {
    1: { complete: 40, incomplete: 1, total: 41 },
    2: { complete: 39, incomplete: 2, total: 41 },
    3: { complete: 37, incomplete: 4, total: 41 },
    6: { complete: 35, incomplete: 6, total: 41 },
    12: { complete: 34, incomplete: 7, total: 41 },
  });

  assert.equal(report.replayInputAudit.rawPointCount, 132);
  assert.equal(report.replayInputAudit.selectorParityVerifiedPointCount, 132);
  assert.equal(report.replayInputAudit.readyPointCount, 102);
  assert.equal(report.replayInputAudit.blockedPointCount, 30);
  assert.deepEqual(report.replayInputAudit.blockedReasonDistribution, {
    INSUFFICIENT_CLOSED_PREFIX_COVERAGE: 2,
    INCOMPLETE_CURRENT_SELECTOR_BAR_COVERAGE: 28,
  });
  assert.equal(report.replayInputAudit.pitViolationCount, 0);

  const september01 = report.recovery.session20260901;
  assert.equal(september01.recoveredArchiveSymbolCount, 154);
  assert.equal(september01.expectedArchiveSymbolCount, 155);
  assert.deepEqual(september01.unavailableSymbols, ['6522.T']);
  assert.equal(september01.readyPoints, 21);
  assert.equal(september01.blockedPoints, 29);
  assert.equal(september01.noInterpolationOrFabrication, true);

  const september02 = report.recovery.session20260902;
  assert.equal(september02.original36ReadyPointsAfterReconstruction, 35);
  assert.equal(september02.original36BlockedPointsAfterReconstruction, 1);
  assert.equal(september02.pointInventory.length, 37);
  assert.equal(september02.pointInventory.filter(point => point.original36PointAudit).length, 36);
  assert.equal(september02.noInterpolationOrFabrication, true);
  for (const point of september02.pointInventory) {
    assert.equal(typeof point.pointTimestamp, 'string');
    assert.equal(point.selectedSymbolCount, point.requiredSymbols.length);
    assert.equal(Array.isArray(point.availableSymbols), true);
    assert.equal(Array.isArray(point.missingSymbols), true);
    assert.equal(point.requiredPrefixBars.length, point.requiredSymbols.length);
    assert.match(point.rawSnapshotSha256, /^[0-9a-f]{64}$/);
    assert.match(point.selectionSha256, /^[0-9a-f]{64}$/);
    assert.match(point.barArchiveSha256, /^[0-9a-f]{64}$/);
    for (const prefix of point.requiredPrefixBars) {
      assert.equal(Array.isArray(prefix.missingBarIntervals), true);
    }
  }

  assert.equal(report.diagnosticCoverage.dailyContext.available, 0);
  assert.equal(report.diagnosticCoverage.marketContext.available, 0);
  assert.equal(report.diagnosticCoverage.tickToPrice.available, 0);
  assert.equal(report.diagnosticCoverage.price.hardGateApplied, false);
  assert.equal(report.diagnosticCoverage.liquidityTurnover.hardGateApplied, false);
  for (const source of report.sourceSearch.sourceArtifacts) {
    assert.match(source.sha256, /^[0-9a-f]{64}$/);
  }
});
