export const DAILY_PAPER_PIPELINE_VERSION = "phase25-daily-paper-pipeline-v1";

const SAFETY = Object.freeze({
  mode: "PAPER_ONLY",
  brokerWriteAllowed: false,
  liveTradingAllowed: false,
  orderCreationAllowed: false,
  orderCancellationAllowed: false,
  orderModificationAllowed: false,
  productionUpdateAllowed: false,
  automaticPromotionAllowed: false,
  humanApprovalRequired: true,
});

const normalizeSymbol = (value) => String(value ?? "").trim().toUpperCase();
const unique = (values) => [...new Set(values)];

function requireFn(value, name) {
  if (typeof value !== "function") throw new TypeError(`${name} must be a function`);
  return value;
}

export async function runDailyPaperPipeline({ marketDate, symbols = [], dependencies = {}, context = {} } = {}) {
  const getMarketSnapshot = requireFn(dependencies.getMarketSnapshot, "dependencies.getMarketSnapshot");
  const validateData = requireFn(dependencies.validateData, "dependencies.validateData");
  const detectRegime = requireFn(dependencies.detectRegime, "dependencies.detectRegime");
  const rankSymbols = requireFn(dependencies.rankSymbols, "dependencies.rankSymbols");
  const generatePredictions = requireFn(dependencies.generatePredictions, "dependencies.generatePredictions");
  const createPaperOrders = requireFn(dependencies.createPaperOrders, "dependencies.createPaperOrders");
  const simulateFills = requireFn(dependencies.simulateFills, "dependencies.simulateFills");
  const persistRun = requireFn(dependencies.persistRun, "dependencies.persistRun");

  const normalizedSymbols = unique(symbols.map(normalizeSymbol).filter(Boolean));
  const snapshot = await getMarketSnapshot({ marketDate, symbols: normalizedSymbols, context, safety: SAFETY });
  const dataQuality = await validateData({ marketDate, snapshot, symbols: normalizedSymbols, context, safety: SAFETY });

  if (dataQuality?.status === "BLOCKED") {
    const blockedRun = {
      version: DAILY_PAPER_PIPELINE_VERSION,
      marketDate: marketDate ?? null,
      status: "BLOCKED",
      reason: "DATA_QUALITY_BLOCKED",
      symbols: normalizedSymbols,
      snapshot,
      dataQuality,
      regime: null,
      rankings: [],
      predictions: [],
      paperOrders: [],
      fills: [],
      safety: SAFETY,
      sideEffects: { paperWrites: 0, brokerWrites: 0, liveOrders: 0 },
    };
    await persistRun({ run: blockedRun, context, safety: SAFETY });
    return blockedRun;
  }

  const regime = await detectRegime({ marketDate, snapshot, context, safety: SAFETY });
  const rankings = await rankSymbols({ marketDate, symbols: normalizedSymbols, snapshot, regime, context, safety: SAFETY });
  const predictions = await generatePredictions({ marketDate, rankings, snapshot, regime, context, safety: SAFETY });
  const paperOrders = await createPaperOrders({ marketDate, predictions, snapshot, regime, context, safety: SAFETY });
  const fills = await simulateFills({ marketDate, paperOrders, snapshot, context, safety: SAFETY });

  const run = {
    version: DAILY_PAPER_PIPELINE_VERSION,
    marketDate: marketDate ?? null,
    status: "COMPLETED",
    symbols: normalizedSymbols,
    snapshot,
    dataQuality,
    regime,
    rankings: Array.isArray(rankings) ? rankings : [],
    predictions: Array.isArray(predictions) ? predictions : [],
    paperOrders: Array.isArray(paperOrders) ? paperOrders : [],
    fills: Array.isArray(fills) ? fills : [],
    safety: SAFETY,
    sideEffects: {
      paperWrites: 1,
      brokerWrites: 0,
      liveOrders: 0,
      productionUpdates: 0,
      automaticPromotions: 0,
    },
  };

  await persistRun({ run, context, safety: SAFETY });
  return run;
}

export default runDailyPaperPipeline;
