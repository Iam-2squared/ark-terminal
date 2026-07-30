const allowedRanges = new Set(["6mo", "1y", "2y", "5y"]);

const allowedIntervals = new Set(["1d", "1wk"]);

function normalizeSymbol(value) {
  const symbol = String(value || "")
    .trim()
    .toUpperCase()
    .replace(/\s+/g, "");

  if (/^(?:\d{4}|\d{3}[A-Z])$/.test(symbol)) {
    return `${symbol}.T`;
  }

  return symbol;
}

function finite(value) {
  return Number.isFinite(Number(value));
}

async function fetchYahooHistory({ symbol, range, interval }) {
  const url =
    "https://query2.finance.yahoo.com" +
    "/v8/finance/chart/" +
    encodeURIComponent(symbol) +
    `?range=${encodeURIComponent(range)}` +
    `&interval=${encodeURIComponent(interval)}` +
    "&events=div%2Csplits";

  const upstream = await fetch(url, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "User-Agent": "Mozilla/5.0 " + "(compatible; ArkTerminal/2.0)",
    },
  });

  if (!upstream.ok) {
    throw new Error(`Yahoo Finance HTTP ${upstream.status}`);
  }

  const payload = await upstream.json();

  const chart = payload.chart;

  if (chart?.error || !chart?.result?.[0]) {
    throw new Error(chart?.error?.description || "株価履歴がありません。");
  }

  const result = chart.result[0];

  const quote = result.indicators?.quote?.[0] || {};

  const timestamps = result.timestamp || [];

  const candles = timestamps
    .map((time, index) => ({
      time: Number(time),
      open: Number(quote.open?.[index]),
      high: Number(quote.high?.[index]),
      low: Number(quote.low?.[index]),
      close: Number(quote.close?.[index]),
      volume: Number(quote.volume?.[index]) || 0,
    }))
    .filter(
      (candle) =>
        finite(candle.time) &&
        finite(candle.open) &&
        finite(candle.high) &&
        finite(candle.low) &&
        finite(candle.close),
    );

  if (!candles.length) {
    throw new Error("有効な株価履歴がありません。");
  }

  const meta = result.meta || {};

  return {
    symbol,
    range,
    interval,
    provider: "yahoo-finance",
    meta: {
      currency: meta.currency || null,
      exchangeName: meta.exchangeName || meta.fullExchangeName || null,
      instrumentType: meta.instrumentType || null,
      timezone: meta.exchangeTimezoneName || null,
      regularMarketPrice: finite(meta.regularMarketPrice)
        ? Number(meta.regularMarketPrice)
        : null,
      previousClose: finite(meta.previousClose ?? meta.chartPreviousClose)
        ? Number(meta.previousClose ?? meta.chartPreviousClose)
        : null,
      regularMarketVolume: finite(meta.regularMarketVolume)
        ? Number(meta.regularMarketVolume)
        : null,
    },
    candles,
    updatedAt: new Date().toISOString(),
  };
}

export default async function handler(request, response) {
  response.setHeader("Access-Control-Allow-Origin", "*");

  response.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");

  response.setHeader(
    "Cache-Control",
    "s-maxage=60, stale-while-revalidate=300",
  );

  if (request.method === "OPTIONS") {
    return response.status(204).end();
  }

  if (request.method !== "GET") {
    return response.status(405).json({
      error: "GETのみ利用できます。",
    });
  }

  const symbol = normalizeSymbol(request.query.symbol);

  const range = allowedRanges.has(request.query.range)
    ? request.query.range
    : "2y";

  const interval = allowedIntervals.has(request.query.interval)
    ? request.query.interval
    : "1d";

  if (!symbol) {
    return response.status(400).json({
      error: "銘柄コードが必要です。",
    });
  }

  try {
    const history = await fetchYahooHistory({
      symbol,
      range,
      interval,
    });

    return response.status(200).json(history);
  } catch (error) {
    console.error("History API:", error);

    return response.status(502).json({
      error: "株価履歴の取得に失敗しました。",
      symbol,
    });
  }
}

export const HistoryInternals = {
  normalizeSymbol,
  fetchYahooHistory,
};
