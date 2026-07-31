import {
  DEFAULT_ALERT_SETTINGS,
  SCREENER_STORAGE_KEYS,
} from "./config.js";

function browserStorage(storage) {
  return storage || globalThis.localStorage;
}

function readJson(key, fallback, storage) {
  try {
    const value = browserStorage(storage)?.getItem(key);

    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
}

function writeJson(key, value, storage) {
  browserStorage(storage)?.setItem(key, JSON.stringify(value));

  return value;
}

function boundedNumber(value, fallback, minimum, maximum) {
  const numeric = Number(value);

  if (!Number.isFinite(numeric)) {
    return fallback;
  }

  return Math.max(minimum, Math.min(maximum, numeric));
}

export function loadWatchlist(storage) {
  const saved = readJson(SCREENER_STORAGE_KEYS.watchlist, [], storage);

  return new Set(
    (Array.isArray(saved) ? saved : []).map((symbol) => String(symbol)),
  );
}

export function saveWatchlist(watchlist, storage) {
  const values = [...watchlist].map(String).sort();

  writeJson(SCREENER_STORAGE_KEYS.watchlist, values, storage);

  return new Set(values);
}

export function toggleWatchlist(symbol, storage) {
  const watchlist = loadWatchlist(storage);
  const normalized = String(symbol);

  if (watchlist.has(normalized)) {
    watchlist.delete(normalized);
  } else {
    watchlist.add(normalized);
  }

  return saveWatchlist(watchlist, storage);
}

export function loadAlertSettings(storage) {
  const saved = readJson(
    SCREENER_STORAGE_KEYS.alertSettings,
    {},
    storage,
  );

  return {
    ...DEFAULT_ALERT_SETTINGS,
    ...(saved && typeof saved === "object" ? saved : {}),
  };
}

export function saveAlertSettings(settings, storage) {
  const normalized = {
    enabled: settings?.enabled === true,
    minimumScore: boundedNumber(
      settings?.minimumScore,
      DEFAULT_ALERT_SETTINGS.minimumScore,
      0,
      100,
    ),
    minimumConfidence: boundedNumber(
      settings?.minimumConfidence,
      DEFAULT_ALERT_SETTINGS.minimumConfidence,
      0,
      100,
    ),
    watchlistOnly: settings?.watchlistOnly !== false,
    cooldownHours: boundedNumber(
      settings?.cooldownHours,
      DEFAULT_ALERT_SETTINGS.cooldownHours,
      1,
      24 * 30,
    ),
  };

  return writeJson(
    SCREENER_STORAGE_KEYS.alertSettings,
    normalized,
    storage,
  );
}

export function loadAlertHistory(storage) {
  const saved = readJson(SCREENER_STORAGE_KEYS.alertHistory, {}, storage);

  return saved && typeof saved === "object" ? saved : {};
}

export function saveAlertHistory(history, storage) {
  return writeJson(SCREENER_STORAGE_KEYS.alertHistory, history, storage);
}
