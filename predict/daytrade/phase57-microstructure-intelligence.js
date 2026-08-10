export const PHASE57_P22_SAFETY = Object.freeze({
  mode: 'PHASE57_MICROSTRUCTURE_READ_ONLY_RESEARCH',
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

// Official MARKETSPEED II RSS 2026-03-30 contract used by P22.
// RssTickList exposes time, executed volume and executed price only; it does NOT expose aggressor side.
export const MARKETSPEED_II_P22_READ_ONLY_CONTRACT = Object.freeze({
  RssTickList: Object.freeze({
    mode: 'READ_ONLY',
    maxRows: 300,
    officialFields: Object.freeze(['時刻', '出来高', '約定値']),
    nativeAggressorSideAvailable: false,
  }),
  RssMarket: Object.freeze({
    mode: 'READ_ONLY',
    officialTopOfBookFields: Object.freeze(['最良売気配値', '最良買気配値', '最良売気配数量', '最良買気配数量', '最良売気配詳細時刻', '最良買気配詳細時刻']),
    officialDepthPattern: Object.freeze({
      askPrice: '最良売気配値1..10',
      bidPrice: '最良買気配値1..10',
      askSize: '最良売気配数量1..10',
      bidSize: '最良買気配数量1..10',
      overSize: 'OVER気配数量',
      underSize: 'UNDER気配数量',
    }),
  }),
  orderFunctionsUsed: false,
});

const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const numberOrNull = value => finite(value) ? Number(value) : null;
const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
const mean = values => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;

function timeMs(value) {
  const parsed = Date.parse(value ?? '');
  return Number.isFinite(parsed) ? parsed : null;
}

function firstValue(object, keys) {
  for (const key of keys) if (object && object[key] !== undefined && object[key] !== null && object[key] !== '') return object[key];
  return null;
}

function imbalance(bid, ask) {
  if (!finite(bid) || !finite(ask)) return null;
  const total = Number(bid) + Number(ask);
  return total === 0 ? 0 : (Number(bid) - Number(ask)) / total;
}

function normalizeLevel(snapshot, side, level) {
  const isAsk = side === 'ask';
  const priceKeys = isAsk
    ? [`askPrice${level}`, `sellPrice${level}`, `最良売気配値${level}`]
    : [`bidPrice${level}`, `buyPrice${level}`, `最良買気配値${level}`];
  const sizeKeys = isAsk
    ? [`askSize${level}`, `sellSize${level}`, `最良売気配数量${level}`]
    : [`bidSize${level}`, `buySize${level}`, `最良買気配数量${level}`];
  const price = numberOrNull(firstValue(snapshot, priceKeys));
  const size = numberOrNull(firstValue(snapshot, sizeKeys));
  return price !== null || size !== null ? Object.freeze({ level, price, size }) : null;
}

function normalizeQuoteSnapshot(snapshot = {}) {
  const timestamp = firstValue(snapshot, ['timestamp', 'capturedAt', 'asOf', 'time']);
  const bestAsk = numberOrNull(firstValue(snapshot, ['bestAsk', 'ask', '最良売気配値']));
  const bestBid = numberOrNull(firstValue(snapshot, ['bestBid', 'bid', '最良買気配値']));
  const askSize = numberOrNull(firstValue(snapshot, ['askSize', 'bestAskSize', '最良売気配数量']));
  const bidSize = numberOrNull(firstValue(snapshot, ['bidSize', 'bestBidSize', '最良買気配数量']));
  const asks = [];
  const bids = [];
  for (let level = 1; level <= 10; level += 1) {
    const askLevel = normalizeLevel(snapshot, 'ask', level);
    const bidLevel = normalizeLevel(snapshot, 'bid', level);
    if (askLevel) asks.push(askLevel);
    if (bidLevel) bids.push(bidLevel);
  }
  return Object.freeze({
    timestamp: timestamp ?? null,
    timeMs: timeMs(timestamp),
    bestAsk,
    bestBid,
    askSize,
    bidSize,
    asks: Object.freeze(asks),
    bids: Object.freeze(bids),
    overSize: numberOrNull(firstValue(snapshot, ['overSize', 'OVER気配数量'])),
    underSize: numberOrNull(firstValue(snapshot, ['underSize', 'UNDER気配数量'])),
  });
}

function normalizeTick(tick = {}, index = 0) {
  const timestamp = firstValue(tick, ['timestamp', 'capturedAt', 'time', '時刻']);
  const price = numberOrNull(firstValue(tick, ['price', 'executionPrice', '約定値']));
  const size = numberOrNull(firstValue(tick, ['size', 'volume', 'executionVolume', '出来高']));
  if (price === null || price <= 0) return null;
  return Object.freeze({ index, timestamp: timestamp ?? null, timeMs: timeMs(timestamp), price, size: size ?? 0 });
}

function weightedDepth(sideLevels) {
  let weighted = 0;
  let raw = 0;
  let levels = 0;
  for (const level of sideLevels) {
    if (!finite(level.size) || Number(level.size) < 0) continue;
    const size = Number(level.size);
    raw += size;
    weighted += size / Math.max(1, Number(level.level));
    levels += 1;
  }
  return { weighted, raw, levels };
}

function quoteFeatures(quote) {
  const spread = finite(quote.bestAsk) && finite(quote.bestBid) ? quote.bestAsk - quote.bestBid : null;
  const mid = finite(quote.bestAsk) && finite(quote.bestBid) ? (quote.bestAsk + quote.bestBid) / 2 : null;
  const spreadBps = finite(spread) && finite(mid) && mid !== 0 ? spread / mid * 10000 : null;
  const topBookImbalance = imbalance(quote.bidSize, quote.askSize);
  const askDepth = weightedDepth(quote.asks);
  const bidDepth = weightedDepth(quote.bids);
  const depthImbalance = imbalance(bidDepth.raw, askDepth.raw);
  const weightedDepthImbalance = imbalance(bidDepth.weighted, askDepth.weighted);
  const microprice = finite(quote.bestAsk) && finite(quote.bestBid) && finite(quote.bidSize) && finite(quote.askSize) && quote.bidSize + quote.askSize > 0
    ? (quote.bestAsk * quote.bidSize + quote.bestBid * quote.askSize) / (quote.bidSize + quote.askSize)
    : null;
  const micropriceEdgeBps = finite(microprice) && finite(mid) && mid !== 0 ? (microprice / mid - 1) * 10000 : null;
  const overUnderImbalance = imbalance(quote.underSize, quote.overSize);
  return Object.freeze({
    bestBid: quote.bestBid,
    bestAsk: quote.bestAsk,
    bidSize: quote.bidSize,
    askSize: quote.askSize,
    mid,
    spread,
    spreadBps,
    topBookImbalance,
    bidDepth: bidDepth.raw,
    askDepth: askDepth.raw,
    depthImbalance,
    weightedBidDepth: bidDepth.weighted,
    weightedAskDepth: askDepth.weighted,
    weightedDepthImbalance,
    microprice,
    micropriceEdgeBps,
    overSize: quote.overSize,
    underSize: quote.underSize,
    overUnderImbalance,
  });
}

function latestCausalQuote(quotes, tickTimeMs) {
  if (tickTimeMs === null) return null;
  let found = null;
  for (const quote of quotes) {
    if (quote.timeMs === null || quote.timeMs > tickTimeMs) break;
    found = quote;
  }
  return found;
}

function classifyTicks(ticks, quotes) {
  const classified = [];
  let previousPrice = null;
  for (const tick of ticks) {
    const quote = latestCausalQuote(quotes, tick.timeMs);
    let side = 0;
    let method = 'UNCLASSIFIED';
    if (quote && finite(quote.bestAsk) && finite(quote.bestBid)) {
      if (tick.price >= quote.bestAsk) {
        side = 1;
        method = 'CAUSAL_QUOTE_ASK';
      } else if (tick.price <= quote.bestBid) {
        side = -1;
        method = 'CAUSAL_QUOTE_BID';
      }
    }
    if (side === 0 && previousPrice !== null) {
      if (tick.price > previousPrice) {
        side = 1;
        method = 'TICK_RULE_UP';
      } else if (tick.price < previousPrice) {
        side = -1;
        method = 'TICK_RULE_DOWN';
      }
    }
    classified.push(Object.freeze({ ...tick, side, method, quoteTimestamp: quote?.timestamp ?? null }));
    previousPrice = tick.price;
  }
  return Object.freeze(classified);
}

function flowFeatures(classifiedTicks) {
  const buyVolume = classifiedTicks.filter(tick => tick.side > 0).reduce((sum, tick) => sum + tick.size, 0);
  const sellVolume = classifiedTicks.filter(tick => tick.side < 0).reduce((sum, tick) => sum + tick.size, 0);
  const knownVolume = buyVolume + sellVolume;
  const totalVolume = classifiedTicks.reduce((sum, tick) => sum + tick.size, 0);
  const signedVolumeImbalance = knownVolume > 0 ? (buyVolume - sellVolume) / knownVolume : null;
  const aggressiveBuyRatio = knownVolume > 0 ? buyVolume / knownVolume : null;
  const knownCount = classifiedTicks.filter(tick => tick.side !== 0).length;
  const quoteClassifiedCount = classifiedTicks.filter(tick => tick.method.startsWith('CAUSAL_QUOTE_')).length;
  const tickRuleClassifiedCount = classifiedTicks.filter(tick => tick.method.startsWith('TICK_RULE_')).length;
  const firstTime = classifiedTicks.find(tick => tick.timeMs !== null)?.timeMs ?? null;
  const lastTime = [...classifiedTicks].reverse().find(tick => tick.timeMs !== null)?.timeMs ?? null;
  const durationSeconds = firstTime !== null && lastTime !== null && lastTime > firstTime ? (lastTime - firstTime) / 1000 : null;
  const tradeIntensityPerSecond = finite(durationSeconds) && durationSeconds > 0 ? classifiedTicks.length / durationSeconds : null;
  const meanTradeSize = classifiedTicks.length ? mean(classifiedTicks.map(tick => tick.size)) : null;
  return Object.freeze({
    tickCount: classifiedTicks.length,
    totalVolume,
    buyVolume,
    sellVolume,
    knownAggressorVolume: knownVolume,
    aggressiveBuyRatio,
    aggressiveSellRatio: aggressiveBuyRatio === null ? null : 1 - aggressiveBuyRatio,
    signedVolumeImbalance,
    classifiedTickFraction: classifiedTicks.length ? knownCount / classifiedTicks.length : null,
    quoteClassifiedCount,
    tickRuleClassifiedCount,
    unclassifiedCount: classifiedTicks.length - knownCount,
    tradeIntensityPerSecond,
    meanTradeSize,
  });
}

function quoteHistoryFeatures(quotes) {
  const spreads = quotes.map(quoteFeatures).map(feature => feature.spreadBps).filter(finite);
  const imbalances = quotes.map(quoteFeatures).map(feature => feature.topBookImbalance).filter(finite);
  const validTimes = quotes.map(quote => quote.timeMs).filter(value => value !== null);
  const durationSeconds = validTimes.length >= 2 && validTimes.at(-1) > validTimes[0] ? (validTimes.at(-1) - validTimes[0]) / 1000 : null;
  return Object.freeze({
    quoteSnapshotCount: quotes.length,
    averageSpreadBps: mean(spreads),
    latestSpreadBps: spreads.at(-1) ?? null,
    spreadChangeBps: spreads.length >= 2 ? spreads.at(-1) - spreads[0] : null,
    averageTopBookImbalance: mean(imbalances),
    latestTopBookImbalance: imbalances.at(-1) ?? null,
    quoteUpdateRatePerSecond: finite(durationSeconds) && durationSeconds > 0 ? (quotes.length - 1) / durationSeconds : null,
  });
}

export function buildMicrostructureIntelligence({
  snapshot = {},
  quoteSnapshots = [],
  ticks = [],
  asOf = null,
} = {}) {
  const current = normalizeQuoteSnapshot(snapshot);
  const history = (Array.isArray(quoteSnapshots) ? quoteSnapshots : []).map(normalizeQuoteSnapshot)
    .filter(quote => quote.timeMs !== null)
    .sort((a, b) => a.timeMs - b.timeMs);
  if (current.timeMs !== null && !history.some(quote => quote.timeMs === current.timeMs)) history.push(current);
  history.sort((a, b) => (a.timeMs ?? Infinity) - (b.timeMs ?? Infinity));
  const normalizedTicks = (Array.isArray(ticks) ? ticks : []).map(normalizeTick).filter(Boolean)
    .sort((a, b) => (a.timeMs ?? Infinity) - (b.timeMs ?? Infinity));
  const classifiedTicks = classifyTicks(normalizedTicks, history);
  const currentFeatures = quoteFeatures(current);
  const flow = flowFeatures(classifiedTicks);
  const quoteHistory = quoteHistoryFeatures(history);
  const asOfMs = timeMs(asOf);
  const latestQuoteMs = history.filter(quote => quote.timeMs !== null).at(-1)?.timeMs ?? current.timeMs;
  const latestTickMs = normalizedTicks.filter(tick => tick.timeMs !== null).at(-1)?.timeMs ?? null;
  const quoteStalenessMs = asOfMs !== null && latestQuoteMs !== null ? Math.max(0, asOfMs - latestQuoteMs) : null;
  const tickStalenessMs = asOfMs !== null && latestTickMs !== null ? Math.max(0, asOfMs - latestTickMs) : null;
  const futureQuoteAssignments = classifiedTicks.filter(tick => tick.quoteTimestamp && tick.timeMs !== null && timeMs(tick.quoteTimestamp) > tick.timeMs).length;

  return Object.freeze({
    phase: '57.p22',
    status: finite(currentFeatures.bestBid) && finite(currentFeatures.bestAsk) ? 'MICROSTRUCTURE_INTELLIGENCE_READY' : 'PARTIAL_MICROSTRUCTURE_INTELLIGENCE',
    features: Object.freeze({ ...currentFeatures, ...flow, ...quoteHistory, quoteStalenessMs, tickStalenessMs }),
    dataQuality: Object.freeze({
      quoteSnapshotCount: history.length,
      tickCount: normalizedTicks.length,
      futureQuoteAssignments,
      causalQuoteMatching: true,
      nativeAggressorSideAssumed: false,
      rssTickListNativeAggressorSideAvailable: false,
      maxOfficialRssTickRows: 300,
    }),
    classifiedTicks,
    source: Object.freeze({
      mode: 'READ_ONLY',
      functions: Object.freeze(['RssMarket', 'RssTickList']),
      officialContract: MARKETSPEED_II_P22_READ_ONLY_CONTRACT,
      rssOrderFunctionsUsed: false,
    }),
    researchOnly: true,
    reviewOnly: true,
    recommendationAllowed: false,
    paperTradingAllowed: false,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
    humanApprovalRequired: true,
    safety: PHASE57_P22_SAFETY,
  });
}

export default { buildMicrostructureIntelligence };
