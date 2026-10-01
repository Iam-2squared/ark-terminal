export const PHASE57_P23_9A_SAFETY = Object.freeze({
  mode: 'PHASE57_ENTRY_OPPORTUNITY_HISTORICAL_RESEARCH_ONLY',
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

export const ENTRY_OPPORTUNITY_FEATURES = Object.freeze([
  'directionSign',
  'directionalReturnFromOpenPct',
  'directionalMomentum1Pct',
  'directionalMomentum3Pct',
  'rangePosition20Directional',
  'directionalVwapDistancePct',
  'directionalMa5DistancePct',
  'directionalMa5SlopePct',
  'directionalBreakoutDistancePct',
  'relativeVolume5',
  'atrPct10',
  'compression5to20',
  'directionalBodyStrength',
  'favorableWickRatio',
  'adverseWickRatio',
  'minutesFromOpenNormalized',
]);

const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const clamp = (value, lo, hi) => Math.max(lo, Math.min(hi, Number(value)));
const mean = values => values.length ? values.reduce((sum, value) => sum + Number(value), 0) / values.length : 0;

function signFromDirection(direction) {
  if (direction === 1 || direction === 'LONG' || direction === 'long') return 1;
  if (direction === 0 || direction === -1 || direction === 'SHORT' || direction === 'short') return -1;
  throw new Error(`unsupported direction: ${direction}`);
}

function normalizeBars(input = []) {
  return (Array.isArray(input) ? input : [])
    .map(bar => ({
      timestamp: new Date(bar.timestamp).toISOString(),
      open: Number(bar.open),
      high: Number(bar.high),
      low: Number(bar.low),
      close: Number(bar.close),
      volume: Number(bar.volume || 0),
      sessionDate: bar.sessionDate == null ? null : String(bar.sessionDate),
    }))
    .filter(bar => [bar.open, bar.high, bar.low, bar.close, bar.volume].every(Number.isFinite))
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp));
}

function pctRatio(numerator, denominator) {
  return Number(denominator) ? (Number(numerator) / Number(denominator) - 1) * 100 : 0;
}

function movingAverage(bars, length, field = 'close') {
  const slice = bars.slice(-Math.max(1, Number(length) || 1));
  return slice.length ? mean(slice.map(bar => Number(bar[field]))) : null;
}

function trueRanges(bars) {
  return bars.map((bar, index) => {
    const priorClose = index > 0 ? Number(bars[index - 1].close) : Number(bar.open);
    return Math.max(
      Number(bar.high) - Number(bar.low),
      Math.abs(Number(bar.high) - priorClose),
      Math.abs(Number(bar.low) - priorClose),
    );
  });
}

function sessionMinutes(timestamp) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tokyo', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(timestamp));
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  const minutes = Number(values.hour) * 60 + Number(values.minute);
  if (minutes <= 11 * 60 + 30) return Math.max(0, minutes - 9 * 60);
  return Math.max(0, 150 + (minutes - (12 * 60 + 30)));
}

