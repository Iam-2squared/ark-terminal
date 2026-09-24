import { createHash } from 'node:crypto';
import {
  buildIntradayDynamicUniverseTimeline,
  PHASE57_INTRADAY_UNIVERSE_POLICY,
} from './phase57-p25-intraday-dynamic-universe.js';
import { buildProspectiveP21HistoricalRows } from './phase57-p21-prospective-history.js';
import { buildProspectiveP21FeatureFeed } from './phase57-p21-prospective-feature-feed.js';
import { buildProspectiveP21FrozenDecision } from './phase57-p21-prospective-frozen-base.js';
import { buildFrozenPhase57SnapshotFromRuntimeDecision } from '../scalping/phase58-phase57-runtime-adapter.js';
import { PHASE58_P13_FROZEN_POLICY } from '../scalping/phase58-phase57-prospective-pipeline.js';
import { buildEntryQualityV2PathLabels } from './phase57-entry-quality-v2-labels.js';
import { PHASE57_ENTRY_QUALITY_V2_SAFETY } from './phase57-entry-quality-v2-research.js';
import { ENTRY_V2_SOURCE_CLASS } from './phase57-entry-quality-v2-candidate-inventory.js';

export const ENTRY_V2_HISTORICAL_REPLAY_POLICY = Object.freeze({
  mode: 'ENTRY_V2_HISTORICAL_RETROSPECTIVE_REPLAY_READ_ONLY',
  sourceClass: ENTRY_V2_SOURCE_CLASS.historicalReplay,
  datasetRole: 'DEVELOPMENT_ONLY',
  prospective: false,
  formalOos: false,
  currentSelectorCandidateId: 'INTRADAY_DYNAMIC_5M_UNIVERSE_V1',
  frozenEntryBaseline: 'PHASE57_P21_FROZEN_ENTRY',
  acceptedRawSnapshotPhases: Object.freeze([
    '57.p25.marketwide-5m-fresh-capture',
    '57.entry-quality-v2.historical-market-reconstruction',
  ]),
  minimumMarketwideSymbols: 3000,
  minimumClosedPrefixBars: 6,
  completedBarRule: 'bar.timestamp + 5 minutes <= decisionTimestamp',
  archivedPitSourceClass: ENTRY_V2_SOURCE_CLASS.historicalReplayArchivedPit,
  laterFetchedSourceClass: ENTRY_V2_SOURCE_CLASS.historicalReconstructionLaterFetched,
  sourceLineageRequired: true,
  missingInputsMayBeBackfilled: false,
  oldSelectorMembershipMayBeReused: false,
  byteEquivalentFrozenPriorModelReuseAllowed: true,
  selectorChangesAllowed: false,
  entryChangesAllowed: false,
  exitChangesAllowed: false,
  capitalAllocationChangesAllowed: false,
  automaticPromotionAllowed: false,
  executionAllowed: false,
});

export const ENTRY_V2_HISTORICAL_REPLAY_SAFETY = Object.freeze({
  ...PHASE57_ENTRY_QUALITY_V2_SAFETY,
  mode: 'ENTRY_V2_HISTORICAL_RETROSPECTIVE_REPLAY_READ_ONLY',
  historicalReplayOnly: true,
  developmentOnly: true,
  prospective: false,
  formalOos: false,
});

const FALSE_KEYS = Object.freeze([
  'executionAllowed',
  'brokerWriteAllowed',
  'excelOrderWriteAllowed',
  'rssOrderFunctionAllowed',
  'liveTradingAllowed',
  'paperTradingAllowed',
  'automaticPromotionAllowed',
  'productionUpdateAllowed',
  'transmitted',
]);

const FORBIDDEN_RAW_KEYS = Object.freeze([
  'selected',
  'selectedSymbols',
  'DYNAMIC_30',
  'DYNAMIC_40',
  'DYNAMIC_50',
  'outcome',
  'futureReturnPct',
  'netReturnPct',
  'target',
  'label',
]);

const DETAILED_HISTORICAL_SOURCE_CLASSES = Object.freeze([
  ENTRY_V2_SOURCE_CLASS.historicalReplayArchivedPit,
  ENTRY_V2_SOURCE_CLASS.historicalReconstructionLaterFetched,
]);

const sha256 = value => createHash('sha256').update(typeof value === 'string' ? value : JSON.stringify(value)).digest('hex');
const frozenRowKey = row => `${row?.symbol ?? ''}|${row?.sessionDate ?? ''}|${row?.featureCutoff ?? ''}`;

function frozenArtifactHashForAsOf({ picked, trainRows, asOf }) {
  const payload = {
    lineage: 'PHASE57_P21_NESTED_ADAPTIVE_PROSPECTIVE_V1',
    asOf,
    selection: {
      horizonBars: picked.horizonBars,
      featureFamily: picked.featureFamily,
      featureKeys: picked.featureKeys,
      configId: picked.configId,
      modelType: picked.modelType,
      modelOptions: picked.modelOptions,
      threshold: picked.threshold,
    },
    trainingRows: trainRows.map(row => ({
      key: frozenRowKey(row),
      outcomeAt: row.outcomeAt,
      label: Number(row.label),
      actualReturnPct: Number(row.actualReturnPct),
      features: row.features,
    })),
  };
  return sha256(payload);
}

function iso(value, code) {
  const ms = Date.parse(String(value ?? ''));
  if (!Number.isFinite(ms)) throw new Error(`ENTRY_V2_REPLAY_${code}_INVALID`);
  return new Date(ms).toISOString();
}

function jstParts(value) {
  const ms = Date.parse(String(value ?? ''));
  if (!Number.isFinite(ms)) throw new Error('ENTRY_V2_REPLAY_TIMESTAMP_INVALID');
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tokyo',
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(new Date(ms));
  const fields = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return {
    sessionDate: `${fields.year}-${fields.month}-${fields.day}`,
    minuteOfDay: Number(fields.hour) * 60 + Number(fields.minute),
  };
}

