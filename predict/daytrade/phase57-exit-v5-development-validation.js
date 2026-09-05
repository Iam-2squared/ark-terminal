import crypto from 'node:crypto';
import { enrichHistoricalIntradayBars } from './phase57-intraday-multifactor.js';
import { buildMultiHorizonMagnitudeRows } from './phase57-adaptive-horizon-magnitude.js';
import { buildIntradayHorizonDatasets } from './phase57-nested-adaptive-horizon.js';
import { replayNestedAdaptiveOosSignals } from './phase57-adaptive-oos-signal-replay.js';
import { buildP25DataDrivenExitAnalogPool } from './phase57-p25-data-driven-exit.js';
import { PHASE57_P25_2K_POLICY } from './phase57-p25-2k-pinned-history-bridge.js';
import {
  buildExitV5TrainingSamplesFromFrozenRows,
  buildPurgedExitV5Split,
} from './phase57-exit-v5-continuation-dataset.js';
import {
  PHASE57_EXIT_V5_PAIRED_MODEL_IDS,
  fitExitV5PairedModelsFromPurgedSplit,
  summarizeExitV5FourWayPairs,
} from './phase57-exit-v5-paired-evaluator.js';
import { runExitV5AuditedSplitPairedEvaluation } from './phase57-exit-v5-audited-split-evaluator.js';

const SAFETY_FALSE_KEYS = Object.freeze([
  'executionAllowed',
  'brokerWriteAllowed',
  'excelOrderWriteAllowed',
  'rssOrderFunctionAllowed',
  'liveTradingAllowed',
  'paperTradingAllowed',
  'automaticPromotionAllowed',
  'productionUpdateAllowed',
  'transmitted',
  'freshHoldoutConsumed',
]);

const P21_OPTIONS = Object.freeze({
  outerTrainFraction: 0.6,
  outerTestFraction: 0.1,
  outerMinTrainRows: 500,
  innerTrainFraction: 0.6,
  innerTestFraction: 0.15,
  innerMinTrainRows: 200,
  thresholds: Object.freeze([0.55, 0.60, 0.65]),
  minInnerSignals: 50,
  minimumInnerNetReturnPct: 0,
  roundTripCostPct: 0.05,
});

const EXPECTED_VALIDATION_COUNTS = Object.freeze({
  '2026-08-06': 10,
  '2026-08-07': 41,
  '2026-08-10': 73,
  '2026-08-12': 31,
});

export const PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY = Object.freeze({
  phase: '57.exit-v5.development-validation.v1',
  sourceRunId: PHASE57_P25_2K_POLICY.canonicalSourceRunId,
  sourceArtifactName: PHASE57_P25_2K_POLICY.canonicalArtifactName,
  sourceSnapshotSha256: PHASE57_P25_2K_POLICY.canonicalSnapshotSha256,
  sourceDataEndIso: PHASE57_P25_2K_POLICY.canonicalDataEndIso,
  expectedHistorySessionCount: 190,
  expectedDistinctSessionDates: 38,
  historicalUniverse: PHASE57_P25_2K_POLICY.historicalUniverse,
  entrySelector: 'P21_NESTED_ADAPTIVE_OOS_SIGNAL_REPLAY_FROZEN',
  developmentEndDate: '2026-07-31',
  validationStartDate: '2026-08-01',
  validationEndDate: '2026-08-12',
  developmentEnd: '2026-07-31T23:59:59.999Z',
  validationEnd: '2026-08-12T23:59:59.999Z',
  oosEnd: '2026-08-31T23:59:59.999Z',
  expectedFrozenEntryCount: 315,
  expectedDevelopmentEntryCount: 160,
  expectedValidationEntryCount: 155,
  expectedDevelopmentSampleCount: 5897,
  expectedValidationSampleCount: 5382,
  expectedValidationCounts: EXPECTED_VALIDATION_COUNTS,
  expectedEntrySetFingerprint: '1b4b9116de322ae677a04060acc2fd55420d8e41a16cc4cffa5a3bd3d158e931',
  expectedMarketDataFingerprint: '17112106957ad4de8dc68a71c7e01024237d9400778d76b8ef0c674d49fabcf1',
  expectedPairedSubstrateFingerprint: '5311b5b2c7bb16a8dbe03e4f5d3b78bc3030da7a884dd2e4e24e53f5cb8f4e4c',
  p21Options: P21_OPTIONS,
  v5ModelOptions: Object.freeze({
    lambda: 1,
    lowerQuantile: 0.10,
    k: 40,
    minNeighbors: 20,
  }),
  roundTripCostPct: 0.05,
  incrementalCostPct: 0,
  evaluationHorizons: Object.freeze([1, 3, 6]),
  outerOosReadAllowed: false,
  outerOosEvaluationAllowed: false,
  validationRetuningAllowed: false,
  resultBasedRetuningAllowed: false,
  automaticPromotionAllowed: false,
});