export function deriveEntryOpportunityFeatures({ contextBars = [], direction } = {}) {
  const bars = normalizeBars(contextBars);
  if (bars.length < 2) throw new Error('entry opportunity features require at least two completed context bars');
  const sign = signFromDirection(direction);
  const current = bars.at(-1);
  const previous = bars.at(-2);
  const sessionOpen = Number(bars[0].open);
  const prior3 = bars[Math.max(0, bars.length - 4)] ?? bars[0];
  const recent20 = bars.slice(-20);
  const prior20 = bars.slice(Math.max(0, bars.length - 21), -1);
  const high20 = Math.max(...recent20.map(bar => Number(bar.high)));
  const low20 = Math.min(...recent20.map(bar => Number(bar.low)));
  const range20 = Math.max(1e-12, high20 - low20);
  const rawRangePosition = (Number(current.close) - low20) / range20;
  const rangePosition20Directional = sign === 1 ? rawRangePosition : 1 - rawRangePosition;

  const totalVolume = bars.reduce((sum, bar) => sum + Math.max(0, Number(bar.volume)), 0);
  const vwap = totalVolume > 0
    ? bars.reduce((sum, bar) => sum + Number(bar.close) * Math.max(0, Number(bar.volume)), 0) / totalVolume
    : mean(bars.map(bar => Number(bar.close)));

  const ma5 = movingAverage(bars, 5);
  const earlierBars = bars.slice(0, Math.max(1, bars.length - 3));
  const ma5Earlier = movingAverage(earlierBars, 5);
  const priorHigh = prior20.length ? Math.max(...prior20.map(bar => Number(bar.high))) : Number(previous.high);
  const priorLow = prior20.length ? Math.min(...prior20.map(bar => Number(bar.low))) : Number(previous.low);
  const breakoutDistance = sign === 1
    ? pctRatio(Number(current.close), priorHigh)
    : pctRatio(priorLow, Number(current.close));

  const volume5 = bars.slice(-5).map(bar => Math.max(0, Number(bar.volume)));
  const priorVolume = bars.slice(Math.max(0, bars.length - 10), Math.max(0, bars.length - 5)).map(bar => Math.max(0, Number(bar.volume)));
  const relativeVolume5 = mean(priorVolume) > 0 ? mean(volume5) / mean(priorVolume) : 1;

  const tr = trueRanges(bars);
  const tr5 = mean(tr.slice(-5));
  const tr20 = mean(tr.slice(-20));
  const atr10 = mean(tr.slice(-10));
  const atrPct10 = Number(current.close) ? atr10 / Number(current.close) * 100 : 0;
  const compression5to20 = tr20 > 0 ? tr5 / tr20 : 1;

  const candleRange = Math.max(1e-12, Number(current.high) - Number(current.low));
  const body = Number(current.close) - Number(current.open);
  const upperWick = Number(current.high) - Math.max(Number(current.open), Number(current.close));
  const lowerWick = Math.min(Number(current.open), Number(current.close)) - Number(current.low);
  const favorableWick = sign === 1 ? lowerWick : upperWick;
  const adverseWick = sign === 1 ? upperWick : lowerWick;

  return Object.freeze({
    directionSign: sign,
    directionalReturnFromOpenPct: sign * pctRatio(Number(current.close), sessionOpen),
    directionalMomentum1Pct: sign * pctRatio(Number(current.close), Number(previous.close)),
    directionalMomentum3Pct: sign * pctRatio(Number(current.close), Number(prior3.close)),
    rangePosition20Directional: clamp(rangePosition20Directional, 0, 1),
    directionalVwapDistancePct: sign * pctRatio(Number(current.close), vwap),
    directionalMa5DistancePct: sign * pctRatio(Number(current.close), ma5),
    directionalMa5SlopePct: sign * pctRatio(ma5, ma5Earlier),
    directionalBreakoutDistancePct: breakoutDistance,
    relativeVolume5: clamp(relativeVolume5, 0, 20),
    atrPct10: clamp(atrPct10, 0, 20),
    compression5to20: clamp(compression5to20, 0, 10),
    directionalBodyStrength: clamp(sign * body / candleRange, -1, 1),
    favorableWickRatio: clamp(favorableWick / candleRange, 0, 1),
    adverseWickRatio: clamp(adverseWick / candleRange, 0, 1),
    minutesFromOpenNormalized: clamp(sessionMinutes(current.timestamp) / 300, 0, 1.5),
  });
}

export function deriveFixedHorizonOpportunityTargets({ entryPrice, direction, futureBars = [], horizonBars = 12, roundTripCostPct = 0.05 } = {}) {
  const price = Number(entryPrice);
  if (!finite(price) || price <= 0) throw new Error('entryPrice must be positive');
  const sign = signFromDirection(direction);
  const bars = normalizeBars(futureBars).slice(0, Number(horizonBars));
  if (bars.length !== Number(horizonBars)) return null;
  const favorablePrice = sign === 1
    ? Math.max(price, ...bars.map(bar => Number(bar.high)))
    : Math.min(price, ...bars.map(bar => Number(bar.low)));
  const adversePrice = sign === 1
    ? Math.min(price, ...bars.map(bar => Number(bar.low)))
    : Math.max(price, ...bars.map(bar => Number(bar.high)));
  const mfePct = Math.max(0, sign === 1 ? pctRatio(favorablePrice, price) : pctRatio(price, favorablePrice));
  const adversePct = Math.max(0, -(sign === 1 ? pctRatio(adversePrice, price) : pctRatio(price, adversePrice)));
  const endpointGrossReturnPct = sign === 1
    ? pctRatio(Number(bars.at(-1).close), price)
    : pctRatio(price, Number(bars.at(-1).close));
  const endpointNetReturnPct = endpointGrossReturnPct - Number(roundTripCostPct || 0);
  const opportunityScorePct = mfePct - adversePct - Number(roundTripCostPct || 0);
  return Object.freeze({
    horizonBars: Number(horizonBars),
    mfePct,
    adversePct,
    endpointGrossReturnPct,
    endpointNetReturnPct,
    opportunityScorePct,
    outcomeAt: bars.at(-1).timestamp,
    evaluationOnly: true,
    eligibleForModelFeatures: false,
    futureBarsUsedAsPredictors: false,
  });
}

