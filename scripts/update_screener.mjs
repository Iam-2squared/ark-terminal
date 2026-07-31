import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

import { HistoryInternals } from "../api/history.js";
import {
  buildBlockedEntry,
  buildScreenerEntry,
} from "../discovery/engine.js";
import { DEFAULT_WEIGHTS } from "../predict/config.js";
import {
  finalizeScreenerBatch,
  planScreenerBatch,
} from "./screener-progress.mjs";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(scriptDirectory, "..");
const universePath = path.join(root, "data", "screener-universe.json");
const snapshotPath = path.join(root, "data", "screener-snapshot.json");
const progressPath = path.join(root, "data", "screener-progress.json");
const concurrency = Math.max(
  1,
  Math.min(8, Number(process.env.SCREENER_CONCURRENCY) || 4),
);
const delayMs = Math.max(0, Number(process.env.SCREENER_DELAY_MS) || 300);
const maximumSymbols = Math.max(
  0,
  Number(process.env.SCREENER_MAX_SYMBOLS) || 0,
);
const configuredBatchSize = Math.max(
  1,
  Number(process.env.SCREENER_BATCH_SIZE) || 240,
);
const batchSize =
  maximumSymbols > 0
    ? Math.min(configuredBatchSize, maximumSymbols)
    : configuredBatchSize;
const resetProgress =
  String(process.env.SCREENER_RESET_PROGRESS || "").toLowerCase() === "true";

async function readJson(file, fallback) {
  try {
    return JSON.parse(await readFile(file, "utf8"));
  } catch {
    return fallback;
  }
}

function wait(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function retry(task, maximumAttempts = 3) {
  let latestError;

  for (let attempt = 1; attempt <= maximumAttempts; attempt += 1) {
    try {
      return await task();
    } catch (error) {
      latestError = error;

      if (attempt < maximumAttempts) {
        await wait(750 * 2 ** (attempt - 1));
      }
    }
  }

  throw latestError;
}

async function analyze(metadata) {
  const scannedAt = new Date().toISOString();

  try {
    const history = await retry(() =>
      HistoryInternals.fetchYahooHistory({
        symbol: metadata.symbol,
        range: "2y",
        interval: "1d",
      }),
    );

    return buildScreenerEntry({
      history,
      metadata,
      weights: DEFAULT_WEIGHTS,
      scannedAt,
    });
  } catch (error) {
    return buildBlockedEntry({
      symbol: metadata.symbol,
      metadata,
      error,
      scannedAt,
    });
  } finally {
    await wait(delayMs);
  }
}

async function pool(values, worker, size) {
  const results = new Array(values.length);
  let nextIndex = 0;

  async function runWorker() {
    while (nextIndex < values.length) {
      const index = nextIndex;

      nextIndex += 1;
      results[index] = await worker(values[index], index);

      if ((index + 1) % 50 === 0 || index + 1 === values.length) {
        console.log(`Scanned ${index + 1}/${values.length}`);
      }
    }
  }

  await Promise.all(
    Array.from(
      {
        length: Math.min(size, values.length),
      },
      runWorker,
    ),
  );

  return results;
}

const universePayload = await readJson(universePath, {
  entries: [],
});
const universe = Array.isArray(universePayload)
  ? universePayload
  : universePayload.entries || [];

if (!universe.length) {
  throw new Error("スクリーニング対象の銘柄一覧が空です。");
}

const previousPayload = await readJson(snapshotPath, {
  entries: [],
});
const previousEntries = Array.isArray(previousPayload)
  ? previousPayload
  : previousPayload.entries || [];
const previousBySymbol = new Map(
  previousEntries.map((entry) => [String(entry.symbol), entry]),
);
const previousProgress = await readJson(progressPath, {});
const batchPlan = planScreenerBatch({
  universe,
  progress: previousProgress,
  batchSize,
  reset: resetProgress,
});
const selected = batchPlan.selected;

console.log(
  `Cycle ${batchPlan.cycleNumber}: ${batchPlan.startIndex + 1}-${batchPlan.endIndex}/${batchPlan.universeCount}`,
);

const updates = await pool(selected, analyze, concurrency);

updates.forEach((entry) => {
  const previous = previousBySymbol.get(String(entry.symbol));

  if (entry.status === "failed" && previous?.status === "analyzed") {
    previousBySymbol.set(String(entry.symbol), {
      ...previous,
      stale: true,
      lastError: entry.error,
      lastAttemptAt: entry.scannedAt,
    });
  } else {
    previousBySymbol.set(String(entry.symbol), entry);
  }
});

const currentSymbols = new Set(universe.map((entry) => String(entry.symbol)));
const entries = [...previousBySymbol.values()]
  .filter((entry) => currentSymbols.has(String(entry.symbol)))
  .sort((first, second) => {
    const scoreDifference =
      (Number(second.aiScore) || -Infinity) -
      (Number(first.aiScore) || -Infinity);

    return scoreDifference || String(first.symbol).localeCompare(second.symbol);
  });
const analyzedCount = entries.filter(
  (entry) => entry.status === "analyzed",
).length;
const blockedCount = entries.filter(
  (entry) => entry.status === "blocked",
).length;
const failedCount = entries.filter(
  (entry) => entry.status === "failed",
).length;
const batchAnalyzedCount = updates.filter(
  (entry) => entry.status === "analyzed",
).length;
const batchBlockedCount = updates.filter(
  (entry) => entry.status === "blocked",
).length;
const batchFailedCount = updates.filter(
  (entry) => entry.status === "failed",
).length;
const completedAt = new Date().toISOString();
const progress = finalizeScreenerBatch({
  plan: batchPlan,
  counts: {
    analyzed: batchAnalyzedCount,
    blocked: batchBlockedCount,
    failed: batchFailedCount,
  },
  completedAt,
});
const payload = {
  meta: {
    mode: "incremental-scheduled-snapshot",
    generatedAt: completedAt,
    universeCount: universe.length,
    analyzedCount,
    blockedCount,
    failedCount,
    coveragePercent: Math.round((analyzedCount / universe.length) * 100),
    provider: "yahoo-finance",
    model: "Prediction Lab category-capped technical score",
    refreshProgress: {
      cycleNumber: progress.cycleNumber,
      processed: progress.processedInCycle,
      total: progress.universeCount,
      percent: Math.round(
        (progress.processedInCycle / progress.universeCount) * 100,
      ),
      cycleComplete: progress.cycleComplete,
      nextIndex: progress.nextIndex,
      lastFullCycleAt: progress.lastFullCycleAt,
      lastBatch: progress.lastBatch,
    },
  },
  entries,
};

await writeFile(
  snapshotPath,
  `${JSON.stringify(payload, null, 2)}\n`,
  "utf8",
);

await writeFile(
  progressPath,
  `${JSON.stringify(progress, null, 2)}\n`,
  "utf8",
);

console.log(
  `Snapshot: analyzed=${analyzedCount}, blocked=${blockedCount}, failed=${failedCount}, universe=${universe.length}, cycle=${progress.processedInCycle}/${progress.universeCount}`,
);
