import { calculateIndicators } from "./analysis/indicators.js";
import { scoreAnalysis } from "./analysis/scoring.js";
import { loadWeights } from "./analysis/weights.js";
import {
  resolvePredictions,
  runWalkForwardBacktest,
  summarizePerformance,
} from "./backtest/engine.js";
import {
  createPredictionRecord,
  getPredictions,
  savePrediction,
  setPredictions,
} from "./backtest/storage.js";
import { fetchAnalysisBundle } from "./data.js";
import { initMarket, setMarketHistory } from "./market.js";
import { normalizeSymbol } from "./symbols.js";
import {
  clearAnalysisError,
  finite,
  formatNumber,
  initializeRenderers,
  renderAnalysis,
  setAnalysisLoading,
  setBacktestLoading,
  setBacktestStatus,
  setDataSourceStatus,
  showAnalysisError,
} from "./ui/renderers.js";

const inputs = {};

let analysisController = null;
let latestState = null;

function collectInputs() {
  [
    "companyName",
    "stockSymbol",
    "predictionPeriod",
    "runPredictionButton",
    "runBacktestButton",
  ].forEach((id) => {
    inputs[id] = document.getElementById(id);
  });
}

function factorScoreMap(factors) {
  return Object.fromEntries(
    factors
      .filter((factor) => factor.available)
      .map((factor) => [factor.key, factor.score]),
  );
}

function saveCurrentPrediction(state) {
  const latestCandle = state.history.candles.at(-1);
  const record = createPredictionRecord({
    symbol: state.symbol,
    companyName: state.context?.company?.name || state.companyName,
    industry: state.context?.company?.industry,
    period: state.period,
    score: state.analysis.totalScore,
    reasons: state.analysis.factors
      .filter((factor) => factor.available)
      .map((factor) => factor.reason),
    predictionPrice: state.indicators.currentPrice,
    analysisTime: latestCandle.time,
    factorScores: factorScoreMap(state.analysis.factors),
  });

  savePrediction(record);
  setBacktestStatus(
    "今回の分析を成績記録へ保存しました。判定期間経過後に実績を更新します。",
  );
}

function resolveStoredRecords(symbol, candles) {
  const result = resolvePredictions(getPredictions(), symbol, candles);

  if (result.changed) {
    setPredictions(result.records);
  }
}

async function runAnalysis({ saveRecord = false } = {}) {
  const symbol = normalizeSymbol(inputs.stockSymbol.value);
  const companyName = inputs.companyName.value.trim();
  const period = Number(inputs.predictionPeriod.value);

  if (!symbol) {
    showAnalysisError("銘柄コードを入力してください。");
    return;
  }

  analysisController?.abort();
  analysisController = new AbortController();
  setAnalysisLoading(true);
  clearAnalysisError();
  setDataSourceStatus("取得中");

  try {
    const bundle = await fetchAnalysisBundle(symbol, analysisController.signal);
    const indicators = calculateIndicators(bundle.history.candles);
    const weights = loadWeights();
    const analysis = scoreAnalysis({
      indicators,
      context: bundle.context,
      weights,
    });

    latestState = {
      symbol,
      companyName,
      period,
      quote: bundle.quote,
      history: bundle.history,
      context: bundle.context,
      indicators,
      analysis,
      weights,
    };

    setMarketHistory(bundle.history);
    renderAnalysis(latestState);
    resolveStoredRecords(symbol, bundle.history.candles);

    if (saveRecord) {
      saveCurrentPrediction(latestState);
    }
  } catch (error) {
    if (error.name !== "AbortError") {
      console.error("Prediction analysis:", error);
      setDataSourceStatus("取得失敗");
      showAnalysisError(error.message || "分析データを取得できませんでした。");
    }
  } finally {
    setAnalysisLoading(false);
  }
}

function replacePreviousBacktest(records) {
  const existing = getPredictions().filter(
    (record) =>
      !(
        record.source === "walk-forward" &&
        record.symbol === latestState.symbol &&
        Number(record.period) === latestState.period
      ),
  );

  setPredictions([...existing, ...records]);
}

function runBacktest() {
  if (!latestState) {
    setBacktestStatus("先に分析を実行してください。");
    return;
  }

  setBacktestLoading(true);

  try {
    const records = runWalkForwardBacktest({
      candles: latestState.history.candles,
      symbol: latestState.symbol,
      companyName:
        latestState.context?.company?.name || latestState.companyName,
      industry: latestState.context?.company?.industry,
      period: latestState.period,
      weights: latestState.weights,
    });

    replacePreviousBacktest(records);

    const metrics = summarizePerformance(records);
    const winRate = finite(metrics.winRate)
      ? `${formatNumber(metrics.winRate, 1)}%`
      : "--";

    setBacktestStatus(
      `${records.length}件を将来データ混入なしで検証しました。` +
        `勝率 ${winRate}。` +
        '<a class="textLink" href="performance.html">成績ページを開く →</a>',
      true,
    );
  } catch (error) {
    setBacktestStatus(error.message);
  } finally {
    setBacktestLoading(false);
  }
}

function init() {
  collectInputs();
  initializeRenderers();
  initMarket();

  inputs.runPredictionButton.addEventListener("click", () =>
    runAnalysis({ saveRecord: true }),
  );
  inputs.runBacktestButton.addEventListener("click", runBacktest);

  runAnalysis();
}

init();
