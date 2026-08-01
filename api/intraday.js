const INTRADAY_INTERVAL_SECONDS = 15 * 60;

const allowedRanges = new Set([
  "1d",
  "5d",
  "1mo",
]);

const allowedIntervals = new Set([
  "15m",
]);

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function positive(value) {
  return finite(value) && Number(value) > 0;
}

function normalizeIntradaySymbol(value) {
  const symbol = String(value || "")
    .trim()
    .toUpperCase()
    .replace(/\s+/g, "");

  if (/^(?:\d{4}|\d{3}[A-Z])$/.test(symbol)) {
    return `${symbol}.T`;
  }

  return symbol;
}

function intradaySessionDate(
  time,
  timeZone = "UTC",
) {
  if (!finite(time)) {
    return null;
  }

  const date = new Date(Number(time) * 1000);

  if (Number.isNaN(date.getTime())) {
    return null;
  }

  try {
    const parts = new Intl.DateTimeFormat(
      "en-US",
      {
        timeZone,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      },
    ).formatToParts(date);

    const values = Object.fromEntries(
      parts
        .filter((part) =>
          ["year", "month", "day"].includes(
            part.type,
          ),
        )
        .map((part) => [
          part.type,
          part.value,
        ]),
    );

    if (
      values.year &&
      values.month &&
      values.day
    ) {
      return `${values.year}-${values.month}-${values.day}`;
    }
  } catch {
    // 不明なタイムゾーンではUTCへフォールバックする。
  }

  return date.toISOString().slice(0, 10);
}

function buildIntradayCandles(
  result = {},
  {
    nowSeconds = Math.floor(Date.now() / 1000),
  } = {},
) {
  const timestamps = result.timestamp || [];
  const quote =
    result.indicators?.quote?.[0] || {};

  const timeZone =
    result.meta?.exchangeTimezoneName ||
    result.meta?.timezone ||
    "UTC";

  const rows = timestamps.map(
    (time, index) => {
      const open = Number(quote.open?.[index]);
      const high = Number(quote.high?.[index]);
      const low = Number(quote.low?.[index]);
      const close = Number(quote.close?.[index]);

      const rawVolume =
        quote.volume?.[index];

      const volume = finite(rawVolume)
        ? Number(rawVolume)
        : null;

      if (
        !finite(time) ||
        !positive(open) ||
        !positive(high) ||
        !positive(low) ||
        !positive(close) ||
        high < low
      ) {
        return null;
      }

      return {
        time: Number(time),
        open,
        high,
        low,
        close,
        volume:
          finite(volume) && volume >= 0
            ? volume
            : null,

        sessionDate:
          intradaySessionDate(
            time,
            timeZone,
          ),

        isClosed:
          Number(time) +
            INTRADAY_INTERVAL_SECONDS <=
          Number(nowSeconds),
      };
    },
  );

  const candles = rows.filter(Boolean);

  return {
    candles,

    sourceRowCount:
      rows.length,

    droppedRowCount:
      rows.length - candles.length,

    closedRowCount:
      candles.filter(
        (candle) => candle.isClosed,
      ).length,

    volumeRowCount:
      candles.filter(
        (candle) =>
          finite(candle.volume),
      ).length,

    timeZone,
  };
}

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
      currency:
        meta.currency || null,

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
        finite(meta.regularMarketPrice)
          ? Number(meta.regularMarketPrice)
          : null,

      regularMarketTime:
        finite(meta.regularMarketTime)
          ? Number(meta.regularMarketTime)
          : null,

      dataGranularity:
        meta.dataGranularity ||
        interval,
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

    candles:
      built.candles,

    updatedAt:
      new Date().toISOString(),
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

  const symbol =
    normalizeIntradaySymbol(
      request.query?.symbol,
    );

  const range = allowedRanges.has(
    request.query?.range,
  )
    ? request.query.range
    : "5d";

  const interval =
    allowedIntervals.has(
      request.query?.interval,
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

      detail:
        error?.message || null,

      symbol,
    });
  }
}

export const IntradayApiInternals = {
  allowedRanges,
  allowedIntervals,
  finite,
  positive,
  normalizeIntradaySymbol,
  intradaySessionDate,
  buildIntradayCandles,
  fetchYahooIntraday,
};