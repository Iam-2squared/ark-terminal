import {
  MARKET_DATA_DEFINITIONS,
  MARKET_DATA_STATUS,
  getMarketDataDefinition,
} from "./market-data-model.js";
import {
  DEFAULT_MARKET_DATA_STALE_AFTER_MS,
  normalizeMarketData,
  normalizeMarketDataError,
} from "./market-data-normalizer.js";
import {
  DEFAULT_MARKET_DATA_CACHE_TTL_MS,
  MarketDataCache,
} from "./market-data-cache.js";
import { createHistoryMarketDataProvider } from "./market-data-provider.js";

export const DEFAULT_MARKET_DATA_ERROR_TTL_MS = 30 * 1000;

function isAbortError(error) {
  return error?.name === "AbortError";
}

function resolveDefinition(value) {
  const definition = getMarketDataDefinition(value);

  if (!definition) {
    throw new RangeError(`Unknown market data symbol: ${String(value || "")}`);
  }

  return definition;
}

export class MarketDataService {
  constructor({
    provider,
    cache = null,
    definitions = MARKET_DATA_DEFINITIONS,
    normalizer = normalizeMarketData,
    errorNormalizer = normalizeMarketDataError,
    cacheTtlMs = DEFAULT_MARKET_DATA_CACHE_TTL_MS,
    errorTtlMs = DEFAULT_MARKET_DATA_ERROR_TTL_MS,
    staleAfterMs = DEFAULT_MARKET_DATA_STALE_AFTER_MS,
    now = Date.now,
  } = {}) {
    if (!provider || typeof provider.fetch !== "function") {
      throw new TypeError("Market data service provider is required.");
    }

    if (typeof normalizer !== "function" || typeof errorNormalizer !== "function") {
      throw new TypeError("Market data service normalizers must be functions.");
    }

    if (typeof now !== "function") {
      throw new TypeError("Market data service clock must be a function.");
    }

    this.provider = provider;
    this.cacheTtlMs = cacheTtlMs;
    this.errorTtlMs = errorTtlMs;
    this.staleAfterMs = staleAfterMs;
    this.now = now;
    this.cache =
      cache ||
      new MarketDataCache({
        ttlMs: cacheTtlMs,
        now,
      });
    this.definitions = Object.freeze(
      definitions.map((definition) => resolveDefinition(definition)),
    );
    this.normalizer = normalizer;
    this.errorNormalizer = errorNormalizer;
    this.inFlight = new Map();
  }

  async load(definition, { signal, throwOnError = false } = {}) {
    try {
      const raw = await this.provider.fetch(definition, { signal });
      const result = this.normalizer(raw, definition, {
        now: this.now,
        staleAfterMs: this.staleAfterMs,
      });

      this.cache.set(definition.symbol, result, {
        ttlMs:
          result.status === MARKET_DATA_STATUS.ERROR
            ? this.errorTtlMs
            : this.cacheTtlMs,
      });

      return result;
    } catch (error) {
      if (isAbortError(error)) {
        throw error;
      }

      if (throwOnError) {
        throw error;
      }

      const result = this.errorNormalizer(definition, error, {
        now: this.now,
      });

      this.cache.set(definition.symbol, result, {
        ttlMs: this.errorTtlMs,
      });

      return result;
    }
  }

  async get(
    symbol,
    { forceRefresh = false, signal, throwOnError = false } = {},
  ) {
    const definition = resolveDefinition(symbol);

    if (!forceRefresh) {
      const cached = this.cache.get(definition.symbol);

      if (
        cached &&
        !(throwOnError && cached.status === MARKET_DATA_STATUS.ERROR)
      ) {
        return cached;
      }
    }

    const requestKey = `${definition.symbol}:${throwOnError ? "throw" : "safe"}`;
    const pending = this.inFlight.get(requestKey);

    if (pending) {
      return pending;
    }

    const request = this.load(definition, {
      signal,
      throwOnError,
    });

    this.inFlight.set(requestKey, request);

    try {
      return await request;
    } finally {
      if (this.inFlight.get(requestKey) === request) {
        this.inFlight.delete(requestKey);
      }
    }
  }

  async getMany(
    symbols,
    { forceRefresh = false, signal, throwOnError = false } = {},
  ) {
    const requested = Array.isArray(symbols) ? symbols : [];
    const unique = [];
    const seen = new Set();

    for (const symbol of requested) {
      const definition = resolveDefinition(symbol);

      if (!seen.has(definition.symbol)) {
        seen.add(definition.symbol);
        unique.push(definition.symbol);
      }
    }

    return Promise.all(
      unique.map((symbol) =>
        this.get(symbol, {
          forceRefresh,
          signal,
          throwOnError,
        }),
      ),
    );
  }

  getAll(options = {}) {
    return this.getMany(
      this.definitions.map((definition) => definition.symbol),
      options,
    );
  }

  clearCache(symbol = null) {
    if (symbol === null || symbol === undefined) {
      this.cache.clear();
      return true;
    }

    const definition = resolveDefinition(symbol);
    return this.cache.delete(definition.symbol);
  }
}

export function createMarketDataService({
  fetchHistory,
  provider,
  providerOptions = {},
  ...serviceOptions
} = {}) {
  const resolvedProvider =
    provider ||
    createHistoryMarketDataProvider({
      fetchHistory,
      ...providerOptions,
    });

  return new MarketDataService({
    provider: resolvedProvider,
    ...serviceOptions,
  });
}

export default MarketDataService;