export const PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_CONTRACT = Object.freeze({
  selectorPolicyId: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.entrySelector,
  entryPolicyId: 'P21_FROZEN_ENTRY_AT_FINALIZED_CLOSE',
  marketDataPolicyId: `P24_9_CANONICAL_BYTE_SNAPSHOT_${PHASE57_P25_2K_POLICY.canonicalSnapshotSha256}`,
  transactionCostPolicyId: 'ROUND_TRIP_0.05PCT_INCREMENTAL_DIFFERENTIAL_0PCT',
  capitalAllocationPolicyId: 'P25_FROZEN_CAPITAL_ALLOCATION_ASSUMPTIONS',
});

export const PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_SAFETY = Object.freeze({
  phase: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.phase,
  mode: 'PRE_CUTOFF_DEVELOPMENT_VALIDATION_RESEARCH_ONLY',
  researchOnly: true,
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  transmitted: false,
  freshHoldoutConsumed: false,
});

function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

export function hashExitV5DevelopmentValidationObject(value) {
  return crypto.createHash('sha256').update(canonicalJson(value)).digest('hex');
}

function normalizeBar(bar, label) {
  const timestampMs = Date.parse(bar?.timestamp ?? bar?.time ?? '');
  if (!Number.isFinite(timestampMs)) throw new Error(`${label}.timestamp is invalid`);
  const values = Object.fromEntries(['open', 'high', 'low', 'close', 'volume'].map((key) => [key, Number(bar?.[key] ?? (key === 'volume' ? 0 : NaN))]));
  if (![values.open, values.high, values.low, values.close, values.volume].every(Number.isFinite)) throw new Error(`${label} must be finite OHLCV`);
  if (Math.min(values.open, values.high, values.low, values.close) <= 0 || values.volume < 0) throw new Error(`${label} has invalid OHLCV`);
  if (values.high < Math.max(values.open, values.close, values.low) || values.low > Math.min(values.open, values.close, values.high)) {
    throw new Error(`${label} has inconsistent OHLC`);
  }
  return Object.freeze({ timestamp: new Date(timestampMs).toISOString(), ...values });
}

function normalizeSession(session, index) {
  const symbol = String(session?.symbol ?? '').trim().toUpperCase();
  const sessionDate = String(session?.sessionDate ?? '');
  if (!symbol || !/^\d{4}-\d{2}-\d{2}$/.test(sessionDate)) throw new Error(`historicalSessions[${index}] identity is invalid`);
  const bars5m = Object.freeze((session?.bars5m ?? []).map((bar, barIndex) => normalizeBar(bar, `historicalSessions[${index}].bars5m[${barIndex}]`)));
  if (bars5m.length < 30) throw new Error(`historicalSessions[${index}] has fewer than 30 bars`);
  for (let barIndex = 1; barIndex < bars5m.length; barIndex += 1) {
    if (bars5m[barIndex].timestamp <= bars5m[barIndex - 1].timestamp) throw new Error(`historicalSessions[${index}] bars are not strictly chronological`);
  }
  return Object.freeze({ symbol, sessionDate, bars5m });
}

function sortedUnique(values) {
  return [...new Set(values.map(String))].sort();
}

