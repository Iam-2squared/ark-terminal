export const DEFAULT_MARKET_DATA_CACHE_TTL_MS = 5 * 60 * 1000;

function cacheKey(value) {
  const candidate = value && typeof value === "object" ? value.symbol : value;
  const key = String(candidate || "").trim().toUpperCase();

  if (!key) {
    throw new TypeError("Market data cache key is required.");
  }

  return key;
}

function ttlOrDefault(value, fallback) {
  const ttl = Number(value);
  return Number.isFinite(ttl) && ttl >= 0 ? ttl : fallback;
}

export class MarketDataCache {
  constructor({
    ttlMs = DEFAULT_MARKET_DATA_CACHE_TTL_MS,
    now = Date.now,
  } = {}) {
    if (typeof now !== "function") {
      throw new TypeError("Market data cache clock must be a function.");
    }

    this.ttlMs = ttlOrDefault(ttlMs, DEFAULT_MARKET_DATA_CACHE_TTL_MS);
    this.now = now;
    this.cache = new Map();
  }

  set(key, value, { ttlMs = this.ttlMs } = {}) {
    const createdAt = Number(this.now());
    const resolvedTtl = ttlOrDefault(ttlMs, this.ttlMs);

    this.cache.set(cacheKey(key), {
      value,
      createdAt,
      expiresAt: createdAt + resolvedTtl,
    });

    return value;
  }

  get(key) {
    const normalizedKey = cacheKey(key);
    const entry = this.cache.get(normalizedKey);

    if (!entry) {
      return null;
    }

    if (Number(this.now()) >= entry.expiresAt) {
      this.cache.delete(normalizedKey);
      return null;
    }

    return entry.value;
  }

  has(key) {
    return this.get(key) !== null;
  }

  delete(key) {
    return this.cache.delete(cacheKey(key));
  }

  prune() {
    const currentTime = Number(this.now());
    let removed = 0;

    for (const [key, entry] of this.cache) {
      if (currentTime >= entry.expiresAt) {
        this.cache.delete(key);
        removed += 1;
      }
    }

    return removed;
  }

  clear() {
    this.cache.clear();
  }

  size() {
    this.prune();
    return this.cache.size;
  }
}

export const marketDataCache = new MarketDataCache();

export default MarketDataCache;
