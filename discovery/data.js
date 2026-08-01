import {
  ARK_API_BASE,
  DEFAULT_WEIGHTS,
  LIVE_SCAN_BATCH_SIZE,
  SCREENER_PATHS,
} from "./config.js";
import { buildBlockedEntry, buildScreenerEntry } from "./engine.js";

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    cache: "no-store",
    ...options,
  });

  if (!response.ok) {
    throw new Error(`${url} の取得に失敗しました（${response.status}）。`);
  }

  return response.json();
}

function chunks(values, size) {
  const result = [];

  for (let index = 0; index < values.length; index += size) {
    result.push(values.slice(index, index + size));
  }

  return result;
}

function metadataBySymbol(universe) {
  return new Map(
    universe.map((entry) => [
      String(entry.symbol),
      {
        ...entry,
      },
    ]),
  );
}

function calculateDiscoveryScore({ aiScore, confidence, volumeRatio }) {
  const score = Number(aiScore) || 0;
  const confidenceBonus = Number(confidence) >= 70 ? 2 : 0;
  let volumeBonus = 0;

  if (Number(volumeRatio) >= 1.5) {
    volumeBonus = 8;
  } else if (Number(volumeRatio) >= 1.2) {
    volumeBonus = 5;
  } else if (Number(volumeRatio) >= 1.0) {
    volumeBonus = 3;
  } else if (Number(volumeRatio) >= 0.8) {
    volumeBonus = 1;
  }

  return Math.min(100, Math.max(0, score + confidenceBonus + volumeBonus));
}

function mergeEntries(universe, entries) {
  const metadata = metadataBySymbol(universe);

  return entries.map((entry) => {
    const merged = {
      ...(metadata.get(String(entry.symbol)) || {}),
      ...entry,
      themes:
        entry.themes ||
        metadata.get(String(entry.symbol))?.themes ||
        [],
    };

    if (!Object.prototype.hasOwnProperty.call(merged, "discoveryScore")) {
      merged.discoveryScore = calculateDiscoveryScore({
        aiScore: merged.aiScore,
        confidence: merged.confidence,
        volumeRatio: merged.volumeRatio,
      });
    }

    return merged;
  });
}

async function requestScreenerBatch(symbols, signal) {
  const url = new URL(`${ARK_API_BASE}/api/screener`);

  url.searchParams.set("symbols", symbols.join(","));

  return fetchJson(url.toString(), {
    signal,
  });
}

async function requestHistory(symbol, metadata, signal) {
  const url = new URL(`${ARK_API_BASE}/api/history`);

  url.searchParams.set("symbol", symbol);
  url.searchParams.set("range", "2y");
  url.searchParams.set("interval", "1d");

  try {
    const history = await fetchJson(url.toString(), {
      signal,
    });

    return buildScreenerEntry({
      history,
      metadata,
      weights: DEFAULT_WEIGHTS,
    });
  } catch (error) {
    return buildBlockedEntry({
      symbol,
      metadata,
      error,
    });
  }
}

async function fallbackHistoryBatch(symbols, metadata, signal) {
  return Promise.all(
    symbols.map((symbol) =>
      requestHistory(symbol, metadata.get(symbol) || {}, signal),
    ),
  );
}

export async function loadDiscoveryDataset() {
  const [universePayload, snapshotPayload] = await Promise.all([
    fetchJson(SCREENER_PATHS.universe),
    fetchJson(SCREENER_PATHS.snapshot),
  ]);
  const universe = Array.isArray(universePayload)
    ? universePayload
    : universePayload.entries || [];
  const snapshotEntries = Array.isArray(snapshotPayload)
    ? snapshotPayload
    : snapshotPayload.entries || [];

  return {
    universe,
    entries: mergeEntries(universe, snapshotEntries),
    meta: {
      universeUpdatedAt:
        universePayload.updatedAt || universePayload.meta?.updatedAt || null,
      ...(snapshotPayload.meta || {}),
      universeCount: universe.length,
    },
  };
}

export async function scanSymbols({
  symbols,
  universe,
  signal,
  onProgress = () => {},
}) {
  const uniqueSymbols = [...new Set(symbols.map(String))];
  const metadata = metadataBySymbol(universe);
  const batches = chunks(uniqueSymbols, LIVE_SCAN_BATCH_SIZE);
  const entries = [];
  let completed = 0;
  let aggregateEndpointAvailable = true;

  for (const batch of batches) {
    let batchEntries;

    if (aggregateEndpointAvailable) {
      try {
        const payload = await requestScreenerBatch(batch, signal);

        batchEntries = Array.isArray(payload.entries) ? payload.entries : [];
      } catch (error) {
        if (error.name === "AbortError") {
          throw error;
        }

        aggregateEndpointAvailable = false;
      }
    }

    if (!aggregateEndpointAvailable) {
      batchEntries = await fallbackHistoryBatch(batch, metadata, signal);
    }

    entries.push(...mergeEntries(universe, batchEntries || []));
    completed += batch.length;
    onProgress({
      completed,
      total: uniqueSymbols.length,
    });
  }

  return entries;
}

export function mergeScanResults(existing, updates) {
  const bySymbol = new Map(
    (Array.isArray(existing) ? existing : []).map((entry) => [
      String(entry.symbol),
      entry,
    ]),
  );

  updates.forEach((entry) => {
    bySymbol.set(String(entry.symbol), entry);
  });

  return [...bySymbol.values()];
}

export const DataInternals = {
  chunks,
  metadataBySymbol,
  mergeEntries,
};