function sameArray(left, right) {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

export function assertExitV5CanonicalHistoryPack(historyPack) {
  if (historyPack?.status !== 'P25_2_PINNED_HISTORY_PACK_READY') throw new Error('canonical P25 pinned history pack is required');
  if (Number(historyPack.canonicalSourceRunId) !== PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.sourceRunId) throw new Error('canonical source run mismatch');
  if (historyPack.canonicalSnapshotSha256 !== PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.sourceSnapshotSha256) throw new Error('canonical snapshot SHA-256 mismatch');
  if (Number(historyPack.sessionCount) !== PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.expectedHistorySessionCount) throw new Error('canonical history session count mismatch');
  const sessions = (historyPack.sessions ?? []).map(normalizeSession);
  if (sessions.length !== historyPack.sessionCount) throw new Error('canonical history sessions are incomplete');
  const symbols = sortedUnique(sessions.map((session) => session.symbol));
  const expectedSymbols = [...PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.historicalUniverse].sort();
  if (!sameArray(symbols, expectedSymbols)) throw new Error('canonical history universe mismatch');
  const dates = sortedUnique(sessions.map((session) => session.sessionDate));
  if (dates.length !== PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.expectedDistinctSessionDates) throw new Error('canonical distinct session-date count mismatch');
  if (dates.at(-1) !== PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.validationEndDate) throw new Error('canonical history end-date mismatch');
  if (sessions.some((session) => session.sessionDate > PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.validationEndDate)) throw new Error('post-validation data contamination');
  for (const key of SAFETY_FALSE_KEYS) {
    if (historyPack?.safety?.[key] !== false) throw new Error(`canonical history safety violation: ${key}`);
  }
  return Object.freeze({ sessions: Object.freeze(sessions), symbols: Object.freeze(symbols), dates: Object.freeze(dates) });
}

function buildP21FeatureRows(symbol, sessionDate, bars, enriched, baseRows) {
  const index = new Map(bars.map((bar, i) => [bar.timestamp, i]));
  const enrichedByTime = new Map(enriched.map((bar) => [new Date(bar.timestamp).toISOString(), bar]));
  const openingPrice = Number(bars[0]?.open) || 0;
  return baseRows.flatMap((row) => {
    const timestamp = new Date(row.featureCutoff).toISOString();
    const i = index.get(timestamp);
    const current = i === undefined ? null : bars[i];
    const enrichedBar = enrichedByTime.get(timestamp);
    if (!current || !enrichedBar) return [];
    const previous = i > 0 ? bars[i - 1] : current;
    const priorVolumes = bars.slice(Math.max(0, i - 5), i).map((bar) => Number(bar.volume) || 0);
    const averageVolume = priorVolumes.length ? priorVolumes.reduce((sum, value) => sum + value, 0) / priorVolumes.length : 0;
    return [Object.freeze({
      symbol,
      sessionDate,
      featureCutoff: timestamp,
      features: Object.freeze({
        returnFromOpen: openingPrice ? (Number(current.close) / openingPrice - 1) * 100 : 0,
        rangePosition: Number(current.high) > Number(current.low)
          ? (Number(current.close) - Number(current.low)) / (Number(current.high) - Number(current.low))
          : 0.5,
        shortMomentum: Number(previous.close) ? (Number(current.close) / Number(previous.close) - 1) * 100 : 0,
        relativeVolume: averageVolume > 0 ? (Number(current.volume) || 0) / averageVolume : 1,
        ...(enrichedBar.multiFactor ?? {}),
      }),
    })];
  });
}

export function buildExitV5P21ReplayInputs(historicalSessions) {
  const horizons = [1, 3, 6, 12, 24];
  const datasets = Object.fromEntries(horizons.map((horizon) => [horizon, []]));
  const normalizedSessions = (historicalSessions ?? []).map(normalizeSession);
  for (const session of normalizedSessions) {
    const enriched = enrichHistoricalIntradayBars(session.bars5m);
    const baseRows = buildMultiHorizonMagnitudeRows({
      symbol: session.symbol,
      sessionDate: session.sessionDate,
      bars: session.bars5m,
      horizons,
    });
    const featureRows = buildP21FeatureRows(session.symbol, session.sessionDate, session.bars5m, enriched, baseRows);
    const built = buildIntradayHorizonDatasets(baseRows, { horizons, featureRows });
    for (const horizon of horizons) datasets[horizon].push(...built[horizon]);
  }
  for (const horizon of horizons) datasets[horizon].sort((left, right) => left.featureCutoff.localeCompare(right.featureCutoff));
  return Object.freeze({
    horizons: Object.freeze(horizons),
    datasets: Object.freeze(Object.fromEntries(horizons.map((horizon) => [horizon, Object.freeze(datasets[horizon])]))),
    sessions: Object.freeze(normalizedSessions),
  });
}

function jstTimeBucket(timestamp) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Tokyo',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(new Date(timestamp)).map((part) => [part.type, part.value]));
  const minutes = Number(parts.hour) * 60 + Number(parts.minute);
  if (minutes < 600) return '09:00-09:59';
  if (minutes < 690) return '10:00-11:29';
  if (minutes < 840) return '11:30-13:59';
  return '14:00-15:30';
}