function assertTradingSession(value) {
  const { sessionDate, minuteOfDay } = jstParts(value);
  const morning = minuteOfDay >= 9 * 60 && minuteOfDay <= 11 * 60 + 30;
  const afternoon = minuteOfDay >= 12 * 60 + 30 && minuteOfDay <= 15 * 60 + 30;
  if (!morning && !afternoon) throw new Error('ENTRY_V2_REPLAY_DECISION_OUTSIDE_JPX_SESSION');
  return sessionDate;
}

function assertSafety(safety, label) {
  for (const key of FALSE_KEYS) {
    if (safety?.[key] !== false) throw new Error(`ENTRY_V2_REPLAY_UNSAFE_${label}_${key}`);
  }
}

function finite(value) {
  return value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
}

function reasonCounts(rows) {
  const counts = {};
  for (const row of rows) counts[row.reason] = (counts[row.reason] ?? 0) + 1;
  return counts;
}

function normalizeArchiveLineage(archive, sessionDate) {
  const sourceClass = String(archive?.sourceClass ?? '');
  if (!DETAILED_HISTORICAL_SOURCE_CLASSES.includes(sourceClass)) {
    throw new Error('ENTRY_V2_REPLAY_BAR_ARCHIVE_SOURCE_CLASS_INVALID');
  }
  if (archive?.prospective === true || archive?.formalOos === true
    || archive?.classification?.prospective === true || archive?.classification?.formalOos === true) {
    throw new Error('ENTRY_V2_REPLAY_BAR_ARCHIVE_FALSE_PROSPECTIVE_CLASSIFICATION');
  }
  const lineage = archive?.sourceLineage;
  if (!lineage || typeof lineage !== 'object') throw new Error('ENTRY_V2_REPLAY_BAR_ARCHIVE_LINEAGE_REQUIRED');
  const sourceArtifact = String(lineage.sourceArtifact ?? '').trim();
  const sourceArtifactSha256 = String(lineage.sourceArtifactSha256 ?? '').trim().toLowerCase();
  const retrievedAt = iso(lineage.retrievedAt, 'BAR_ARCHIVE_RETRIEVED_AT');
  if (!sourceArtifact) throw new Error('ENTRY_V2_REPLAY_BAR_ARCHIVE_ARTIFACT_REQUIRED');
  if (!/^[0-9a-f]{64}$/.test(sourceArtifactSha256)) {
    throw new Error('ENTRY_V2_REPLAY_BAR_ARCHIVE_ARTIFACT_SHA256_INVALID');
  }
  if (lineage.sessionDate !== undefined && String(lineage.sessionDate) !== sessionDate) {
    throw new Error('ENTRY_V2_REPLAY_BAR_ARCHIVE_LINEAGE_DATE_MISMATCH');
  }
  if (lineage.sourceClass !== undefined && String(lineage.sourceClass) !== sourceClass) {
    throw new Error('ENTRY_V2_REPLAY_BAR_ARCHIVE_LINEAGE_CLASS_MISMATCH');
  }
  if (sourceClass === ENTRY_V2_SOURCE_CLASS.historicalReplayArchivedPit
    && (lineage.archivedPointInTimeCapture !== true || lineage.reconstructionFetchedAfterDecision === true)) {
    throw new Error('ENTRY_V2_REPLAY_ARCHIVED_PIT_ATTESTATION_REQUIRED');
  }
  if (sourceClass === ENTRY_V2_SOURCE_CLASS.historicalReconstructionLaterFetched
    && (lineage.reconstructionFetchedAfterDecision !== true || lineage.archivedPointInTimeCapture === true)) {
    throw new Error('ENTRY_V2_REPLAY_LATER_FETCHED_ATTESTATION_REQUIRED');
  }
  return Object.freeze({
    sourceClass,
    sourceArtifact,
    sourceArtifactSha256,
    sourceArtifactHashScope: lineage.sourceArtifactHashScope ?? null,
    retrievedAt,
    sessionDate,
    provider: lineage.provider ?? null,
    actionRunId: lineage.actionRunId ?? null,
    actionArtifactId: lineage.actionArtifactId ?? null,
    sourceRef: lineage.sourceRef ?? null,
    sourceCommitSha: lineage.sourceCommitSha ?? null,
    archivedPointInTimeCapture: lineage.archivedPointInTimeCapture === true,
    reconstructionFetchedAfterDecision: lineage.reconstructionFetchedAfterDecision === true,
    prospective: false,
    formalOos: false,
    developmentOnly: true,
  });
}

function expectedClosedBarTimestamps(sessionDate, decisionTimestamp) {
  const decisionMs = Date.parse(decisionTimestamp);
  const starts = [
    Date.parse(`${sessionDate}T09:00:00+09:00`),
    Date.parse(`${sessionDate}T12:30:00+09:00`),
  ];
  const ends = [
    Date.parse(`${sessionDate}T11:30:00+09:00`),
    Date.parse(`${sessionDate}T15:30:00+09:00`),
  ];
  const timestamps = [];
  for (let segment = 0; segment < starts.length; segment += 1) {
    for (let cursor = starts[segment]; cursor < ends[segment]; cursor += 5 * 60_000) {
      if (cursor + 5 * 60_000 <= decisionMs) timestamps.push(new Date(cursor).toISOString());
    }
  }
  return timestamps;
}

function collapseMissingIntervals(timestamps) {
  if (!timestamps.length) return Object.freeze([]);
  const ranges = [];
  let start = timestamps[0];
  let end = timestamps[0];
  let count = 1;
  for (const timestamp of timestamps.slice(1)) {
    if (Date.parse(timestamp) - Date.parse(end) === 5 * 60_000) {
      end = timestamp;
      count += 1;
    } else {
      ranges.push(Object.freeze({ start, end, count }));
      start = timestamp;
      end = timestamp;
      count = 1;
    }
  }
  ranges.push(Object.freeze({ start, end, count }));
  return Object.freeze(ranges);
}

