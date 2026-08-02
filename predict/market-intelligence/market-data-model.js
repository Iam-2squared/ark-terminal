export const MARKET_DATA_STATUS = Object.freeze({
  AVAILABLE: "available",
  STALE: "stale",
  UNAVAILABLE: "unavailable",
  ERROR: "error",
});

const VALID_STATUSES = new Set(Object.values(MARKET_DATA_STATUS));

function freezeDefinition(definition) {
  return Object.freeze({
    ...definition,
    aliases: Object.freeze([...(definition.aliases || [])]),
  });
}

export const MARKET_DATA_DEFINITIONS = Object.freeze([
  freezeDefinition({
    symbol: "NIKKEI225",
    label: "日経平均",
    providerSymbol: "^N225",
    assetClass: "index",
    region: "JP",
    source: "yahoo-finance",
    confidence: 95,
    isProxy: false,
    aliases: ["NIKKEI", "N225", "^N225"],
  }),
  freezeDefinition({
    symbol: "TOPIX",
    label: "TOPIX",
    providerSymbol: "1306.T",
    assetClass: "index",
    region: "JP",
    source: "yahoo-finance-etf-proxy",
    confidence: 72,
    isProxy: true,
    aliases: ["1306.T"],
  }),
  freezeDefinition({
    symbol: "JPX400",
    label: "JPX400",
    providerSymbol: "1591.T",
    assetClass: "index",
    region: "JP",
    source: "yahoo-finance-etf-proxy",
    confidence: 72,
    isProxy: true,
    aliases: ["JPX-NIKKEI400", "1591.T"],
  }),
  freezeDefinition({
    symbol: "GROWTH250",
    label: "グロース250",
    providerSymbol: "2516.T",
    assetClass: "index",
    region: "JP",
    source: "yahoo-finance-etf-proxy",
    confidence: 70,
    isProxy: true,
    aliases: ["TSE-GROWTH250", "2516.T"],
  }),
  freezeDefinition({
    symbol: "NASDAQ",
    label: "NASDAQ",
    providerSymbol: "^IXIC",
    assetClass: "index",
    region: "US",
    source: "yahoo-finance",
    confidence: 95,
    isProxy: false,
    aliases: ["NASDAQ-COMPOSITE", "IXIC", "^IXIC"],
  }),
  freezeDefinition({
    symbol: "SP500",
    label: "S&P500",
    providerSymbol: "^GSPC",
    assetClass: "index",
    region: "US",
    source: "yahoo-finance",
    confidence: 95,
    isProxy: false,
    aliases: ["S&P500", "SANDP500", "GSPC", "^GSPC"],
  }),
  freezeDefinition({
    symbol: "SOX",
    label: "SOX",
    providerSymbol: "^SOX",
    assetClass: "index",
    region: "US",
    source: "yahoo-finance",
    confidence: 95,
    isProxy: false,
    aliases: ["PHLX-SOX", "^SOX"],
  }),
  freezeDefinition({
    symbol: "RUSSELL2000",
    label: "Russell2000",
    providerSymbol: "^RUT",
    assetClass: "index",
    region: "US",
    source: "yahoo-finance",
    confidence: 95,
    isProxy: false,
    aliases: ["RUSSELL-2000", "RUT", "^RUT"],
  }),
  freezeDefinition({
    symbol: "VIX",
    label: "VIX",
    providerSymbol: "^VIX",
    assetClass: "volatility-index",
    region: "US",
    source: "yahoo-finance",
    confidence: 95,
    isProxy: false,
    aliases: ["^VIX"],
  }),
  freezeDefinition({
    symbol: "USDJPY",
    label: "USD/JPY",
    providerSymbol: "JPY=X",
    assetClass: "fx",
    region: "GLOBAL",
    source: "yahoo-finance",
    confidence: 92,
    isProxy: false,
    aliases: ["USD/JPY", "USD-JPY", "JPY=X"],
  }),
  freezeDefinition({
    symbol: "US10Y",
    label: "米国10年債利回り",
    providerSymbol: "^TNX",
    assetClass: "yield",
    region: "US",
    source: "yahoo-finance",
    confidence: 92,
    isProxy: false,
    aliases: ["US-10Y", "TNX", "^TNX"],
  }),
  freezeDefinition({
    symbol: "WTI",
    label: "WTI原油",
    providerSymbol: "CL=F",
    assetClass: "commodity",
    region: "GLOBAL",
    source: "yahoo-finance",
    confidence: 90,
    isProxy: false,
    aliases: ["CRUDE-OIL", "CL=F"],
  }),
  freezeDefinition({
    symbol: "GOLD",
    label: "金",
    providerSymbol: "GC=F",
    assetClass: "commodity",
    region: "GLOBAL",
    source: "yahoo-finance",
    confidence: 90,
    isProxy: false,
    aliases: ["XAU", "GC=F"],
  }),
  freezeDefinition({
    symbol: "BITCOIN",
    label: "Bitcoin",
    providerSymbol: "BTC-USD",
    assetClass: "crypto",
    region: "GLOBAL",
    source: "yahoo-finance",
    confidence: 90,
    isProxy: false,
    aliases: ["BTC", "BTCUSD", "BTC-USD"],
  }),
  freezeDefinition({
    symbol: "ETHEREUM",
    label: "Ethereum",
    providerSymbol: "ETH-USD",
    assetClass: "crypto",
    region: "GLOBAL",
    source: "yahoo-finance",
    confidence: 90,
    isProxy: false,
    aliases: ["ETH", "ETHUSD", "ETH-USD"],
  }),
]);