function entryIdentity(row) {
  return Object.freeze({
    symbol: row.symbol,
    sessionDate: row.sessionDate,
    entryTimestamp: row.entryTimestamp,
    entryPrice: row.entryPrice,
    signalDirection: row.signalDirection,
    setup: row.setup,
    selectedModelType: row.selectedModelType,
    selectedConfigId: row.selectedConfigId,
    selectedThreshold: row.selectedThreshold,
    baseHorizonBars: row.baseHorizonBars,
    selectorPolicyId: row.selectorPolicyId,
    entryPolicyId: row.entryPolicyId,
  });
}

export function buildExitV5FrozenRowsFromP21Replay({ historicalSessions, replay }) {
  if (replay?.selectionIntegrity?.outerTestNeverUsedForSelection !== true || replay?.selectionIntegrity?.outerTestNeverUsedForFit !== true) {
    throw new Error('P21 replay must keep outer Entry rows untouched by selection and fit');
  }
  const sessions = (historicalSessions ?? []).map(normalizeSession);
  const store = new Map(sessions.map((session) => [`${session.symbol}|${session.sessionDate}`, {
    bars: session.bars5m,
    index: new Map(session.bars5m.map((bar, index) => [bar.timestamp, index])),
  }]));
  const rows = (replay?.signals ?? []).map((signal, signalIndex) => {
    if (signal?.signalPointInTimeValid !== true || signal?.selectionSource !== 'P21_1_OUTER_OOS_REPLAY') {
      throw new Error(`P21 signal ${signalIndex} lacks point-in-time Entry attestation`);
    }
    const symbol = String(signal.symbol ?? '').trim().toUpperCase();
    const sessionDate = String(signal.sessionDate ?? '');
    const entryTimestamp = new Date(Date.parse(signal.featureCutoff ?? '')).toISOString();
    const state = store.get(`${symbol}|${sessionDate}`);
    const index = state?.index.get(entryTimestamp);
    if (!state || index === undefined) throw new Error(`P21 signal ${signalIndex} entry bar is missing`);
    if (signal.direction !== 1 && signal.direction !== 0) throw new Error(`P21 signal ${signalIndex} direction is invalid`);
    const signalDirection = signal.direction === 1 ? 'LONG' : 'SHORT';
    const contextBars = Object.freeze(state.bars.slice(Math.max(0, index - 12), index + 1));
    const futureBars = Object.freeze(state.bars.slice(index + 1));
    if (!futureBars.length || futureBars[0].timestamp <= entryTimestamp) throw new Error(`P21 signal ${signalIndex} future path is invalid`);
    return Object.freeze({
      entryAccepted: true,
      frozenBeforeOutcome: true,
      currentOutcomeUsed: false,
      symbol,
      sessionDate,
      entryTimestamp,
      entryPrice: Number(state.bars[index].close),
      signalDirection,
      direction: signalDirection,
      setup: String(signal.selectedFeatureFamily ?? 'UNKNOWN'),
      selectedModelType: String(signal.selectedModelType ?? 'UNKNOWN'),
      selectedConfigId: String(signal.selectedConfigId ?? 'UNKNOWN'),
      selectedThreshold: Number(signal.selectedThreshold),
      baseHorizonBars: Number(signal.horizonBars),
      timeOfDayBucket: jstTimeBucket(entryTimestamp),
      sector: 'UNKNOWN',
      contextBars,
      futureBars,
      pointInTimeValid: true,
      signalPointInTimeValid: true,
      selectionSource: signal.selectionSource,
      outcomePending: true,
      ...PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_CONTRACT,
    });
  }).sort((left, right) => left.entryTimestamp.localeCompare(right.entryTimestamp)
    || left.symbol.localeCompare(right.symbol)
    || left.signalDirection.localeCompare(right.signalDirection));

  const keys = rows.map((row) => `${row.sessionDate}|${row.entryTimestamp}|${row.symbol}|${row.signalDirection}`);
  if (new Set(keys).size !== keys.length) throw new Error('duplicate P21 Frozen Entry identity');
  return Object.freeze(rows);
}

function countsByDate(rows) {
  const counts = {};
  for (const row of rows) counts[row.sessionDate] = Number(counts[row.sessionDate] ?? 0) + 1;
  return Object.freeze(Object.fromEntries(Object.entries(counts).sort(([left], [right]) => left.localeCompare(right))));
}

