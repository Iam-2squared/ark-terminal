const tradingViewSymbolMap = {
  AAPL: "NASDAQ:AAPL",
  AMD: "NASDAQ:AMD",
  AMZN: "NASDAQ:AMZN",
  BRK_B: "NYSE:BRK.B",
  GOOGL: "NASDAQ:GOOGL",
  META: "NASDAQ:META",
  MSFT: "NASDAQ:MSFT",
  MU: "NASDAQ:MU",
  NVDA: "NASDAQ:NVDA",
  TSM: "NYSE:TSM",
};

export function normalizeSymbol(value) {
  const symbol = String(value || "")
    .trim()
    .toUpperCase()
    .replace(/\s+/g, "");

  if (!symbol) {
    return "";
  }

  if (/^(?:\d{4}|\d{3}[A-Z])$/.test(symbol)) {
    return `${symbol}.T`;
  }

  return symbol;
}

export function isJapaneseSymbol(value) {
  return normalizeSymbol(value).endsWith(".T");
}

export function getTradingViewSymbol(value) {
  const symbol = normalizeSymbol(value);

  if (!symbol) {
    return "";
  }

  if (symbol.includes(":")) {
    return symbol;
  }

  if (isJapaneseSymbol(symbol)) {
    return `TSE:${symbol.slice(0, -2)}`;
  }

  return tradingViewSymbolMap[symbol.replace(".", "_")] || `NASDAQ:${symbol}`;
}

export function getCurrency(value) {
  return isJapaneseSymbol(value) ? "JPY" : "USD";
}

export function formatPrice(value, symbol) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "--";
  }

  return new Intl.NumberFormat("ja-JP", {
    style: "currency",
    currency: getCurrency(symbol),
    minimumFractionDigits: isJapaneseSymbol(symbol) ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(number);
}
