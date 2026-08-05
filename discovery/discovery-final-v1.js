import { applyScreenerFilters } from "./filtering.js";
import { rankDiscoveryEntries } from "./ranking-adapter-v2.js";

export const DISCOVERY_FINAL_V1 = "discovery-final-v1";

export function createDiscoveryFinalView({
  entries = [],
  filters = {},
  watchlist = new Set(),
  rankingContext = {},
} = {}) {
  const ranked = rankDiscoveryEntries(entries, rankingContext);
  const filtered = applyScreenerFilters(
    ranked.map((entry) => ({
      ...entry,
      discoveryScore: entry.rankingScore,
    })),
    filters,
    watchlist,
  );

  return {
    version: DISCOVERY_FINAL_V1,
    totalCount: ranked.length,
    visibleCount: filtered.length,
    watchlistCount: [...watchlist].length,
    entries: filtered,
    filters: { ...filters },
    emptyState:
      filtered.length === 0
        ? "条件に一致する銘柄がありません。フィルターを調整してください。"
        : null,
  };
}

export function toggleWatchlistSymbol(watchlist = new Set(), symbol) {
  const next = new Set(watchlist);
  const normalized = String(symbol ?? "").trim();
  if (!normalized) return next;
  if (next.has(normalized)) next.delete(normalized);
  else next.add(normalized);
  return next;
}
