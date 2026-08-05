export const REQUEST_CACHE_V1_VERSION = "request-cache-v1";

export class RequestCacheV1 {
  constructor({ ttlMs = 30_000, now = () => Date.now() } = {}) {
    this.ttlMs = ttlMs;
    this.now = now;
    this.cache = new Map();
    this.inflight = new Map();
  }

  get(key) {
    const entry = this.cache.get(key);
    if (!entry) return null;
    if (entry.expiresAt <= this.now()) {
      this.cache.delete(key);
      return null;
    }
    return entry.value;
  }

  set(key, value, ttlMs = this.ttlMs) {
    this.cache.set(key, {
      value,
      expiresAt: this.now() + Math.max(0, Number(ttlMs) || 0),
    });
    return value;
  }

  invalidate(key) {
    this.cache.delete(key);
  }

  clear() {
    this.cache.clear();
    this.inflight.clear();
  }

  async getOrLoad(key, loader, { ttlMs = this.ttlMs, force = false } = {}) {
    if (!force) {
      const cached = this.get(key);
      if (cached !== null) return { value: cached, source: "CACHE" };
      if (this.inflight.has(key)) return { value: await this.inflight.get(key), source: "INFLIGHT" };
    }

    const promise = Promise.resolve().then(loader);
    this.inflight.set(key, promise);
    try {
      const value = await promise;
      this.set(key, value, ttlMs);
      return { value, source: "LOADER" };
    } finally {
      this.inflight.delete(key);
    }
  }

  stats() {
    return {
      version: REQUEST_CACHE_V1_VERSION,
      cachedEntries: this.cache.size,
      inflightRequests: this.inflight.size,
      ttlMs: this.ttlMs,
    };
  }
}

export default RequestCacheV1;
