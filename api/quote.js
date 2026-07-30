function createQuoteResponse({
  symbol,
  price,
  previousClose,
  high,
  low,
  open,
  volume,
  updatedAt,
  provider,
}) {
  const numericPrice = Number(price);

  const numericPreviousClose = Number(previousClose);

  const change = numericPrice - numericPreviousClose;

  const changePercent =
    numericPreviousClose !== 0 ? (change / numericPreviousClose) * 100 : 0;

  return {
    symbol,
    price: numericPrice,
    change,
    changePercent,
    high: Number(high),
    low: Number(low),
    open: Number(open),
    volume: Number.isFinite(Number(volume)) ? Number(volume) : null,
    previousClose: numericPreviousClose,
    updatedAt,
    provider,
  };
}

async function fetchJapaneseQuote(symbol) {
  const yahooUrl =
    "https://query2.finance.yahoo.com" +
    "/v8/finance/chart/" +
    encodeURIComponent(symbol) +
    "?interval=1m&range=1d";

  const yahooResponse = await fetch(yahooUrl, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "User-Agent": "Mozilla/5.0 " + "(compatible; ArkTerminal/1.0)",
    },
  });

  if (!yahooResponse.ok) {
    throw new Error(`Yahoo Finance HTTP ${yahooResponse.status}`);
  }

  const payload = await yahooResponse.json();

  const result =
    payload.chart && payload.chart.result && payload.chart.result[0];

  const meta = result && result.meta;

  const quote =
    result &&
    result.indicators &&
    result.indicators.quote &&
    result.indicators.quote[0];

  const volumes = quote && Array.isArray(quote.volume) ? quote.volume : [];

  const latestVolume = [...volumes]
    .reverse()
    .find((value) => Number.isFinite(Number(value)));

  if (!meta || !Number.isFinite(Number(meta.regularMarketPrice))) {
    throw new Error("日本株の株価データがありません。");
  }

  const previousClose = meta.previousClose ?? meta.chartPreviousClose;

  if (!Number.isFinite(Number(previousClose))) {
    throw new Error("日本株の前日終値がありません。");
  }

  return createQuoteResponse({
    symbol,
    price: meta.regularMarketPrice,
    previousClose,
    high: meta.regularMarketDayHigh,
    low: meta.regularMarketDayLow,
    open: meta.regularMarketOpen ?? previousClose,
    volume: meta.regularMarketVolume ?? latestVolume,
    updatedAt: meta.regularMarketTime
      ? new Date(meta.regularMarketTime * 1000).toISOString()
      : new Date().toISOString(),
    provider: "yahoo-finance",
  });
}

async function fetchFinnhubQuote(symbol, apiKey) {
  if (!apiKey) {
    throw new Error("FINNHUB_API_KEYが設定されていません。");
  }

  const finnhubUrl =
    "https://finnhub.io/api/v1/quote" +
    `?symbol=${encodeURIComponent(symbol)}` +
    `&token=${encodeURIComponent(apiKey)}`;

  const finnhubResponse = await fetch(finnhubUrl, {
    cache: "no-store",
  });

  if (!finnhubResponse.ok) {
    throw new Error(`Finnhub HTTP ${finnhubResponse.status}`);
  }

  const data = await finnhubResponse.json();

  if (!Number.isFinite(Number(data.c)) || Number(data.c) === 0) {
    throw new Error("株価データがありません。");
  }

  return {
    symbol,
    price: Number(data.c),
    change: Number(data.d),
    changePercent: Number(data.dp),
    high: Number(data.h),
    low: Number(data.l),
    open: Number(data.o),
    volume: null,
    previousClose: Number(data.pc),
    updatedAt: data.t
      ? new Date(data.t * 1000).toISOString()
      : new Date().toISOString(),
    provider: "finnhub",
  };
}

async function fetchYahooVolume(symbol) {
  try {
    const yahooUrl =
      "https://query2.finance.yahoo.com" +
      "/v8/finance/chart/" +
      encodeURIComponent(symbol) +
      "?interval=1d&range=5d";

    const yahooResponse = await fetch(yahooUrl, {
      cache: "no-store",
      headers: {
        Accept: "application/json",
        "User-Agent": "Mozilla/5.0 " + "(compatible; ArkTerminal/2.0)",
      },
    });

    if (!yahooResponse.ok) {
      return null;
    }

    const payload = await yahooResponse.json();

    const result =
      payload.chart && payload.chart.result && payload.chart.result[0];

    const volumes =
      result &&
      result.indicators &&
      result.indicators.quote &&
      result.indicators.quote[0] &&
      result.indicators.quote[0].volume;

    if (!Array.isArray(volumes)) {
      return null;
    }

    const latest = [...volumes]
      .reverse()
      .find((value) => Number.isFinite(Number(value)));

    return Number.isFinite(Number(latest)) ? Number(latest) : null;
  } catch {
    return null;
  }
}

export default async function handler(request, response) {
  response.setHeader("Access-Control-Allow-Origin", "*");

  response.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");

  response.setHeader("Cache-Control", "no-store, max-age=0");

  if (request.method === "OPTIONS") {
    return response.status(204).end();
  }

  const symbol = String(request.query.symbol || "")
    .trim()
    .toUpperCase();

  if (!symbol) {
    return response.status(400).json({
      error: "銘柄コードが必要です。",
    });
  }

  try {
    let quote;

    if (symbol.endsWith(".T")) {
      quote = await fetchJapaneseQuote(symbol);
    } else {
      const [finnhubQuote, volume] = await Promise.all([
        fetchFinnhubQuote(symbol, process.env.FINNHUB_API_KEY),
        fetchYahooVolume(symbol),
      ]);

      quote = {
        ...finnhubQuote,
        volume,
      };
    }

    return response.status(200).json(quote);
  } catch (error) {
    console.error(error);

    return response.status(500).json({
      error: "株価の取得に失敗しました。",
      symbol,
    });
  }
}