function normalizeSelected(rows = []) {
  return rows.map(row => ({
    symbol: String(row?.symbol ?? '').trim().toUpperCase(),
    sector: String(row?.sector ?? 'UNKNOWN'),
    currentPrice: Number(row?.currentPrice),
    sourceScannedAt: iso(row?.sourceScannedAt, 'SELECTED_SOURCE_TIMESTAMP'),
    opportunityScore: Number(row?.opportunityScore),
    turnoverYen: Number(row?.turnoverYen),
  }));
}

function normalizeSnapshot(snapshot) {
  if (!snapshot || typeof snapshot !== 'object') throw new Error('ENTRY_V2_REPLAY_RAW_SNAPSHOT_REQUIRED');
  if (!ENTRY_V2_HISTORICAL_REPLAY_POLICY.acceptedRawSnapshotPhases.includes(snapshot.phase)) {
    throw new Error('ENTRY_V2_REPLAY_RAW_SNAPSHOT_PHASE_MISMATCH');
  }
  assertSafety(snapshot.safety, 'RAW_SNAPSHOT');
  if (snapshot?.methodology?.pointInTimeOnly !== true) throw new Error('ENTRY_V2_REPLAY_RAW_SNAPSHOT_NOT_POINT_IN_TIME');
  if (snapshot.phase === '57.entry-quality-v2.historical-market-reconstruction') {
    if (snapshot.sourceClass !== ENTRY_V2_SOURCE_CLASS.historicalReconstructionLaterFetched
      || snapshot.datasetRole !== 'DEVELOPMENT_ONLY'
      || snapshot.prospective !== false
      || snapshot.formalOos !== false
      || snapshot?.sourceLineage?.reconstructionFetchedAfterDecision !== true
      || snapshot?.sourceLineage?.archivedPointInTimeCapture === true
      || snapshot?.methodology?.marketDataBeforeSelector !== true
      || snapshot?.methodology?.futureBarsUsed !== false
      || snapshot?.methodology?.missingBarsInterpolated !== false) {
      throw new Error('ENTRY_V2_REPLAY_LATER_FETCHED_RAW_ATTESTATION_FAILED');
    }
  }
  const observedAt = iso(snapshot.observedAt, 'OBSERVED_AT');
  const sessionDate = assertTradingSession(observedAt);
  const bucketMs = Math.floor(Date.parse(observedAt) / (5 * 60_000)) * (5 * 60_000);
  if (iso(snapshot.bucket, 'BUCKET') !== new Date(bucketMs).toISOString()) throw new Error('ENTRY_V2_REPLAY_BUCKET_MISMATCH');
  if (!Array.isArray(snapshot.rows) || snapshot.rows.length < ENTRY_V2_HISTORICAL_REPLAY_POLICY.minimumMarketwideSymbols) {
    throw new Error('ENTRY_V2_REPLAY_MARKETWIDE_COVERAGE_INSUFFICIENT');
  }
  if (Number(snapshot.symbolCount) !== snapshot.rows.length) throw new Error('ENTRY_V2_REPLAY_SYMBOL_COUNT_MISMATCH');
  if (String(snapshot.stateHash ?? '') !== sha256(JSON.stringify(snapshot.rows))) {
    throw new Error('ENTRY_V2_REPLAY_RAW_STATE_HASH_MISMATCH');
  }

  const seen = new Set();
  const entries = snapshot.rows.map(row => {
    const poisoned = FORBIDDEN_RAW_KEYS.filter(key => Object.prototype.hasOwnProperty.call(row ?? {}, key));
    if (poisoned.length) throw new Error(`ENTRY_V2_REPLAY_RAW_ROW_FORBIDDEN_${poisoned.join('_')}`);
    const symbol = String(row?.symbol ?? '').trim().toUpperCase();
    if (!symbol || seen.has(symbol)) throw new Error('ENTRY_V2_REPLAY_RAW_SYMBOL_INVALID_OR_DUPLICATE');
    seen.add(symbol);
    if (!(Number(row?.price) > 0) || !(Number(row?.volume) > 0) || !finite(row?.changePct)) {
      throw new Error('ENTRY_V2_REPLAY_RAW_ROW_INVALID');
    }
    return Object.freeze({
      symbol,
      sector: String(row?.sector ?? '未分類'),
      market: row?.market ?? null,
      status: 'analyzed',
      currentPrice: Number(row.price),
      volume: Number(row.volume),
      dailyChangePercent: Number(row.changePct),
      scannedAt: observedAt,
    });
  });
  return Object.freeze({
    snapshot,
    observedAt,
    sessionDate,
    entries: Object.freeze(entries),
    snapshotSha256: sha256(JSON.stringify(snapshot)),
  });
}

function measurementIndex(measurements) {
  const index = new Map();
  for (const measurement of Array.isArray(measurements) ? measurements : []) {
    const observedAt = iso(measurement?.observedAt, 'MEASUREMENT_TIMESTAMP');
    if (index.has(observedAt)) throw new Error('ENTRY_V2_REPLAY_DUPLICATE_MEASUREMENT');
    if (measurement?.status !== 'MARKETWIDE_DYNAMIC_5M_MEASUREMENT_READY') {
      throw new Error('ENTRY_V2_REPLAY_MEASUREMENT_NOT_READY');
    }
    assertSafety(measurement.safety, 'MEASUREMENT');
    if (measurement?.policy?.candidateId !== ENTRY_V2_HISTORICAL_REPLAY_POLICY.currentSelectorCandidateId) {
      throw new Error('ENTRY_V2_REPLAY_OLD_OR_DIFFERENT_SELECTOR_REJECTED');
    }
    index.set(observedAt, measurement);
  }
  return index;
}

