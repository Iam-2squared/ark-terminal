const SAFETY_FALSE_KEYS = [
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

export const PHASE57_EXIT_V5_RESEARCH_SAFETY = Object.freeze({
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
});

export const PHASE57_EXIT_V5_DATASET_POLICY = Object.freeze({
  candidateFamily: 'INCREMENTAL_LIQUIDATION_VALUE_V5',
  decisionTarget: 'future liquidation value minus liquidation value now',
  horizonsBars: Object.freeze([1, 3, 6]),
  primaryHorizonBars: 3,
  futureDataAllowedInFeatures: false,
  futureDataAllowedInLabelsOnly: true,
  outerOosRetuningAllowed: false,
  prospectiveRetuningAllowed: false,
  selectorFrozen: true,
  entryFrozen: true,
  directionFrozen: true,
  marketDataFrozen: true,
  transactionCostAssumptionsFrozen: true,
  capitalAllocationFrozen: true,
});

function finite(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function pct(numerator, denominator) {
  return denominator > 0 ? (numerator / denominator) * 100 : 0;
}

function assertBar(bar, label = 'bar') {
  if (!bar || !Number.isFinite(Number(bar.close)) || !bar.timestamp) {
    throw new Error(`${label} must have timestamp and finite close`);
  }
}

function directionSign(direction) {
  if (direction === 'LONG' || direction === 1 || direction === '+1') return 1;
  if (direction === 'SHORT' || direction === -1 || direction === '-1') return -1;
  throw new Error(`unsupported direction: ${direction}`);
}

function directionalReturnPct(price, entryPrice, sign) {
  return sign * pct(finite(price) - entryPrice, entryPrice);
}

function rollingAtrPct(observedBars, lookback = 6) {
  const bars = observedBars.slice(-lookback);
  if (!bars.length) return 0;
  return bars.reduce((sum, bar) => {
    const close = finite(bar.close);
    const range = Math.max(0, finite(bar.high, close) - finite(bar.low, close));
    return sum + pct(range, close);
  }, 0) / bars.length;
}

function runningExcursions(observedBars, entryPrice, sign) {
  let mfePct = 0;
  let maePct = 0;
  let mfeIndex = -1;
  let maeIndex = -1;
  observedBars.forEach((bar, index) => {
    const favorablePrice = sign > 0 ? finite(bar.high, bar.close) : finite(bar.low, bar.close);
    const adversePrice = sign > 0 ? finite(bar.low, bar.close) : finite(bar.high, bar.close);
    const favorable = directionalReturnPct(favorablePrice, entryPrice, sign);
    const adverse = directionalReturnPct(adversePrice, entryPrice, sign);
    if (favorable > mfePct) {
      mfePct = favorable;
      mfeIndex = index;
    }
    if (adverse < maePct) {
      maePct = adverse;
      maeIndex = index;
    }
  });
  return { mfePct, maePct, mfeIndex, maeIndex };
}

function closeVwap(observedBars) {
  let weighted = 0;
  let volume = 0;
  for (const bar of observedBars) {
    const v = Math.max(0, finite(bar.volume));
    weighted += finite(bar.close) * v;
    volume += v;
  }
  return volume > 0 ? weighted / volume : finite(observedBars.at(-1)?.close);
}

function prefixVwap(observedBars, endExclusive) {
  return closeVwap(observedBars.slice(0, endExclusive));
}

function averageVolume(bars) {
  return bars.length ? bars.reduce((sum, bar) => sum + Math.max(0, finite(bar.volume)), 0) / bars.length : 0;
}

/**
 * Causal feature builder for EXIT v5 research.
 * Deliberately accepts only bars observed through t. There is no futureBars argument.
 */
export function buildExitV5Features({ entryPrice, direction, observedBars }) {
  if (!(Number(entryPrice) > 0)) throw new Error('entryPrice must be positive');
  if (!Array.isArray(observedBars) || observedBars.length < 2) throw new Error('observedBars must contain at least 2 finalized bars');
  observedBars.forEach((bar, index) => assertBar(bar, `observedBars[${index}]`));
  for (let index = 1; index < observedBars.length; index += 1) {
    if (Date.parse(observedBars[index].timestamp) <= Date.parse(observedBars[index - 1].timestamp)) {
      throw new Error('observedBars timestamps must be strictly increasing');
    }
  }

  const sign = directionSign(direction);
  const current = observedBars.at(-1);
  const previous = observedBars.at(-2);
  const currentReturnPct = directionalReturnPct(current.close, Number(entryPrice), sign);
  const { mfePct, maePct, mfeIndex, maeIndex } = runningExcursions(observedBars, Number(entryPrice), sign);
  const givebackPct = Math.max(0, mfePct - currentReturnPct);
  const captureRatio = mfePct > 0 ? currentReturnPct / mfePct : 0;
  const atrPct = rollingAtrPct(observedBars);

  const priorMfe = runningExcursions(observedBars.slice(0, -1), Number(entryPrice), sign).mfePct;
  const mfeVelocityPctPerBar = mfePct - priorMfe;
  const barsSinceLastMfe = mfeIndex >= 0 ? observedBars.length - 1 - mfeIndex : observedBars.length;
  const barsSinceLastMae = maeIndex >= 0 ? observedBars.length - 1 - maeIndex : observedBars.length;

  const vwap = closeVwap(observedBars);
  const priorVwap = prefixVwap(observedBars, observedBars.length - 1);
  const vwapDistancePct = sign * pct(finite(current.close) - vwap, vwap);
  const vwapSlopePctPerBar = sign * pct(vwap - priorVwap, priorVwap);

  const priorVolume = averageVolume(observedBars.slice(Math.max(0, observedBars.length - 7), -1));
  const rvol = priorVolume > 0 ? finite(current.volume) / priorVolume : 0;

  const previousDirectionalReturn = directionalReturnPct(previous.close, Number(entryPrice), sign);
  const currentMomentumPct = currentReturnPct - previousDirectionalReturn;
  const prePrevious = observedBars.length >= 3 ? observedBars.at(-3) : previous;
  const prePreviousDirectionalReturn = directionalReturnPct(prePrevious.close, Number(entryPrice), sign);
  const previousMomentumPct = previousDirectionalReturn - prePreviousDirectionalReturn;
  const momentumDecelerationPct = previousMomentumPct - currentMomentumPct;

  return Object.freeze({
    featureAt: current.timestamp,
    currentReturnPct,
    atrPct,
    currentReturnAtr: atrPct > 0 ? currentReturnPct / atrPct : 0,
    runningMfePct: mfePct,
    runningMfeAtr: atrPct > 0 ? mfePct / atrPct : 0,
    runningMaePct: maePct,
    runningMaeAtr: atrPct > 0 ? maePct / atrPct : 0,
    givebackPct,
    givebackAtr: atrPct > 0 ? givebackPct / atrPct : 0,
    captureRatio,
    mfeVelocityPctPerBar,
    barsSinceLastMfe,
    barsSinceLastMae,
    vwapDistancePct,
    vwapSlopePctPerBar,
    rvol,
    currentMomentumPct,
    momentumDecelerationPct,
    elapsedBars: observedBars.length,
    directionSign: sign,
  });
}

/**
 * Label builder is intentionally separate from buildExitV5Features.
 * Future finalized bars are legal here because this function is training/evaluation only.
 * Label is the incremental directional liquidation value relative to exiting at t.
 */
export function buildExitV5Labels({ currentBar, futureBars, direction, horizonsBars = PHASE57_EXIT_V5_DATASET_POLICY.horizonsBars }) {
  assertBar(currentBar, 'currentBar');
  if (!Array.isArray(futureBars)) throw new Error('futureBars must be an array');
  futureBars.forEach((bar, index) => assertBar(bar, `futureBars[${index}]`));
  const sign = directionSign(direction);
  const currentPrice = Number(currentBar.close);
  const labels = {};

  for (const horizon of horizonsBars) {
    if (!Number.isInteger(horizon) || horizon <= 0) throw new Error(`invalid horizon: ${horizon}`);
    const futureBar = futureBars[horizon - 1];
    if (!futureBar) continue;
    if (Date.parse(futureBar.timestamp) <= Date.parse(currentBar.timestamp)) {
      throw new Error('label bar must be strictly after currentBar');
    }
    labels[horizon] = sign * pct(Number(futureBar.close) - currentPrice, currentPrice);
  }

  const maxHorizon = Math.max(...Object.keys(labels).map(Number), 0);
  const labelThrough = maxHorizon > 0 ? futureBars[maxHorizon - 1].timestamp : currentBar.timestamp;
  return Object.freeze({
    labelAt: currentBar.timestamp,
    labelThrough,
    incrementalLiquidationReturnPctByHorizon: Object.freeze(labels),
  });
}

export function buildExitV5TrainingSample({ entryPrice, direction, observedBars, futureBars }) {
  const features = buildExitV5Features({ entryPrice, direction, observedBars });
  const labels = buildExitV5Labels({ currentBar: observedBars.at(-1), futureBars, direction });
  return Object.freeze({ features, labels });
}

function parseBoundary(value, name) {
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) throw new Error(`${name} must be an ISO timestamp`);
  return parsed;
}

/**
 * Time-ordered split with label-boundary purging. A sample is admitted only when
 * its complete forward label window is contained inside the same split.
 */
export function buildPurgedExitV5Split(samples, { developmentEnd, validationEnd, oosEnd }) {
  const devEnd = parseBoundary(developmentEnd, 'developmentEnd');
  const valEnd = parseBoundary(validationEnd, 'validationEnd');
  const outEnd = parseBoundary(oosEnd, 'oosEnd');
  if (!(devEnd < valEnd && valEnd < outEnd)) throw new Error('split boundaries must be strictly increasing');

  const result = { development: [], validation: [], oos: [], prospective: [], purged: [] };
  const ordered = [...samples].sort((a, b) => Date.parse(a.features.featureAt) - Date.parse(b.features.featureAt));

  for (const sample of ordered) {
    const at = parseBoundary(sample.features.featureAt, 'featureAt');
    const through = parseBoundary(sample.labels.labelThrough, 'labelThrough');
    if (through < at) throw new Error('labelThrough cannot precede featureAt');

    if (at <= devEnd) {
      (through <= devEnd ? result.development : result.purged).push(sample);
    } else if (at <= valEnd) {
      (through <= valEnd ? result.validation : result.purged).push(sample);
    } else if (at <= outEnd) {
      (through <= outEnd ? result.oos : result.purged).push(sample);
    } else {
      result.prospective.push(sample);
    }
  }

  return Object.freeze(Object.fromEntries(Object.entries(result).map(([key, value]) => [key, Object.freeze(value)])));
}

export function assertExitV5ResearchSafety() {
  for (const key of SAFETY_FALSE_KEYS) {
    if (PHASE57_EXIT_V5_RESEARCH_SAFETY[key] !== false) throw new Error(`unsafe EXIT v5 research flag: ${key}`);
  }
  if (PHASE57_EXIT_V5_RESEARCH_SAFETY.researchOnly !== true) throw new Error('EXIT v5 must remain researchOnly');
  return true;
}
