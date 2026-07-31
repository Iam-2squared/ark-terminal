import { calculateIndicators } from "./analysis/indicators.js";
import {
  DataQualityError,
  validateIndicatorCalculations,
  validateHistoryData,
} from "./analysis/data-quality.js";
import { createPredictionOutput } from "./analysis/prediction-output.js";
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
import { extractPredictionFeatures } from "./learning/feature-extractor.js";
import { fetchAnalysisBundle } from "./data.js";
import { initMarket, setMarketHistory } from "./market.js";
import { normalizeSymbol } from "./symbols.js";
import {
  clearAnalysisError,
  finite,
  formatNumber,
  initializeRenderers,
  renderAnalysis,
  renderDataQualityReport,
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

function applyQueryParameters() {
  const parameters = new URLSearchParams(globalThis.location?.search || "");
  const symbol = parameters.get("symbol");
  const companyName = parameters.get("name");

  if (symbol) {
    inputs.stockSymbol.value = symbol.replace(/\.T$/i, "");
  }

  if (companyName) {
    inputs.companyName.value = companyName;
  }
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
    direction: state.prediction.direction,
    expectedMoveRange: state.prediction.expectedMoveRange,
    expectedReturn: state.prediction.expectedReturn,
    downsideRisk: state.prediction.downsideRisk,
    confidence: state.prediction.confidence,
    dataQuality: {
      status: state.quality.status,
      qualityScore: state.quality.qualityScore,
      missingRate: state.quality.missingRate,
    },
    marketRegime: state.marketEnvironment?.regime || "未取得",
    market: state.context?.company?.exchange || "未取得",
    features: extractPredictionFeatures(state.indicators),
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

  return result.records;
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
    let quality = validateHistoryData(bundle.history);

    renderDataQualityReport(quality);

    if (!quality.canScore) {
      throw new DataQualityError(quality);
    }

    const indicators = calculateIndicators(quality.candles, {
      qualityReport: quality,
    });
    const calculationValidation = validateIndicatorCalculations(
      indicators,
      quality.candles,
    );

    quality = {
      ...quality,
      status: calculationValidation.canScore ? quality.status : "failed",
      canScore: quality.canScore && calculationValidation.canScore,
      issues: [...quality.issues, ...calculationValidation.blockingIssues],
      blockingIssues: [
        ...quality.blockingIssues,
        ...calculationValidation.blockingIssues,
      ],
      calculationValidation,
    };
    renderDataQualityReport(quality);

    if (!quality.canScore) {
      throw new DataQualityError(quality);
    }

    const weights = loadWeights();
    const analysis = scoreAnalysis({
      indicators,
      context: bundle.context,
      weights,
    });
    const resolvedRecords = resolveStoredRecords(symbol, quality.candles);
    const prediction = createPredictionOutput({
      analysis,
      indicators,
      quality,
      period,
      records: resolvedRecords,
      symbol,
      marketEnvironment: bundle.marketEnvironment,
    });

    latestState = {
      symbol,
      companyName,
      period,
      quote: bundle.quote,
      history: {
        ...bundle.history,
        candles: quality.candles,
      },
      context: bundle.context,
      marketEnvironment: bundle.marketEnvironment,
      indicators,
      analysis,
      quality,
      prediction,
      weights,
    };

    setMarketHistory(latestState.history);
    renderAnalysis(latestState);

    if (saveRecord) {
      saveCurrentPrediction(latestState);
    }
  } catch (error) {
    if (error.name !== "AbortError") {
      console.error("Prediction analysis:", error);
      setDataSourceStatus(
        error instanceof DataQualityError ? "品質エラー" : "取得失敗",
      );
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
    const result = runWalkForwardBacktest({
      candles: latestState.history.candles,
      symbol: latestState.symbol,
      companyName:
        latestState.context?.company?.name || latestState.companyName,
      industry: latestState.context?.company?.industry,
      period: latestState.period,
      weights: latestState.weights,
      historyMetadata: {
        adjustmentMethod: latestState.history.adjustmentMethod,
        meta: latestState.history.meta,
        sourceQuality: latestState.history.sourceQuality,
        corporateActions: latestState.history.corporateActions,
      },
    });

    replacePreviousBacktest(result.records);

    const testRecords = result.records.filter(
      (record) => record.partition === "test",
    );
    const metrics = summarizePerformance(testRecords);
    const winRate = finite(metrics.winRate)
      ? `${formatNumber(metrics.winRate, 1)}%`
      : "--";
    const interval = metrics.winRateConfidenceInterval;
    const confidenceInterval =
      finite(interval?.lower) && finite(interval?.upper)
        ? `（95%信頼区間 ${formatNumber(interval.lower, 1)}～${formatNumber(
            interval.upper,
            1,
          )}%）`
        : "";

    setBacktestStatus(
      `学習${result.meta.partitions.training}件・検証${result.meta.partitions.validation}件・最終テスト${result.meta.partitions.test}件。` +
        `最終テスト勝率 ${winRate}${confidenceInterval}。` +
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
  applyQueryParameters();
  initializeRenderers();
  initMarket();

  inputs.runPredictionButton.addEventListener("click", () =>
    runAnalysis({ saveRecord: true }),
  );
  inputs.runBacktestButton.addEventListener("click", runBacktest);

  runAnalysis();
}

init();
