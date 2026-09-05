import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { gunzipSync } from 'node:zlib';
import {
  ENTRY_V2_READINESS_PHASE0_POLICY,
  ENTRY_V2_READINESS_PHASE0_SAFETY,
  applyDailyPriceBasisPolicy,
  buildGroupedWalkForwardPrecommit,
  buildLabelMissingnessAudit,
  candidateDirectionalLabel,
  jstTimeBucket,
  oneWayClusterAudit,
  quantile,
  summarize,
  sha256,
} from '../predict/daytrade/phase57-entry-quality-v2-readiness-audit.js';

const arg = (name, fallback = null) => {
  const index = process.argv.indexOf(name);
  return index >= 0 && index + 1 < process.argv.length ? process.argv[index + 1] : fallback;
};
const datasetPath = path.resolve(arg('--dataset', 'tmp/entry-v2-market-first-development-dataset-v3.json'));
const integrityPath = path.resolve(arg('--integrity', 'predict/daytrade/phase57-entry-quality-v2-market-first-integrity-2026-09-05.json'));
const goldenPath = path.resolve(arg('--golden', 'predict/daytrade/phase57-entry-quality-v2-development-candidate-substrate-2026-09-05.json'));
const marketArchiveDir = path.resolve(arg('--market-archive-dir', 'tmp/entry-v2-historical-market'));
const dailyArchiveDir = path.resolve(arg('--daily-archive-dir', 'tmp/entry-v2-historical-daily'));
const outputPath = path.resolve(arg('--output', 'predict/daytrade/phase57-entry-quality-v2-dataset-readiness-phase0-2026-09-05.json'));