export function buildEntryOpportunityExample({ symbol, sessionDate, featureCutoff, contextBars, futureBars, entryPrice, direction, horizonBars = 12, roundTripCostPct = 0.05 } = {}) {
  const features = deriveEntryOpportunityFeatures({ contextBars, direction });
  const targets = deriveFixedHorizonOpportunityTargets({ entryPrice, direction, futureBars, horizonBars, roundTripCostPct });
  if (!targets) return null;
  return Object.freeze({
    symbol: String(symbol ?? ''),
    sessionDate: String(sessionDate ?? ''),
    featureCutoff: new Date(featureCutoff ?? contextBars?.at?.(-1)?.timestamp).toISOString(),
    direction: signFromDirection(direction) === 1 ? 'LONG' : 'SHORT',
    entryPrice: Number(entryPrice),
    features,
    targets,
    pointInTimeFeaturesOnly: true,
    futureTargetsEvaluationOnly: true,
  });
}

function solveLinearSystem(matrix, vector) {
  const n = matrix.length;
  const a = matrix.map((row, index) => [...row.map(Number), Number(vector[index])]);
  for (let col = 0; col < n; col += 1) {
    let pivot = col;
    for (let row = col + 1; row < n; row += 1) if (Math.abs(a[row][col]) > Math.abs(a[pivot][col])) pivot = row;
    if (Math.abs(a[pivot][col]) < 1e-12) a[pivot][col] = a[pivot][col] >= 0 ? 1e-12 : -1e-12;
    [a[col], a[pivot]] = [a[pivot], a[col]];
    const divisor = a[col][col];
    for (let j = col; j <= n; j += 1) a[col][j] /= divisor;
    for (let row = 0; row < n; row += 1) {
      if (row === col) continue;
      const factor = a[row][col];
      if (!factor) continue;
      for (let j = col; j <= n; j += 1) a[row][j] -= factor * a[col][j];
    }
  }
  return a.map(row => row[n]);
}

function fitTarget(rows, standardizedX, targetKey, lambda) {
  const p = ENTRY_OPPORTUNITY_FEATURES.length + 1;
  const xtx = Array.from({ length: p }, () => Array(p).fill(0));
  const xty = Array(p).fill(0);
  for (let i = 0; i < rows.length; i += 1) {
    const x = [1, ...standardizedX[i]];
    const y = Number(rows[i].targets[targetKey]);
    for (let r = 0; r < p; r += 1) {
      xty[r] += x[r] * y;
      for (let c = 0; c < p; c += 1) xtx[r][c] += x[r] * x[c];
    }
  }
  for (let i = 1; i < p; i += 1) xtx[i][i] += Number(lambda);
  return solveLinearSystem(xtx, xty);
}