function assertExpectedCounts(rows) {
  const developmentRows = rows.filter((row) => row.sessionDate <= PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.developmentEndDate);
  const validationRows = rows.filter((row) => row.sessionDate >= PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.validationStartDate
    && row.sessionDate <= PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.validationEndDate);
  if (rows.length !== PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.expectedFrozenEntryCount) throw new Error('Frozen Entry count drift');
  if (developmentRows.length !== PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.expectedDevelopmentEntryCount) throw new Error('development Entry count drift');
  if (validationRows.length !== PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.expectedValidationEntryCount) throw new Error('validation Entry count drift');
  const actualValidationCounts = countsByDate(validationRows);
  if (canonicalJson(actualValidationCounts) !== canonicalJson(EXPECTED_VALIDATION_COUNTS)) throw new Error('validation Entry date/count drift');
  return Object.freeze({ developmentRows: Object.freeze(developmentRows), validationRows: Object.freeze(validationRows), actualValidationCounts });
}

export function buildExitV5DevelopmentValidationSplit(frozenRows) {
  const samples = buildExitV5TrainingSamplesFromFrozenRows(frozenRows);
  const split = buildPurgedExitV5Split(samples, {
    developmentEnd: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.developmentEnd,
    validationEnd: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.validationEnd,
    oosEnd: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.oosEnd,
  });
  return Object.freeze({ samples, split });
}

export function prepareExitV5DevelopmentValidationSubstrate(historyPack) {
  assertExitV5DevelopmentValidationSafety();
  const canonical = assertExitV5CanonicalHistoryPack(historyPack);
  const inputs = buildExitV5P21ReplayInputs(canonical.sessions);
  const replay = replayNestedAdaptiveOosSignals(inputs.datasets, PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.p21Options);
  if (replay.status !== 'ADAPTIVE_OUTER_OOS_SIGNALS_REPLAYED') throw new Error(`P21 Frozen Entry replay blocked: ${replay.status}`);
  const frozenRows = buildExitV5FrozenRowsFromP21Replay({ historicalSessions: inputs.sessions, replay });
  const entryCounts = assertExpectedCounts(frozenRows);
  if (Math.min(...frozenRows.map((row) => row.futureBars.length)) < 24) throw new Error('Frozen Entry future-path coverage drift');
  const { samples, split } = buildExitV5DevelopmentValidationSplit(frozenRows);
  if (split.development.length !== PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.expectedDevelopmentSampleCount) throw new Error('development state-sample count drift');
  if (split.validation.length !== PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.expectedValidationSampleCount) throw new Error('validation state-sample count drift');
  if (split.purged.length || split.oos.length || split.prospective.length) throw new Error('pre-cutoff substrate crossed a split boundary');

  const entrySetFingerprint = hashExitV5DevelopmentValidationObject(frozenRows.map(entryIdentity));
  const marketDataFingerprint = hashExitV5DevelopmentValidationObject(frozenRows.map((row) => ({
    key: `${row.sessionDate}|${row.entryTimestamp}|${row.symbol}|${row.signalDirection}`,
    contextBars: row.contextBars,
    futureBars: row.futureBars,
  })));
  const pairedSubstrateFingerprint = hashExitV5DevelopmentValidationObject({
    phase: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.phase,
    entrySetFingerprint,
    marketDataFingerprint,
    frozenRows,
  });
  if (entrySetFingerprint !== PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.expectedEntrySetFingerprint) throw new Error('Frozen Entry fingerprint drift');
  if (marketDataFingerprint !== PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.expectedMarketDataFingerprint) throw new Error('paired market-data fingerprint drift');
  if (pairedSubstrateFingerprint !== PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.expectedPairedSubstrateFingerprint) throw new Error('paired substrate fingerprint drift');

  return Object.freeze({
    schemaVersion: 1,
    phase: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.phase,
    status: 'EXIT_V5_DEVELOPMENT_VALIDATION_SUBSTRATE_READY',
    source: Object.freeze({
      runId: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.sourceRunId,
      artifactName: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.sourceArtifactName,
      snapshotSha256: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.sourceSnapshotSha256,
      dataEndIso: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.sourceDataEndIso,
    }),
    entrySetFingerprint,
    marketDataFingerprint,
    pairedSubstrateFingerprint,
    frozenEntryCount: frozenRows.length,
    developmentEntryCount: entryCounts.developmentRows.length,
    validationEntryCount: entryCounts.validationRows.length,
    validationCountsByDate: entryCounts.actualValidationCounts,
    stateSampleAudit: Object.freeze({
      all: samples.length,
      development: split.development.length,
      validation: split.validation.length,
      purged: split.purged.length,
      oos: split.oos.length,
      prospective: split.prospective.length,
      splitPolicy: split.splitPolicy,
      boundaries: split.boundaries,
    }),
    p21ReplayAudit: Object.freeze({
      status: replay.status,
      signalCount: replay.signalCount,
      outerFoldCount: replay.outerFoldCount,
      selectionIntegrity: replay.selectionIntegrity,
      outerResults: Object.freeze(replay.outerResults.map((fold) => Object.freeze({
        fold: fold.fold,
        status: fold.status,
        trainCutoff: fold.trainCutoff ?? null,
        testStart: fold.testStart ?? null,
        testEnd: fold.testEnd ?? null,
        selectedHorizonBars: fold.selectedHorizonBars ?? null,
        selectedFeatureFamily: fold.selectedFeatureFamily ?? null,
        selectedModelType: fold.selectedModelType ?? null,
        selectedConfigId: fold.selectedConfigId ?? null,
        selectedThreshold: fold.selectedThreshold ?? null,
        signalCount: fold.signalCount ?? 0,
        outerUntouchedBySelection: fold.outerUntouchedBySelection === true,
        outerNeverUsedForFit: fold.outerNeverUsedForFit === true,
      }))),
    }),
    frozenRows,
    methodology: Object.freeze({
      p21SelectorReplayFrozenBeforeExitV5Evaluation: true,
      p21OuterRowsNeverUsedForEntryFitOrSelection: true,
      entryIdentityExcludesFutureBars: true,
      futureBarsRole: 'V5_LABELS_AND_SEQUENTIAL_PAIRED_EXIT_EVALUATION_ONLY',
      exactCanonicalMarketDataOnly: true,
      randomSplit: false,
      sessionAwareSplit: true,
      entireBoundarySessionPurged: true,
      outerOosRead: false,
      outerOosEvaluation: false,
      prospectiveEvaluation: false,
      resultBasedRetuning: false,
    }),
    pairedContract: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_CONTRACT,
    safety: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_SAFETY,
  });
}

