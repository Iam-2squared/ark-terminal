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

function normalizeSplits(events) {
  return Object.values(events?.splits || {})
    .map((event) => {
      const [ratioNumerator, ratioDenominator] = String(event.splitRatio || "")
        .split(":")
        .map(Number);
      const numerator = Number(event.numerator ?? ratioNumerator);
      const denominator = Number(event.denominator ?? ratioDenominator);

      if (
        !finite(event.date) ||
        !finite(numerator) ||
        !finite(denominator) ||
        numerator <= 0 ||
        denominator <= 0
      ) {
        return null;
      }

      return {
        time: Number(event.date),
        numerator,
        denominator,
        ratio: numerator / denominator,
        splitRatio: `${numerator}:${denominator}`,
      };
    })
    .filter(Boolean)
    .sort((first, second) => first.time - second.time);
}

function splitVolumeFactor(time, splits) {
  return splits
    .filter((split) => split.time > time)
    .reduce((factor, split) => factor * split.ratio, 1);
}

function buildAdjustedCandles(result, splits) {
  const quote = result.indicators?.quote?.[0] || {};
  const adjusted = result.indicators?.adjclose?.[0]?.adjclose || [];
  const timestamps = result.timestamp || [];

  const rows = timestamps.map((time, index) => {
    const rawOpen = Number(quote.open?.[index]);
    const rawHigh = Number(quote.high?.[index]);
    const rawLow = Number(quote.low?.[index]);
    const rawClose = Number(quote.close?.[index]);
    const rawVolume = Number(quote.volume?.[index]);
    const adjustedClose = Number(adjusted[index]);
    const adjustedCloseProvided = finite(adjustedClose) && adjustedClose > 0;

    if (
      !finite(time) ||
      !finite(rawOpen) ||
      !finite(rawHigh) ||
      !finite(rawLow) ||
      !finite(rawClose) ||
      rawClose <= 0
    ) {
      return null;
    }

    const adjustmentFactor = adjustedCloseProvided
      ? adjustedClose / rawClose
      : 1;
    const volumeAdjustmentFactor = splitVolumeFactor(Number(time), splits);

    if (
      !finite(adjustmentFactor) ||
      adjustmentFactor <= 0 ||
      !finite(volumeAdjustmentFactor) ||
      volumeAdjustmentFactor <= 0
    ) {
      return null;
    }

    return {
      time: Number(time),
      open: rawOpen * adjustmentFactor,
      high: rawHigh * adjustmentFactor,
      low: rawLow * adjustmentFactor,
      close: rawClose * adjustmentFactor,
      volume:
        finite(rawVolume) && rawVolume >= 0
          ? rawVolume * volumeAdjustmentFactor
          : null,
      rawClose,
      adjustedClose: adjustedCloseProvided
        ? adjustedClose
        : rawClose * adjustmentFactor,
      adjustedCloseProvided,
      adjustmentFactor,
      volumeAdjustmentFactor,
    };
  });

  return {
    candles: rows.filter(Boolean),
    sourceRowCount: rows.length,
    droppedRowCount: rows.filter((row) => row === null).length,
    adjustedCloseCount: rows.filter((row) => row && row.adjustedCloseProvided)
      .length,
  };
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
      "User-Agent": "Mozilla/5.0 " + "(compatible; ArkTerminal/3.0)",
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
  const splits = normalizeSplits(result.events);
  const adjustedData = buildAdjustedCandles(result, splits);

  if (!adjustedData.candles.length) {
    throw new Error("有効な株価履歴がありません。");
  }

  const meta = result.meta || {};

  return {
    symbol,
    range,
    interval,
    provider: "yahoo-finance",
    adjustmentMethod: "adjusted-close-price-and-split-adjusted-volume",
    meta: {
      currency: meta.currency || null,
      priceUnit: meta.currency || null,
      volumeUnit: "shares",
      shortName: meta.shortName || null,
      longName: meta.longName || null,
      exchangeName: meta.exchangeName || meta.fullExchangeName || null,
      instrumentType: meta.instrumentType || null,
      timezone: meta.exchangeTimezoneName || null,
      marketCap: finite(meta.marketCap) ? Number(meta.marketCap) : null,
      sharesOutstanding: finite(meta.sharesOutstanding)
        ? Number(meta.sharesOutstanding)
        : null,
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
    sourceQuality: {
      sourceRowCount: adjustedData.sourceRowCount,
      droppedRowCount: adjustedData.droppedRowCount,
      adjustedCloseCount: adjustedData.adjustedCloseCount,
      splitCount: splits.length,
    },
    corporateActions: {
      splits,
    },
    candles: adjustedData.candles,
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
  normalizeSplits,
  splitVolumeFactor,
  buildAdjustedCandles,
  fetchYahooHistory,
};