function archiveIndex(barArchives) {
  const index = new Map();
  for (const archive of Array.isArray(barArchives) ? barArchives : []) {
    const sessionDate = String(archive?.sessionDate ?? '');
    if (!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate)) throw new Error('ENTRY_V2_REPLAY_BAR_ARCHIVE_DATE_INVALID');
    if (index.has(sessionDate)) throw new Error('ENTRY_V2_REPLAY_DUPLICATE_BAR_ARCHIVE');
    assertSafety(archive.safety, 'BAR_ARCHIVE');
    const sourceLineage = normalizeArchiveLineage(archive, sessionDate);
    index.set(sessionDate, Object.freeze({
      ...archive,
      sourceClass: sourceLineage.sourceClass,
      sourceLineage,
      sessionBarsSha256: sha256(JSON.stringify(archive.sessionBarsBySymbol ?? {})),
    }));
  }
  return index;
}

function normalizeBars(bars, sessionDate) {
  if (!Array.isArray(bars) || !bars.length) return null;
  let previousMs = -Infinity;
  return Object.freeze(bars.map((bar, index) => {
    const timestamp = iso(bar?.timestamp, `BAR_${index}_TIMESTAMP`);
    const ms = Date.parse(timestamp);
    if (ms <= previousMs) throw new Error('ENTRY_V2_REPLAY_BARS_NOT_STRICTLY_ORDERED');
    previousMs = ms;
    const normalized = Object.freeze({
      timestamp,
      open: Number(bar?.open), high: Number(bar?.high), low: Number(bar?.low), close: Number(bar?.close),
      volume: Number(bar?.volume ?? 0),
    });
    if (![normalized.open, normalized.high, normalized.low, normalized.close, normalized.volume].every(Number.isFinite)
      || normalized.open <= 0 || normalized.close <= 0 || normalized.high < normalized.low || normalized.volume < 0) {
      throw new Error('ENTRY_V2_REPLAY_BAR_INVALID');
    }
    if (jstParts(timestamp).sessionDate !== sessionDate) throw new Error('ENTRY_V2_REPLAY_CROSS_SESSION_BAR');
    return normalized;
  }));
}

function selectedV2Membership(measurement, symbol) {
  const matches = (measurement?.selectedV2 ?? []).filter(row => String(row?.symbol ?? '').trim().toUpperCase() === symbol);
  if (matches.length > 1) throw new Error('ENTRY_V2_REPLAY_DUPLICATE_V2_MEMBERSHIP');
  if (!matches.length) return null;
  assertSafety(measurement?.dynamic5mV2?.safety, 'MEASUREMENT_V2');
  return Object.freeze({
    variant: 'DYNAMIC5M_V2',
    selectorCandidateId: String(measurement?.dynamic5mV2?.candidateId ?? 'INTRADAY_DYNAMIC_5M_UNIVERSE_V2'),
    v2Score: finite(matches[0].v2Score) ? Number(matches[0].v2Score) : null,
  });
}

