export const PAPER_FORWARD_ORCHESTRATOR_VERSION = "paper-forward-orchestrator-v1";

const SAFETY = Object.freeze({
  mode: "PAPER_ONLY",
  executionAllowed: false,
  brokerWriteAllowed: false,
  liveTradingAllowed: false,
  orderCreationAllowed: false,
  orderCancellationAllowed: false,
  orderModificationAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

function ensureFunction(value, name) {
  if (typeof value !== "function") throw new TypeError(`${name} must be a function`);
  return value;
}

function ensureArray(value, name) {
  if (!Array.isArray(value)) throw new TypeError(`${name} must be an array`);
  return value;
}

function normalizeHorizon(value) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

export async function runPaperForwardCycle({
  marketDate,
  symbols = [],
  horizons = [1, 3, 5, 10, 20],
  dependencies = {},
  context = {},
} = {}) {
  const getMarketSnapshot = ensureFunction(dependencies.getMarketSnapshot, "dependencies.getMarketSnapshot");
  const generatePredictions = ensureFunction(dependencies.generatePredictions, "dependencies.generatePredictions");
  const savePredictions = ensureFunction(dependencies.savePredictions, "dependencies.savePredictions");
  const resolveOutcomes = ensureFunction(dependencies.resolveOutcomes, "dependencies.resolveOutcomes");
  const saveOutcomes = ensureFunction(dependencies.saveOutcomes, "dependencies.saveOutcomes");
  const refreshDashboard = ensureFunction(dependencies.refreshDashboard, "dependencies.refreshDashboard");
  const compareCandidate = ensureFunction(dependencies.compareCandidate, "dependencies.compareCandidate");

  const safeSymbols = ensureArray(symbols, "symbols")
    .map((symbol) => String(symbol ?? "").trim().toUpperCase())
    .filter(Boolean);
  const safeHorizons = ensureArray(horizons, "horizons")
    .map(normalizeHorizon)
    .filter((value) => value !== null);

  const snapshot = await getMarketSnapshot({ marketDate, symbols: safeSymbols, context, safety: SAFETY });
  const predictions = ensureArray(
    await generatePredictions({ marketDate, symbols: safeSymbols, horizons: safeHorizons, snapshot, context, safety: SAFETY }),
    "generated predictions",
  );
  const savedPredictions = await savePredictions({ marketDate, predictions, context, safety: SAFETY });
  const outcomes = ensureArray(
    await resolveOutcomes({ marketDate, horizons: safeHorizons, predictions, snapshot, context, safety: SAFETY }),
    "resolved outcomes",
  );
  const savedOutcomes = await saveOutcomes({ marketDate, outcomes, context, safety: SAFETY });
  const dashboard = await refreshDashboard({ marketDate, predictions, outcomes, context, safety: SAFETY });
  const candidateReview = await compareCandidate({ marketDate, dashboard, outcomes, context, safety: SAFETY });

  return {
    version: PAPER_FORWARD_ORCHESTRATOR_VERSION,
    marketDate: marketDate ?? null,
    symbols: safeSymbols,
    horizons: safeHorizons,
    snapshot,
    predictions,
    savedPredictions,
    outcomes,
    savedOutcomes,
    dashboard,
    candidateReview,
    sideEffects: {
      paperRecordsWritten: true,
      brokerWrites: 0,
      liveOrders: 0,
      productionUpdates: 0,
      automaticPromotions: 0,
    },
    safety: SAFETY,
  };
}

export default runPaperForwardCycle;