function lookupKey(value) {
  return String(value ?? "")
    .trim()
    .toUpperCase()
    .replace(/[\s/_-]+/g, "")
    .replace(/&/g, "AND");
}

const DEFINITION_LOOKUP = new Map();

for (const definition of MARKET_DATA_DEFINITIONS) {
  const values = [
    definition.symbol,
    definition.providerSymbol,
    ...definition.aliases,
  ];

  for (const value of values) {
    const key = lookupKey(value);

    if (key) {
      DEFINITION_LOOKUP.set(key, definition);
    }
  }
}

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function timestampOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const numericTimestamp =
    typeof value === "number" || /^\d+(?:\.\d+)?$/.test(String(value))
      ? Number(value)
      : null;
  const date = new Date(
    numericTimestamp !== null && numericTimestamp < 1_000_000_000_000
      ? numericTimestamp * 1000
      : value,
  );
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function clampConfidence(value) {
  const number = finiteOrNull(value) ?? 0;
  return Math.round(Math.max(0, Math.min(100, number)));
}

export function getMarketDataDefinition(value) {
  const candidate = value && typeof value === "object" ? value.symbol : value;
  return DEFINITION_LOOKUP.get(lookupKey(candidate)) ?? null;
}

export function listMarketDataDefinitions() {
  return [...MARKET_DATA_DEFINITIONS];
}

export function createMarketDataPoint({
  symbol,
  price = null,
  change = null,
  changePercent = null,
  timestamp = null,
  source = "unknown",
  status,
  confidence = 0,
} = {}) {
  const definition = getMarketDataDefinition(symbol);
  const normalizedSymbol = definition?.symbol || String(symbol || "").trim();

  if (!normalizedSymbol) {
    throw new TypeError("Market data symbol is required.");
  }

  const normalizedPrice = finiteOrNull(price);
  const requestedStatus = VALID_STATUSES.has(status)
    ? status
    : normalizedPrice !== null && normalizedPrice > 0
      ? MARKET_DATA_STATUS.AVAILABLE
      : MARKET_DATA_STATUS.UNAVAILABLE;
  const normalizedStatus =
    normalizedPrice === null || normalizedPrice <= 0
      ? requestedStatus === MARKET_DATA_STATUS.ERROR
        ? MARKET_DATA_STATUS.ERROR
        : MARKET_DATA_STATUS.UNAVAILABLE
      : requestedStatus;
  const exposesPrice =
    normalizedStatus === MARKET_DATA_STATUS.AVAILABLE ||
    normalizedStatus === MARKET_DATA_STATUS.STALE;

  return Object.freeze({
    symbol: normalizedSymbol,
    price: exposesPrice ? normalizedPrice : null,
    change: exposesPrice ? finiteOrNull(change) : null,
    changePercent: exposesPrice ? finiteOrNull(changePercent) : null,
    timestamp: timestampOrNull(timestamp),
    source: String(source || "unknown"),
    status: normalizedStatus,
    confidence: exposesPrice ? clampConfidence(confidence) : 0,
  });
}

export function isMarketDataPoint(value) {
  if (!value || typeof value !== "object") {
    return false;
  }

  const definition = getMarketDataDefinition(value.symbol);
  const price = finiteOrNull(value.price);
  const confidence = finiteOrNull(value.confidence);
  const validTimestamp =
    value.timestamp === null || timestampOrNull(value.timestamp) !== null;

  return Boolean(
    definition &&
      VALID_STATUSES.has(value.status) &&
      typeof value.source === "string" &&
      validTimestamp &&
      confidence !== null &&
      confidence >= 0 &&
      confidence <= 100 &&
      ((value.status === MARKET_DATA_STATUS.AVAILABLE ||
        value.status === MARKET_DATA_STATUS.STALE)
        ? price !== null && price > 0
        : value.price === null),
  );
}

export default MARKET_DATA_DEFINITIONS;
