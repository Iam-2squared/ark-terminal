const runtimeLocation = globalThis.location;

const isLiveServer =
  runtimeLocation &&
  (runtimeLocation.hostname === "127.0.0.1" ||
    runtimeLocation.hostname === "localhost") &&
  runtimeLocation.port !== "3000";

export const ARK_API_BASE =
  !runtimeLocation || isLiveServer
    ? "https://ark-terminal.vercel.app"
    : runtimeLocation.origin;

export const QUOTE_REFRESH_MS = 15000;
export const SYMBOL_INPUT_DEBOUNCE_MS = 600;
export const HISTORY_RANGE = "10y";
export const HISTORY_INTERVAL = "1d";
export const INTRADAY_RANGE = "5d";
export const INTRADAY_INTERVAL = "15m";

export const FACTOR_CATEGORIES = Object.freeze({
  movingAverages: "trend",
  macd: "trend",
  adx: "trend",
  rsi: "overheat",
  bollingerBands: "overheat",
  stochastic: "overheat",
  atr: "risk",
  volume: "volume",
  vwap: "relativePosition",
  high52Week: "relativePosition",
  low52Week: "relativePosition",
  news: "external",
  disclosure: "external",
  sentiment: "external",
});

export const CATEGORY_WEIGHTS = Object.freeze({
  trend: 24,
  overheat: 14,
  risk: 8,
  volume: 8,
  relativePosition: 16,
  external: 30,
});

export const CATEGORY_LABELS = Object.freeze({
  trend: "トレンド系",
  overheat: "過熱系",
  risk: "リスク系",
  volume: "出来高系",
  relativePosition: "相対位置系",
  external: "外部情報",
});

export const DEFAULT_WEIGHTS = Object.freeze({
  movingAverages: 25,
  rsi: 6,
  macd: 7,
  bollingerBands: 5,
  volume: 5,
  adx: 4,
  atr: 4,
  stochastic: 4,
  vwap: 4,
  high52Week: 3,
  low52Week: 3,
  news: 12,
  disclosure: 10,
  sentiment: 8,
});

export const STORAGE_KEYS = Object.freeze({
  predictions: "arkPredictionLab.predictions.v2",
  weights: "arkPredictionLab.weights.v2",
  tradeMemory: "arkTradeMemory.records.v1",
  marketIntelligenceSnapshots:
    "arkPredictionLab.marketIntelligenceSnapshots.v1",
});

export const MINIMUM_OPTIMIZER_SAMPLES = 60;

export const BACKTEST_SPLIT = Object.freeze({
  training: 0.6,
  validation: 0.2,
  test: 0.2,
  minimumHistory: 252,
  minimumPartitionSamples: 10,
});

export const BACKTEST_COSTS = Object.freeze({
  commissionBpsPerSide: 5,
  slippageBpsPerSide: 10,
});
