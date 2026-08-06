import {
  PHASE42_SAFETY,
  createFeatureRecord,
  createFeatureStoreShard,
  auditFeatureStoreShard,
  buildFeatureStoreManifest,
  validateFeatureStoreManifest,
} from "./phase42-feature-store.js";

function finite(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function mean(values) {
  const items = values.filter(Number.isFinite);
  return items.length ? items.reduce((sum, value) => sum + value, 0) / items.length : null;
}

function stddev(values) {
  const items = values.filter(Number.isFinite);
  if (items.length < 2) return null;
  const average = mean(items);
  return Math.sqrt(items.reduce((sum, value) => sum + ((value - average) ** 2), 0) / items.length);
}

function ema(values, period) {
  const items = values.filter(Number.isFinite);
  if (!items.length) return null;
  const multiplier = 2 / (period + 1);
  let result = items[0];
  for (let index = 1; index < items.length; index += 1) {
    result = (items[index] - result) * multiplier + result;
  }
  return result;
}

function rollingWindow(values, endIndex, period) {
  const start = Math.max(0, endIndex - period + 1);
  return values.slice(start, endIndex + 1);
}

function computeRsi(closes, endIndex, period = 14) {
  if (endIndex < 1) return null;
  const start = Math.max(1, endIndex - period + 1);
  let gains = 0;
  let losses = 0;
  let count = 0;
  for (let index = start; index <= endIndex; index += 1) {
    const change = closes[index] - closes[index - 1];
    if (!Number.isFinite(change)) continue;
    if (change >= 0) gains += change;
    else losses += Math.abs(change);
    count += 1;
  }
  if (!count) return null;
  if (losses === 0) return 100;
  const rs = (gains / count) / (losses / count);
  return 100 - (100 / (1 + rs));
}

function computeTrueRange(records, index) {
  const current = records[index];
  if (!current) return null;
  const high = finite(current.high);
  const low = finite(current.low);
  const previousClose = index > 0 ? finite(records[index - 1].close) : null;
  if (!Number.isFinite(high) || !Number.isFinite(low)) return null;
  const candidates = [high - low];
  if (Number.isFinite(previousClose)) {
    candidates.push(Math.abs(high - previousClose));
    candidates.push(Math.abs(low - previousClose));
  }
  return Math.max(...candidates.filter(Number.isFinite));
}

function computeAtr(records, endIndex, period = 14) {
  const values = [];
  const start = Math.max(0, endIndex - period + 1);
  for (let index = start; index <= endIndex; index += 1) values.push(computeTrueRange(records, index));
  return mean(values);
}

function computeVwap(records, endIndex, period = 20) {
  let weighted = 0;
  let volumeSum = 0;
  const start = Math.max(0, endIndex - period + 1);
  for (let index = start; index <= endIndex; index += 1) {
    const item = records[index];
    const high = finite(item.high);
    const low = finite(item.low);
    const close = finite(item.close);
    const volume = finite(item.volume);
    if (![high, low, close, volume].every(Number.isFinite) || volume <= 0) continue;
    const typical = (high + low + close) / 3;
    weighted += typical * volume;
    volumeSum += volume;
  }
  return volumeSum > 0 ? weighted / volumeSum : null;
}

function computeAdx(records, endIndex, period = 14) {
  if (endIndex < 1) return null;
  const plusDm = [];
  const minusDm = [];
  const trs = [];
  const start = Math.max(1, endIndex - period + 1);
  for (let index = start; index <= endIndex; index += 1) {
    const current = records[index];
    const previous = records[index - 1];
    const currentHigh = finite(current.high);
    const currentLow = finite(current.low);
    const previousHigh = finite(previous.high);
    const previousLow = finite(previous.low);
    if (![currentHigh, currentLow, previousHigh, previousLow].every(Number.isFinite)) continue;
    const upMove = currentHigh - previousHigh;
    const downMove = previousLow - currentLow;
    plusDm.push(upMove > downMove && upMove > 0 ? upMove : 0);
    minusDm.push(downMove > upMove && downMove > 0 ? downMove : 0);
    trs.push(computeTrueRange(records, index));
  }
  const atr = mean(trs);
  if (!Number.isFinite(atr) || atr === 0) return null;
  const plusDi = 100 * (mean(plusDm) / atr);
  const minusDi = 100 * (mean(minusDm) / atr);
  const denominator = plusDi + minusDi;
  return denominator === 0 ? 0 : 100 * Math.abs(plusDi - minusDi) / denominator;
}

function computeFeatures(records, index) {
  const closes = records.map((record) => finite(record.close));
  const volumes = records.map((record) => finite(record.volume));
  const close = closes[index];
  const previousClose = index > 0 ? closes[index - 1] : null;
  const ma5 = mean(rollingWindow(closes, index, 5));
  const ma25 = mean(rollingWindow(closes, index, 25));
  const ma75 = mean(rollingWindow(closes, index, 75));
  const ema12 = ema(rollingWindow(closes, index, 60), 12);
  const ema26 = ema(rollingWindow(closes, index, 90), 26);
  const macd = Number.isFinite(ema12) && Number.isFinite(ema26) ? ema12 - ema26 : null;
  const bbWindow = rollingWindow(closes, index, 20);
  const bbMiddle = mean(bbWindow);
  const bbStd = stddev(bbWindow);
  const bbUpper = Number.isFinite(bbMiddle) && Number.isFinite(bbStd) ? bbMiddle + (2 * bbStd) : null;
  const bbLower = Number.isFinite(bbMiddle) && Number.isFinite(bbStd) ? bbMiddle - (2 * bbStd) : null;
  const volume20 = mean(rollingWindow(volumes, index, 20));
  const return1d = Number.isFinite(close) && Number.isFinite(previousClose) && previousClose !== 0
    ? (close / previousClose) - 1
    : null;
  const returns20 = rollingWindow(closes, index, 21)
    .map((value, position, items) => position === 0 || !Number.isFinite(value) || !Number.isFinite(items[position - 1]) || items[position - 1] === 0
      ? null
      : (value / items[position - 1]) - 1);

  return {
    close,
    return1d,
    ma5,
    ma25,
    ma75,
    ma5Distance: Number.isFinite(close) && Number.isFinite(ma5) && ma5 !== 0 ? (close / ma5) - 1 : null,
    ma25Distance: Number.isFinite(close) && Number.isFinite(ma25) && ma25 !== 0 ? (close / ma25) - 1 : null,
    ma75Distance: Number.isFinite(close) && Number.isFinite(ma75) && ma75 !== 0 ? (close / ma75) - 1 : null,
    rsi14: computeRsi(closes, index, 14),
    macd,
    atr14: computeAtr(records, index, 14),
    adx14: computeAdx(records, index, 14),
    vwap20: computeVwap(records, index, 20),
    bbMiddle20: bbMiddle,
    bbUpper20: bbUpper,
    bbLower20: bbLower,
    bbWidth20: Number.isFinite(bbUpper) && Number.isFinite(bbLower) && Number.isFinite(bbMiddle) && bbMiddle !== 0
      ? (bbUpper - bbLower) / bbMiddle
      : null,
    volumeRatio20: Number.isFinite(volumes[index]) && Number.isFinite(volume20) && volume20 !== 0
      ? volumes[index] / volume20
      : null,
    volatility20: stddev(returns20),
  };
}

export function generateFeatureRecordsFromDataLake(shard, options = {}) {
  const featureSetId = String(options.featureSetId ?? "core-v1");
  const records = (shard?.records ?? [])
    .filter((record) => record.kind === "OHLCV")
    .sort((a, b) => `${a.symbol}:${a.sessionDate}`.localeCompare(`${b.symbol}:${b.sessionDate}`));
  const grouped = new Map();
  for (const record of records) {
    if (!grouped.has(record.symbol)) grouped.set(record.symbol, []);
    grouped.get(record.symbol).push(record);
  }

  const generated = [];
  for (const [symbol, symbolRecords] of grouped.entries()) {
    for (let index = 0; index < symbolRecords.length; index += 1) {
      const source = symbolRecords[index];
      generated.push(createFeatureRecord({
        featureSetId,
        symbol,
        sessionDate: source.sessionDate,
        generatedAt: options.generatedAt ?? source.updatedAt,
        sourceShardId: shard?.shardId ?? null,
        sourceChecksum: shard?.checksum ?? null,
        features: computeFeatures(symbolRecords, index),
      }));
    }
  }
  return generated;
}

export function buildFeatureIntegrationBundle(dataLakeShard, options = {}) {
  const records = generateFeatureRecordsFromDataLake(dataLakeShard, options);
  const shard = createFeatureStoreShard({ records });
  const audit = auditFeatureStoreShard(shard, {
    minimumFeatures: options.minimumFeatures ?? 10,
    maximumMissingRate: options.maximumMissingRate ?? 0.55,
  });
  const manifest = buildFeatureStoreManifest({ shards: [shard], generatedAt: options.generatedAt });
  const validation = validateFeatureStoreManifest(manifest, [shard]);
  const blockers = [...audit.blockers, ...validation.blockers];

  return {
    status: blockers.length ? "BLOCKED" : "READY_FOR_HUMAN_REVIEW",
    records,
    shard,
    audit,
    manifest,
    validation,
    dashboard: {
      featureSetId: records[0]?.featureSetId ?? options.featureSetId ?? "core-v1",
      symbols: [...new Set(records.map((record) => record.symbol))],
      recordCount: records.length,
      featureCount: audit.totalFeatures,
      missingRate: audit.missingRate,
      latestSessionDate: records.map((record) => record.sessionDate).sort().at(-1) ?? null,
      sourceShardId: dataLakeShard?.shardId ?? null,
      sourceChecksum: dataLakeShard?.checksum ?? null,
      canUseForTraining: blockers.length === 0,
      reviewRequired: true,
      blockers: [...new Set(blockers)],
      warnings: [...new Set(audit.warnings)],
    },
    integrations: {
      predictionLab: { enabled: blockers.length === 0, mode: "READ_ONLY_FEATURE_INPUT" },
      backtest: { enabled: blockers.length === 0, mode: "READ_ONLY_FEATURE_INPUT" },
      candidateEvaluation: { enabled: blockers.length === 0, automaticPromotionAllowed: false },
    },
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...PHASE42_SAFETY },
  };
}
