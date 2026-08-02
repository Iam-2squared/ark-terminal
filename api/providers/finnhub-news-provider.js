const FINNHUB_API_BASE = "https://finnhub.io/api/v1/";
const DEFAULT_NEWS_LIMIT = 12;
const NEWS_LOOKBACK_DAYS = 14;

function requireFetch(fetchImpl) {
  if (typeof fetchImpl !== "function") {
    throw new TypeError("Finnhub provider requires fetch.");
  }
}

function requireApiKey(apiKey) {
  const normalized = String(apiKey || "").trim();

  if (!normalized) {
    throw new Error("FINNHUB_API_KEY is not configured.");
  }

  return normalized;
}

function formatDate(date) {
  return date.toISOString().slice(0, 10);
}

function resolveNow(now) {
  const value = typeof now === "function" ? now() : now;
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    throw new TypeError("Finnhub provider clock is invalid.");
  }

  return date;
}

async function fetchFinnhub(
  path,
  params,
  {
    apiKey,
    fetchImpl = globalThis.fetch,
  } = {},
) {
  requireFetch(fetchImpl);

  const token = requireApiKey(apiKey);
  const url = new URL(path, FINNHUB_API_BASE);

  for (const [key, value] of Object.entries(params || {})) {
    if (value !== null && value !== undefined && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }

  url.searchParams.set("token", token);

  const upstream = await fetchImpl(url, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
    },
  });

  if (!upstream.ok) {
    throw new Error(`Finnhub ${path} HTTP ${upstream.status}`);
  }

  return upstream.json();
}

export async function fetchFinnhubCompany(
  symbol,
  options = {},
) {
  const profile = await fetchFinnhub(
    "stock/profile2",
    { symbol },
    options,
  );

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
    source: "Finnhub",
  };
}

export async function fetchFinnhubCompanyNews(
  symbol,
  {
    apiKey,
    fetchImpl = globalThis.fetch,
    now = Date.now,
    limit = DEFAULT_NEWS_LIMIT,
  } = {},
) {
  const to = resolveNow(now);
  const from = new Date(to);

  from.setUTCDate(from.getUTCDate() - NEWS_LOOKBACK_DAYS);

  const news = await fetchFinnhub(
    "company-news",
    {
      symbol,
      from: formatDate(from),
      to: formatDate(to),
    },
    {
      apiKey,
      fetchImpl,
    },
  );

  if (!Array.isArray(news)) {
    return [];
  }

  const itemLimit = Math.min(50, Math.max(1, Math.floor(Number(limit) || 1)));

  return news
    .map((item) => ({
      id: item.id || `${item.datetime}-${item.headline}`,
      headline: String(item.headline || "").trim(),
      summary: String(item.summary || "").trim(),
      source: String(item.source || "Finnhub").trim(),
      url: item.url || "",
      image: item.image || "",
      publishedAt: item.datetime
        ? new Date(Number(item.datetime) * 1000).toISOString()
        : null,
      symbol,
      type: "news",
      confidence: 85,
      status: "available",
    }))
    .filter((item) => item.headline)
    .sort((left, right) =>
      String(right.publishedAt || "").localeCompare(
        String(left.publishedAt || ""),
      ),
    )
    .slice(0, itemLimit);
}

export const FinnhubNewsProviderInternals = Object.freeze({
  FINNHUB_API_BASE,
  DEFAULT_NEWS_LIMIT,
  NEWS_LOOKBACK_DAYS,
  formatDate,
  resolveNow,
  fetchFinnhub,
});
