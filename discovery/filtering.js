import { MARKET_CAP_BANDS, PRICE_BANDS } from "./config.js";

function finite(value) {
  if (value === null || value === undefined || value === "") {
    return false;
  }

  return Number.isFinite(Number(value));
}

function inBand(value, band) {
  if (!finite(value)) {
    return false;
  }

  const number = Number(value);

  if (finite(band.minimum) && number < Number(band.minimum)) {
    return false;
  }

  if (finite(band.maximum) && number >= Number(band.maximum)) {
    return false;
  }

  return true;
}

function includesQuery(entry, query) {
  const normalized = String(query || "")
    .trim()
    .toLocaleLowerCase("ja");

  if (!normalized) {
    return true;
  }

  return [
    entry.code,
    entry.symbol,
    entry.name,
    entry.market,
    entry.sector,
    ...(entry.themes || []),
  ]
    .join(" ")
    .toLocaleLowerCase("ja")
    .includes(normalized);
}

function marketCapMatches(value, key) {
  const band = MARKET_CAP_BANDS[key] || MARKET_CAP_BANDS.all;

  if (band.unknownOnly) {
    return !finite(value);
  }

  if (key === "all" || !key) {
    return true;
  }

  return inBand(value, band);
}

function comparisonValue(entry, sort) {
  switch (sort) {
    case "confidenceDesc":
      return Number(entry.confidence) || -Infinity;
    case "volumeDesc":
      return Number(entry.volumeRatio) || -Infinity;
    case "expectedMoveDesc":
      return Number(entry.expectedMove) || -Infinity;
    case "priceAsc":
      return finite(entry.currentPrice) ? -Number(entry.currentPrice) : -Infinity;
    default:
      return Number(entry.aiScore) || -Infinity;
  }
}

export function applyScreenerFilters(
  entries,
  filters = {},
  watchlist = new Set(),
) {
  const priceBand = PRICE_BANDS[filters.priceBand] || PRICE_BANDS.all;
  const minimumScore = finite(filters.minimumScore)
    ? Number(filters.minimumScore)
    : 0;
  const minimumConfidence = finite(filters.minimumConfidence)
    ? Number(filters.minimumConfidence)
    : 0;
  const minimumVolumeRatio = finite(filters.minimumVolumeRatio)
    ? Number(filters.minimumVolumeRatio)
    : 0;
  const budget = finite(filters.budget) && Number(filters.budget) > 0
    ? Number(filters.budget)
    : null;

  return (Array.isArray(entries) ? entries : [])
    .filter((entry) => entry.status === "analyzed")
    .filter((entry) => includesQuery(entry, filters.query))
    .filter(
      (entry) =>
        !filters.market ||
        filters.market === "all" ||
        entry.market === filters.market,
    )
    .filter(
      (entry) =>
        !filters.theme ||
        filters.theme === "all" ||
        entry.sector === filters.theme ||
        entry.themes?.includes(filters.theme),
    )
    .filter(
      (entry) =>
        !filters.risk ||
        filters.risk === "all" ||
        entry.risk === filters.risk,
    )
    .filter((entry) => inBand(entry.currentPrice, priceBand))
    .filter(
      (entry) => budget === null || Number(entry.purchaseAmount) <= budget,
    )
    .filter((entry) => marketCapMatches(entry.marketCap, filters.marketCap))
    .filter((entry) => Number(entry.aiScore) >= minimumScore)
    .filter((entry) => Number(entry.confidence) >= minimumConfidence)
    .filter((entry) => Number(entry.volumeRatio) >= minimumVolumeRatio)
    .filter(
      (entry) =>
        !filters.watchlistOnly || watchlist.has(String(entry.symbol)),
    )
    .sort((first, second) => {
      const difference =
        comparisonValue(second, filters.sort) -
        comparisonValue(first, filters.sort);

      return difference || String(first.symbol).localeCompare(second.symbol);
    });
}

export function collectFilterOptions(universe) {
  const markets = new Set();
  const themes = new Set();

  (Array.isArray(universe) ? universe : []).forEach((entry) => {
    if (entry.market) {
      markets.add(entry.market);
    }

    if (entry.sector) {
      themes.add(entry.sector);
    }

    (entry.themes || []).forEach((theme) => themes.add(theme));
  });

  return {
    markets: [...markets].sort((first, second) =>
      first.localeCompare(second, "ja"),
    ),
    themes: [...themes].sort((first, second) =>
      first.localeCompare(second, "ja"),
    ),
  };
}

export const FilteringInternals = {
  finite,
  inBand,
  includesQuery,
  marketCapMatches,
};
