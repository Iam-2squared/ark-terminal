import {
  loadAlertHistory,
  loadAlertSettings,
  saveAlertHistory,
} from "./storage.js";

function finite(value) {
  if (value === null || value === undefined || value === "") {
    return false;
  }

  return Number.isFinite(Number(value));
}

export function evaluateAlertCandidates({
  entries,
  settings,
  watchlist = new Set(),
  history = {},
  now = Date.now(),
}) {
  if (!settings?.enabled) {
    return [];
  }

  const cooldownMs = (Number(settings.cooldownHours) || 12) * 60 * 60 * 1000;

  return (Array.isArray(entries) ? entries : []).filter((entry) => {
    if (
      entry.status !== "analyzed" ||
      !finite(entry.aiScore) ||
      !finite(entry.confidence)
    ) {
      return false;
    }

    if (
      Number(entry.aiScore) < Number(settings.minimumScore) ||
      Number(entry.confidence) < Number(settings.minimumConfidence)
    ) {
      return false;
    }

    if (settings.watchlistOnly && !watchlist.has(String(entry.symbol))) {
      return false;
    }

    const lastNotifiedAt = Number(history[entry.symbol]?.notifiedAt) || 0;

    return now - lastNotifiedAt >= cooldownMs;
  });
}

export async function requestBrowserNotificationPermission() {
  if (!("Notification" in globalThis)) {
    return "unsupported";
  }

  if (Notification.permission === "granted") {
    return "granted";
  }

  return Notification.requestPermission();
}

export function runBrowserAlerts(entries, watchlist, storage) {
  const settings = loadAlertSettings(storage);
  const history = loadAlertHistory(storage);
  const now = Date.now();
  const candidates = evaluateAlertCandidates({
    entries,
    settings,
    watchlist,
    history,
    now,
  });

  if (
    !candidates.length ||
    !("Notification" in globalThis) ||
    Notification.permission !== "granted"
  ) {
    return candidates;
  }

  candidates.forEach((entry) => {
    new Notification(`${entry.name} ${entry.aiScore}点`, {
      body: `信頼度${entry.confidence}・期待変動幅${Number(
        entry.expectedMove || 0,
      ).toFixed(1)}%`,
      tag: `ark-screener-${entry.symbol}`,
    });

    history[entry.symbol] = {
      notifiedAt: now,
      score: entry.aiScore,
    };
  });

  saveAlertHistory(history, storage);

  return candidates;
}

export const AlertInternals = {
  finite,
};
