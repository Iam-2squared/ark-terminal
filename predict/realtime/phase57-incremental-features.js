const DEFAULT_WINDOWS = Object.freeze([3, 6, 12, 24]);

function finite(name, value) {
  if (!Number.isFinite(value)) throw new Error(`${name} must be finite`);
  return value;
}

function barTime(bar) {
  return bar.at ?? bar.time ?? bar.timestamp;
}

export function createSymbolFeatureState(symbol, { windows = DEFAULT_WINDOWS } = {}) {
  if (!symbol) throw new Error("symbol required");
  const normalizedWindows = [...new Set(windows)].map(Number).sort((a, b) => a - b);
  if (!normalizedWindows.length || normalizedWindows.some((x) => !Number.isInteger(x) || x <= 0)) {
    throw new Error("windows must contain positive integers");
  }
  return {
    symbol,
    windows: normalizedWindows,
    barsSeen: 0,
    lastBarTime: null,
    lastClose: null,
    sessionOpen: null,
    sessionHigh: null,
    sessionLow: null,
    cumulativeVolume: 0,
    cumulativeTypicalPriceVolume: 0,
    rolling: Object.fromEntries(normalizedWindows.map((window) => [window, []])),
    features: null,
  };
}

function rollingSnapshot(queue) {
  const n = queue.length;
  if (!n) return { n: 0, closeSma: null, volumeSma: null, high: null, low: null, returnPercent: null };
  const closeSma = queue.reduce((sum, bar) => sum + bar.close, 0) / n;
  const volumeSma = queue.reduce((sum, bar) => sum + bar.volume, 0) / n;
  const high = Math.max(...queue.map((bar) => bar.high));
  const low = Math.min(...queue.map((bar) => bar.low));
  const first = queue[0].open;
  const last = queue[n - 1].close;
  return {
    n,
    closeSma,
    volumeSma,
    high,
    low,
    returnPercent: first ? ((last / first) - 1) * 100 : null,
  };
}

export function applyFiveMinuteBar(symbolState, bar) {
  if (!symbolState?.symbol) throw new Error("symbol feature state required");
  const at = barTime(bar);
  if (!at) throw new Error("bar requires at/time/timestamp");
  if (symbolState.lastBarTime && at <= symbolState.lastBarTime) throw new Error("bar must be strictly causal");

  const open = finite("open", Number(bar.open));
  const high = finite("high", Number(bar.high));
  const low = finite("low", Number(bar.low));
  const close = finite("close", Number(bar.close));
  const volume = finite("volume", Number(bar.volume));
  if (open <= 0 || high <= 0 || low <= 0 || close <= 0 || volume < 0 || high < low) throw new Error("invalid OHLCV bar");

  const previousClose = symbolState.lastClose;
  const normalized = Object.freeze({ at, open, high, low, close, volume });
  symbolState.barsSeen += 1;
  symbolState.lastBarTime = at;
  symbolState.lastClose = close;
  symbolState.sessionOpen ??= open;
  symbolState.sessionHigh = symbolState.sessionHigh == null ? high : Math.max(symbolState.sessionHigh, high);
  symbolState.sessionLow = symbolState.sessionLow == null ? low : Math.min(symbolState.sessionLow, low);
  symbolState.cumulativeVolume += volume;
  const typicalPrice = (high + low + close) / 3;
  symbolState.cumulativeTypicalPriceVolume += typicalPrice * volume;

  const rolling = {};
  for (const window of symbolState.windows) {
    const queue = symbolState.rolling[window];
    queue.push(normalized);
    if (queue.length > window) queue.shift();
    rolling[window] = rollingSnapshot(queue);
  }

  const features = Object.freeze({
    symbol: symbolState.symbol,
    at,
    barsSeen: symbolState.barsSeen,
    open,
    high,
    low,
    close,
    volume,
    barReturnPercent: previousClose ? ((close / previousClose) - 1) * 100 : null,
    sessionReturnPercent: symbolState.sessionOpen ? ((close / symbolState.sessionOpen) - 1) * 100 : null,
    sessionHigh: symbolState.sessionHigh,
    sessionLow: symbolState.sessionLow,
    cumulativeVolume: symbolState.cumulativeVolume,
    vwap: symbolState.cumulativeVolume > 0 ? symbolState.cumulativeTypicalPriceVolume / symbolState.cumulativeVolume : null,
    rolling: Object.freeze(rolling),
  });
  symbolState.features = features;
  return features;
}

export function applyMarketFiveMinuteBar(sessionState, { symbol, bar, windows = DEFAULT_WINDOWS } = {}) {
  if (!sessionState?.symbols) throw new Error("realtime session state required");
  if (!symbol) throw new Error("symbol required");
  const at = barTime(bar);
  if (!at) throw new Error("bar requires at/time/timestamp");
  // Market-wide causal clock: all symbols may share the current bucket, but a
  // later accepted bucket makes any older cross-symbol arrival invalid.
  if (sessionState.lastBarTime && Date.parse(String(at)) < Date.parse(String(sessionState.lastBarTime))) {
    throw new Error("market bar timestamp cannot move backward across symbols");
  }
  sessionState.symbols[symbol] ??= createSymbolFeatureState(symbol, { windows });
  const features = applyFiveMinuteBar(sessionState.symbols[symbol], bar);
  if (!sessionState.lastBarTime || Date.parse(String(features.at)) > Date.parse(String(sessionState.lastBarTime))) {
    sessionState.lastBarTime = features.at;
  }
  return features;
}

export { DEFAULT_WINDOWS };