export function fitEntryOpportunityRidge(rows = [], { lambda = 8 } = {}) {
  const training = (Array.isArray(rows) ? rows : []).filter(row => row?.pointInTimeFeaturesOnly === true && row?.futureTargetsEvaluationOnly === true);
  if (training.length < 20) throw new Error('entry opportunity ridge requires at least 20 historical examples');
  const means = {};
  const stds = {};
  for (const key of ENTRY_OPPORTUNITY_FEATURES) {
    const values = training.map(row => Number(row.features[key]));
    if (values.some(value => !Number.isFinite(value))) throw new Error(`non-finite feature: ${key}`);
    means[key] = mean(values);
    const variance = mean(values.map(value => (value - means[key]) ** 2));
    stds[key] = Math.sqrt(variance) || 1;
  }
  const standardizedX = training.map(row => ENTRY_OPPORTUNITY_FEATURES.map(key => (Number(row.features[key]) - means[key]) / stds[key]));
  const weights = {
    mfePct: fitTarget(training, standardizedX, 'mfePct', lambda),
    adversePct: fitTarget(training, standardizedX, 'adversePct', lambda),
    endpointNetReturnPct: fitTarget(training, standardizedX, 'endpointNetReturnPct', lambda),
  };
  const predictTarget = (features, targetKey) => {
    const x = [1, ...ENTRY_OPPORTUNITY_FEATURES.map(key => (Number(features[key]) - means[key]) / stds[key])];
    return x.reduce((sum, value, index) => sum + value * Number(weights[targetKey][index]), 0);
  };
  return Object.freeze({
    trainingCount: training.length,
    lambda: Number(lambda),
    featureKeys: ENTRY_OPPORTUNITY_FEATURES,
    predict(features, { roundTripCostPct = 0.05 } = {}) {
      for (const key of ENTRY_OPPORTUNITY_FEATURES) if (!finite(features?.[key])) throw new Error(`missing feature: ${key}`);
      const expectedMfePct = Math.max(0, predictTarget(features, 'mfePct'));
      const expectedAdversePct = Math.max(0, predictTarget(features, 'adversePct'));
      const expectedNetReturnPct = predictTarget(features, 'endpointNetReturnPct');
      const expectedOpportunityScorePct = expectedMfePct - expectedAdversePct - Number(roundTripCostPct || 0);
      const gatePass = expectedNetReturnPct > 0 && expectedOpportunityScorePct > 0;
      return Object.freeze({
        expectedMfePct,
        expectedAdversePct,
        expectedNetReturnPct,
        expectedOpportunityScorePct,
        gatePass,
        gateRule: 'EXPECTED_ENDPOINT_NET_GT_0_AND_EXPECTED_MFE_MINUS_ADVERSE_MINUS_COST_GT_0',
        futureOutcomeUsedForPrediction: false,
      });
    },
  });
}

function pearson(xs, ys) {
  if (xs.length !== ys.length || xs.length < 2) return null;
  const mx = mean(xs); const my = mean(ys);
  let num = 0; let dx = 0; let dy = 0;
  for (let i = 0; i < xs.length; i += 1) {
    const a = Number(xs[i]) - mx; const b = Number(ys[i]) - my;
    num += a * b; dx += a * a; dy += b * b;
  }
  return dx > 0 && dy > 0 ? num / Math.sqrt(dx * dy) : null;
}

function summarizeReturns(values = []) {
  const rows = values.map(Number).filter(Number.isFinite);
  const positive = rows.filter(value => value > 0).reduce((sum, value) => sum + value, 0);
  const negative = -rows.filter(value => value < 0).reduce((sum, value) => sum + value, 0);
  return Object.freeze({
    signalCount: rows.length,
    hitRate: rows.length ? rows.filter(value => value > 0).length / rows.length : null,
    netAverageReturnPct: rows.length ? mean(rows) : null,
    profitFactor: negative > 0 ? positive / negative : (positive > 0 ? Infinity : null),
  });
}