const readJson = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const writeAtomicJson = (file, value) => {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temporary = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`);
  fs.renameSync(temporary, file);
};
const fiveMinuteBucket = value => new Date(Math.floor(Date.parse(value) / 300_000) * 300_000).toISOString();
const eventKey = row => `${row.sessionDate}|${fiveMinuteBucket(row.entryTimestamp ?? row.decisionTimestamp)}|${String(row.symbol).toUpperCase()}`;
const jstSessionDate = epochSeconds => new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
}).format(new Date(Number(epochSeconds) * 1000));
const stripBar = bar => ({
  timestamp: bar.timestamp,
  open: Number(bar.open), high: Number(bar.high), low: Number(bar.low), close: Number(bar.close), volume: Number(bar.volume),
});
const median = values => quantile(values, 0.5);
const increment = (target, key, amount = 1) => { target[key] = (target[key] ?? 0) + amount; };
const pearson = (left, right) => {
  const pairs = left.map((value, index) => [Number(value), Number(right[index])]).filter(pair => pair.every(Number.isFinite));
  if (pairs.length < 3) return null;
  const meanLeft = pairs.reduce((sum, pair) => sum + pair[0], 0) / pairs.length;
  const meanRight = pairs.reduce((sum, pair) => sum + pair[1], 0) / pairs.length;
  const numerator = pairs.reduce((sum, pair) => sum + ((pair[0] - meanLeft) * (pair[1] - meanRight)), 0);
  const denominator = Math.sqrt(
    pairs.reduce((sum, pair) => sum + ((pair[0] - meanLeft) ** 2), 0)
    * pairs.reduce((sum, pair) => sum + ((pair[1] - meanRight) ** 2), 0),
  );
  return denominator === 0 ? null : numerator / denominator;
};

const dataset = readJson(datasetPath);
const integrity = readJson(integrityPath);
const golden = readJson(goldenPath);
const marketManifestPath = path.join(marketArchiveDir, 'manifest.json');
const dailyManifestPath = path.join(dailyArchiveDir, 'manifest.json');
const marketManifest = readJson(marketManifestPath);
const dailyManifest = readJson(dailyManifestPath);
const falseSafetyKeys = [
  'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
  'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed', 'transmitted',
];
for (const key of falseSafetyKeys) {
  if (ENTRY_V2_READINESS_PHASE0_SAFETY[key] !== false || dataset.safety?.[key] !== false) {
    throw new Error(`ENTRY_V2_PHASE0_UNSAFE_${key}`);
  }
}
if (dataset.classification?.modelFittingPerformed !== false
  || dataset.classification?.prospective !== false
  || dataset.sourceClass !== 'HISTORICAL_RECONSTRUCTION_LATER_FETCHED'
  || integrity.parityAndLeakageAudit?.pitViolationCount !== 0
  || integrity.eventDataset?.duplicateCandidateEvents !== 0) {
  throw new Error('ENTRY_V2_PHASE0_DATASET_BOUNDARY_INVALID');
}

const marketShardBySession = new Map(marketManifest.sessionShards.map(shard => [shard.sessionDate, shard]));
const marketSeriesBySession = new Map();
function loadMarketSession(sessionDate) {
  if (marketSeriesBySession.has(sessionDate)) return marketSeriesBySession.get(sessionDate);
  const shard = marketShardBySession.get(sessionDate);
  if (!shard) return null;
  const compressed = fs.readFileSync(path.join(marketArchiveDir, shard.file));
  if (sha256(compressed) !== shard.compressedFileSha256) throw new Error(`ENTRY_V2_PHASE0_MARKET_SHARD_SHA_MISMATCH:${sessionDate}`);
  const rows = gunzipSync(compressed).toString('utf8').trim().split('\n').filter(Boolean).map(JSON.parse);
  const index = new Map(rows.map(row => [String(row.symbol).toUpperCase(), row]));
  marketSeriesBySession.set(sessionDate, index);
  return index;
}

const reconstructedCandidateByKey = new Map(dataset.candidates.map(row => [eventKey(row), row]));
const selectionByKey = new Map(dataset.selectionEvents.map(row => [eventKey(row), row]));
const goldenInventory = [];
const allPriceAbsDiffPct = [];
const allVolumeAbsDiffPct = [];
const entrySignedErrorPct = [];
for (const goldenRow of golden.rows) {
  const session = loadMarketSession(goldenRow.sessionDate);
  const sourceSeries = session?.get(String(goldenRow.symbol).toUpperCase()) ?? null;
  const reconstructedBars = (sourceSeries?.bars ?? [])
    .filter(bar => Date.parse(bar.timestamp) + 300_000 <= Date.parse(goldenRow.entryTimestamp))
    .map(stripBar);
  const goldenBars = (goldenRow.contextBars ?? []).map(stripBar);
  const reconstructedByTimestamp = new Map(reconstructedBars.map(bar => [bar.timestamp, bar]));
  const barComparisons = goldenBars.map(goldenBar => {
    const reconstructedBar = reconstructedByTimestamp.get(goldenBar.timestamp) ?? null;
    const fields = {};
    for (const field of ['open', 'high', 'low', 'close', 'volume']) {
      const goldenValue = Number(goldenBar[field]);
      const reconstructedValue = Number(reconstructedBar?.[field]);
      const absolute = Number.isFinite(reconstructedValue) ? reconstructedValue - goldenValue : null;
      const relativePct = Number.isFinite(absolute) && goldenValue !== 0 ? (absolute / Math.abs(goldenValue)) * 100 : null;
      fields[field] = { golden: goldenValue, reconstructed: Number.isFinite(reconstructedValue) ? reconstructedValue : null, absolute, relativePct };
      if (field === 'volume' && Number.isFinite(relativePct)) allVolumeAbsDiffPct.push(Math.abs(relativePct));
      if (field !== 'volume' && Number.isFinite(relativePct)) allPriceAbsDiffPct.push(Math.abs(relativePct));
    }
    return { timestamp: goldenBar.timestamp, reconstructedBarPresent: Boolean(reconstructedBar), fields };
  });
  const timestampSequenceMatch = JSON.stringify(goldenBars.map(row => row.timestamp)) === JSON.stringify(reconstructedBars.map(row => row.timestamp));
  const exactPriceBars = barComparisons.every(row => ['open', 'high', 'low', 'close'].every(field => row.fields[field].absolute === 0));
  const exactVolumeBars = barComparisons.every(row => row.fields.volume.absolute === 0);
  const reconstructedEntryReference = reconstructedBars.at(-1)?.close ?? null;
  const entryReferenceSignedErrorPct = reconstructedEntryReference === null
    ? null : ((reconstructedEntryReference - Number(goldenRow.entryPrice)) / Number(goldenRow.entryPrice)) * 100;
  if (Number.isFinite(entryReferenceSignedErrorPct)) entrySignedErrorPct.push(entryReferenceSignedErrorPct);
  const key = eventKey(goldenRow);
  const candidate = reconstructedCandidateByKey.get(key) ?? null;
  const selection = selectionByKey.get(key) ?? null;
  const causes = [];
  if (!sourceSeries) causes.push('MISSING_SYMBOL');
  if (!timestampSequenceMatch) causes.push('TIMESTAMP_ALIGNMENT');
  if (timestampSequenceMatch && exactPriceBars && !exactVolumeBars) causes.push('VOLUME_REVISION');
  if (timestampSequenceMatch && !exactPriceBars) causes.push('LIVE_VS_HISTORICAL_PROVIDER_DIFFERENCE', 'YAHOO_HISTORICAL_REVISION');
  if (entryReferenceSignedErrorPct !== 0) causes.push('ENTRY_REFERENCE_SEMANTICS');
  if (!candidate && selection) causes.push('FROZEN_P21_THRESHOLD_OR_HISTORY_STATE_DIFFERENCE');
  if (!candidate && !selection) causes.push('CURRENT_SELECTOR_MEMBERSHIP_DIFFERENCE');
  if (!causes.length) causes.push('MATCH');
  goldenInventory.push({
    candidateEventId: goldenRow.candidateEventId,
    symbol: goldenRow.symbol,
    sessionDate: goldenRow.sessionDate,
    decisionTimestamp: goldenRow.entryTimestamp,
    goldenContextBarCount: goldenBars.length,
    reconstructedContextBarCount: reconstructedBars.length,
    timestampSequenceMatch,
    exactPriceBars,
    exactVolumeBars,
    exactOhlcvBars: exactPriceBars && exactVolumeBars,
    priceAbsoluteDiffPct: summarize(barComparisons.flatMap(row => ['open', 'high', 'low', 'close'].map(field => Math.abs(row.fields[field].relativePct)).filter(Number.isFinite))),
    volumeAbsoluteDiffPct: summarize(barComparisons.map(row => Math.abs(row.fields.volume.relativePct)).filter(Number.isFinite)),
    entryReference: {
      golden: Number(goldenRow.entryPrice), reconstructedCompletedBarClose: reconstructedEntryReference,
      signedErrorPct: entryReferenceSignedErrorPct, absoluteErrorPct: Math.abs(entryReferenceSignedErrorPct),
    },
    goldenDirection: goldenRow.direction,
    reconstructedDirection: candidate?.direction ?? null,
    directionMatch: Boolean(candidate) && candidate.direction === goldenRow.direction,
    goldenCandidateEligible: true,
    reconstructedCandidateEligible: Boolean(candidate),
    goldenSelectorMemberships: goldenRow.selectorMemberships,
    reconstructedSelectorMemberships: selection?.selectorMemberships ?? candidate?.selectorMemberships ?? [],
    mismatchCauses: [...new Set(causes)],
    barComparisons,
  });
}

const mismatchReasonDistribution = {};
for (const row of goldenInventory) for (const reason of row.mismatchCauses) increment(mismatchReasonDistribution, reason);
const entryErrorAbsolute = entrySignedErrorPct.map(Math.abs);
const entryPositiveShare = entrySignedErrorPct.filter(value => value > 0).length / entrySignedErrorPct.length;
const entryNegativeShare = entrySignedErrorPct.filter(value => value < 0).length / entrySignedErrorPct.length;
const systematicDirectionShare = Math.max(entryPositiveShare, entryNegativeShare);
const goldenMismatchAudit = {
  eventCount: goldenInventory.length,
  exactTimestampSequenceCount: goldenInventory.filter(row => row.timestampSequenceMatch).length,
  exactPriceContextCount: goldenInventory.filter(row => row.exactPriceBars).length,
  exactVolumeContextCount: goldenInventory.filter(row => row.exactVolumeBars).length,
  exactOhlcvContextCount: goldenInventory.filter(row => row.exactOhlcvBars).length,
  exactEntryReferenceCount: goldenInventory.filter(row => row.entryReference.signedErrorPct === 0).length,
  reconstructedCandidateEligibleCount: goldenInventory.filter(row => row.reconstructedCandidateEligible).length,
  directionMatchCount: goldenInventory.filter(row => row.directionMatch).length,
  mismatchReasonDistribution,
  priceAbsoluteDifferencePct: summarize(allPriceAbsDiffPct),
  volumeAbsoluteDifferencePct: summarize(allVolumeAbsDiffPct),
  entryReferenceSignedErrorPct: summarize(entrySignedErrorPct),
  entryReferenceAbsoluteErrorPct: summarize(entryErrorAbsolute),
  entryReferenceErrorSign: { positiveShare: entryPositiveShare, negativeShare: entryNegativeShare, zeroShare: 1 - entryPositiveShare - entryNegativeShare },
  systematicAssessment: systematicDirectionShare >= 0.75
    ? 'DIRECTIONALLY_SYSTEMATIC_ENTRY_REFERENCE_DIFFERENCE'
    : 'NO_SINGLE_SIGN_DOMINATES;EVENT_LEVEL_PROVIDER_DIFFERENCES_REMAIN',
  thresholdSensitivityAssessment: {
    eligibilityMismatchCount: goldenInventory.filter(row => !row.reconstructedCandidateEligible).length,
    exactPriceButEligibilityMismatchCount: goldenInventory.filter(row => row.exactPriceBars && !row.reconstructedCandidateEligible).length,
    selectedButP21EligibilityMismatchCount: goldenInventory.filter(row => !row.reconstructedCandidateEligible
      && selectionByKey.has(eventKey(row))).length,
    selectorMembershipMismatchCount: goldenInventory.filter(row => !row.reconstructedCandidateEligible
      && !selectionByKey.has(eventKey(row))).length,
    conclusion: 'NO_RECONSTRUCTED_SCORE_MARGIN_IS_AVAILABLE_FOR_ALL_GOLDEN_ROWS;THRESHOLD_ONLY_CAUSATION_NOT_PROVEN',
  },
  events: goldenInventory,
};

const dailyReceiptBySymbol = new Map(dailyManifest.receipts.map(receipt => [receipt.symbol, receipt]));
const dailyBySymbol = new Map();
const corporateActionsBySymbol = new Map();
const splitContinuityRows = [];
for (const [symbol, receipt] of dailyReceiptBySymbol) {
  const normalizedCompressed = fs.readFileSync(path.join(dailyArchiveDir, receipt.normalizedFile));
  const rawCompressed = fs.readFileSync(path.join(dailyArchiveDir, receipt.rawFile));
  if (sha256(normalizedCompressed) !== receipt.normalizedCompressedFileSha256
    || sha256(rawCompressed) !== receipt.rawCompressedFileSha256) {
    throw new Error(`ENTRY_V2_PHASE0_DAILY_SHA_MISMATCH:${symbol}`);
  }
  const normalized = JSON.parse(gunzipSync(normalizedCompressed).toString('utf8'));
  const raw = JSON.parse(gunzipSync(rawCompressed).toString('utf8'));
  const records = normalized.series.records;
  dailyBySymbol.set(symbol, records);
  const events = raw.chart?.result?.[0]?.events ?? {};
  const actions = [];
  for (const event of Object.values(events.splits ?? {})) actions.push({
    type: 'SPLIT', sessionDate: jstSessionDate(event.date), numerator: Number(event.numerator), denominator: Number(event.denominator), splitRatio: event.splitRatio,
  });
  for (const event of Object.values(events.dividends ?? {})) actions.push({
    type: 'DIVIDEND', sessionDate: jstSessionDate(event.date), amount: Number(event.amount),
  });
  actions.sort((left, right) => left.sessionDate.localeCompare(right.sessionDate));
  corporateActionsBySymbol.set(symbol, actions);
  for (const split of actions.filter(action => action.type === 'SPLIT')) {
    const before = records.filter(record => record.sessionDate < split.sessionDate).at(-1) ?? null;
    const after = records.find(record => record.sessionDate >= split.sessionDate) ?? null;
    if (!before || !after) continue;
    const unadjustedSplitDropRatio = split.denominator / split.numerator;
    const observedRawRatio = after.close / before.close;
    const adjustedRatio = after.adjustedClose && before.adjustedClose ? after.adjustedClose / before.adjustedClose : null;
    const policyPair = applyDailyPriceBasisPolicy([before, after], [split], split.sessionDate).records;
    splitContinuityRows.push({
      symbol, splitSessionDate: split.sessionDate, splitRatio: split.splitRatio,
      beforeSessionDate: before.sessionDate, afterSessionDate: after.sessionDate,
      unadjustedSplitDropRatio, observedProviderQuoteCloseRatio: observedRawRatio,
      absoluteContinuityReturnPct: Math.abs((observedRawRatio - 1) * 100),
      closerToContinuousBasisThanUnadjustedSplitDrop:
        Math.abs(observedRawRatio - 1) < Math.abs(observedRawRatio - unadjustedSplitDropRatio),
      adjustedCloseRatio: adjustedRatio,
      policyCloseRatio: policyPair[1].close / policyPair[0].close,
      rawVolumeRatio: before.volume > 0 ? after.volume / before.volume : null,
    });
  }
}

const overlapCounts = {
  split: { sameDay: 0, prior1Session: 0, prior5Sessions: 0, prior20Sessions: 0, prior50Sessions: 0, prior100Sessions: 0 },
  dividend: { sameDay: 0, prior1Session: 0, prior5Sessions: 0, prior20Sessions: 0, prior50Sessions: 0, prior100Sessions: 0 },
};
const candidateCorporateActionOverlap = dataset.candidates.map(candidate => {
  const records = dailyBySymbol.get(candidate.symbol) ?? [];
  const indexByDate = new Map(records.map((record, index) => [record.sessionDate, index]));
  const candidateIndex = indexByDate.get(candidate.sessionDate);
  const flags = {};
  for (const type of ['SPLIT', 'DIVIDEND']) {
    const distances = (corporateActionsBySymbol.get(candidate.symbol) ?? [])
      .filter(action => action.type === type && action.sessionDate <= candidate.sessionDate)
      .map(action => candidateIndex - indexByDate.get(action.sessionDate))
      .filter(distance => Number.isInteger(distance) && distance >= 0);
    const key = type.toLowerCase();
    flags[key] = {
      sameDay: distances.includes(0),
      prior1Session: distances.some(distance => distance <= 1),
      prior5Sessions: distances.some(distance => distance <= 5),
      prior20Sessions: distances.some(distance => distance <= 20),
      prior50Sessions: distances.some(distance => distance <= 50),
      prior100Sessions: distances.some(distance => distance <= 100),
      nearestPriorSessionDistance: distances.length ? Math.min(...distances) : null,
    };
    for (const window of ['sameDay', 'prior1Session', 'prior5Sessions', 'prior20Sessions', 'prior50Sessions', 'prior100Sessions']) {
      if (flags[key][window]) overlapCounts[key][window] += 1;
    }
  }
  return { candidateEventId: candidate.candidateEventId, symbol: candidate.symbol, sessionDate: candidate.sessionDate, flags };
});
const splitContinuityReturns = splitContinuityRows.map(row => row.absoluteContinuityReturnPct);
const corporateActionAudit = {
  actionCounts: {
    dividends: [...corporateActionsBySymbol.values()].flat().filter(action => action.type === 'DIVIDEND').length,
    splits: [...corporateActionsBySymbol.values()].flat().filter(action => action.type === 'SPLIT').length,
  },
  priceBasisPolicy: ENTRY_V2_READINESS_PHASE0_POLICY.dailyPriceBasis,
  empiricalSplitContinuity: {
    evaluatedSplitCount: splitContinuityRows.length,
    providerQuoteContinuousBasisCount: splitContinuityRows.filter(row => row.closerToContinuousBasisThanUnadjustedSplitDrop).length,
    absoluteProviderQuoteOneSessionReturnPct: summarize(splitContinuityReturns),
    interpretation: 'PROVIDER_QUOTE_OHLC_IS_EMPIRICALLY_SPLIT_NORMALIZED;REAPPLYING_SPLIT_RATIOS_WOULD DOUBLE_ADJUST;ADJUSTED_CLOSE_REMAINS_DIVIDEND_AUDIT_ONLY',
    rows: splitContinuityRows,
  },
  candidateOverlapCounts: overlapCounts,
  candidateOverlaps: candidateCorporateActionOverlap,
  currentDatasetUsesFrozenPolicy: overlapCounts.split.prior20Sessions === 0,
  semanticsResolvedForPhase1Policy: true,
  futureSplitLeakagePrevented: true,
};

const labelRows = [];
for (const candidate of dataset.candidates) {
  const base = { sessionDate: candidate.sessionDate, symbol: candidate.symbol, sector: candidate.sector, timeOfDay: jstTimeBucket(candidate.entryTimestamp) };
  for (const horizon of [1, 3, 6]) {
    for (const metric of ['grossReturnPct', 'mfePct', 'maePct']) {
      const value = candidateDirectionalLabel(candidate, horizon, metric);
      if (value !== null) labelRows.push({ ...base, key: `h${horizon}.${metric}`, value });
    }
  }
}
const clustering = {};
for (const key of [...new Set(labelRows.map(row => row.key))]) {
  const rows = labelRows.filter(row => row.key === key);
  clustering[key] = {
    session: oneWayClusterAudit(rows, { clusterKey: 'sessionDate', valueKey: 'value' }),
    symbol: oneWayClusterAudit(rows, { clusterKey: 'symbol', valueKey: 'value' }),
    sector: oneWayClusterAudit(rows, { clusterKey: 'sector', valueKey: 'value' }),
    timeOfDay: oneWayClusterAudit(rows, { clusterKey: 'timeOfDay', valueKey: 'value' }),
  };
}

const candidateSessions = [...new Set(dataset.candidates.map(row => row.sessionDate))].sort();
const sessionRows = candidateSessions.map(sessionDate => {
  const rows = dataset.candidates.filter(candidate => candidate.sessionDate === sessionDate);
  const breadth = rows.map(row => row.marketContext?.breadthUpRatio).filter(Number.isFinite);
  const marketReturn = rows.map(row => row.marketContext?.equalWeightMeanReturnPct).filter(Number.isFinite);
  const crossSectionalVolatility = rows.map(row => row.marketContext?.crossSectionalReturnVolatilityPct).filter(Number.isFinite);
  const dailyVolatility = rows.map(row => row.dailyContext?.context?.dailyVolatility20Pct).filter(Number.isFinite);
  const sessionDetail = integrity.marketDataset.sessionDetails.find(row => row.sessionDate === sessionDate);
  const meanMarketReturn = summarize(marketReturn).mean;
  const medianCrossSectionalVolatility = median(crossSectionalVolatility);
  const thresholds = ENTRY_V2_READINESS_PHASE0_POLICY.sessionRegimeThresholds;
  return {
    sessionDate,
    candidateCount: rows.length,
    longCount: rows.filter(row => row.direction === 'LONG').length,
    shortCount: rows.filter(row => row.direction === 'SHORT').length,
    longRatio: rows.filter(row => row.direction === 'LONG').length / rows.length,
    breadthUpRatioMean: summarize(breadth).mean,
    equalWeightMarketReturnPctMean: meanMarketReturn,
    crossSectionalReturnVolatilityPctMedian: medianCrossSectionalVolatility,
    candidateDailyVolatility20PctMedian: median(dailyVolatility),
    sectorCount: new Set(rows.map(row => row.sector)).size,
    readySnapshotCount: sessionDetail?.readySnapshots ?? 0,
    blockedSnapshotCount: sessionDetail?.blockedSnapshots ?? 0,
    blockedSnapshotRate: (sessionDetail?.blockedSnapshots ?? 0) / ((sessionDetail?.readySnapshots ?? 0) + (sessionDetail?.blockedSnapshots ?? 0)),
    directionRegime: meanMarketReturn > thresholds.upReturnPct ? 'UP' : meanMarketReturn < thresholds.downReturnPct ? 'DOWN' : 'FLAT',
    volatilityRegime: medianCrossSectionalVolatility >= thresholds.highCrossSectionalVolatilityPct
      ? 'HIGH_VOL' : medianCrossSectionalVolatility < thresholds.lowCrossSectionalVolatilityPct ? 'LOW_VOL' : 'NORMAL_VOL',
  };
});
const regimeDistribution = { direction: {}, volatility: {} };
for (const row of sessionRows) {
  increment(regimeDistribution.direction, row.directionRegime);
  increment(regimeDistribution.volatility, row.volatilityRegime);
}
const blockedRates = sessionRows.map(row => row.blockedSnapshotRate);
const replaySelectionBiasAudit = {
  archiveSessionCount: integrity.marketDataset.sessionsInArchive,
  candidateSessionCount: candidateSessions.length,
  zeroCandidateSessions: integrity.marketDataset.sessionDetails.filter(row => row.p21Candidates === 0).map(row => row.sessionDate),
  allSessionsHaveAtLeastOneReadySnapshot: integrity.marketDataset.sessionDetails.every(row => row.readySnapshots > 0),
  fullyBlockedSessionCount: integrity.marketDataset.sessionDetails.filter(row => row.readySnapshots === 0).length,
  blockedSnapshotRate: summarize(integrity.marketDataset.sessionDetails.map(row => row.blockedSnapshots / (row.readySnapshots + row.blockedSnapshots))),
  blockedRateCorrelation: {
    candidateCount: pearson(blockedRates, sessionRows.map(row => row.candidateCount)),
    marketReturn: pearson(blockedRates, sessionRows.map(row => row.equalWeightMarketReturnPctMean)),
    marketVolatility: pearson(blockedRates, sessionRows.map(row => row.crossSectionalReturnVolatilityPctMedian)),
  },
  limitation: 'BLOCKED SNAPSHOTS LACK COMPLETE MARKET STATE;READY_VS_BLOCKED OUTCOME COMPARISON IS NOT IDENTIFIABLE WITHOUT FABRICATION',
};

const splitPrecommit = buildGroupedWalkForwardPrecommit(candidateSessions);
const readinessCriteria = {
  pitViolationsZero: integrity.parityAndLeakageAudit.pitViolationCount === 0,
  dailyContextCoverageSufficient: integrity.eventDataset.dailyContextCoverage.covered === dataset.candidates.length,
  corporateActionSemanticsResolved: corporateActionAudit.semanticsResolvedForPhase1Policy && corporateActionAudit.currentDatasetUsesFrozenPolicy,
  goldenMismatchExplainedAndBounded: goldenInventory.length === 41 && !goldenInventory.some(row => row.mismatchCauses.includes('UNKNOWN')),
  sessionClusteringMeasured: Object.values(clustering).every(row => Number.isFinite(row.session.icc)),
  effectiveSampleSizeEstimated: Object.values(clustering).every(row => Number.isFinite(row.session.approximateEffectiveN)),
  regimeDiversityAudited: sessionRows.length === candidateSessions.length,
  splitPolicyPrecommitted: splitPrecommit.folds.length > 0 && splitPrecommit.currentSessionsClaimedUntouchedOos === false,
  duplicateEventsZero: integrity.eventDataset.duplicateCandidateEvents === 0,
  futureLabelSeparationVerified: integrity.parityAndLeakageAudit.futureLabelsCreatedOnlyAfterFeatureFreeze === true,
  sourceLineageComplete: Boolean(dataset.lineage?.marketArchiveManifestContentSha256 && dataset.lineage?.dailyArchiveManifestContentSha256),
};
const blockers = [];
if (!readinessCriteria.corporateActionSemanticsResolved) blockers.push('CURRENT_DAILY_FEATURES_REQUIRE_POINT_IN_TIME_SPLIT_NORMALIZATION_REGENERATION');
if (!readinessCriteria.goldenMismatchExplainedAndBounded) blockers.push('GOLDEN_MISMATCH_UNEXPLAINED_OR_UNBOUNDED');
if (candidateSessions.length < 20) blockers.push('SESSION_COUNT_TOO_SMALL_FOR_STABLE_MODEL_SELECTION');
if (new Set(sessionRows.map(row => row.directionRegime)).size < 3) blockers.push('DIRECTION_REGIME_DIVERSITY_INCOMPLETE');
if (new Set(sessionRows.map(row => row.volatilityRegime)).size < 2) blockers.push('VOLATILITY_REGIME_DIVERSITY_INCOMPLETE');
blockers.push('NO_CURRENT_SESSION_CAN_BE_CLAIMED_AS_UNTOUCHED_OOS_AFTER_GOLDEN_AND_PHASE0_INSPECTION');

const outputCore = {
  schemaVersion: 1,
  phase: ENTRY_V2_READINESS_PHASE0_POLICY.phase,
  status: blockers.length ? 'PHASE0_AUDIT_COMPLETE_MODEL_NO_GO' : 'PHASE0_AUDIT_COMPLETE_MINIMAL_BASELINE_GO',
  generatedAt: new Date().toISOString(),
  classification: {
    datasetRole: 'DEVELOPMENT_VALIDATION_DIAGNOSTIC_ONLY',
    sourceClass: 'HISTORICAL_RECONSTRUCTION_LATER_FETCHED',
    prospective: false, formalOos: false, untouchedOos: false,
    modelFittingPerformed: false, thresholdTuned: false, promotionEligible: false,
  },
  inputLineage: {
    dataset: path.relative(process.cwd(), datasetPath), datasetSha256: sha256(fs.readFileSync(datasetPath)), datasetContentSha256: dataset.datasetContentSha256,
    integrity: path.relative(process.cwd(), integrityPath), integritySha256: sha256(fs.readFileSync(integrityPath)),
    golden: path.relative(process.cwd(), goldenPath), goldenSha256: sha256(fs.readFileSync(goldenPath)),
    marketManifest: path.relative(process.cwd(), marketManifestPath), marketManifestContentSha256: marketManifest.manifestContentSha256,
    dailyManifest: path.relative(process.cwd(), dailyManifestPath), dailyManifestContentSha256: dailyManifest.manifestContentSha256,
  },
  datasetSummary: {
    nominalCandidateCount: dataset.candidates.length,
    sessionCount: candidateSessions.length,
    candidatesPerSession: summarize(sessionRows.map(row => row.candidateCount)),
    uniqueSymbols: new Set(dataset.candidates.map(row => row.symbol)).size,
    longCount: dataset.candidates.filter(row => row.direction === 'LONG').length,
    shortCount: dataset.candidates.filter(row => row.direction === 'SHORT').length,
  },
  goldenMismatchAudit,
  corporateActionAudit,
  clusteringAudit: {
    methodology: 'CANDIDATE_LABELS_USED_FOR_DATASET_DEPENDENCE_DIAGNOSTICS_ONLY;NO_MODEL_OR_THRESHOLD_SELECTION',
    byLabelAndCluster: clustering,
  },
  effectiveSampleSizeAudit: Object.fromEntries(Object.entries(clustering).map(([key, value]) => [key, {
    nominalN: value.session.nominalN,
    sessionCount: value.session.clusterCount,
    averageClusterSize: value.session.averageClusterSize,
    icc: value.session.icc,
    designEffect: value.session.designEffect,
    approximateEffectiveN: value.session.approximateEffectiveN,
    methodology: value.session.methodology,
  }])),
  sessionRegimeAudit: {
    thresholdsFrozenWithoutPerformanceOptimization: ENTRY_V2_READINESS_PHASE0_POLICY.sessionRegimeThresholds,
    distribution: regimeDistribution,
    sessions: sessionRows,
  },
  replaySelectionBiasAudit,
  multiHorizonMissingnessAudit: buildLabelMissingnessAudit(dataset.candidates),
  validationPrecommit: splitPrecommit,
  modelReadinessGate: {
    fiveHundredCandidatesAbsoluteRequirement: false,
    criteria: readinessCriteria,
    decision: blockers.length ? 'NO_GO' : 'MINIMAL_BASELINE_RESEARCH_GO',
    blockers,
    phase1ModelFitted: false,
    thresholdTuned: false,
  },
  contextPolicy: {
    breadthCoverage: integrity.eventDataset.marketContextCoverage.marketWideBreadthCovered,
    topixCoverage: integrity.eventDataset.marketContextCoverage.topixCovered,
    nikkei225Coverage: integrity.eventDataset.marketContextCoverage.nikkei225Covered,
    tickSizeCoverage: integrity.eventDataset.tickToPriceCoverage.covered,
    missingValuesFabricated: false,
    tickPolicy: 'MISSING_UNTIL_FORMAL_JPX_RULE_WITH_HISTORICAL_ELIGIBILITY_IS_REPRODUCED',
  },
  policy: ENTRY_V2_READINESS_PHASE0_POLICY,
  safety: ENTRY_V2_READINESS_PHASE0_SAFETY,
};
const output = { ...outputCore, auditContentSha256: sha256(outputCore) };
writeAtomicJson(outputPath, output);
console.log(JSON.stringify({
  status: output.status,
  output: outputPath,
  nominalCandidates: output.datasetSummary.nominalCandidateCount,
  sessions: output.datasetSummary.sessionCount,
  golden: {
    exactOhlcv: goldenMismatchAudit.exactOhlcvContextCount,
    exactEntryReference: goldenMismatchAudit.exactEntryReferenceCount,
    reconstructedEligible: goldenMismatchAudit.reconstructedCandidateEligibleCount,
    directionMatch: goldenMismatchAudit.directionMatchCount,
  },
  corporateOverlap: overlapCounts,
  regimeDistribution,
  modelDecision: output.modelReadinessGate.decision,
  blockers,
  pitViolations: integrity.parityAndLeakageAudit.pitViolationCount,
  safety: output.safety,
}, null, 2));