export function auditEntryV2HistoricalReplayInputs({
  marketSnapshots = [],
  storedMeasurements = [],
  barArchives = [],
} = {}) {
  if (!Array.isArray(marketSnapshots) || !marketSnapshots.length) throw new Error('ENTRY_V2_REPLAY_MARKET_SNAPSHOTS_REQUIRED');
  assertSafety(ENTRY_V2_HISTORICAL_REPLAY_SAFETY, 'RESEARCH_POLICY');
  const measurements = measurementIndex(storedMeasurements);
  const archives = archiveIndex(barArchives);
  const seenObservedAt = new Set();
  const seenBuckets = new Set();
  const blockedPoints = [];
  const readyPoints = [];
  const allPoints = [];
  const barCache = new Map();
  let exactSelectorParityCount = 0;
  let selectedMembershipCount = 0;

  const normalizedSnapshots = marketSnapshots.map(normalizeSnapshot)
    .sort((a, b) => a.observedAt.localeCompare(b.observedAt));
  for (const source of normalizedSnapshots) {
    if (seenObservedAt.has(source.observedAt)) throw new Error('ENTRY_V2_REPLAY_DUPLICATE_RAW_POINT');
    seenObservedAt.add(source.observedAt);
    const bucketKey = `${source.sessionDate}|${iso(source.snapshot.bucket, 'BUCKET')}`;
    if (seenBuckets.has(bucketKey)) throw new Error('ENTRY_V2_REPLAY_DUPLICATE_RAW_BUCKET');
    seenBuckets.add(bucketKey);
    const timeline = buildIntradayDynamicUniverseTimeline({
      snapshots: [{ asOf: source.observedAt, entries: source.entries }],
    });
    const replaySelected = normalizeSelected(timeline.points[0]?.rawUniverse ?? []);
    if (!replaySelected.length) throw new Error('ENTRY_V2_REPLAY_CURRENT_SELECTOR_EMPTY');
    selectedMembershipCount += replaySelected.length;

    const measurement = measurements.get(source.observedAt) ?? null;
    let exactSelectorParity = null;
    if (measurement) {
      if (Number(measurement.inputSymbols) !== source.entries.length) {
        throw new Error('ENTRY_V2_REPLAY_MEASUREMENT_INPUT_COUNT_MISMATCH');
      }
      exactSelectorParity = JSON.stringify(replaySelected) === JSON.stringify(normalizeSelected(measurement.selected ?? []));
      if (!exactSelectorParity) throw new Error('ENTRY_V2_REPLAY_CURRENT_SELECTOR_PARITY_MISMATCH');
      exactSelectorParityCount += 1;
    }

    const archive = archives.get(source.sessionDate);
    let reason = null;
    let missingBarSymbolCount = 0;
    let insufficientPrefixSymbolCount = 0;
    const prefixes = {};
    const fullBarsBySymbol = {};
    const requiredSymbols = replaySelected.map(row => row.symbol).sort();
    const availableSymbols = [];
    const prefixReadySymbols = [];
    const symbolCoverage = [];
    const expectedClosedBars = expectedClosedBarTimestamps(source.sessionDate, source.observedAt);
    if (!archive || !archive.sessionBarsBySymbol || !Object.keys(archive.sessionBarsBySymbol).length) {
      reason = 'MISSING_SESSION_BAR_ARCHIVE';
      missingBarSymbolCount = replaySelected.length;
      for (const symbol of requiredSymbols) {
        symbolCoverage.push(Object.freeze({
          symbol,
          requiredPrefixBarCount: ENTRY_V2_HISTORICAL_REPLAY_POLICY.minimumClosedPrefixBars,
          nominalClosedIntervalCount: expectedClosedBars.length,
          availablePrefixBarCount: 0,
          missingBarIntervals: collapseMissingIntervals(expectedClosedBars),
          barArchiveAvailable: false,
          minimumPrefixSatisfied: false,
        }));
      }
    } else {
      for (const selected of replaySelected) {
        const cacheKey = `${source.sessionDate}|${selected.symbol}`;
        if (!barCache.has(cacheKey)) {
          barCache.set(cacheKey, normalizeBars(archive.sessionBarsBySymbol[selected.symbol], source.sessionDate));
        }
        const fullBars = barCache.get(cacheKey);
        if (!fullBars) {
          missingBarSymbolCount += 1;
          symbolCoverage.push(Object.freeze({
            symbol: selected.symbol,
            requiredPrefixBarCount: ENTRY_V2_HISTORICAL_REPLAY_POLICY.minimumClosedPrefixBars,
            nominalClosedIntervalCount: expectedClosedBars.length,
            availablePrefixBarCount: 0,
            missingBarIntervals: collapseMissingIntervals(expectedClosedBars),
            barArchiveAvailable: false,
            minimumPrefixSatisfied: false,
          }));
          continue;
        }
        availableSymbols.push(selected.symbol);
        const prefix = fullBars.filter(bar => Date.parse(bar.timestamp) + 5 * 60_000 <= Date.parse(source.observedAt));
        const availableTimestamps = new Set(prefix.map(bar => bar.timestamp));
        const missingTimestamps = expectedClosedBars.filter(timestamp => !availableTimestamps.has(timestamp));
        const minimumPrefixSatisfied = prefix.length >= ENTRY_V2_HISTORICAL_REPLAY_POLICY.minimumClosedPrefixBars;
        symbolCoverage.push(Object.freeze({
          symbol: selected.symbol,
          requiredPrefixBarCount: ENTRY_V2_HISTORICAL_REPLAY_POLICY.minimumClosedPrefixBars,
          nominalClosedIntervalCount: expectedClosedBars.length,
          availablePrefixBarCount: prefix.length,
          missingBarIntervals: collapseMissingIntervals(missingTimestamps),
          barArchiveAvailable: true,
          minimumPrefixSatisfied,
        }));
        if (!minimumPrefixSatisfied) {
          insufficientPrefixSymbolCount += 1;
          continue;
        }
        prefixReadySymbols.push(selected.symbol);
        fullBarsBySymbol[selected.symbol] = fullBars;
        prefixes[selected.symbol] = Object.freeze(prefix);
      }
      if (missingBarSymbolCount) reason = 'INCOMPLETE_CURRENT_SELECTOR_BAR_COVERAGE';
      else if (insufficientPrefixSymbolCount) reason = 'INSUFFICIENT_CLOSED_PREFIX_COVERAGE';
    }

    const point = Object.freeze({
      sourceClass: archive?.sourceClass ?? ENTRY_V2_SOURCE_CLASS.historicalReplay,
      aggregateSourceClass: ENTRY_V2_SOURCE_CLASS.historicalReplay,
      datasetRole: 'DEVELOPMENT_ONLY',
      prospective: false,
      formalOos: false,
      observedAt: source.observedAt,
      sessionDate: source.sessionDate,
      rawSnapshotSha256: source.snapshotSha256,
      rawSymbolCount: source.entries.length,
      currentSelectorCandidateId: PHASE57_INTRADAY_UNIVERSE_POLICY.candidateId,
      selectedCount: replaySelected.length,
      selected: Object.freeze(replaySelected.map(row => Object.freeze(row))),
      selectionSha256: sha256(JSON.stringify(replaySelected)),
      barArchiveAvailable: Boolean(archive),
      barArchiveSha256: archive?.sessionBarsSha256 ?? null,
      sourceLineage: archive?.sourceLineage ?? null,
      storedMeasurementAvailable: Boolean(measurement),
      exactSelectorParity,
      measurement,
      prefixes: Object.freeze(prefixes),
      fullBarsBySymbol: Object.freeze(fullBarsBySymbol),
      requiredSymbols: Object.freeze(requiredSymbols),
      availableSymbols: Object.freeze(availableSymbols.sort()),
      missingSymbols: Object.freeze(requiredSymbols.filter(symbol => !availableSymbols.includes(symbol))),
      prefixReadySymbols: Object.freeze(prefixReadySymbols.sort()),
      symbolCoverage: Object.freeze(symbolCoverage.sort((a, b) => a.symbol.localeCompare(b.symbol))),
      missingBarSymbolCount,
      insufficientPrefixSymbolCount,
      status: reason ? 'ENTRY_V2_HISTORICAL_REPLAY_POINT_BLOCKED' : 'ENTRY_V2_HISTORICAL_REPLAY_POINT_INPUT_READY',
      reason,
    });
    allPoints.push(point);
    if (reason) blockedPoints.push(point);
    else readyPoints.push(point);
  }

  return Object.freeze({
    policy: ENTRY_V2_HISTORICAL_REPLAY_POLICY,
    safety: ENTRY_V2_HISTORICAL_REPLAY_SAFETY,
    sourceClass: ENTRY_V2_SOURCE_CLASS.historicalReplay,
    pointCount: allPoints.length,
    readyPointCount: readyPoints.length,
    blockedPointCount: blockedPoints.length,
    selectedMembershipCount,
    storedMeasurementCount: measurements.size,
    exactSelectorParityCount,
    sourceClassBreakdown: Object.freeze(allPoints.reduce((counts, point) => {
      counts[point.sourceClass] = (counts[point.sourceClass] ?? 0) + 1;
      return counts;
    }, {})),
    blockedReasonDistribution: Object.freeze(reasonCounts(blockedPoints)),
    pitViolationCount: 0,
    points: Object.freeze(allPoints),
    readyPoints: Object.freeze(readyPoints),
    blockedPoints: Object.freeze(blockedPoints),
    classification: Object.freeze({
      historicalRetrospectiveReplay: true,
      developmentOnly: true,
      prospective: false,
      formalOos: false,
      promotionEligible: false,
    }),
    status: 'ENTRY_V2_HISTORICAL_REPLAY_INPUT_AUDIT_READY',
  });
}