export function evaluateEntryOpportunityWalkForward({ trainingExamples = [], frozenTestExamples = [], minTrainRows = 500, lambda = 8, roundTripCostPct = 0.05 } = {}) {
  const train = Array.isArray(trainingExamples) ? trainingExamples : [];
  const test = Array.isArray(frozenTestExamples) ? frozenTestExamples : [];
  const dates = [...new Set(test.map(row => String(row.sessionDate)))].sort();
  const predictions = [];
  const dateDiagnostics = [];
  for (const date of dates) {
    const historical = train.filter(row => String(row.sessionDate) < date);
    const dateRows = test.filter(row => String(row.sessionDate) === date);
    if (historical.length < Number(minTrainRows)) {
      dateDiagnostics.push(Object.freeze({ sessionDate: date, status: 'ABSTAIN_INSUFFICIENT_PRIOR_HISTORY', priorTrainingRows: historical.length, frozenSignalCount: dateRows.length }));
      continue;
    }
    const model = fitEntryOpportunityRidge(historical, { lambda });
    for (const row of dateRows) {
      const prediction = model.predict(row.features, { roundTripCostPct });
      predictions.push(Object.freeze({
        symbol: row.symbol,
        sessionDate: row.sessionDate,
        featureCutoff: row.featureCutoff,
        direction: row.direction,
        ...prediction,
        realizedMfePct: Number(row.targets.mfePct),
        realizedAdversePct: Number(row.targets.adversePct),
        realizedEndpointNetReturnPct: Number(row.targets.endpointNetReturnPct),
        realizedOpportunityScorePct: Number(row.targets.opportunityScorePct),
        realizedRatchetNetReturnPct: Number(row.realizedRatchetNetReturnPct),
        priorTrainingRows: historical.length,
        outerOutcomeUsedForModelFit: false,
      }));
    }
    dateDiagnostics.push(Object.freeze({ sessionDate: date, status: 'EVALUATED', priorTrainingRows: historical.length, frozenSignalCount: dateRows.length }));
  }

  const allReturns = predictions.map(row => row.realizedRatchetNetReturnPct);
  const gatedRows = predictions.filter(row => row.gatePass);
  const gatedReturns = gatedRows.map(row => row.realizedRatchetNetReturnPct);
  const allSummary = summarizeReturns(allReturns);
  const gatedSummary = summarizeReturns(gatedReturns);
  return Object.freeze({
    phase: '57.p23.9a-entry-opportunity-intelligence',
    status: predictions.length ? 'HISTORICAL_ENTRY_OPPORTUNITY_WALK_FORWARD_EVALUATED' : 'NO_ENTRY_OPPORTUNITY_PREDICTIONS',
    predictionCount: predictions.length,
    frozenTestCount: test.length,
    evaluatedCoverage: test.length ? predictions.length / test.length : 0,
    gateCoverage: predictions.length ? gatedRows.length / predictions.length : 0,
    allFrozenRatchet: allSummary,
    gatedFrozenRatchet: gatedSummary,
    deltas: Object.freeze({
      netAverageReturnPct: gatedSummary.netAverageReturnPct == null || allSummary.netAverageReturnPct == null ? null : gatedSummary.netAverageReturnPct - allSummary.netAverageReturnPct,
      profitFactor: gatedSummary.profitFactor == null || allSummary.profitFactor == null || !Number.isFinite(gatedSummary.profitFactor) || !Number.isFinite(allSummary.profitFactor) ? null : gatedSummary.profitFactor - allSummary.profitFactor,
      hitRate: gatedSummary.hitRate == null || allSummary.hitRate == null ? null : gatedSummary.hitRate - allSummary.hitRate,
    }),
    correlations: Object.freeze({
      expectedMfeVsRealizedMfe: pearson(predictions.map(row => row.expectedMfePct), predictions.map(row => row.realizedMfePct)),
      expectedAdverseVsRealizedAdverse: pearson(predictions.map(row => row.expectedAdversePct), predictions.map(row => row.realizedAdversePct)),
      expectedNetVsRealizedEndpointNet: pearson(predictions.map(row => row.expectedNetReturnPct), predictions.map(row => row.realizedEndpointNetReturnPct)),
      expectedOpportunityVsRealizedOpportunity: pearson(predictions.map(row => row.expectedOpportunityScorePct), predictions.map(row => row.realizedOpportunityScorePct)),
      expectedNetVsRealizedRatchetNet: pearson(predictions.map(row => row.expectedNetReturnPct), predictions.map(row => row.realizedRatchetNetReturnPct)),
    }),
    dateDiagnostics: Object.freeze(dateDiagnostics),
    predictions: Object.freeze(predictions),
    integrity: Object.freeze({
      trainingUsesPriorSessionsOnly: true,
      sameSessionTrainingForbidden: true,
      futureTargetsEvaluationOnly: true,
      futureExtremaUsedAsFeatures: false,
      frozenEntryDirectionAndTimestampChanged: false,
      gateRulePreRegisteredBeforeOuterMeasurement: true,
      outerOutcomeUsedForGateSelection: false,
      developmentWindowReused: true,
      finalUntouchedOosEdgeClaimAllowed: false,
    }),
    edgeClaimAllowed: false,
    recommendationAllowed: false,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    paperTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    overnightHoldingAllowed: false,
    transmitted: false,
    safety: PHASE57_P23_9A_SAFETY,
  });
}

export default {
  ENTRY_OPPORTUNITY_FEATURES,
  PHASE57_P23_9A_SAFETY,
  deriveEntryOpportunityFeatures,
  deriveFixedHorizonOpportunityTargets,
  buildEntryOpportunityExample,
  fitEntryOpportunityRidge,
  evaluateEntryOpportunityWalkForward,
};
