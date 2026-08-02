import {
  fetchFinnhubCompany,
  fetchFinnhubCompanyNews,
} from "../server/providers/finnhub-news-provider.js";
import {
  fetchJquantsTdnetDisclosures,
  normalizeJquantsCode,
} from "../server/providers/jquants-tdnet-provider.js";

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

async function fetchCompany(
  symbol,
  apiKey,
  fetchImpl = globalThis.fetch,
) {
  return fetchFinnhubCompany(symbol, {
    apiKey,
    fetchImpl,
  });
}

async function fetchNews(
  symbol,
  apiKey,
  fetchImpl = globalThis.fetch,
  now = Date.now,
) {
  return fetchFinnhubCompanyNews(symbol, {
    apiKey,
    fetchImpl,
    now,
  });
}

async function fetchDisclosures(
  symbol,
  apiKey,
  fetchImpl = globalThis.fetch,
) {
  return fetchJquantsTdnetDisclosures(symbol, {
    apiKey,
    fetchImpl,
  });
}

function rejectionMessage(result) {
  return result?.status === "rejected"
    ? String(result.reason?.message || result.reason || "Provider failed.")
    : null;
}

function resolvedStatus(
  result,
  {
    configured,
    applicable = true,
    requireValue = false,
  },
) {
  if (!applicable) return "not_applicable";
  if (!configured) return "not_configured";
  if (result?.status !== "fulfilled") return "unavailable";
  if (requireValue && !result.value) return "unavailable";
  return "available";
}

export async function loadMarketContext(
  rawSymbol,
  {
    finnhubApiKey = "",
    jquantsApiKey = "",
    fetchImpl = globalThis.fetch,
    now = Date.now,
  } = {},
) {
  const symbol = normalizeSymbol(rawSymbol);

  if (!symbol) {
    throw new TypeError("Market context symbol is required.");
  }

  const hasFinnhub = Boolean(String(finnhubApiKey || "").trim());
  const jquantsCode = normalizeJquantsCode(symbol);
  const hasJquants = Boolean(String(jquantsApiKey || "").trim());
  const disclosuresApplicable = Boolean(jquantsCode);
  const [companyResult, newsResult, disclosureResult] =
    await Promise.allSettled([
      hasFinnhub
        ? fetchCompany(symbol, finnhubApiKey, fetchImpl)
        : Promise.resolve(null),
      hasFinnhub
        ? fetchNews(symbol, finnhubApiKey, fetchImpl, now)
        : Promise.resolve([]),
      disclosuresApplicable && hasJquants
        ? fetchDisclosures(symbol, jquantsApiKey, fetchImpl)
        : Promise.resolve([]),
    ]);
  const errors = [
    rejectionMessage(companyResult),
    rejectionMessage(newsResult),
    rejectionMessage(disclosureResult),
  ].filter(Boolean);
  const warnings = [];

  if (!hasFinnhub) {
    warnings.push("FINNHUB_API_KEYが設定されていません。");
  }

  if (disclosuresApplicable && !hasJquants) {
    warnings.push("JQUANTS_API_KEYが設定されていません。");
  }

  return {
    symbol,
    company:
      companyResult.status === "fulfilled" ? companyResult.value : null,
    news: newsResult.status === "fulfilled" ? newsResult.value : [],
    disclosures:
      disclosureResult.status === "fulfilled" ? disclosureResult.value : [],
    sentiment: null,
    status: {
      company: resolvedStatus(companyResult, {
        configured: hasFinnhub,
        requireValue: true,
      }),
      news: resolvedStatus(newsResult, {
        configured: hasFinnhub,
      }),
      disclosures: resolvedStatus(disclosureResult, {
        configured: hasJquants,
        applicable: disclosuresApplicable,
      }),
      sentiment: "not_configured",
    },
    providers: {
      company: "Finnhub",
      news: "Finnhub",
      disclosures: disclosuresApplicable ? "J-Quants TDnet v2" : null,
    },
    errors: [...errors, ...warnings],
    providerErrors: errors,
    warnings,
    executionAllowed: false,
  };
}

export default async function handler(request, response) {
  response.setHeader("Access-Control-Allow-Origin", "*");
  response.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  response.setHeader(
    "Cache-Control",
    "s-maxage=300, stale-while-revalidate=900",
  );

  if (request.method === "OPTIONS") {
    return response.status(204).end();
  }

  const symbol = normalizeSymbol(request.query.symbol);

  if (!symbol) {
    return response.status(400).json({
      error: "銘柄コードが必要です。",
    });
  }

  try {
    const payload = await loadMarketContext(symbol, {
      finnhubApiKey: process.env.FINNHUB_API_KEY,
      jquantsApiKey: process.env.JQUANTS_API_KEY,
    });

    return response.status(200).json(payload);
  } catch (error) {
    console.error("Market context API:", error);

    return response.status(502).json({
      symbol,
      company: null,
      news: [],
      disclosures: [],
      sentiment: null,
      status: {
        company: "unavailable",
        news: "unavailable",
        disclosures: "unavailable",
        sentiment: "not_configured",
      },
      errors: [error.message || "市場コンテキストを取得できませんでした。"],
      warnings: [],
      executionAllowed: false,
    });
  }
}

export const ContextInternals = Object.freeze({
  normalizeSymbol,
  fetchCompany,
  fetchNews,
  fetchDisclosures,
  rejectionMessage,
  resolvedStatus,
});