export function assertExitV5DevelopmentValidationSubstrate(substrate) {
  if (substrate?.phase !== PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.phase || substrate?.status !== 'EXIT_V5_DEVELOPMENT_VALIDATION_SUBSTRATE_READY') {
    throw new Error('EXIT v5 development/validation substrate is invalid');
  }
  const rows = substrate.frozenRows ?? [];
  assertExpectedCounts(rows);
  const entryFingerprint = hashExitV5DevelopmentValidationObject(rows.map(entryIdentity));
  const marketFingerprint = hashExitV5DevelopmentValidationObject(rows.map((row) => ({
    key: `${row.sessionDate}|${row.entryTimestamp}|${row.symbol}|${row.signalDirection}`,
    contextBars: row.contextBars,
    futureBars: row.futureBars,
  })));
  if (entryFingerprint !== substrate.entrySetFingerprint || marketFingerprint !== substrate.marketDataFingerprint) throw new Error('EXIT v5 substrate fingerprint mismatch');
  if (entryFingerprint !== PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.expectedEntrySetFingerprint
    || marketFingerprint !== PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.expectedMarketDataFingerprint) {
    throw new Error('EXIT v5 substrate does not match the precommitted Frozen Entry and market-data fingerprints');
  }
  const fullFingerprint = hashExitV5DevelopmentValidationObject({
    phase: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.phase,
    entrySetFingerprint: entryFingerprint,
    marketDataFingerprint: marketFingerprint,
    frozenRows: rows,
  });
  if (fullFingerprint !== substrate.pairedSubstrateFingerprint) throw new Error('EXIT v5 full substrate fingerprint mismatch');
  if (fullFingerprint !== PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.expectedPairedSubstrateFingerprint) throw new Error('EXIT v5 substrate precommitment mismatch');
  if (canonicalJson(substrate.pairedContract) !== canonicalJson(PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_CONTRACT)) throw new Error('EXIT v5 paired contract drift');
  for (const key of SAFETY_FALSE_KEYS) if (substrate?.safety?.[key] !== false) throw new Error(`EXIT v5 substrate safety violation: ${key}`);
  return true;
}

export function fitExitV5DevelopmentModelsFromSubstrate(substrate) {
  assertExitV5DevelopmentValidationSubstrate(substrate);
  const { samples, split } = buildExitV5DevelopmentValidationSplit(substrate.frozenRows);
  if (split.development.length !== PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.expectedDevelopmentSampleCount) throw new Error('development sample count mismatch');
  const fittedModels = fitExitV5PairedModelsFromPurgedSplit(split, PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.v5ModelOptions);
  return Object.freeze({ samples, split, fittedModels });
}