function buildFrozenP21Scorer(historySessions, reusablePriorModelCache = null) {
  if (reusablePriorModelCache !== null && !(reusablePriorModelCache instanceof Map)) {
    throw new TypeError('ENTRY_V2_REPLAY_REUSABLE_PRIOR_MODEL_CACHE_MUST_BE_MAP');
  }
  const actualHistorySymbols = [...new Set((historySessions ?? [])
    .map(session => String(session?.symbol ?? '').trim().toUpperCase()).filter(Boolean))].sort();
  const expectedHistorySymbols = [...PHASE58_P13_FROZEN_POLICY.historicalUniverse].sort();
  if (JSON.stringify(actualHistorySymbols) !== JSON.stringify(expectedHistorySymbols)) {
    throw new Error('ENTRY_V2_REPLAY_FROZEN_HISTORY_UNIVERSE_MISMATCH');
  }
  const cached = buildProspectiveP21HistoricalRows({
    sessions: historySessions,
    horizons: PHASE58_P13_FROZEN_POLICY.horizonsBars,
  });
  if (cached.complete !== true) throw new Error(`ENTRY_V2_REPLAY_FROZEN_HISTORY_${cached.status}`);
  const priorOnlyCache = new Map();
  const historicalOutcomeTimes = Object.values(cached.historicalHorizonRowsByBars ?? {})
    .flat().map(row => Date.parse(row?.outcomeAt ?? '')).filter(Number.isFinite);
  const maxFrozenHistoricalOutcomeMs = historicalOutcomeTimes.length ? Math.max(...historicalOutcomeTimes) : null;
  const frozenHistoryFingerprint = sha256(JSON.stringify(historySessions));
  let byteEquivalentReusableBundle = reusablePriorModelCache?.get(frozenHistoryFingerprint) ?? null;
  return currentPrefix => {
    const feed = buildProspectiveP21FeatureFeed({
      symbol: currentPrefix.symbol,
      sessionDate: currentPrefix.sessionDate,
      bars5m: currentPrefix.bars5m,
      horizons: PHASE58_P13_FROZEN_POLICY.horizonsBars,
      latestBarClosed: true,
    });
    if (!feed.complete) return { complete: false, status: 'BLOCKED_P21_CURRENT_FEATURE_FEED' };
    const currentFeatureCutoffs = [...new Set(Object.values(feed.currentRowsByHorizon ?? {})
      .flat().map(row => String(row?.featureCutoff ?? '')).filter(Boolean))];
    const currentAsOf = currentFeatureCutoffs.length === 1 ? currentFeatureCutoffs[0] : null;
    if (byteEquivalentReusableBundle && currentAsOf
      && maxFrozenHistoricalOutcomeMs !== null && maxFrozenHistoricalOutcomeMs <= Date.parse(currentAsOf)
      && !priorOnlyCache.has(currentAsOf)) {
      priorOnlyCache.set(currentAsOf, Object.freeze({
        ...byteEquivalentReusableBundle,
        asOf: currentAsOf,
        artifactSha256: frozenArtifactHashForAsOf({
          picked: byteEquivalentReusableBundle.picked,
          trainRows: byteEquivalentReusableBundle.trainRows,
          asOf: currentAsOf,
        }),
      }));
    }
    const base = buildProspectiveP21FrozenDecision({
      historicalHorizonRowsByBars: cached.historicalHorizonRowsByBars,
      currentRowsByHorizon: feed.currentRowsByHorizon,
      options: PHASE58_P13_FROZEN_POLICY.selectionOptions,
      priorOnlyCache,
    });
    if (!byteEquivalentReusableBundle && currentAsOf
      && maxFrozenHistoricalOutcomeMs !== null && maxFrozenHistoricalOutcomeMs <= Date.parse(currentAsOf)) {
      const fitted = priorOnlyCache.get(currentAsOf);
      if (fitted?.status === 'PRIOR_ONLY_MODEL_READY' && typeof fitted.predictor === 'function') {
        byteEquivalentReusableBundle = fitted;
        reusablePriorModelCache?.set(frozenHistoryFingerprint, fitted);
      }
    }
    if (!base.complete) return { complete: false, status: 'BLOCKED_P21_PROSPECTIVE_BASE' };
    const built = buildFrozenPhase57SnapshotFromRuntimeDecision({
      decision: base.decision,
      modelId: base.modelId,
      artifactSha256: base.artifactSha256,
    });
    if (!built.complete) return { complete: false, status: 'BLOCKED_PHASE57_RUNTIME_ADAPTER' };
    return {
      complete: true,
      status: 'PHASE57_FROZEN_P21_SNAPSHOT_READY',
      decision: base.decision,
      snapshot: built.snapshot,
      modelId: base.modelId,
      artifactSha256: base.artifactSha256,
    };
  };
}

