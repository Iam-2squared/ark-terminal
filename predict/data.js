import {
  ARK_API_BASE,
  HISTORY_INTERVAL,
  HISTORY_RANGE,
  INTRADAY_INTERVAL,
  INTRADAY_RANGE,
} from "./config.js";
import { fetchMarketEnvironment } from "./market-context/service.js";

async function fetchJson(path, params, signal) {
  const url = new URL(path, ARK_API_BASE);

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      url.searchParams.set(key, value);
    }
  });

  url.searchParams.set("t", Date.now());

  const response = await fetch(url, {
    cache: "no-store",
    signal,
  });

  let payload;

  try {
    payload = await response.json();
  } catch {
    throw new Error("APIの応答を読み取れませんでした。");
  }

  if (!response.ok) {
    throw new Error(payload.error || `API HTTP ${response.status}`);
  }

  return payload;
}

export function fetchQuote(symbol, signal) {
  return fetchJson("/api/quote", { symbol }, signal);
}

export function fetchHistory(
  symbol,
  { range = HISTORY_RANGE, interval = HISTORY_INTERVAL, signal } = {},
) {
  return fetchJson(
    "/api/history",
    {
      symbol,
      range,
      interval,
    },
    signal,
  );
}

export function fetchIntradayHistory(
  symbol,
  {
    range = INTRADAY_RANGE,
    interval = INTRADAY_INTERVAL,
    signal,
  } = {},
) {
  return fetchJson(
    "/api/intraday",
    {
      symbol,
      range,
      interval,
    },
    signal,
  );
}
export async function fetchMarketContext(symbol, signal) {
  try {
    return await fetchJson("/api/context", { symbol }, signal);
  } catch (error) {
    if (error.name === "AbortError") {
      throw error;
    }

    return {
      symbol,
      company: null,
      news: [],
      disclosures: [],
      status: {
        company: "unavailable",
        news: "unavailable",
        disclosures: "not_configured",
      },
      errors: [error.message],
    };
  }
}

export async function fetchAnalysisBundle(symbol, signal) {
  const [quoteResult, historyResult, contextResult, marketEnvironmentResult] =
    await Promise.allSettled([
      fetchQuote(symbol, signal),
      fetchHistory(symbol, { signal }),
      fetchMarketContext(symbol, signal),
      fetchMarketEnvironment({
        symbol,
        signal,
        fetchHistory,
      }),
    ]);

  if (historyResult.status === "rejected") {
    throw historyResult.reason;
  }

  return {
    quote: quoteResult.status === "fulfilled" ? quoteResult.value : null,
    history: historyResult.value,
    context:
      contextResult.status === "fulfilled"
        ? contextResult.value
        : {
            symbol,
            company: null,
            news: [],
            disclosures: [],
            status: {
              company: "unavailable",
              news: "unavailable",
              disclosures: "not_configured",
            },
            errors: [
              contextResult.reason?.message ||
                "企業情報を取得できませんでした。",
            ],
          },
    marketEnvironment:
      marketEnvironmentResult.status === "fulfilled"
        ? marketEnvironmentResult.value
        : {
            score: null,
            regime: "データなし",
            series: [],
            registry: [],
            errors: [
              marketEnvironmentResult.reason?.message ||
                "市場環境を取得できませんでした。",
            ],
          },
  };
}
