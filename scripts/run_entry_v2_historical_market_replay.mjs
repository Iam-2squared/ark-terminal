import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { gunzipSync } from 'node:zlib';
import {
  ENTRY_V2_HISTORICAL_MARKET_POLICY,
  ENTRY_V2_HISTORICAL_MARKET_SAFETY,
  buildEntryV2HistoricalMarketSnapshots,
  buildEntryV2HistoricalMarketContext,
  buildEntryV2HistoricalSelectorMeasurements,
  buildEntryV2HistoricalSessionBarArchive,
  fingerprintEntryV2SelectionScope,
} from '../predict/daytrade/phase57-entry-quality-v2-historical-market-data.js';
import { buildEntryV2HistoricalRetrospectiveReplay } from '../predict/daytrade/phase57-entry-quality-v2-historical-replay.js';
import {
  ENTRY_V2_HISTORICAL_DAILY_SAFETY,
  buildEntryV2HistoricalDailyContext,
} from '../predict/daytrade/phase57-entry-quality-v2-historical-daily-data.js';

const arg = (name, fallback = null) => {
  const index = process.argv.indexOf(name);
  return index >= 0 && index + 1 < process.argv.length ? process.argv[index + 1] : fallback;
};
const archiveDir = path.resolve(arg('--archive-dir', 'tmp/entry-v2-historical-market'));
const historyPackPath = path.resolve(arg('--history-pack', 'tmp/entry-v2-frozen/p25-history.json'));
const outputPath = path.resolve(arg('--output', 'tmp/entry-v2-market-first-development-dataset.json'));
const integrityOutputPath = path.resolve(arg('--integrity-output', 'tmp/entry-v2-market-first-integrity.json'));
const selectionSymbolsOutputPath = path.resolve(arg('--selection-symbols-output', 'tmp/entry-v2-market-first-selection-symbols.json'));
const goldenSubstratePath = path.resolve(arg('--golden-substrate', 'predict/daytrade/phase57-entry-quality-v2-development-candidate-substrate-2026-09-05.json'));
const dailyArchiveDirArgument = arg('--daily-archive-dir');
const dailyArchiveDir = dailyArchiveDirArgument ? path.resolve(dailyArchiveDirArgument) : null;
const onlySession = arg('--session');
if (onlySession && !/^\d{4}-\d{2}-\d{2}$/.test(onlySession)) {
  throw new Error('usage: [--archive-dir <dir>] [--history-pack <json>] [--output <json>] '
    + '[--integrity-output <json>] [--golden-substrate <json>] [--session YYYY-MM-DD]');
}