export function runExitV5DevelopmentValidationShard({ historyPack, substrate, validationSessionDate }) {
  assertExitV5DevelopmentValidationSafety();
  const canonical = assertExitV5CanonicalHistoryPack(historyPack);
  assertExitV5DevelopmentValidationSubstrate(substrate);
  const sessionDate = String(validationSessionDate ?? '');
  const expectedCount = EXPECTED_VALIDATION_COUNTS[sessionDate];
  if (!Number.isInteger(expectedCount)) throw new Error('validationSessionDate is not a frozen Validation session');
  const evaluationRows = substrate.frozenRows.filter((row) => row.sessionDate === sessionDate);
  if (evaluationRows.length !== expectedCount) throw new Error('validation shard Frozen Entry count mismatch');
  const { split, fittedModels } = fitExitV5DevelopmentModelsFromSubstrate(substrate);
  const analogPool = buildP25DataDrivenExitAnalogPool({ historicalSessions: canonical.sessions })
    .filter((row) => String(row.sessionDate) < sessionDate);
  if (!analogPool.length || analogPool.some((row) => String(row.sessionDate) >= sessionDate)) throw new Error('causal analog shard pruning failed');
  const evaluation = runExitV5AuditedSplitPairedEvaluation({
    evaluationRows,
    purgedSplit: split,
    analogPool,
    fittedModels,
    splitName: 'validation',
    pairedContract: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_CONTRACT,
    roundTripCostPct: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.roundTripCostPct,
    incrementalCostPct: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.incrementalCostPct,
    evaluationHorizons: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.evaluationHorizons,
  });
  return Object.freeze({
    schemaVersion: 1,
    phase: '57.exit-v5.development-validation.shard.v1',
    status: 'EXIT_V5_VALIDATION_SHARD_EVALUATED',
    splitName: 'validation',
    sessionDate,
    pairedCount: evaluation.pairedCount,
    validationStateSampleCount: split.validation.filter((sample) => sample.provenance?.sessionDate === sessionDate).length,
    causalAnalogCount: analogPool.length,
    entrySetFingerprint: substrate.entrySetFingerprint,
    marketDataFingerprint: substrate.marketDataFingerprint,
    pairedSubstrateFingerprint: substrate.pairedSubstrateFingerprint,
    developmentFingerprint: fittedModels.developmentFingerprint,
    developmentSampleCount: fittedModels.sampleCount,
    pairedContract: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_CONTRACT,
    evaluation,
    classification: Object.freeze({
      developmentOrValidationOnly: true,
      formalOos: false,
      prospective: false,
      promotionEligible: false,
    }),
    methodology: Object.freeze({
      analogPoolPrunedToPriorSessionsOnly: true,
      analogPruningChangesBaselineDecision: false,
      strictAuditedSplitEntrypoint: true,
      v5FitSplit: 'development',
      v5RefitOnValidation: false,
      outerOosRead: false,
      outerOosRetuning: false,
      prospectiveRetuning: false,
      resultBasedRetuning: false,
    }),
    safety: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_SAFETY,
  });
}

