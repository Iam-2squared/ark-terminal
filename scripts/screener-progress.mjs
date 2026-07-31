import { createHash } from "node:crypto";

export const SCREENER_PROGRESS_VERSION = 1;

function positiveInteger(value, fallback) {
  const numeric = Number(value);

  return Number.isInteger(numeric) && numeric > 0 ? numeric : fallback;
}

export function fingerprintUniverse(universe) {
  const symbols = (Array.isArray(universe) ? universe : [])
    .map((entry) => String(entry.symbol || ""))
    .filter(Boolean)
    .join("\n");

  return createHash("sha256").update(symbols).digest("hex");
}

export function planScreenerBatch({
  universe,
  progress = {},
  batchSize = 240,
  reset = false,
  now = new Date().toISOString(),
}) {
  if (!Array.isArray(universe) || !universe.length) {
    throw new Error("スクリーニング対象の銘柄一覧が空です。");
  }

  const universeFingerprint = fingerprintUniverse(universe);
  const universeChanged =
    progress.universeFingerprint !== universeFingerprint ||
    Number(progress.universeCount) !== universe.length;
  const startsNewCycle =
    reset || universeChanged || progress.cycleComplete === true;
  const requestedBatchSize = positiveInteger(batchSize, 240);
  const cycleNumber = startsNewCycle
    ? universeChanged || !Number.isInteger(Number(progress.cycleNumber))
      ? 1
      : Number(progress.cycleNumber) + 1
    : positiveInteger(progress.cycleNumber, 1);
  const previousNextIndex = Number(progress.nextIndex);
  const startIndex =
    startsNewCycle ||
    !Number.isInteger(previousNextIndex) ||
    previousNextIndex < 0 ||
    previousNextIndex >= universe.length
      ? 0
      : previousNextIndex;
  const endIndex = Math.min(
    universe.length,
    startIndex + requestedBatchSize,
  );

  return {
    selected: universe.slice(startIndex, endIndex),
    universeCount: universe.length,
    universeFingerprint,
    universeChanged,
    startsNewCycle,
    cycleNumber,
    cycleStartedAt: startsNewCycle
      ? now
      : progress.cycleStartedAt || now,
    previousLastFullCycleAt: progress.lastFullCycleAt || null,
    previousBatchesCompleted: Math.max(
      0,
      Number(progress.batchesCompleted) || 0,
    ),
    processedBefore: startsNewCycle
      ? 0
      : Math.max(0, Number(progress.processedInCycle) || 0),
    startIndex,
    endIndex,
    plannedAt: now,
  };
}

export function finalizeScreenerBatch({
  plan,
  counts = {},
  completedAt = new Date().toISOString(),
}) {
  const processedInCycle = Math.min(
    plan.universeCount,
    plan.processedBefore + plan.selected.length,
  );
  const cycleComplete = plan.endIndex >= plan.universeCount;

  return {
    version: SCREENER_PROGRESS_VERSION,
    universeFingerprint: plan.universeFingerprint,
    universeCount: plan.universeCount,
    cycleNumber: plan.cycleNumber,
    cycleStartedAt: plan.cycleStartedAt,
    lastBatchAt: completedAt,
    lastFullCycleAt: cycleComplete
      ? completedAt
      : plan.previousLastFullCycleAt,
    nextIndex: cycleComplete ? 0 : plan.endIndex,
    processedInCycle,
    cycleComplete,
    batchesCompleted: plan.previousBatchesCompleted + 1,
    lastBatch: {
      startIndex: plan.startIndex,
      endIndex: plan.endIndex,
      count: plan.selected.length,
      analyzed: Math.max(0, Number(counts.analyzed) || 0),
      blocked: Math.max(0, Number(counts.blocked) || 0),
      failed: Math.max(0, Number(counts.failed) || 0),
    },
  };
}

export const ScreenerProgressInternals = {
  positiveInteger,
};