export function buildEntryV2HistoricalRetrospectiveReplay({
  marketSnapshots = [],
  storedMeasurements = [],
  barArchives = [],
  frozenHistorySessions = [],
  horizonsBars = [1, 2, 3, 6, 12],
  roundTripCostBps = 0,
  reusablePriorModelCache = null,
} = {}) {
  const audit = auditEntryV2HistoricalReplayInputs({ marketSnapshots, storedMeasurements, barArchives });
  const scorePrefix = buildFrozenP21Scorer(frozenHistorySessions, reusablePriorModelCache);
  const candidates = [];
  const scorerBlockedPoints = [];
  const seen = new Set();

  for (const point of audit.readyPoints) {
    const scored = [];
    let reason = null;
    for (const row of point.selected) {
      const prefix = point.prefixes[row.symbol];
      let result;
      try {
        result = scorePrefix({
          symbol: row.symbol,
          sessionDate: point.sessionDate,
          bars5m: prefix,
        });
      } catch (error) {
        reason = `SCORER_EXCEPTION:${String(error?.message ?? error)}`;
        break;
      }
      if (!result?.complete || !result?.decision) {
        reason = String(result?.status ?? 'SCORER_NOT_READY');
        break;
      }
      const decision = result.decision;
      const context = decision.context ?? {};
      if (decision.futureOutcomeUsed !== false || decision.frozenByPhase57 !== true || decision.pointInTimeOnly !== true) {
        reason = 'FROZEN_ENTRY_ATTESTATION_FAILED';
        break;
      }
      scored.push({ row, prefix, result, decision, context });
    }
    if (reason) {
      scorerBlockedPoints.push(Object.freeze({
        observedAt: point.observedAt,
        sessionDate: point.sessionDate,
        reason,
        status: 'ENTRY_V2_HISTORICAL_REPLAY_POINT_BLOCKED_BY_FROZEN_ENTRY',
      }));
      continue;
    }

    for (const scoredRow of scored) {
      const directionSign = Number(scoredRow.decision.direction);
      if (scoredRow.context.signalEligible !== true || ![-1, 1].includes(directionSign)) continue;
      const candidateId = `${point.sessionDate}|${point.observedAt}|${scoredRow.row.symbol}`;
      if (seen.has(candidateId)) throw new Error('ENTRY_V2_REPLAY_DUPLICATE_FROZEN_CANDIDATE');
      seen.add(candidateId);
      const featureCutoff = iso(scoredRow.decision.asOf ?? scoredRow.prefix.at(-1)?.timestamp, 'FEATURE_CUTOFF');
      if (featureCutoff !== scoredRow.prefix.at(-1).timestamp || Date.parse(featureCutoff) > Date.parse(point.observedAt)) {
        throw new Error('ENTRY_V2_REPLAY_FEATURE_CUTOFF_LINEAGE_MISMATCH');
      }
      const direction = directionSign === 1 ? 'LONG' : 'SHORT';
      const fullBars = point.fullBarsBySymbol[scoredRow.row.symbol];
      // Provider timestamps are five-minute interval starts. At a decision made at t,
      // the bar starting at t is the first label-only future bar; the feature prefix
      // remains limited to bars whose start + 5 minutes <= t.
      const futureBars = fullBars.filter(bar => Date.parse(bar.timestamp) >= Date.parse(point.observedAt));
      const labels = buildEntryQualityV2PathLabels({
        entryTimestamp: point.observedAt,
        entryPrice: scoredRow.row.currentPrice,
        futureBars,
        horizonsBars,
        roundTripCostBps,
      });
      const selectorMemberships = [Object.freeze({
        variant: 'DYNAMIC5M_V1',
        selectorCandidateId: ENTRY_V2_HISTORICAL_REPLAY_POLICY.currentSelectorCandidateId,
      })];
      const v2Membership = selectedV2Membership(point.measurement, scoredRow.row.symbol);
      if (v2Membership) selectorMemberships.push(v2Membership);
      const selectionLineage = Object.freeze({
        variant: 'DYNAMIC5M_V1',
        variantId: ENTRY_V2_HISTORICAL_REPLAY_POLICY.currentSelectorCandidateId,
        selectionTimestamp: point.observedAt,
        sourceAsOf: scoredRow.row.sourceScannedAt,
        selectorCandidateId: ENTRY_V2_HISTORICAL_REPLAY_POLICY.currentSelectorCandidateId,
        opportunityScore: scoredRow.row.opportunityScore,
        v2Score: v2Membership?.v2Score ?? null,
      });
      candidates.push(Object.freeze({
        sourceClass: point.sourceClass,
        aggregateSourceClass: ENTRY_V2_SOURCE_CLASS.historicalReplay,
        datasetRole: 'DEVELOPMENT_ONLY',
        prospective: false,
        formalOos: false,
        candidateId,
        candidateEventId: candidateId,
        sessionDate: point.sessionDate,
        symbol: scoredRow.row.symbol,
        sector: scoredRow.row.sector,
        selectionTimestamp: point.observedAt,
        entryTimestamp: point.observedAt,
        featureCutoff,
        entryPrice: scoredRow.row.currentPrice,
        direction,
        signalDirection: directionSign,
        confidence: finite(scoredRow.decision.confidence) ? Number(scoredRow.decision.confidence) : null,
        probability: finite(scoredRow.context.probability) ? Number(scoredRow.context.probability) : null,
        selectedHorizonBars: finite(scoredRow.context.selectedHorizonBars) ? Number(scoredRow.context.selectedHorizonBars) : null,
        selectedFeatureFamily: scoredRow.context.selectedFeatureFamily ?? scoredRow.decision.setup ?? null,
        selectedModelType: scoredRow.context.selectedModelType ?? null,
        selectedConfigId: scoredRow.context.selectedConfigId ?? null,
        selectedThreshold: finite(scoredRow.context.selectedThreshold) ? Number(scoredRow.context.selectedThreshold) : null,
        opportunityScore: scoredRow.row.opportunityScore,
        modelId: scoredRow.result.modelId,
        artifactSha256: scoredRow.result.artifactSha256,
        selectorMemberships: Object.freeze(selectorMemberships),
        contextBars: scoredRow.prefix,
        contextBarCount: scoredRow.prefix.length,
        contextBarsSha256: sha256(JSON.stringify(scoredRow.prefix)),
        availableFutureBars: labels.availableFutureBars,
        qualityLabels: labels.labels,
        labelCompleteness: Object.freeze(Object.fromEntries(labels.labels.map(label => [label.horizonBars, label.complete]))),
        featureFrozenBeforeOfflineLabels: true,
        frozenBeforeOutcome: true,
        currentOutcomeUsed: false,
        selectionLineage,
        baselineEntry: Object.freeze({
          candidateId,
          entryAccepted: true,
          symbol: scoredRow.row.symbol,
          sessionDate: point.sessionDate,
          entryTimestamp: point.observedAt,
          entryPrice: scoredRow.row.currentPrice,
          direction,
          signalDirection: directionSign,
          contextBars: scoredRow.prefix,
          selectionLineage,
          frozenBeforeOutcome: true,
          currentOutcomeUsed: false,
        }),
        rawSnapshotSha256: point.rawSnapshotSha256,
        selectionSha256: point.selectionSha256,
        barArchiveSha256: point.barArchiveSha256,
        sourceLineage: point.sourceLineage,
        pointInTimeValid: true,
        pitViolationCount: 0,
      }));
    }
  }

  candidates.sort((a, b) => a.entryTimestamp.localeCompare(b.entryTimestamp) || a.symbol.localeCompare(b.symbol));
  const countsByDirection = { LONG: 0, SHORT: 0 };
  const symbolSet = new Set();
  const sessionSet = new Set();
  const sourceClassBreakdown = {};
  const labelCompletenessByHorizon = Object.fromEntries([...new Set(horizonsBars.map(Number))]
    .sort((a, b) => a - b).map(horizon => [horizon, { complete: 0, incomplete: 0, total: candidates.length }]));
  for (const candidate of candidates) {
    countsByDirection[candidate.direction] += 1;
    symbolSet.add(candidate.symbol);
    sessionSet.add(candidate.sessionDate);
    sourceClassBreakdown[candidate.sourceClass] = (sourceClassBreakdown[candidate.sourceClass] ?? 0) + 1;
    for (const [horizon, stats] of Object.entries(labelCompletenessByHorizon)) {
      if (candidate.labelCompleteness[horizon] === true) stats.complete += 1;
      else stats.incomplete += 1;
    }
  }
  const allBlocked = [...audit.blockedPoints, ...scorerBlockedPoints];
  return Object.freeze({
    policy: ENTRY_V2_HISTORICAL_REPLAY_POLICY,
    safety: ENTRY_V2_HISTORICAL_REPLAY_SAFETY,
    sourceClass: ENTRY_V2_SOURCE_CLASS.historicalReplay,
    audit,
    candidateCount: candidates.length,
    uniqueCandidateEventCount: seen.size,
    duplicateCandidateCount: 0,
    uniqueSymbolCount: symbolSet.size,
    sessionCount: sessionSet.size,
    countsByDirection: Object.freeze(countsByDirection),
    countsBySourceClass: Object.freeze(sourceClassBreakdown),
    labelCompletenessByHorizon: Object.freeze(Object.fromEntries(Object.entries(labelCompletenessByHorizon)
      .map(([horizon, stats]) => [horizon, Object.freeze(stats)]))),
    candidates: Object.freeze(candidates),
    scorerBlockedPointCount: scorerBlockedPoints.length,
    scorerBlockedPoints: Object.freeze(scorerBlockedPoints),
    totalBlockedPointCount: allBlocked.length,
    blockedReasonDistribution: Object.freeze(reasonCounts(allBlocked)),
    pitViolationCount: 0,
    classification: Object.freeze({
      historicalRetrospectiveReplay: true,
      developmentOnly: true,
      nonProspective: true,
      prospective: false,
      formalOos: false,
      promotionEligible: false,
    }),
    status: 'ENTRY_V2_HISTORICAL_RETROSPECTIVE_REPLAY_READY_NON_PROSPECTIVE',
  });
}