export function reduceExitV5DevelopmentValidationShards(shards) {
  assertExitV5DevelopmentValidationSafety();
  if (!Array.isArray(shards) || !shards.length) throw new Error('validation shards are required');
  const ordered = [...shards].sort((left, right) => String(left?.sessionDate).localeCompare(String(right?.sessionDate)));
  const expectedDates = Object.keys(EXPECTED_VALIDATION_COUNTS);
  if (!sameArray(ordered.map((shard) => String(shard?.sessionDate)), expectedDates)) throw new Error('validation shard session lineage mismatch');
  const first = ordered[0];
  const pairs = [];
  for (const shard of ordered) {
    if (shard?.status !== 'EXIT_V5_VALIDATION_SHARD_EVALUATED' || shard?.splitName !== 'validation') throw new Error('invalid validation shard status');
    if (Number(shard.pairedCount) !== EXPECTED_VALIDATION_COUNTS[shard.sessionDate]) throw new Error(`validation shard pair count mismatch: ${shard.sessionDate}`);
    for (const key of ['entrySetFingerprint', 'marketDataFingerprint', 'pairedSubstrateFingerprint', 'developmentFingerprint']) {
      if (shard[key] !== first[key]) throw new Error(`validation shard ${key} mismatch`);
    }
    if (canonicalJson(shard.pairedContract) !== canonicalJson(PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_CONTRACT)) throw new Error('validation shard paired contract mismatch');
    const splitAudit = shard?.evaluation?.splitAudit;
    if (splitAudit?.status !== 'EXIT_V5_AUDITED_SPLIT_ROWS_CONFIRMED'
      || splitAudit?.splitName !== 'validation'
      || Number(splitAudit?.rowCount) !== Number(shard.pairedCount)
      || splitAudit?.fullTradeTrajectoryContained !== true
      || splitAudit?.purgedBoundarySessionsExcluded !== true
      || shard?.evaluation?.methodology?.exactOuterSplitMembershipEnforced !== true) {
      throw new Error(`validation shard audited split evidence mismatch: ${shard.sessionDate}`);
    }
    for (const key of SAFETY_FALSE_KEYS) if (shard?.safety?.[key] !== false) throw new Error(`validation shard safety violation: ${key}`);
    pairs.push(...(shard?.evaluation?.pairs ?? []));
  }
  pairs.sort((left, right) => left.invariant.entryTimestamp.localeCompare(right.invariant.entryTimestamp) || left.pairKey.localeCompare(right.pairKey));
  if (pairs.length !== PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.expectedValidationEntryCount) throw new Error('combined Validation pair count mismatch');
  const summary = summarizeExitV5FourWayPairs(pairs);
  return Object.freeze({
    schemaVersion: 1,
    phase: '57.exit-v5.development-validation.combined.v1',
    status: 'EXIT_V5_DEVELOPMENT_VALIDATION_EVIDENCE_READY',
    splitName: 'validation',
    sessionDates: Object.freeze(expectedDates),
    pairedCount: pairs.length,
    comparisonModels: PHASE57_EXIT_V5_PAIRED_MODEL_IDS,
    entrySetFingerprint: first.entrySetFingerprint,
    marketDataFingerprint: first.marketDataFingerprint,
    pairedSubstrateFingerprint: first.pairedSubstrateFingerprint,
    developmentFingerprint: first.developmentFingerprint,
    developmentSampleCount: first.developmentSampleCount,
    pairedContract: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_CONTRACT,
    pairs: Object.freeze(pairs),
    summary,
    classification: Object.freeze({
      developmentOrValidationOnly: true,
      formalOos: false,
      prospective: false,
      promotionEligible: false,
      performanceConclusion: 'VALIDATION_RESEARCH_EVIDENCE_ONLY',
    }),
    methodology: Object.freeze({
      completeFrozenValidationLineage: true,
      exactSameFrozenInputForAllFourModels: true,
      strictOuterSplitMembershipEnforced: true,
      fullTradeTrajectoryContainedInValidation: true,
      purgedBoundarySessionsExcluded: true,
      developmentOnlyV5Fit: true,
      validationRefit: false,
      outerOosRead: false,
      outerOosEvaluation: false,
      outerOosRetuning: false,
      prospectiveEvaluation: false,
      prospectiveRetuning: false,
      resultBasedRetuning: false,
      bestResultOnlyReporting: false,
      automaticPromotion: false,
    }),
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
    safety: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_SAFETY,
  });
}

export function assertExitV5DevelopmentValidationSafety() {
  for (const key of SAFETY_FALSE_KEYS) {
    if (PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_SAFETY[key] !== false) throw new Error(`EXIT v5 development/validation safety violation: ${key}`);
  }
  if (PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_SAFETY.researchOnly !== true) throw new Error('EXIT v5 development/validation must remain research-only');
  if (PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.outerOosReadAllowed !== false
    || PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.outerOosEvaluationAllowed !== false
    || PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY.automaticPromotionAllowed !== false) {
    throw new Error('EXIT v5 development/validation policy boundary violation');
  }
  return true;
}

export default {
  PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_POLICY,
  PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_CONTRACT,
  PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_SAFETY,
  assertExitV5CanonicalHistoryPack,
  assertExitV5DevelopmentValidationSafety,
  assertExitV5DevelopmentValidationSubstrate,
  buildExitV5P21ReplayInputs,
  buildExitV5FrozenRowsFromP21Replay,
  buildExitV5DevelopmentValidationSplit,
  prepareExitV5DevelopmentValidationSubstrate,
  fitExitV5DevelopmentModelsFromSubstrate,
  runExitV5DevelopmentValidationShard,
  reduceExitV5DevelopmentValidationShards,
};
