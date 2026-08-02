import { getMarketDataDefinition } from "./market-data-model.js";

function resolveDefinition(value) {
  const definition = getMarketDataDefinition(value);

  if (!definition) {
    throw new RangeError(`Unknown market data symbol: ${String(value || "")}`);
  }

  return definition;
}

function isAbortError(error) {
  return error?.name === "AbortError";
}

export class MarketDataProviderError extends Error {
  constructor(message, { symbol = null, provider = null, attempts = [] } = {}) {
    super(message);
    this.name = "MarketDataProviderError";
    this.symbol = symbol;
    this.provider = provider;
    this.attempts = attempts;
  }
}

export class MarketDataProvider {
  constructor({ name, fetcher, supports = () => true } = {}) {
    if (!name || typeof name !== "string") {
      throw new TypeError("Market data provider name is required.");
    }

    if (typeof fetcher !== "function") {
      throw new TypeError("Market data provider fetcher must be a function.");
    }

    if (typeof supports !== "function") {
      throw new TypeError("Market data provider supports must be a function.");
    }

    this.name = name;
    this.fetcher = fetcher;
    this.supports = supports;
  }

  canFetch(definitionOrSymbol) {
    const definition = resolveDefinition(definitionOrSymbol);
    return Boolean(this.supports(definition));
  }

  async fetch(definitionOrSymbol, options = {}) {
    const definition = resolveDefinition(definitionOrSymbol);

    if (!this.canFetch(definition)) {
      throw new MarketDataProviderError(
        `${this.name} does not support ${definition.symbol}.`,
        {
          symbol: definition.symbol,
          provider: this.name,
        },
      );
    }

    return this.fetcher(definition, options);
  }
}

export function createHistoryMarketDataProvider({
  fetchHistory,
  name = "ark-history-api",
  range = "6mo",
  interval = "1d",
} = {}) {
  if (typeof fetchHistory !== "function") {
    throw new TypeError("fetchHistory must be a function.");
  }

  return new MarketDataProvider({
    name,
    supports: (definition) => Boolean(definition.providerSymbol),
    fetcher: async (definition, { signal } = {}) => {
      const raw = await fetchHistory(definition.providerSymbol, {
        range,
        interval,
        signal,
      });

      return {
        ...raw,
        provider: raw?.provider || name,
        requestedSymbol: definition.symbol,
        providerSymbol: definition.providerSymbol,
      };
    },
  });
}

export class CompositeMarketDataProvider {
  constructor(providers = []) {
    this.providers = providers.filter(
      (provider) => provider && typeof provider.fetch === "function",
    );

    if (!this.providers.length) {
      throw new TypeError("At least one market data provider is required.");
    }

    this.name = this.providers.map((provider) => provider.name).join(" -> ");
  }

  canFetch(definitionOrSymbol) {
    return this.providers.some(
      (provider) =>
        typeof provider.canFetch !== "function" ||
        provider.canFetch(definitionOrSymbol),
    );
  }

  async fetch(definitionOrSymbol, options = {}) {
    const definition = resolveDefinition(definitionOrSymbol);
    const attempts = [];

    for (const provider of this.providers) {
      if (
        typeof provider.canFetch === "function" &&
        !provider.canFetch(definition)
      ) {
        continue;
      }

      try {
        return await provider.fetch(definition, options);
      } catch (error) {
        if (isAbortError(error)) {
          throw error;
        }

        attempts.push({
          provider: provider.name || "unknown",
          message: error?.message || String(error),
        });
      }
    }

    throw new MarketDataProviderError(
      `No provider could fetch ${definition.symbol}.`,
      {
        symbol: definition.symbol,
        provider: this.name,
        attempts,
      },
    );
  }
}

export function composeMarketDataProviders(...providers) {
  return new CompositeMarketDataProvider(providers.flat());
}

export default MarketDataProvider;
