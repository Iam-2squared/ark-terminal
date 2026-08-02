const JQUANTS_API_BASE = "https://api.jquants.com/";
const TDNET_PATH = "v2/td/list";
const DEFAULT_DISCLOSURE_LIMIT = 30;
const DEFAULT_MAXIMUM_PAGES = 3;

function requireFetch(fetchImpl) {
  if (typeof fetchImpl !== "function") {
    throw new TypeError("J-Quants TDnet provider requires fetch.");
  }
}

function requireApiKey(apiKey) {
  const normalized = String(apiKey || "").trim();

  if (!normalized) {
    throw new Error("JQUANTS_API_KEY is not configured.");
  }

  return normalized;
}

export function normalizeJquantsCode(value) {
  const symbol = String(value || "")
    .trim()
    .toUpperCase()
    .replace(/\s+/g, "");
  const base = symbol.endsWith(".T") ? symbol.slice(0, -2) : symbol;

  if (/^(?:\d{4}|\d{3}[A-Z])$/.test(base)) {
    return `${base}0`;
  }

  if (/^(?:\d{5}|\d{3}[A-Z]\d)$/.test(base)) {
    return base;
  }

  return null;
}

function normalizeDate(value) {
  const text = String(value || "").trim();

  if (/^\d{8}$/.test(text)) {
    return `${text.slice(0, 4)}-${text.slice(4, 6)}-${text.slice(6, 8)}`;
  }

  return /^\d{4}-\d{2}-\d{2}$/.test(text) ? text : null;
}

function normalizeTime(value) {
  const text = String(value || "").trim();

  if (/^\d{6}$/.test(text)) {
    return `${text.slice(0, 2)}:${text.slice(2, 4)}:${text.slice(4, 6)}`;
  }

  if (/^\d{4}$/.test(text)) {
    return `${text.slice(0, 2)}:${text.slice(2, 4)}:00`;
  }

  if (/^\d{2}:\d{2}$/.test(text)) {
    return `${text}:00`;
  }

  return /^\d{2}:\d{2}:\d{2}$/.test(text) ? text : null;
}

function disclosureTimestamp(dateValue, timeValue) {
  const date = normalizeDate(dateValue);
  const time = normalizeTime(timeValue) || "00:00:00";

  if (!date) {
    return null;
  }

  const timestamp = new Date(`${date}T${time}+09:00`);
  return Number.isNaN(timestamp.getTime()) ? null : timestamp.toISOString();
}

function safeDocumentUrl(value) {
  try {
    const url = new URL(String(value || ""));
    return url.protocol === "https:" || url.protocol === "http:"
      ? url.toString()
      : null;
  } catch {
    return null;
  }
}

function firstDocumentUrl(documents) {
  const items = Array.isArray(documents) ? documents : [documents];

  for (const item of items) {
    if (typeof item === "string") {
      const url = safeDocumentUrl(item);
      if (url) return url;
      continue;
    }

    if (!item || typeof item !== "object") continue;

    for (const key of ["Url", "URL", "url", "DocumentUrl", "DocUrl"]) {
      const url = safeDocumentUrl(item[key]);
      if (url) return url;
    }
  }

  return null;
}

function disclosureTags(value) {
  const items = Array.isArray(value) ? value : value ? [value] : [];

  return [
    "tdnet",
    ...items
      .map((item) =>
        typeof item === "object"
          ? item?.Name ?? item?.name ?? item?.Item ?? item?.item ?? item?.Code
          : item,
      )
      .map((item) => String(item || "").trim())
      .filter(Boolean),
  ].slice(0, 12);
}

export function normalizeTdnetDisclosure(raw = {}) {
  const publishedAt = disclosureTimestamp(raw.DiscDate, raw.DiscTime);
  const headline = String(raw.Title || "").trim();

  return {
    id:
      String(raw.DiscNo || "").trim() ||
      [raw.Code, raw.DiscDate, raw.DiscTime, headline].join("-"),
    headline,
    title: headline,
    summary: "",
    source: "TDnet / J-Quants",
    url: firstDocumentUrl(raw.Docs),
    publishedAt,
    symbol: String(raw.Code || "").trim() || null,
    type: "tdnet",
    confidence: publishedAt ? 95 : 80,
    status: headline ? "available" : "unavailable",
    importance: 80,
    tags: disclosureTags(raw.DiscItems),
    revision: raw.RevNo ?? null,
    disclosureStatus: raw.DiscStatus ?? null,
  };
}

async function fetchTdnetPage(
  code,
  {
    apiKey,
    fetchImpl,
    apiBase,
    paginationKey = null,
  },
) {
  const url = new URL(TDNET_PATH, apiBase);
  url.searchParams.set("code", code);

  if (paginationKey) {
    url.searchParams.set("pagination_key", paginationKey);
  }

  const response = await fetchImpl(url, {
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "x-api-key": apiKey,
    },
  });

  if (!response.ok) {
    throw new Error(`J-Quants TDnet HTTP ${response.status}`);
  }

  return response.json();
}

export async function fetchJquantsTdnetDisclosures(
  symbol,
  {
    apiKey,
    fetchImpl = globalThis.fetch,
    apiBase = JQUANTS_API_BASE,
    limit = DEFAULT_DISCLOSURE_LIMIT,
    maximumPages = DEFAULT_MAXIMUM_PAGES,
  } = {},
) {
  requireFetch(fetchImpl);

  const token = requireApiKey(apiKey);
  const code = normalizeJquantsCode(symbol);

  if (!code) {
    return [];
  }

  const itemLimit = Math.min(100, Math.max(1, Math.floor(Number(limit) || 1)));
  const pageLimit = Math.min(
    10,
    Math.max(1, Math.floor(Number(maximumPages) || 1)),
  );
  const records = new Map();
  const seenPaginationKeys = new Set();
  let paginationKey = null;

  for (let page = 0; page < pageLimit && records.size < itemLimit; page += 1) {
    const payload = await fetchTdnetPage(code, {
      apiKey: token,
      fetchImpl,
      apiBase,
      paginationKey,
    });

    for (const raw of Array.isArray(payload?.data) ? payload.data : []) {
      const disclosure = normalizeTdnetDisclosure(raw);

      if (disclosure.headline) {
        records.set(disclosure.id, disclosure);
      }
    }

    const nextKey = String(
      payload?.pagination_key ?? payload?.paginationKey ?? "",
    ).trim();

    if (!nextKey || seenPaginationKeys.has(nextKey)) {
      break;
    }

    seenPaginationKeys.add(nextKey);
    paginationKey = nextKey;
  }

  return [...records.values()]
    .sort((left, right) =>
      String(right.publishedAt || "").localeCompare(
        String(left.publishedAt || ""),
      ),
    )
    .slice(0, itemLimit);
}

export const JquantsTdnetProviderInternals = Object.freeze({
  JQUANTS_API_BASE,
  TDNET_PATH,
  DEFAULT_DISCLOSURE_LIMIT,
  DEFAULT_MAXIMUM_PAGES,
  normalizeDate,
  normalizeTime,
  disclosureTimestamp,
  firstDocumentUrl,
  disclosureTags,
  fetchTdnetPage,
});
