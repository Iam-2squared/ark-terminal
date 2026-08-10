import { findIntradayHistoricalAnalogs } from './phase57-intraday-historical-analog.js';

export const PHASE57_P23_1_SAFETY = Object.freeze({
  mode: 'PHASE57_INTRADAY_ANALOG_OOS_READ_ONLY_RESEARCH',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  overnightHoldingAllowed: false,
  humanApprovalRequired: true,
});

const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const mean = values => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;

function median(values) {
  if (!values.length) return null;
  const sorted = values.slice().sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function normalizedRows(rows = []) {
  return (Array.isArray(rows) ? rows : [])
    .filter(row => row && typeof row === 'object' && row.sessionDate && row.featureCutoff && row.outcomeAt && finite(row.actualReturnPct))
    .slice()
    .sort((a, b) => String(a.featureCutoff).localeCompare(String(b.featureCutoff)) || String(a.id ?? '').localeCompare(String(b.id ?? '')));
}

export function buildSessionWalkForwardFolds(rows = [], {
  initialTrainFraction = 0.6,
  testFraction = 0.1,
  minimumTrainSessions = 20,
} = {}) {
  const ordered = normalizedRows(rows);
  const sessions = [...new Set(ordered.map(row => String(row.sessionDate)))].sort();
  if (sessions.length < Math.max(2, minimumTrainSessions + 1)) return Object.freeze([]);
  const initialTrain = Math.max(minimumTrainSessions, Math.floor(sessions.length * Number(initialTrainFraction || 0.6)));
  const testSize = Math.max(1, Math.floor(sessions.length * Number(testFraction || 0.1)));
  const folds = [];
  let trainEnd = initialTrain;
  let fold = 0;
  while (trainEnd < sessions.length) {
    const testEnd = Math.min(sessions.length, trainEnd + testSize);
    const trainSessions = sessions.slice(0, trainEnd);
    const testSessions = sessions.slice(trainEnd, testEnd);
    if (!testSessions.length) break;
    const trainSet = new Set(trainSessions);
    const testSet = new Set(testSessions);
    const trainRows = ordered.filter(row => trainSet.has(String(row.sessionDate)));
    const testRows = ordered.filter(row => testSet.has(String(row.sessionDate)));
    folds.push(Object.freeze({
      fold,
      trainSessionStart: trainSessions[0],
      trainSessionEnd: trainSessions.at(-1),
      testSessionStart: testSessions[0],
      testSessionEnd: testSessions.at(-1),
      trainSessionCount: trainSessions.length,
      testSessionCount: testSessions.length,
      trainRows: Object.freeze(trainRows),
      testRows: Object.freeze(testRows),
    }));
    trainEnd = testEnd;
    fold += 1;
  }
  return Object.freeze(folds);
}

function summarizeSignals(signals = []) {
  const rows = signals.filter(row => finite(row.netReturnPct));
  const nets = rows.map(row => Number(row.netReturnPct));
  const gross = rows.map(row => Number(row.grossAlignedReturnPct)).filter(Number.isFinite);
  const positive = nets.filter(value => value > 0).reduce((sum, value) => sum + value, 0);
  const negative = -nets.filter(value => value < 0).reduce((sum, value) => sum + value, 0);
  let equity = 0;
  let peak = 0;
  let maxDrawdownPct = 0;
  for (const value of nets) {
    equity += value;
    peak = Math.max(peak, equity);
    maxDrawdownPct = Math.max(maxDrawdownPct, peak - equity);
  }
  return Object.freeze({
    signalCount: rows.length,
    directionalHitRate: rows.length ? rows.filter(row => row.directionCorrect).length / rows.length : null,
    positiveNetRate: rows.length ? rows.filter(row => Number(row.netReturnPct) > 0).length / rows.length : null,
    grossAverageReturnPct: gross.length ? mean(gross) : null,
    netAverageReturnPct: nets.length ? mean(nets) : null,
    medianNetReturnPct: nets.length ? median(nets) : null,
    profitFactor: negative > 0 ? positive / negative : positive > 0 ? Infinity : null,
    maxDrawdownPct,
  });
}

function baselineDirection(trainRows) {
  const returns = trainRows.map(row => Number(row.actualReturnPct)).filter(Number.isFinite);
  const expected = mean(returns);
  if (!finite(expected)) return 1;
  return Number(expected) >= 0 ? 1 : -1;
}

function brierAccumulator(thresholds) {
  return Object.fromEntries(thresholds.map(threshold => [String(threshold), { sum: 0, count: 0 }]));
}

function finishBrier(accumulator) {
  return Object.fromEntries(Object.entries(accumulator).map(([key, value]) => [key, value.count ? value.sum / value.count : null]));
}

export function evaluateIntradayAnalogOos(rows = [], {
  featureKeys,
  featureWeights = {},
  topK = 25,
  minimumAnalogs = 20,
  minFeatureFraction = 0.8,
  roundTripCostPct = 0.05,
  minimumExpectedNetPct = 0,
  contextPenalties = {},
  sameSymbolOnly = true,
  excludeCurrentSession = true,
  moveThresholdsPct = [0.5, 1, 2, 3],
  initialTrainFraction = 0.6,
  testFraction = 0.1,
  minimumTrainSessions = 20,
} = {}) {
  const ordered = normalizedRows(rows);
  const horizons = [...new Set(ordered.map(row => Number(row.horizonBars)).filter(Number.isFinite))];
  if (horizons.length !== 1) throw new Error('P23.1 evaluator requires exactly one predeclared horizon per evaluation');
  const horizonBars = horizons[0];
  const folds = buildSessionWalkForwardFolds(ordered, { initialTrainFraction, testFraction, minimumTrainSessions });
  const allSignals = [];
  const matchedBaselineSignals = [];
  const foldResults = [];
  const predictionFingerprint = [];
  const brier = brierAccumulator(moveThresholdsPct);
  let readyQueries = 0;
  let returnAbsoluteErrorSum = 0;
  let returnAbsoluteErrorCount = 0;

  for (const fold of folds) {
    const foldSignals = [];
    const foldBaselineSignals = [];
    let foldReady = 0;
    const baseline = baselineDirection(fold.trainRows);
    const trainLastOutcomeAt = fold.trainRows.reduce((latest, row) => Math.max(latest, Date.parse(row.outcomeAt)), -Infinity);
    const testFirstFeatureCutoff = fold.testRows.reduce((earliest, row) => Math.min(earliest, Date.parse(row.featureCutoff)), Infinity);
    if (trainLastOutcomeAt > testFirstFeatureCutoff) throw new Error(`fold ${fold.fold} train outcome crosses outer test feature cutoff`);

    for (const row of fold.testRows) {
      const result = findIntradayHistoricalAnalogs({
        query: {
          symbol: row.symbol,
          sessionDate: row.sessionDate,
          asOf: row.featureCutoff,
          featureCutoff: row.featureCutoff,
          horizonBars,
          features: row.features,
          context: row.context ?? {},
        },
        candidates: fold.trainRows,
        featureKeys,
        featureWeights,
        topK,
        minimumAnalogs,
        minFeatureFraction,
        excludeCurrentSession,
        sameSymbolOnly,
        contextPenalties,
        roundTripCostPct,
      });
      if (result.status !== 'INTRADAY_ANALOGS_READY') continue;
      foldReady += 1;
      readyQueries += 1;
      const summary = result.summary;
      const predictedReturn = Number(summary.weightedMeanReturnPct);
      if (Number.isFinite(predictedReturn)) {
        returnAbsoluteErrorSum += Math.abs(predictedReturn - Number(row.actualReturnPct));
        returnAbsoluteErrorCount += 1;
      }
      for (const threshold of moveThresholdsPct) {
        const key = String(threshold);
        const probability = Number(summary.moveProbabilityByThresholdPct?.[key]);
        if (!Number.isFinite(probability)) continue;
        const actual = Math.abs(Number(row.actualReturnPct)) >= Number(threshold) ? 1 : 0;
        brier[key].sum += (probability - actual) ** 2;
        brier[key].count += 1;
      }

      const netLong = Number(summary.expectedNetLongReturnPctAfterCost);
      const netShort = Number(summary.expectedNetShortReturnPctAfterCost);
      const direction = netLong >= netShort ? 1 : -1;
      const predictedNet = Math.max(netLong, netShort);
      predictionFingerprint.push(Object.freeze({
        fold: fold.fold,
        id: String(row.id ?? row.featureCutoff),
        direction,
        predictedNetReturnPct: Number.isFinite(predictedNet) ? predictedNet : null,
        analogIds: Object.freeze(result.analogs.map(analog => analog.id)),
      }));
      if (!Number.isFinite(predictedNet) || predictedNet <= Number(minimumExpectedNetPct)) continue;

      const actualReturn = Number(row.actualReturnPct);
      const grossAligned = direction === 1 ? actualReturn : -actualReturn;
      const netReturn = grossAligned - Number(roundTripCostPct);
      const signal = Object.freeze({
        fold: fold.fold,
        id: String(row.id ?? row.featureCutoff),
        featureCutoff: row.featureCutoff,
        sessionDate: row.sessionDate,
        direction,
        directionCorrect: direction === 1 ? actualReturn > 0 : actualReturn < 0,
        predictedNetReturnPct: predictedNet,
        grossAlignedReturnPct: grossAligned,
        netReturnPct: netReturn,
      });
      foldSignals.push(signal);
      allSignals.push(signal);

      const baselineGross = baseline === 1 ? actualReturn : -actualReturn;
      const baselineSignal = Object.freeze({
        ...signal,
        direction: baseline,
        directionCorrect: baseline === 1 ? actualReturn > 0 : actualReturn < 0,
        grossAlignedReturnPct: baselineGross,
        netReturnPct: baselineGross - Number(roundTripCostPct),
      });
      foldBaselineSignals.push(baselineSignal);
      matchedBaselineSignals.push(baselineSignal);
    }

    const analogMetrics = summarizeSignals(foldSignals);
    const baselineMetrics = summarizeSignals(foldBaselineSignals);
    foldResults.push(Object.freeze({
      fold: fold.fold,
      trainSessionStart: fold.trainSessionStart,
      trainSessionEnd: fold.trainSessionEnd,
      testSessionStart: fold.testSessionStart,
      testSessionEnd: fold.testSessionEnd,
      trainSessionCount: fold.trainSessionCount,
      testSessionCount: fold.testSessionCount,
      trainRowCount: fold.trainRows.length,
      testRowCount: fold.testRows.length,
      readyQueryCount: foldReady,
      baselineDirection: baseline,
      analog: analogMetrics,
      matchedUnconditionalBaseline: baselineMetrics,
      deltaMatchedNetAverageReturnPct: finite(analogMetrics.netAverageReturnPct) && finite(baselineMetrics.netAverageReturnPct)
        ? Number(analogMetrics.netAverageReturnPct) - Number(baselineMetrics.netAverageReturnPct)
        : null,
      outerOutcomesUsedForPrediction: false,
    }));
  }

  const metrics = summarizeSignals(allSignals);
  const baselineMetrics = summarizeSignals(matchedBaselineSignals);
  return Object.freeze({
    phase: '57.p23.1',
    status: folds.length ? 'INTRADAY_ANALOG_REAL_OOS_EVALUATED' : 'INSUFFICIENT_SESSIONS_FOR_OOS',
    horizonBars,
    rowCount: ordered.length,
    sessionCount: new Set(ordered.map(row => row.sessionDate)).size,
    outerFoldCount: folds.length,
    readyQueryCount: readyQueries,
    coverage: ordered.length ? readyQueries / ordered.length : 0,
    ...metrics,
    matchedUnconditionalBaseline: baselineMetrics,
    deltaMatchedNetAverageReturnPct: finite(metrics.netAverageReturnPct) && finite(baselineMetrics.netAverageReturnPct)
      ? Number(metrics.netAverageReturnPct) - Number(baselineMetrics.netAverageReturnPct)
      : null,
    expectedReturnMaePct: returnAbsoluteErrorCount ? returnAbsoluteErrorSum / returnAbsoluteErrorCount : null,
    magnitudeBrierByThresholdPct: Object.freeze(finishBrier(brier)),
    foldResults: Object.freeze(foldResults),
    predictionFingerprint: Object.freeze(predictionFingerprint),
    configuration: Object.freeze({
      topK,
      minimumAnalogs,
      minFeatureFraction,
      roundTripCostPct,
      minimumExpectedNetPct,
      contextPenalties: Object.freeze({ ...contextPenalties }),
      sameSymbolOnly,
      excludeCurrentSession,
      moveThresholdsPct: Object.freeze(moveThresholdsPct.slice()),
      initialTrainFraction,
      testFraction,
      minimumTrainSessions,
    }),
    selectionIntegrity: Object.freeze({
      horizonSelectedFromOuterOos: false,
      analogParametersSelectedFromOuterOos: false,
      outerOutcomesUsedForPrediction: false,
      candidatePoolRestrictedToPreOuterTrainingSessions: true,
      candidateOutcomesFullyRealizedBeforeOuterQueries: true,
      currentSessionExcluded: Boolean(excludeCurrentSession),
      postSelectionAcrossHorizonsAllowed: false,
      configFrozenBeforeOuterEvaluation: true,
    }),
    edgeClaimAllowed: false,
    recommendationAllowed: false,
    paperTradingAllowed: false,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    overnightHoldingAllowed: false,
    transmitted: false,
    safety: PHASE57_P23_1_SAFETY,
  });
}

export default { buildSessionWalkForwardFolds, evaluateIntradayAnalogOos };
