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
export const HISTORY_RANGE = "2y";
export const HISTORY_INTERVAL = "1d";

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
});

export const MINIMUM_OPTIMIZER_SAMPLES = 20;