export function separateEntryV2ActualAndHistoricalSources({ actualInventory, historicalReplay } = {}) {
  if (actualInventory?.sourceClass !== ENTRY_V2_SOURCE_CLASS.actualDurable) {
    throw new Error('ENTRY_V2_SOURCE_SEPARATION_ACTUAL_DURABLE_REQUIRED');
  }
  if (historicalReplay?.sourceClass !== ENTRY_V2_SOURCE_CLASS.historicalReplay
    || historicalReplay?.classification?.prospective !== false
    || historicalReplay?.classification?.developmentOnly !== true) {
    throw new Error('ENTRY_V2_SOURCE_SEPARATION_HISTORICAL_CLASS_INVALID');
  }
  const actualEventIds = new Set((actualInventory.rows ?? []).map(row => row.candidateEventId));
  const overlap = [];
  const independentHistorical = [];
  for (const candidate of historicalReplay.candidates ?? []) {
    if (!DETAILED_HISTORICAL_SOURCE_CLASSES.includes(candidate?.sourceClass)) {
      throw new Error('ENTRY_V2_SOURCE_SEPARATION_DETAILED_HISTORICAL_CLASS_REQUIRED');
    }
    if (actualEventIds.has(candidate.candidateEventId)) overlap.push(candidate);
    else independentHistorical.push(candidate);
  }
  return Object.freeze({
    actualDurableCandidates: Object.freeze([...(actualInventory.rows ?? [])]),
    historicalReplayCandidates: Object.freeze([...(historicalReplay.candidates ?? [])]),
    independentHistoricalDevelopmentCandidates: Object.freeze(independentHistorical),
    actualDurableCandidateCount: actualEventIds.size,
    historicalReplayCandidateCount: (historicalReplay.candidates ?? []).length,
    overlapExcludedFromHistoricalDevelopmentCount: overlap.length,
    independentHistoricalDevelopmentCandidateCount: independentHistorical.length,
    sourceClassesKeptSeparate: true,
    historicalIncludedInProspectiveDenominator: false,
    promotionEligible: false,
    status: 'ENTRY_V2_ACTUAL_AND_HISTORICAL_SOURCES_STRICTLY_SEPARATED',
  });
}

export default {
  ENTRY_V2_HISTORICAL_REPLAY_POLICY,
  ENTRY_V2_HISTORICAL_REPLAY_SAFETY,
  auditEntryV2HistoricalReplayInputs,
  buildEntryV2HistoricalRetrospectiveReplay,
  separateEntryV2ActualAndHistoricalSources,
};
