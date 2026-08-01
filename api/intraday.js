import {
  buildIntradayCandles,
  normalizeIntradaySymbol,
} from "../predict/trading/intraday-market.js";

const allowedRanges = new Set([
  "1d",
  "5d",
  "1mo",
]);

const allowedIntervals = new Set([
  "15m",
]);

async function fetchYahooIntraday({
  symbol,
  range,
  interval,
}) {
  const url =
    "https://query2.finance.yahoo.com" +
    "/v8/finance/chart/" +
    encodeURIComponent(symbol) +
    `?range=${encodeURIComponent(range)}` +
    `&interval=${encodeURIComponent(interval)}` +
    "&includePrePost=false" +
    "&events=div%2Csplits";

  const upstream = await fetch(url, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "User-Agent":
        "Mozilla/5.0 " +
        "(compatible; ArkTerminal/3.0)",
    },
  });

  if (!upstream.ok) {
    throw new Error(
      `Yahoo Finance HTTP ${upstream.status}`,
    );
  }

  const payload = await upstream.json();
  const chart = payload.chart;

  if (
    chart?.error ||
    !chart?.result?.[0]
  ) {
    throw new Error(
      chart?.error?.description ||
        "15分足データがありません。",
    );
  }

  const result = chart.result[0];
  const built =
    buildIntradayCandles(result);

  if (!built.candles.length) {
    throw new Error(
      "有効な15分足データがありません。",
    );
  }

  const meta = result.meta || {};

  return {
    symbol,
    range,
    interval,
    provider: "yahoo-finance",
    adjustmentMethod:
      "raw-intraday-ohlcv",

    meta: {
      currency: meta.currency || null,
      exchangeName:
        meta.exchangeName ||
        meta.fullExchangeName ||
        null,
      instrumentType:
        meta.instrumentType || null,
      timezone:
        meta.exchangeTimezoneName ||
        null,
      regularMarketPrice:
        Number.isFinite(
          Number(meta.regularMarketPrice),
        )
          ? Number(meta.regularMarketPrice)
          : null,
      regularMarketTime:
        Number.isFinite(
          Number(meta.regularMarketTime),
        )
          ? Number(meta.regularMarketTime)
          : null,
      dataGranularity:
        meta.dataGranularity || interval,
    },

    sourceQuality: {
      sourceRowCount:
        built.sourceRowCount,
      droppedRowCount:
        built.droppedRowCount,
      closedRowCount:
        built.closedRowCount,
      volumeRowCount:
        built.volumeRowCount,
    },

    candles: built.candles,
    updatedAt: new Date().toISOString(),
  };
}

export default async function handler(
  request,
  response,
) {
  response.setHeader(
    "Access-Control-Allow-Origin",
    "*",
  );

  response.setHeader(
    "Access-Control-Allow-Methods",
    "GET, OPTIONS",
  );

  response.setHeader(
    "Cache-Control",
    "s-maxage=15, stale-while-revalidate=30",
  );

  if (request.method === "OPTIONS") {
    return response.status(204).end();
  }

  if (request.method !== "GET") {
    return response.status(405).json({
      error: "GETのみ利用できます。",
    });
  }

  const symbol = normalizeIntradaySymbol(
    request.query.symbol,
  );

  const range = allowedRanges.has(
    request.query.range,
  )
    ? request.query.range
    : "5d";

  const interval = allowedIntervals.has(
    request.query.interval,
  )
    ? request.query.interval
    : "15m";

  if (!symbol) {
    return response.status(400).json({
      error: "銘柄コードが必要です。",
    });
  }

  try {
    const intraday =
      await fetchYahooIntraday({
        symbol,
        range,
        interval,
      });

    return response
      .status(200)
      .json(intraday);
  } catch (error) {
    console.error(
      "Intraday API:",
      error,
    );

    return response.status(502).json({
      error:
        "15分足データの取得に失敗しました。",
      symbol,
    });
  }
}

export const IntradayApiInternals = {
  allowedRanges,
  allowedIntervals,
  fetchYahooIntraday,
};