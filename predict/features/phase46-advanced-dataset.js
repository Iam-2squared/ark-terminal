import crypto from "node:crypto";

export const PHASE46_ADVANCED_SAFETY = Object.freeze({
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

function mean(values) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function std(values) {
  if (values.length < 2) return 0;
  const avg = mean(values);
  return Math.sqrt(values.reduce((sum, value) => sum + ((value - avg) ** 2), 0) / values.length);
}

function ema(values, period) {
  if (!values.length) return 0;
  const alpha = 2 / (period + 1);
  let value = values[0];
  for (let i = 1; i < values.length; i += 1) value = alpha * values[i] + (1 - alpha) * value;
  return value;
}

function checksum(value) {
  return crypto.createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

function pctChange(current, previous) {
  return previous === 0 ? 0 : (current / previous) - 1;
}

function rollingMean(rows, index, period, selector) {
  if (index + 1 < period) return null;
  return mean(rows.slice(index - period + 1, index + 1).map(selector));
}

function trueRange(row, prevClose) {
  const high = Number(row.high);
  const low = Number(row.low);
  return Math.max(high - low, Math.abs(high - prevClose), Math.abs(low - prevClose));
}

function computeRsi(closes, period = 14) {
  if (closes.length < period + 1) return 50;
  const recent = closes.slice(-(period + 1));
  const changes = recent.slice(1).map((value, i) => value - recent[i]);
  const gains = changes.map((value) => Math.max(value, 0));
  const losses = changes.map((value) => Math.max(-value, 0));
  const avgGain = mean(gains);
  const avgLoss = mean(losses);
  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return 100 - (100 / (1 + rs));
}

function computeAtr(rows, index, period = 14) {
  if (index < period) return 0;
  const ranges = [];
  for (let i = index - period + 1; i <= index; i += 1) {
    const prevClose = Number(rows[i - 1]?.close ?? rows[i].close);
    ranges.push(trueRange(rows[i], prevClose));
  }
  const close = Number(rows[index].close) || 1;
  return mean(ranges) / close;
}

function computeStochastic(rows, index, period = 14) {
  if (index + 1 < period) return 50;
  const window = rows.slice(index - period + 1, index + 1);
  const highest = Math.max(...window.map((row) => Number(row.high)));
  const lowest = Math.min(...window.map((row) => Number(row.low)));
  const close = Number(rows[index].close);
  return highest === lowest ? 50 : ((close - lowest) / (highest - lowest)) * 100;
}

function computeAdxApprox(rows, index, period = 14) {
  if (index < period) return 0;
  const dx = [];
  for (let i = index - period + 1; i <= index; i += 1) {
    const current = rows[i];
    const previous = rows[i - 1];
    const up = Number(current.high) - Number(previous.high);
    const down = Number(previous.low) - Number(current.low);
    const plusDm = up > down && up > 0 ? up : 0;
    const minusDm = down > up && down > 0 ? down : 0;
    const tr = trueRange(current, Number(previous.close)) || 1;
    const plusDi = (plusDm / tr) * 100;
    const minusDi = (minusDm / tr) * 100;
    const denom = plusDi + minusDi;
    dx.push(denom === 0 ? 0 : (Math.abs(plusDi - minusDi) / denom) * 100);
  }
  return mean(dx);
}

function computeChartStructure(rows, index, currentClose) {
  const lookback20 = rows.slice(index - 19, index + 1);
  const prior20 = rows.slice(index - 20, index);
  const lookback60 = rows.slice(index - 59, index + 1);
  const high20 = Math.max(...lookback20.map((row) => Number(row.high)));
  const low20 = Math.min(...lookback20.map((row) => Number(row.low)));
  const priorHigh20 = Math.max(...prior20.map((row) => Number(row.high)));
  const priorLow20 = Math.min(...prior20.map((row) => Number(row.low)));
  const high60 = Math.max(...lookback60.map((row) => Number(row.high)));
  const low60 = Math.min(...lookback60.map((row) => Number(row.low)));
  const range20 = high20 - low20;
  const range60 = high60 - low60;
  const closePosition20 = range20 === 0 ? 0.5 : (currentClose - low20) / range20;
  const closePosition60 = range60 === 0 ? 0.5 : (currentClose - low60) / range60;
  const breakoutUp20 = priorHigh20 === 0 ? 0 : Math.max(0, currentClose / priorHigh20 - 1);
  const breakdownDown20 = priorLow20 === 0 ? 0 : Math.max(0, priorLow20 / currentClose - 1);
  return { closePosition20, closePosition60, breakoutUp20, breakdownDown20 };
}

function classifyRegime({ ma20Gap, ma75Gap, adx14Approx, volatility20, atr14 }) {
  const trendScore = (Math.abs(ma20Gap) + Math.abs(ma75Gap)) * 100 + (adx14Approx / 100);
  const highVol = volatility20 >= 0.025 || atr14 >= 0.03;
  const trending = adx14Approx >= 25 || trendScore >= 0.08;
  const direction = ma20Gap >= 0 && ma75Gap >= 0 ? 1 : (ma20Gap <= 0 && ma75Gap <= 0 ? -1 : 0);
  if (trending && highVol) return { regimeTrend: direction, regimeVolatility: 1, regimeCode: direction > 0 ? 3 : direction < 0 ? -3 : 2 };
  if (trending) return { regimeTrend: direction, regimeVolatility: 0, regimeCode: direction > 0 ? 2 : direction < 0 ? -2 : 1 };
  if (highVol) return { regimeTrend: 0, regimeVolatility: 1, regimeCode: 4 };
  return { regimeTrend: 0, regimeVolatility: 0, regimeCode: 0 };
}

export function generateExtendedFeatures(records = []) {
  if (!Array.isArray(records)) throw new TypeError("records must be an array");
  const bySymbol = new Map();
  for (const row of records) {
    if (!row?.symbol || !row?.sessionDate) throw new TypeError("symbol and sessionDate are required");
    const rows = bySymbol.get(row.symbol) || [];
    rows.push(row);
    bySymbol.set(row.symbol, rows);
  }

  const output = [];
  for (const [symbol, rows] of bySymbol) {
    rows.sort((a, b) => String(a.sessionDate).localeCompare(String(b.sessionDate)));
    for (let index = 75; index < rows.length - 1; index += 1) {
      const current = rows[index];
      const next = rows[index + 1];
      const currentClose = Number(current.close);
      const nextClose = Number(next.close);
      if (!Number.isFinite(currentClose) || !Number.isFinite(nextClose) || currentClose === 0) continue;

      const closes = rows.slice(0, index + 1).map((row) => Number(row.close));
      const volumes20 = rows.slice(index - 19, index + 1).map((row) => Number(row.volume));
      const window20 = rows.slice(index - 19, index + 1);
      const typicalPrice = window20.map((row) => (Number(row.high) + Number(row.low) + Number(row.close)) / 3);
      const volumeSum = volumes20.reduce((sum, value) => sum + value, 0);
      const vwap20 = volumeSum === 0 ? currentClose : typicalPrice.reduce((sum, value, i) => sum + value * volumes20[i], 0) / volumeSum;
      const sma20 = mean(window20.map((row) => Number(row.close)));
      const sigma20 = std(window20.map((row) => Number(row.close)));
      const recentReturns20 = window20.slice(1).map((row, i) => pctChange(Number(row.close), Number(window20[i].close)));

      const ma5 = rollingMean(rows, index, 5, (row) => Number(row.close));
      const ma10 = rollingMean(rows, index, 10, (row) => Number(row.close));
      const ma20 = rollingMean(rows, index, 20, (row) => Number(row.close));
      const ma25 = rollingMean(rows, index, 25, (row) => Number(row.close));
      const ma50 = rollingMean(rows, index, 50, (row) => Number(row.close));
      const ma75 = rollingMean(rows, index, 75, (row) => Number(row.close));
      const ema12 = ema(closes.slice(-60), 12);
      const ema26 = ema(closes.slice(-60), 26);
      const macd = currentClose ? (ema12 - ema26) / currentClose : 0;
      const macdSeries = [];
      const macdSource = closes.slice(-40);
      for (let i = 26; i <= macdSource.length; i += 1) {
        const slice = macdSource.slice(0, i);
        macdSeries.push(ema(slice, 12) - ema(slice, 26));
      }
      const macdSignal = macdSeries.length ? ema(macdSeries, 9) / currentClose : 0;
      const high52Window = rows.slice(Math.max(0, index - 251), index + 1);
      const high52 = Math.max(...high52Window.map((row) => Number(row.high)));
      const low52 = Math.min(...high52Window.map((row) => Number(row.low)));
      const range52 = high52 - low52;
      const prevClose = Number(rows[index - 1].close);
      const open = Number(current.open);
      const actualReturn = (nextClose / currentClose) - 1;
      const ma20Gap = currentClose / ma20 - 1;
      const ma75Gap = currentClose / ma75 - 1;
      const atr14 = computeAtr(rows, index, 14);
      const volatility20 = std(recentReturns20);
      const adx14Approx = computeAdxApprox(rows, index, 14);
      const chartStructure = computeChartStructure(rows, index, currentClose);
      const regime = classifyRegime({ ma20Gap, ma75Gap, adx14Approx, volatility20, atr14 });

      const featureValues = Object.freeze({
        rsi14: computeRsi(closes, 14),
        atr14,
        vwapGap20: currentClose ? (currentClose / vwap20) - 1 : 0,
        bollingerZ20: sigma20 === 0 ? 0 : (currentClose - sma20) / sigma20,
        volumeRatio20: mean(volumes20) === 0 ? 0 : Number(current.volume) / mean(volumes20),
        volatility20,
        ma5Gap: currentClose / ma5 - 1,
        ma10Gap: currentClose / ma10 - 1,
        ma20Gap,
        ma25Gap: currentClose / ma25 - 1,
        ma50Gap: currentClose / ma50 - 1,
        ma75Gap,
        macd,
        macdSignal,
        macdHistogram: macd - macdSignal,
        stochastic14: computeStochastic(rows, index, 14),
        adx14Approx,
        return1: pctChange(currentClose, Number(rows[index - 1].close)),
        return3: pctChange(currentClose, Number(rows[index - 3].close)),
        return5: pctChange(currentClose, Number(rows[index - 5].close)),
        return10: pctChange(currentClose, Number(rows[index - 10].close)),
        return20: pctChange(currentClose, Number(rows[index - 20].close)),
        gapOpenPrevClose: prevClose ? open / prevClose - 1 : 0,
        intradayReturn: open ? currentClose / open - 1 : 0,
        rangePosition52w: range52 === 0 ? 0.5 : (currentClose - low52) / range52,
        ...chartStructure,
        ...regime,
      });

      output.push(Object.freeze({
        symbol,
        sessionDate: current.sessionDate,
        featureCutoff: current.sessionDate,
        labelAvailableAt: next.sessionDate,
        close: currentClose,
        label: actualReturn > 0 ? 1 : 0,
        actualReturn,
        features: featureValues,
        ...featureValues,
        futureDataUsed: false,
      }));
    }
  }
  return Object.freeze(output);
}

export function splitDatasetByTime(rows = [], { trainRatio = 0.6, validationRatio = 0.2 } = {}) {
  if (!Array.isArray(rows)) throw new TypeError("rows must be an array");
  if (trainRatio <= 0 || validationRatio <= 0 || trainRatio + validationRatio >= 1) throw new RangeError("invalid split ratios");
  const sorted = [...rows].sort((a, b) => String(a.sessionDate).localeCompare(String(b.sessionDate)));
  const trainEnd = Math.floor(sorted.length * trainRatio);
  const validationEnd = trainEnd + Math.floor(sorted.length * validationRatio);
  const train = sorted.slice(0, trainEnd);
  const validation = sorted.slice(trainEnd, validationEnd);
  const test = sorted.slice(validationEnd);
  const lastTrain = train.at(-1)?.sessionDate ?? null;
  const firstValidation = validation[0]?.sessionDate ?? null;
  const lastValidation = validation.at(-1)?.sessionDate ?? null;
  const firstTest = test[0]?.sessionDate ?? null;
  const temporalOrderValid = (!lastTrain || !firstValidation || lastTrain <= firstValidation)
    && (!lastValidation || !firstTest || lastValidation <= firstTest);
  return Object.freeze({ status: temporalOrderValid ? "VALID" : "BLOCKED", train: Object.freeze(train), validation: Object.freeze(validation), test: Object.freeze(test), temporalOrderValid, safety: PHASE46_ADVANCED_SAFETY });
}

export function buildDatasetLineage({ datasetVersion, sourceManifestChecksum, featureVersion = "phase48-alpha-regime-v1", rows = [] } = {}) {
  if (!datasetVersion || !sourceManifestChecksum) throw new TypeError("datasetVersion and sourceManifestChecksum are required");
  const payload = { schemaVersion: 1, datasetVersion, sourceManifestChecksum, featureVersion, rowCount: rows.length, generatedAt: new Date().toISOString() };
  return Object.freeze({ ...payload, lineageChecksum: checksum(payload), safety: PHASE46_ADVANCED_SAFETY });
}

export function auditAdvancedDataset({ rows = [], split = null, lineage = null } = {}) {
  const blockers = [];
  const keys = new Set();
  for (const row of rows) {
    const key = `${row.symbol}:${row.sessionDate}`;
    if (keys.has(key)) blockers.push("DUPLICATE_ROW");
    keys.add(key);
    if (row.futureDataUsed !== false) blockers.push("FUTURE_DATA_FLAG");
    if (row.featureCutoff && row.featureCutoff > row.sessionDate) blockers.push("FEATURE_CUTOFF_AFTER_SESSION");
    if (![0, 1].includes(Number(row.label))) blockers.push("LABEL_INVALID");
    if (!Number.isFinite(Number(row.actualReturn))) blockers.push("ACTUAL_RETURN_INVALID");
    if (!row.features || !Object.values(row.features).some((value) => Number.isFinite(Number(value)))) blockers.push("FEATURES_MISSING");
    if (row.labelAvailableAt && row.labelAvailableAt <= row.sessionDate) blockers.push("LABEL_AVAILABILITY_INVALID");
  }
  if (split && split.temporalOrderValid !== true) blockers.push("TEMPORAL_SPLIT_INVALID");
  if (!lineage?.lineageChecksum) blockers.push("LINEAGE_MISSING");
  return Object.freeze({ status: blockers.length ? "BLOCKED" : "VALID", blockers: Object.freeze([...new Set(blockers)]), rowCount: rows.length, safety: PHASE46_ADVANCED_SAFETY });
}
