import { ARK_API_BASE, DEFAULT_WEIGHTS } from "../predict/config.js";

export { ARK_API_BASE, DEFAULT_WEIGHTS };

export const SCREENER_PATHS = Object.freeze({
  universe: "../data/screener-universe.json",
  snapshot: "../data/screener-snapshot.json",
});

export const SCREENER_STORAGE_KEYS = Object.freeze({
  watchlist: "arkDiscovery.watchlist.v1",
  alertSettings: "arkDiscovery.alertSettings.v1",
  alertHistory: "arkDiscovery.alertHistory.v1",
});

export const LIVE_SCAN_BATCH_SIZE = 6;
export const INITIAL_LIVE_SCAN_LIMIT = 18;

export const DEFAULT_ALERT_SETTINGS = Object.freeze({
  enabled: false,
  minimumScore: 70,
  minimumConfidence: 55,
  watchlistOnly: true,
  cooldownHours: 12,
});

export const PRICE_BANDS = Object.freeze({
  all: {
    minimum: null,
    maximum: null,
  },
  under300: {
    minimum: 0,
    maximum: 300,
  },
  from300To500: {
    minimum: 300,
    maximum: 500,
  },
  from500To1000: {
    minimum: 500,
    maximum: 1000,
  },
  from1000To3000: {
    minimum: 1000,
    maximum: 3000,
  },
  over3000: {
    minimum: 3000,
    maximum: null,
  },
});

export const MARKET_CAP_BANDS = Object.freeze({
  all: {
    minimum: null,
    maximum: null,
  },
  small: {
    minimum: 0,
    maximum: 50_000_000_000,
  },
  medium: {
    minimum: 50_000_000_000,
    maximum: 300_000_000_000,
  },
  large: {
    minimum: 300_000_000_000,
    maximum: 1_000_000_000_000,
  },
  mega: {
    minimum: 1_000_000_000_000,
    maximum: null,
  },
  unknown: {
    unknownOnly: true,
  },
});
