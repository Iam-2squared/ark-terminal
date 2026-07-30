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

function formatDate(date) {
  return date.toISOString().slice(0, 10);
}

async function fetchFinnhub(path, params, apiKey) {
  const url = new URL(`https://finnhub.io/api/v1/${path}`);

  Object.entries(params).forEach(([key, value]) =>
    url.searchParams.set(key, value),
  );

  url.searchParams.set("token", apiKey);

  const upstream = await fetch(url, {
    cache: "no-store",
  });

  if (!upstream.ok) {
    throw new Error(`Finnhub ${path} HTTP ${upstream.status}`);
  }

  return upstream.json();
}

async function fetchCompany(symbol, apiKey) {
  const profile = await fetchFinnhub("stock/profile2", { symbol }, apiKey);

  if (!profile?.name) {
    return null;
  }

  return {
    name: profile.name,
    ticker: profile.ticker || symbol,
    country: profile.country || null,
    exchange: profile.exchange || null,
    industry: profile.finnhubIndustry || null,
    marketCapitalization: Number(profile.marketCapitalization) || null,
    website: profile.weburl || null,
    logo: profile.logo || null,
  };
}

async function fetchNews(symbol, apiKey) {
  const to = new Date();

  const from = new Date();

  from.setUTCDate(from.getUTCDate() - 14);

  const news = await fetchFinnhub(
    "company-news",
    {
      symbol,
      from: formatDate(from),
      to: formatDate(to),
    },
    apiKey,
  );

  if (!Array.isArray(news)) {
    return [];
  }

  return news
    .slice(0, 12)
    .map((item) => ({
      id: item.id || `${item.datetime}-${item.headline}`,
      headline: item.headline || "",
      summary: item.summary || "",
      source: item.source || "",
      url: item.url || "",
      image: item.image || "",
      publishedAt: item.datetime
        ? new Date(item.datetime * 1000).toISOString()
        : null,
    }))
    .filter((item) => item.headline);
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

  const apiKey = process.env.FINNHUB_API_KEY;

  if (!apiKey) {
    return response.status(200).json({
      symbol,
      company: null,
      news: [],
      disclosures: [],
      sentiment: null,
      status: {
        company: "not_configured",
        news: "not_configured",
        disclosures: "not_configured",
        sentiment: "not_configured",
      },
      errors: ["FINNHUB_API_KEYが設定されていません。"],
    });
  }

  const [companyResult, newsResult] = await Promise.allSettled([
    fetchCompany(symbol, apiKey),
    fetchNews(symbol, apiKey),
  ]);

  const errors = [];

  if (companyResult.status === "rejected") {
    errors.push(companyResult.reason.message);
  }

  if (newsResult.status === "rejected") {
    errors.push(newsResult.reason.message);
  }

  return response.status(200).json({
    symbol,
    company: companyResult.status === "fulfilled" ? companyResult.value : null,
    news: newsResult.status === "fulfilled" ? newsResult.value : [],
    disclosures: [],
    sentiment: null,
    status: {
      company:
        companyResult.status === "fulfilled" && companyResult.value
          ? "available"
          : "unavailable",
      news: newsResult.status === "fulfilled" ? "available" : "unavailable",
      disclosures: "not_configured",
      sentiment: "not_configured",
    },
    errors,
  });
}

export const ContextInternals = {
  normalizeSymbol,
  fetchCompany,
  fetchNews,
};