const FALSE_KEYS = [
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
for (const key of FALSE_KEYS) {
  if (ENTRY_V2_HISTORICAL_MARKET_SAFETY[key] !== false) throw new Error(`ENTRY_V2_MARKET_REPLAY_UNSAFE_${key}`);
}

const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
const readJson = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const writeAtomicJson = (file, value) => {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temporary = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`);
  fs.renameSync(temporary, file);
};
const sumObject = (target, source) => {
  for (const [key, value] of Object.entries(source ?? {})) target[key] = (target[key] ?? 0) + Number(value ?? 0);
};
const increment = (object, key) => { object[key] = (object[key] ?? 0) + 1; };
const numericSummary = values => {
  const sorted = values.map(Number).filter(Number.isFinite).sort((left, right) => left - right);
  if (!sorted.length) return { count: 0, min: null, median: null, max: null, mean: null };
  const middle = Math.floor(sorted.length / 2);
  const median = sorted.length % 2 === 0
    ? (sorted[middle - 1] + sorted[middle]) / 2
    : sorted[middle];
  return {
    count: sorted.length,
    min: sorted[0],
    median,
    max: sorted.at(-1),
    mean: sorted.reduce((sum, value) => sum + value, 0) / sorted.length,
  };
};
const stripBar = bar => ({
  timestamp: bar.timestamp,
  open: Number(bar.open),
  high: Number(bar.high),
  low: Number(bar.low),
  close: Number(bar.close),
  volume: Number(bar.volume),
});
const fiveMinuteBucket = value => new Date(Math.floor(Date.parse(value) / 300_000) * 300_000).toISOString();
const bucketEventKey = row => `${row.sessionDate}|${fiveMinuteBucket(row.entryTimestamp ?? row.selectionTimestamp)}|${String(row.symbol).toUpperCase()}`;

const manifestPath = path.join(archiveDir, 'manifest.json');
const manifest = readJson(manifestPath);
const manifestCore = structuredClone(manifest);
delete manifestCore.manifestContentSha256;
if (sha256(Buffer.from(JSON.stringify(manifestCore))) !== manifest.manifestContentSha256
  || manifest.sourceClass !== 'HISTORICAL_RECONSTRUCTION_LATER_FETCHED'
  || manifest.classification?.prospective !== false
  || manifest.classification?.formalOos !== false
  || manifest.dataSemantics?.selectedSymbolsDeterminedAcquisition !== false
  || manifest.frozenBoundaries?.currentDynamic5mSelectorFixed !== true
  || manifest.frozenBoundaries?.frozenP21EntryFixed !== true
  || manifest.frozenBoundaries?.replayStartAfterFrozenHistory !== true) {
  throw new Error('ENTRY_V2_MARKET_REPLAY_MANIFEST_LINEAGE_OR_BOUNDARY_INVALID');
}
for (const key of FALSE_KEYS) {
  if (manifest.safety?.[key] !== false) throw new Error(`ENTRY_V2_MARKET_REPLAY_MANIFEST_UNSAFE_${key}`);
}
const historyPack = readJson(historyPackPath);
const frozenHistorySessions = historyPack.sessions ?? historyPack.historicalSessions;
if (!Array.isArray(frozenHistorySessions) || !frozenHistorySessions.length) {
  throw new Error('ENTRY_V2_MARKET_REPLAY_FROZEN_HISTORY_SESSIONS_REQUIRED');
}
const frozenHistoryDates = frozenHistorySessions.map(row => String(row?.sessionDate ?? '')).filter(Boolean).sort();
if (frozenHistoryDates.at(-1) !== ENTRY_V2_HISTORICAL_MARKET_POLICY.frozenP21HistoryEndSessionDate) {
  throw new Error('ENTRY_V2_MARKET_REPLAY_FROZEN_HISTORY_END_MISMATCH');
}
const earliestLeakageFreeReplaySessionDate = new Date(`${frozenHistoryDates.at(-1)}T00:00:00.000Z`);
earliestLeakageFreeReplaySessionDate.setUTCDate(earliestLeakageFreeReplaySessionDate.getUTCDate() + 1);
const historyPackSha256 = sha256(fs.readFileSync(historyPackPath));

let dailyManifest = null;
let dailyManifestPath = null;
const dailyReceiptBySymbol = new Map();
const dailyRecordCache = new Map();
if (dailyArchiveDir) {
  dailyManifestPath = path.join(dailyArchiveDir, 'manifest.json');
  dailyManifest = readJson(dailyManifestPath);
  const dailyCore = structuredClone(dailyManifest);
  delete dailyCore.manifestContentSha256;
  if (sha256(Buffer.from(JSON.stringify(dailyCore))) !== dailyManifest.manifestContentSha256
    || dailyManifest.sourceClass !== 'HISTORICAL_RECONSTRUCTION_LATER_FETCHED'
    || dailyManifest.classification?.prospective !== false
    || dailyManifest.classification?.formalOos !== false
    || dailyManifest.selectionScope?.marketArchiveManifestContentSha256 !== manifest.manifestContentSha256
    || dailyManifest.dataSemantics?.sameSessionFinalDailyForbidden !== true
    || dailyManifest.dataSemantics?.adjustedCloseUsedAsFeature !== false
    || dailyManifest.dataSemantics?.missingDailyBarsInterpolatedOrFabricated !== false) {
    throw new Error('ENTRY_V2_MARKET_REPLAY_DAILY_MANIFEST_LINEAGE_OR_BOUNDARY_INVALID');
  }
  for (const key of FALSE_KEYS) {
    if (dailyManifest.safety?.[key] !== false || ENTRY_V2_HISTORICAL_DAILY_SAFETY[key] !== false) {
      throw new Error(`ENTRY_V2_MARKET_REPLAY_DAILY_UNSAFE_${key}`);
    }
  }
  for (const receipt of dailyManifest.receipts ?? []) dailyReceiptBySymbol.set(receipt.symbol, receipt);
}

function loadDailyRecords(symbol) {
  if (!dailyManifest) return null;
  if (dailyRecordCache.has(symbol)) return dailyRecordCache.get(symbol);
  const receipt = dailyReceiptBySymbol.get(symbol);
  if (!receipt) {
    dailyRecordCache.set(symbol, null);
    return null;
  }
  const file = path.join(dailyArchiveDir, receipt.normalizedFile);
  const compressed = fs.readFileSync(file);
  const uncompressed = gunzipSync(compressed);
  if (sha256(compressed) !== receipt.normalizedCompressedFileSha256
    || sha256(uncompressed) !== receipt.normalizedPayloadSha256) {
    throw new Error(`ENTRY_V2_MARKET_REPLAY_DAILY_SYMBOL_HASH_MISMATCH:${symbol}`);
  }
  const normalized = JSON.parse(uncompressed.toString('utf8'));
  if (normalized?.series?.symbol !== symbol || !Array.isArray(normalized?.series?.records)) {
    throw new Error(`ENTRY_V2_MARKET_REPLAY_DAILY_SYMBOL_PAYLOAD_INVALID:${symbol}`);
  }
  dailyRecordCache.set(symbol, normalized.series.records);
  return normalized.series.records;
}

const golden = fs.existsSync(goldenSubstratePath) ? readJson(goldenSubstratePath) : { rows: [] };
const goldenRows = Array.isArray(golden?.rows) ? golden.rows : [];
const goldenBySession = new Map();
for (const row of goldenRows) {
  if (!goldenBySession.has(row.sessionDate)) goldenBySession.set(row.sessionDate, []);
  goldenBySession.get(row.sessionDate).push(row);
}
const goldenBarAudits = [];

const requestedSessionShards = (manifest.sessionShards ?? [])
  .filter(row => !onlySession || row.sessionDate === onlySession)
  .sort((left, right) => left.sessionDate.localeCompare(right.sessionDate));
if (!requestedSessionShards.length) throw new Error('ENTRY_V2_MARKET_REPLAY_NO_SESSION_SHARDS');

const candidates = [];
const selectionEvents = [];
const marketContexts = [];
const candidateIds = new Set();
const selectionEventIds = new Set();
const perSession = [];
const marketSnapshotBlockedReasons = {};
const replayBlockedReasons = {};
let totalMarketBars = 0;
let totalSnapshots = 0;
let totalSnapshotReady = 0;
let totalSnapshotBlocked = 0;
let internalSelectorParityCount = 0;
let pitViolationCount = 0;
const reusablePriorModelCache = new Map();

for (let sessionIndex = 0; sessionIndex < requestedSessionShards.length; sessionIndex += 1) {
  const shard = requestedSessionShards[sessionIndex];
  const shardPath = path.join(archiveDir, shard.file);
  const compressedBytes = fs.readFileSync(shardPath);
  const ndjsonBytes = gunzipSync(compressedBytes);
  if (sha256(compressedBytes) !== shard.compressedFileSha256
    || sha256(ndjsonBytes) !== shard.uncompressedNdjsonSha256) {
    throw new Error(`ENTRY_V2_MARKET_REPLAY_SESSION_SHARD_HASH_MISMATCH:${shard.sessionDate}`);
  }
  const sessionSeries = ndjsonBytes.toString('utf8').split(/\r?\n/).filter(Boolean).map(JSON.parse);
  if (sessionSeries.length !== shard.retainedSymbolCount
    || new Set(sessionSeries.map(row => row.symbol)).size !== sessionSeries.length) {
    throw new Error(`ENTRY_V2_MARKET_REPLAY_SESSION_SHARD_SYMBOL_COUNT_MISMATCH:${shard.sessionDate}`);
  }
  totalMarketBars += sessionSeries.reduce((sum, row) => sum + (row.bars?.length ?? 0), 0);
  console.log(JSON.stringify({ stage: 'SESSION_LOADED', sessionDate: shard.sessionDate, symbols: sessionSeries.length }));

  const snapshotAudit = buildEntryV2HistoricalMarketSnapshots({
    sessionDate: shard.sessionDate,
    sessionSeries,
    universeSymbolCount: manifest.universe.requestedSnapshotSymbolCount,
    sourceLineage: {
      sourceArtifact: shard.file,
      sourceArtifactSha256: shard.compressedFileSha256,
      sourceManifestSha256: manifest.manifestContentSha256,
      retrievedAt: manifest.createdAt,
      provider: manifest.provider,
      reconstructionFetchedAfterDecision: true,
      archivedPointInTimeCapture: false,
    },
  });
  totalSnapshots += snapshotAudit.pointCount;
  totalSnapshotReady += snapshotAudit.readyPointCount;
  totalSnapshotBlocked += snapshotAudit.blockedPointCount;
  sumObject(marketSnapshotBlockedReasons, snapshotAudit.blockedReasonDistribution);
  pitViolationCount += snapshotAudit.pitViolationCount;
  console.log(JSON.stringify({ stage: 'SNAPSHOTS_READY', sessionDate: shard.sessionDate, ready: snapshotAudit.readyPointCount, blocked: snapshotAudit.blockedPointCount }));

  const snapshotByObservedAt = new Map(snapshotAudit.readyPoints.map(snapshot => [snapshot.observedAt, snapshot]));
  for (const snapshot of snapshotAudit.readyPoints) {
    marketContexts.push(buildEntryV2HistoricalMarketContext({ snapshot }));
  }

  if (!snapshotAudit.readyPoints.length) {
    perSession.push({
      sessionDate: shard.sessionDate,
      marketSymbols: sessionSeries.length,
      marketBars: sessionSeries.reduce((sum, row) => sum + (row.bars?.length ?? 0), 0),
      snapshots: snapshotAudit.pointCount,
      readySnapshots: 0,
      blockedSnapshots: snapshotAudit.blockedPointCount,
      selectedEvents: 0,
      p21Candidates: 0,
      replayBlockedPoints: 0,
    });
    continue;
  }

  const selector = buildEntryV2HistoricalSelectorMeasurements({ snapshots: snapshotAudit.readyPoints });
  console.log(JSON.stringify({ stage: 'CURRENT_DYNAMIC5M_READY', sessionDate: shard.sessionDate, measurements: selector.measurementCount }));
  const requiredSymbols = [...new Set(selector.measurements.flatMap(measurement => measurement.selected.map(row => row.symbol)))].sort();
  const archive = buildEntryV2HistoricalSessionBarArchive({
    sessionDate: shard.sessionDate,
    sessionSeries,
    requiredSymbols,
    retrievedAt: manifest.createdAt,
    sourceArtifact: shard.file,
    sourceArtifactSha256: shard.compressedFileSha256,
    sourceManifestSha256: manifest.manifestContentSha256,
  });
  const replay = buildEntryV2HistoricalRetrospectiveReplay({
    marketSnapshots: snapshotAudit.readyPoints,
    storedMeasurements: selector.measurements,
    barArchives: [archive],
    frozenHistorySessions,
    reusablePriorModelCache,
  });
  console.log(JSON.stringify({ stage: 'FROZEN_P21_REPLAY_READY', sessionDate: shard.sessionDate, candidates: replay.candidateCount }));
  internalSelectorParityCount += replay.audit.exactSelectorParityCount;
  pitViolationCount += replay.pitViolationCount;
  sumObject(replayBlockedReasons, replay.blockedReasonDistribution);

  const candidatesByEvent = new Map();
  for (const candidate of replay.candidates) {
    if (candidateIds.has(candidate.candidateEventId)) throw new Error('ENTRY_V2_MARKET_REPLAY_DUPLICATE_CANDIDATE_EVENT');
    candidateIds.add(candidate.candidateEventId);
    const sourceSnapshot = snapshotByObservedAt.get(candidate.entryTimestamp);
    if (!sourceSnapshot) throw new Error('ENTRY_V2_MARKET_REPLAY_CANDIDATE_MARKET_CONTEXT_MISSING');
    let dailyContext = Object.freeze({
      status: 'ENTRY_V2_HISTORICAL_DAILY_ARCHIVE_NOT_CONNECTED',
      available: false,
      context: null,
      sourceClass: 'HISTORICAL_RECONSTRUCTION_LATER_FETCHED',
      prospective: false,
      formalOos: false,
    });
    if (dailyManifest) {
      const records = loadDailyRecords(candidate.symbol);
      if (!records) {
        dailyContext = Object.freeze({
          ...dailyContext,
          status: 'ENTRY_V2_HISTORICAL_DAILY_SYMBOL_ARCHIVE_MISSING',
        });
      } else {
        try {
          dailyContext = buildEntryV2HistoricalDailyContext({
            symbol: candidate.symbol,
            decisionTimestamp: candidate.entryTimestamp,
            records,
          });
        } catch (error) {
          dailyContext = Object.freeze({
            ...dailyContext,
            status: `ENTRY_V2_HISTORICAL_DAILY_CONTEXT_BLOCKED:${String(error?.message ?? error)}`,
          });
        }
      }
    }
    const enrichedCandidate = Object.freeze({
      ...candidate,
      marketContext: buildEntryV2HistoricalMarketContext({ snapshot: sourceSnapshot, sector: candidate.sector }),
      dailyContext,
    });
    candidatesByEvent.set(candidate.candidateEventId, enrichedCandidate);
    candidates.push(enrichedCandidate);
  }
  for (const measurement of selector.measurements) {
    const memberships = new Map();
    for (const row of measurement.selected) memberships.set(row.symbol, {
      symbol: row.symbol,
      sector: row.sector,
      entryReferencePrice: row.currentPrice,
      turnoverYen: row.turnoverYen,
      opportunityScore: row.opportunityScore,
      variants: ['DYNAMIC5M_V1'],
      v2Score: null,
    });
    for (const row of measurement.selectedV2) {
      const current = memberships.get(row.symbol) ?? {
        symbol: row.symbol,
        sector: row.sector,
        entryReferencePrice: row.currentPrice,
        turnoverYen: row.turnoverYen,
        opportunityScore: row.opportunityScore,
        variants: [],
        v2Score: null,
      };
      current.variants.push('DYNAMIC5M_V2');
      current.v2Score = row.v2Score;
      memberships.set(row.symbol, current);
    }
    for (const item of memberships.values()) {
      item.variants.sort();
      const selectionEventId = `${shard.sessionDate}|${measurement.observedAt}|${item.symbol}`;
      if (selectionEventIds.has(selectionEventId)) throw new Error('ENTRY_V2_MARKET_REPLAY_DUPLICATE_SELECTION_EVENT');
      selectionEventIds.add(selectionEventId);
      const p21Candidate = candidatesByEvent.get(selectionEventId) ?? null;
      selectionEvents.push({
        selectionEventId,
        sourceClass: 'HISTORICAL_RECONSTRUCTION_LATER_FETCHED',
        datasetRole: 'DEVELOPMENT_ONLY',
        prospective: false,
        formalOos: false,
        sessionDate: shard.sessionDate,
        decisionTimestamp: measurement.observedAt,
        symbol: item.symbol,
        sector: item.sector,
        entryReferencePrice: item.entryReferencePrice,
        turnoverYen: item.turnoverYen,
        opportunityScore: item.opportunityScore,
        selectorMemberships: item.variants,
        v2Score: item.v2Score,
        selectionEligible: true,
        oldP21SignalEligible: Boolean(p21Candidate),
        oldP21Direction: p21Candidate?.direction ?? null,
        oldP21CandidateEventId: p21Candidate?.candidateEventId ?? null,
        currentDynamic5mSelectorFixed: true,
        frozenP21EntryFixed: true,
    futureOutcomeUsed: false,
        rawSnapshotSha256: measurement.rawSnapshotSha256,
      });
    }
  }

  const seriesIndex = new Map(sessionSeries.map(row => [row.symbol, row]));
  for (const goldenRow of goldenBySession.get(shard.sessionDate) ?? []) {
    const bars = seriesIndex.get(String(goldenRow.symbol).toUpperCase())?.bars ?? [];
    const reconstructedPrefix = bars
      .filter(bar => Date.parse(bar.timestamp) + 300_000 <= Date.parse(goldenRow.entryTimestamp))
      .map(stripBar);
    const goldenPrefix = (goldenRow.contextBars ?? []).map(stripBar);
    const reconstructedReference = reconstructedPrefix.at(-1)?.close ?? null;
    const goldenTimestamps = goldenPrefix.map(bar => bar.timestamp);
    const reconstructedTimestamps = reconstructedPrefix.map(bar => bar.timestamp);
    goldenBarAudits.push({
      goldenCandidateEventId: goldenRow.candidateEventId,
      bucketEventKey: bucketEventKey(goldenRow),
      sessionDate: shard.sessionDate,
      symbol: goldenRow.symbol,
      sourceClass: goldenRow.sourceClass,
      goldenContextBarCount: goldenPrefix.length,
      reconstructedContextBarCount: reconstructedPrefix.length,
      timestampSequenceMatch: JSON.stringify(reconstructedTimestamps) === JSON.stringify(goldenTimestamps),
      exactContextBars: JSON.stringify(reconstructedPrefix) === JSON.stringify(goldenPrefix),
      goldenEntryReferencePrice: goldenRow.entryPrice,
      reconstructedCompletedBarReferencePrice: reconstructedReference,
      exactEntryReferencePrice: Number(goldenRow.entryPrice) === Number(reconstructedReference),
      goldenContextBarsSha256: sha256(Buffer.from(JSON.stringify(goldenPrefix))),
      reconstructedContextBarsSha256: sha256(Buffer.from(JSON.stringify(reconstructedPrefix))),
    });
  }

  perSession.push({
    sessionDate: shard.sessionDate,
    marketSymbols: sessionSeries.length,
    marketBars: sessionSeries.reduce((sum, row) => sum + (row.bars?.length ?? 0), 0),
    snapshots: snapshotAudit.pointCount,
    readySnapshots: snapshotAudit.readyPointCount,
    blockedSnapshots: snapshotAudit.blockedPointCount,
    minimumSnapshotSymbols: snapshotAudit.minimumSymbolCount,
    maximumSnapshotSymbols: snapshotAudit.maximumSymbolCount,
    selectedEvents: selectionEvents.filter(row => row.sessionDate === shard.sessionDate).length,
    p21Candidates: replay.candidateCount,
    p21Long: replay.countsByDirection.LONG,
    p21Short: replay.countsByDirection.SHORT,
    replayReadyPoints: replay.audit.readyPointCount,
    replayBlockedPoints: replay.totalBlockedPointCount,
    replayBlockedReasons: replay.blockedReasonDistribution,
    replayBlockedPointDiagnostics: replay.audit.blockedPoints.map(point => ({
      observedAt: point.observedAt,
      reason: point.reason,
      requiredSymbolCount: point.requiredSymbols.length,
      missingSymbols: point.missingSymbols,
      insufficientPrefixSymbols: point.symbolCoverage.filter(row => !row.minimumPrefixSatisfied).map(row => ({
        symbol: row.symbol,
        availablePrefixBarCount: row.availablePrefixBarCount,
        requiredPrefixBarCount: row.requiredPrefixBarCount,
        missingBarIntervals: row.missingBarIntervals,
      })),
    })),
    scorerBlockedPointDiagnostics: replay.scorerBlockedPoints,
    internalSelectorParity: replay.audit.exactSelectorParityCount,
    pitViolations: replay.pitViolationCount,
  });
  console.log(JSON.stringify({
    completedSession: sessionIndex + 1,
    totalSessions: requestedSessionShards.length,
    sessionDate: shard.sessionDate,
    readySnapshots: snapshotAudit.readyPointCount,
    selectedEvents: perSession.at(-1).selectedEvents,
    p21Candidates: replay.candidateCount,
    replayBlockedPoints: replay.totalBlockedPointCount,
  }));
}

candidates.sort((left, right) => left.entryTimestamp.localeCompare(right.entryTimestamp) || left.symbol.localeCompare(right.symbol));
selectionEvents.sort((left, right) => left.decisionTimestamp.localeCompare(right.decisionTimestamp) || left.symbol.localeCompare(right.symbol));
const reconstructedCandidateByBucket = new Map(candidates.map(candidate => [bucketEventKey(candidate), candidate]));
const goldenCandidateAudits = goldenRows
  .filter(row => requestedSessionShards.some(shard => shard.sessionDate === row.sessionDate))
  .map(row => {
    const reconstructed = reconstructedCandidateByBucket.get(bucketEventKey(row)) ?? null;
    return {
      goldenCandidateEventId: row.candidateEventId,
      bucketEventKey: bucketEventKey(row),
      sourceClass: row.sourceClass,
      reconstructedCandidatePresent: Boolean(reconstructed),
      directionMatch: reconstructed ? reconstructed.direction === row.direction : false,
      featureCutoffMatch: reconstructed ? reconstructed.featureCutoff === row.featureCutoff : false,
      modelIdMatch: reconstructed ? reconstructed.modelId === row.modelId : false,
    };
  });

const countsByDirection = { LONG: 0, SHORT: 0 };
const candidateMemberships = { v1Only: 0, v2Only: 0, v1AndV2: 0 };
const selectionMemberships = { v1Only: 0, v2Only: 0, v1AndV2: 0 };
const labelCompletenessByHorizon = Object.fromEntries([1, 2, 3, 6, 12].map(horizon => [horizon, { complete: 0, incomplete: 0 }]));
const sectors = {};
const timeOfDay = {};
const priceBuckets = { lt100: 0, from100To499: 0, from500To999: 0, from1000To4999: 0, gte5000: 0 };
const liquidityTurnoverBuckets = { lt100m: 0, from100mTo999m: 0, from1bTo9_9b: 0, gte10b: 0, missing: 0 };
for (const selection of selectionEvents) {
  const hasV1 = selection.selectorMemberships.includes('DYNAMIC5M_V1');
  const hasV2 = selection.selectorMemberships.includes('DYNAMIC5M_V2');
  increment(selectionMemberships, hasV1 && hasV2 ? 'v1AndV2' : hasV1 ? 'v1Only' : 'v2Only');
}
const selectionById = new Map(selectionEvents.map(row => [row.selectionEventId, row]));
for (const candidate of candidates) {
  increment(countsByDirection, candidate.direction);
  const variants = candidate.selectorMemberships.map(row => row.variant);
  const hasV1 = variants.includes('DYNAMIC5M_V1');
  const hasV2 = variants.includes('DYNAMIC5M_V2');
  increment(candidateMemberships, hasV1 && hasV2 ? 'v1AndV2' : hasV1 ? 'v1Only' : 'v2Only');
  increment(sectors, candidate.sector ?? 'UNKNOWN');
  const jstHour = Number(new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Tokyo', hour: '2-digit', hourCycle: 'h23' }).format(new Date(candidate.entryTimestamp)));
  increment(timeOfDay, jstHour < 10 ? '09:xx' : jstHour < 12 ? '10:00-11:30' : jstHour < 14 ? '12:30-13:59' : '14:00-15:30');
  const price = Number(candidate.entryPrice);
  increment(priceBuckets, price < 100 ? 'lt100' : price < 500 ? 'from100To499' : price < 1000 ? 'from500To999' : price < 5000 ? 'from1000To4999' : 'gte5000');
  const turnover = Number(selectionById.get(candidate.candidateEventId)?.turnoverYen);
  increment(liquidityTurnoverBuckets, !Number.isFinite(turnover) ? 'missing' : turnover < 1e8 ? 'lt100m' : turnover < 1e9 ? 'from100mTo999m' : turnover < 1e10 ? 'from1bTo9_9b' : 'gte10b');
  for (const [horizon, stats] of Object.entries(labelCompletenessByHorizon)) {
    increment(stats, candidate.labelCompleteness[horizon] === true ? 'complete' : 'incomplete');
  }
}

const uniqueSymbols = [...new Set(candidates.map(row => row.symbol))].sort();
const uniqueSelectionSymbols = [...new Set(selectionEvents.map(row => row.symbol))].sort();
const sessions = [...new Set(candidates.map(row => row.sessionDate))].sort();
const dailyContextStatusDistribution = {};
for (const candidate of candidates) increment(dailyContextStatusDistribution, candidate.dailyContext?.status ?? 'MISSING');
const dailyContextCovered = candidates.filter(candidate => candidate.dailyContext?.available === true).length;
const availablePriorSessionSummary = numericSummary(candidates
  .filter(candidate => candidate.dailyContext?.available === true)
  .map(candidate => candidate.dailyContext.availablePriorSessions));
const dailyArchiveRecordSummary = numericSummary((dailyManifest?.receipts ?? [])
  .map(receipt => receipt.acceptedDailyRecordCount));
const dailyCorporateActionAudit = (dailyManifest?.receipts ?? []).reduce((audit, receipt) => {
  const actions = receipt.corporateActionEventCounts ?? {};
  const dividends = Number(actions.dividends ?? 0);
  const splits = Number(actions.splits ?? 0);
  audit.dividendEventCount += dividends;
  audit.splitEventCount += splits;
  if (dividends > 0) audit.symbolsWithDividendEvents += 1;
  if (splits > 0) audit.symbolsWithSplitEvents += 1;
  return audit;
}, { dividendEventCount: 0, splitEventCount: 0, symbolsWithDividendEvents: 0, symbolsWithSplitEvents: 0 });
const replayBlockedPointCount = perSession.reduce((sum, row) => sum + Number(row.replayBlockedPoints ?? 0), 0);
const checkpoint = candidates.length >= 1000 ? 'CHECKPOINT_C_1000_REACHED'
  : candidates.length >= 500 ? 'CHECKPOINT_B_500_REACHED'
    : candidates.length >= 200 ? 'CHECKPOINT_A_200_REACHED' : 'BELOW_CHECKPOINT_A_200';
const generatedAt = new Date().toISOString();
const selectionScopeCore = {
  schemaVersion: 1,
  phase: '57.entry-quality-v2.market-first-selection-symbol-scope',
  status: 'CURRENT_DYNAMIC5M_SELECTION_SYMBOL_SCOPE_READY_NO_MODEL',
  generatedAt,
  sourceClass: 'HISTORICAL_RECONSTRUCTION_LATER_FETCHED',
  datasetRole: 'DEVELOPMENT_ONLY',
  prospective: false,
  formalOos: false,
  scope: 'ALL_SYMBOLS_SELECTED_BY_CURRENT_DYNAMIC5M_V1_OR_V2_IN_READY_RECONSTRUCTED_SNAPSHOTS',
  symbolCount: uniqueSelectionSymbols.length,
  symbols: uniqueSelectionSymbols,
  selectionEventCount: selectionEvents.length,
  marketArchiveManifestContentSha256: manifest.manifestContentSha256,
  dailyDataMayInfluenceHistoricalSelectorReplay: false,
  candidateOutcomeUsedToChooseSymbols: false,
  safety: ENTRY_V2_HISTORICAL_MARKET_SAFETY,
};
const selectionScope = {
  ...selectionScopeCore,
  selectionScopeContentSha256: fingerprintEntryV2SelectionScope(selectionScopeCore),
};
if (dailyManifest && (
  dailyManifest.selectionScope?.selectionScopeContentSha256 !== selectionScope.selectionScopeContentSha256
  || Number(dailyManifest.selectionScope?.fullSelectionSymbolCount) !== uniqueSelectionSymbols.length
  || Number(dailyManifest.requestedSymbolCount) !== uniqueSelectionSymbols.length
)) {
  throw new Error('ENTRY_V2_MARKET_REPLAY_DAILY_SELECTION_SCOPE_MISMATCH');
}
const datasetCore = {
  schemaVersion: 1,
  phase: '57.entry-quality-v2.market-first-development-dataset',
  status: `${checkpoint}_NO_MODEL`,
  generatedAt,
  sourceClass: 'HISTORICAL_RECONSTRUCTION_LATER_FETCHED',
  classification: {
    datasetRole: 'DEVELOPMENT_ONLY',
    historicalReconstruction: true,
    nonProspective: true,
    prospective: false,
    formalOos: false,
    actualDurable: false,
    modelFittingPerformed: false,
    modelFittingAllowed: false,
    promotionEligible: false,
  },
  fixedBoundaries: {
    selector: 'CURRENT_DYNAMIC5M',
    entry: 'PHASE57_P21_FROZEN_ENTRY',
    selectorChanged: false,
    entryChanged: false,
    exitChanged: false,
    capitalAllocationChanged: false,
    costAssumptionsChanged: false,
  },
  lineage: {
    marketArchiveManifest: path.relative(process.cwd(), manifestPath),
    marketArchiveManifestContentSha256: manifest.manifestContentSha256,
    frozenHistoryPack: path.relative(process.cwd(), historyPackPath),
    frozenHistoryPackSha256: historyPackSha256,
    frozenHistoryEndSessionDate: frozenHistoryDates.at(-1),
    goldenSubstrate: fs.existsSync(goldenSubstratePath) ? path.relative(process.cwd(), goldenSubstratePath) : null,
    goldenSubstrateSha256: fs.existsSync(goldenSubstratePath) ? sha256(fs.readFileSync(goldenSubstratePath)) : null,
    selectionScope: path.relative(process.cwd(), selectionSymbolsOutputPath),
    selectionScopeContentSha256: selectionScope.selectionScopeContentSha256,
    dailyArchiveManifest: dailyManifestPath ? path.relative(process.cwd(), dailyManifestPath) : null,
    dailyArchiveManifestContentSha256: dailyManifest?.manifestContentSha256 ?? null,
  },
  selectionEventCount: selectionEvents.length,
  p21CandidateEventCount: candidates.length,
  marketContextCount: marketContexts.length,
  marketContexts,
  selectionEvents,
  candidates,
  safety: ENTRY_V2_HISTORICAL_MARKET_SAFETY,
};
const dataset = { ...datasetCore, datasetContentSha256: sha256(Buffer.from(JSON.stringify(datasetCore))) };
writeAtomicJson(outputPath, dataset);
writeAtomicJson(selectionSymbolsOutputPath, selectionScope);

const integrity = {
  schemaVersion: 1,
  phase: '57.entry-quality-v2.market-first-integrity',
  status: checkpoint,
  generatedAt,
  classification: dataset.classification,
  checkpoints: {
    checkpoint200Reached: candidates.length >= 200,
    checkpoint500Reached: candidates.length >= 500,
    checkpoint1000Reached: candidates.length >= 1000,
    checkpoint,
  },
  marketDataset: {
    provider: manifest.provider,
    totalMarketBars,
    totalReconstructedSnapshots: totalSnapshots,
    readySnapshots: totalSnapshotReady,
    blockedSnapshots: totalSnapshotBlocked,
    marketSnapshotBlockedReasons,
    requestedUniverseSymbols: manifest.universe.requestedSnapshotSymbolCount,
    fetchedSymbols: manifest.fetchedSymbolCount,
    failedSymbols: manifest.failedSymbolCount,
    sessionsInArchive: requestedSessionShards.length,
    sessionDetails: perSession,
    sourceClass: manifest.sourceClass,
    universeAudit: manifest.universe,
    dataSemantics: manifest.dataSemantics,
  },
  eventDataset: {
    totalSelectedEvents: selectionEvents.length,
    totalP21CandidateEvents: candidates.length,
    independentCandidateEvents: candidateIds.size,
    duplicateCandidateEvents: candidates.length - candidateIds.size,
    uniqueSymbols,
    uniqueSymbolCount: uniqueSymbols.length,
    uniqueSelectionSymbolCount: uniqueSelectionSymbols.length,
    sessions,
    sessionCount: sessions.length,
    countsByDirection,
    candidateMemberships,
    selectionMemberships,
    labelCompletenessByHorizon,
    priceBuckets,
    liquidityTurnoverBuckets,
    timeOfDay,
    sectors,
    sourceClassBreakdown: { HISTORICAL_RECONSTRUCTION_LATER_FETCHED: candidates.length },
    dailyContextCoverage: {
      archiveConnected: Boolean(dailyManifest),
      covered: dailyContextCovered,
      missingOrBlocked: candidates.length - dailyContextCovered,
      total: candidates.length,
      status: dailyManifest
        ? (dailyContextCovered === candidates.length ? 'STRICT_PRIOR_SESSION_DAILY_CONTEXT_CONNECTED' : 'PARTIAL_OR_BLOCKED')
        : 'NOT_YET_CONNECTED_NO_VALUE_FABRICATED',
      statusDistribution: dailyContextStatusDistribution,
      requestedSelectionSymbolCount: dailyManifest?.requestedSymbolCount ?? 0,
      fetchedSelectionSymbolCount: dailyManifest?.fetchedSymbolCount ?? 0,
      failedSelectionSymbolCount: dailyManifest?.failedSymbolCount ?? 0,
      archiveDailyRecordCount: dailyArchiveRecordSummary.count > 0
        ? (dailyManifest.receipts ?? []).reduce((sum, receipt) => sum + Number(receipt.acceptedDailyRecordCount ?? 0), 0)
        : 0,
      archiveRecordsPerSymbol: dailyArchiveRecordSummary,
      availablePriorSessionsPerCandidate: availablePriorSessionSummary,
      requiredPriorSessions: 101,
      retainedPriorSessionTarget: 250,
      blockedReasonDistribution: Object.fromEntries(Object.entries(dailyContextStatusDistribution)
        .filter(([status]) => status !== 'ENTRY_V2_HISTORICAL_PRIOR_DAILY_CONTEXT_READY')),
      corporateActionAudit: {
        ...dailyCorporateActionAudit,
        adjustedCloseStoredForAuditOnly: dailyManifest?.dataSemantics?.adjustedCloseStoredForAuditOnly ?? false,
        adjustedCloseUsedAsFeature: dailyManifest?.dataSemantics?.adjustedCloseUsedAsFeature ?? false,
        providerQuoteCorporateActionSemanticsResolved:
          dailyManifest?.dataSemantics?.providerQuoteCorporateActionSemanticsResolved ?? false,
      },
      providerQuoteCorporateActionSemanticsResolved:
        dailyManifest?.dataSemantics?.providerQuoteCorporateActionSemanticsResolved ?? false,
    },
    marketContextCoverage: {
      marketWideBreadthCovered: candidates.filter(row => row.marketContext?.marketBreadthContextAvailable === true).length,
      benchmarkIndexCovered: candidates.filter(row => row.marketContext?.benchmarkIndexContextAvailable === true).length,
      topixCovered: 0,
      nikkei225Covered: 0,
      total: candidates.length,
      status: 'MARKETWIDE_BREADTH_CONNECTED;TOPIX_NIKKEI_NOT_YET_CONNECTED_NO_VALUE_FABRICATED',
    },
    tickToPriceCoverage: { covered: 0, total: candidates.length, status: 'TICK_SCHEDULE_NOT_YET_CONNECTED_NO_VALUE_FABRICATED' },
  },
  parityAndLeakageAudit: {
    internalCurrentDynamic5mDeterministicParityCount: internalSelectorParityCount,
    priorGoldenStoredRawSnapshotParityReference: '132/132;REFERENCE_ONLY_NOT_CLAIMED_FOR_YAHOO_RECONSTRUCTION',
    goldenBarAuditCount: goldenBarAudits.length,
    goldenExactContextBarCount: goldenBarAudits.filter(row => row.exactContextBars).length,
    goldenTimestampSequenceMatchCount: goldenBarAudits.filter(row => row.timestampSequenceMatch).length,
    goldenExactEntryReferencePriceCount: goldenBarAudits.filter(row => row.exactEntryReferencePrice).length,
    goldenCandidateAuditCount: goldenCandidateAudits.length,
    goldenReconstructedCandidatePresentCount: goldenCandidateAudits.filter(row => row.reconstructedCandidatePresent).length,
    goldenDirectionMatchCount: goldenCandidateAudits.filter(row => row.directionMatch).length,
    providerTimestampSemanticClassification: goldenBarAudits.length > 0
      && goldenBarAudits.every(row => row.timestampSequenceMatch)
      ? 'PROVIDER_NATIVE_BAR_START_SEQUENCE_MATCHES_ALL_GOLDEN_PREFIXES;OHLCV_REVISION_RISK_REMAINS'
      : manifest.dataSemantics.providerBarOpenVsCloseSemanticClassification,
    pitViolationCount,
    futureLabelsCreatedOnlyAfterFeatureFreeze: true,
    completedBarRule: ENTRY_V2_HISTORICAL_MARKET_POLICY.completedBarRule,
    missingBarsInterpolatedOrFabricated: false,
    goldenBarAudits,
    goldenCandidateAudits,
    existingGoldenRowsExcludedFromDevelopmentAggregation: true,
    goldenOverlapEventCount: goldenCandidateAudits.filter(row => row.reconstructedCandidatePresent).length,
  },
  blocked: {
    marketSnapshotBlockedCount: totalSnapshotBlocked,
    marketSnapshotBlockedReasons,
    replayBlockedPointCount,
    replayBlockedReasons,
  },
  riskAudit: {
    survivorshipBiasRisk: manifest.universe?.survivorshipBiasRisk ?? 'UNKNOWN',
    historicalUniverseClaimedComplete: manifest.universe?.claimedAsCompleteHistoricalJpxUniverse ?? false,
    corporateActionRisk: dailyManifest?.dataSemantics?.providerQuoteCorporateActionSemanticsResolved === true
      ? 'RESOLVED' : 'PROVIDER_QUOTE_OHLC_SEMANTICS_UNRESOLVED;ADJUSTED_CLOSE_AUDIT_ONLY',
    providerRevisionRisk: goldenBarAudits.some(row => !row.exactContextBars)
      ? 'PRESENT_GOLDEN_OHLCV_PARITY_INCOMPLETE' : 'NO_DIFFERENCE_OBSERVED_IN_GOLDEN_OVERLAP',
    yahooFiveMinuteObservedRetention: 'APPROXIMATELY_60_DAYS_AS_OF_2026-09-05',
    fixedFrozenHistoryEndSessionDate: frozenHistoryDates.at(-1),
    earliestLeakageFreeReplaySessionDate: earliestLeakageFreeReplaySessionDate.toISOString().slice(0, 10),
    checkpoint500PhysicalConstraint:
      candidates.length >= 500
        ? null
        : 'NO_ADDITIONAL_COMPLETED_SESSION_IN_ARCHIVE_AFTER_FROZEN_HISTORY_BOUNDARY;OLDER_REPLAY_REQUIRES_STRICTLY_CAUSAL_OLDER_FROZEN_P21_HISTORY_OR_A_NEW_PROVIDER',
  },
  modelReadiness: {
    modelFittingAllowed: false,
    reasons: [
      ...(dailyContextCovered !== candidates.length ? ['DAILY_CONTEXT_COVERAGE_INCOMPLETE'] : []),
      ...(dailyManifest?.dataSemantics?.providerQuoteCorporateActionSemanticsResolved === false
        ? ['DAILY_PROVIDER_QUOTE_CORPORATE_ACTION_SEMANTICS_UNRESOLVED'] : []),
      'UNIVERSE_COMPLETENESS_AND_SURVIVORSHIP_AUDIT_INCOMPLETE',
      ...(goldenBarAudits.some(row => !row.exactContextBars) ? ['GOLDEN_OHLCV_PARITY_INCOMPLETE_PROVIDER_REVISION_PRESENT'] : []),
      'DEVELOPMENT_VALIDATION_UNTOUCHED_OOS_BOUNDARIES_NOT_YET_FROZEN',
      ...(candidates.length < 200 ? ['INDEPENDENT_CANDIDATE_COUNT_BELOW_200'] : []),
      'DATASET_READINESS_PHASE0_REQUIRED_BEFORE_MODEL_FITTING',
      ...(pitViolationCount > 0 ? ['PIT_VIOLATIONS_PRESENT'] : []),
    ],
    optionalContextGaps: [
      'TOPIX_NIKKEI_POINT_IN_TIME_CONTEXT_NOT_YET_CONNECTED',
      'TICK_SCHEDULE_NOT_YET_CONNECTED',
    ],
    entryV2ModelFitted: false,
    thresholdTuned: false,
  },
  lineage: dataset.lineage,
  datasetOutput: path.relative(process.cwd(), outputPath),
  selectionSymbolsOutput: path.relative(process.cwd(), selectionSymbolsOutputPath),
  selectionScopeContentSha256: selectionScope.selectionScopeContentSha256,
  datasetContentSha256: dataset.datasetContentSha256,
  safety: ENTRY_V2_HISTORICAL_MARKET_SAFETY,
};
writeAtomicJson(integrityOutputPath, integrity);
console.log(JSON.stringify({
  status: integrity.status,
  dataset: outputPath,
  integrity: integrityOutputPath,
  selectionSymbols: selectionSymbolsOutputPath,
  totalMarketBars,
  snapshots: { total: totalSnapshots, ready: totalSnapshotReady, blocked: totalSnapshotBlocked },
  selectionEvents: selectionEvents.length,
  p21Candidates: candidates.length,
  uniqueSymbols: uniqueSymbols.length,
  sessions: sessions.length,
  countsByDirection,
  labelCompletenessByHorizon,
  pitViolationCount,
  golden: {
    barAudits: goldenBarAudits.length,
    exactContextBars: goldenBarAudits.filter(row => row.exactContextBars).length,
    candidateAudits: goldenCandidateAudits.length,
    reconstructedCandidatesPresent: goldenCandidateAudits.filter(row => row.reconstructedCandidatePresent).length,
  },
  modelFittingAllowed: false,
  safety: ENTRY_V2_HISTORICAL_MARKET_SAFETY,
}, null, 2));
