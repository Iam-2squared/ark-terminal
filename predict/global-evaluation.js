import { normalizeSymbol } from "./symbols.js";

export const GLOBAL_EVALUATION_VERSION = "global-evaluation-v1";
export const DEFAULT_GLOBAL_EVALUATION_LIMIT = 50;

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function average(values) {
  return values.length
    ? values.reduce((sum, value) => sum + Number(value), 0) /
        values.length
    : null;
}

function median(values) {
  if (!values.length) {
    return null;
  }

  const ordered = [...values].sort((first, second) => first - second);
  const middle = Math.floor(ordered.length / 2);

  return ordered.length % 2
    ? ordered[middle]
    : (ordered[middle - 1] + ordered[middle]) / 2;
}

function maximumDrawdown(returns) {
  let equity = 1;
  let peak = 1;
  let worst = 0;

  returns.forEach((value) => {
    equity *= Math.max(0, 1 + Number(value) / 100);
    peak = Math.max(peak, equity);

    if (peak > 0) {
      worst = Math.min(
        worst,
        ((equity - peak) / peak) * 100,
      );
    }
  });

  return worst;
}

function compoundedReturn(returns) {
  if (!returns.length) {
    return null;
  }

  const equity = returns.reduce(
    (value, item) =>
      value * Math.max(0, 1 + Number(item) / 100),
    1,
  );

  return (equity - 1) * 100;
}

function symbolTokens(value) {
  if (Array.isArray(value)) {
    return value;
  }

  return String(value || "").split(/[\s,;、]+/);
}

function validSymbol(symbol) {
  return (
    /^(?:\d{4}|\d{3}[A-Z])\.T$/.test(symbol) ||
    /^[A-Z][A-Z0-9._:-]{0,19}$/.test(symbol)
  );
}

export function parseGlobalEvaluationSymbols(
  value,
  {
    maximumSymbols = DEFAULT_GLOBAL_EVALUATION_LIMIT,
  } = {},
) {
  const symbols = [];
  const duplicates = [];
  const invalid = [];
  const omitted = [];
  const seen = new Set();

  symbolTokens(value)
    .map((token) => String(token || "").trim())
    .filter(Boolean)
    .forEach((token) => {
      const symbol = normalizeSymbol(token);

      if (!symbol || !validSymbol(symbol)) {
        invalid.push(token);
        return;
      }

      if (seen.has(symbol)) {
        duplicates.push(symbol);
        return;
      }

      seen.add(symbol);

      if (symbols.length >= maximumSymbols) {
        omitted.push(symbol);
        return;
      }

      symbols.push(symbol);
    });

  return {
    symbols,
    duplicates,
    invalid,
    omitted,
    maximumSymbols,
    truncated: omitted.length > 0,
  };
}

export function createGlobalEvaluationBatchId({
  now = Date.now(),
  random = Math.random(),
} = {}) {
  const timestamp = Number(now).toString(36);
  const suffix = Math.floor(Number(random) * 1_000_000_000)
    .toString(36)
    .padStart(6, "0");

  return `global-${timestamp}-${suffix}`;
}

export function globalEvaluationRecordKey(record = {}) {
  return [
    record.batchId || "",
    record.symbol || "",
    Number(record.period) || 0,
    Number(record.analysisTime) || 0,
    record.partition || "",
  ].join("|");
}

export function deduplicateGlobalEvaluationRecords(records = []) {
  const unique = new Map();
  let duplicateCount = 0;

  records.forEach((record) => {
    const key = globalEvaluationRecordKey(record);

    if (unique.has(key)) {
      duplicateCount += 1;
    }

    unique.set(key, record);
  });

  return {
    records: Array.from(unique.values()),
    duplicateCount,
  };
}

function resolvedTestRecords(records) {
  return (records || []).filter(
    (record) =>
      record.partition === "test" &&
      record.status === "resolved" &&
      finite(record.actualReturn),
  );
}

function metricReturns(records, resolver) {
  return records
    .map(resolver)
    .filter(finite)
    .map(Number);
}

function returnMetrics(returns) {
  return {
    sampleCount: returns.length,
    averageReturn: average(returns),
    medianReturn: median(returns),
    compoundedReturn: compoundedReturn(returns),
    maximumDrawdown: returns.length
      ? maximumDrawdown(returns)
      : null,
  };
}

export function buildGlobalEvaluationSummary(records = []) {
  const testRecords = resolvedTestRecords(records);
  const adopted = testRecords.filter(
    (record) => record.hit === true || record.hit === false,
  );
  const wins = adopted.filter((record) => record.hit === true);

  const strategyReturns = metricReturns(
    testRecords,
    (record) =>
      finite(record.strategyReturn)
        ? Number(record.strategyReturn)
        : 0,
  );

  const adoptedStrategyReturns = metricReturns(
    adopted,
    (record) => record.strategyReturn,
  );

  const benchmarkReturns = metricReturns(
    testRecords,
    (record) => record.actualReturn,
  );

  const strategy = returnMetrics(strategyReturns);
  const adoptedStrategy = returnMetrics(adoptedStrategyReturns);
  const benchmark = returnMetrics(benchmarkReturns);

  const sampleCount = testRecords.length;
  const adoptedCount = adopted.length;
  const symbolCount = new Set(
    testRecords.map((record) => record.symbol).filter(Boolean),
  ).size;

  const warnings = [];

  if (sampleCount < 100) {
    warnings.push(
      "最終テストが100件未満のため、精度は暫定値です。",
    );
  }

  if (symbolCount < 10) {
    warnings.push(
      "評価銘柄が10銘柄未満のため、銘柄偏りへ注意が必要です。",
    );
  }

  return {
    version: GLOBAL_EVALUATION_VERSION,
    sampleCount,
    symbolCount,
    adoptedCount,
    abstainCount: sampleCount - adoptedCount,
    coverageRate: sampleCount
      ? (adoptedCount / sampleCount) * 100
      : null,
    winRate: adoptedCount
      ? (wins.length / adoptedCount) * 100
      : null,
    strategy,
    adoptedStrategy,
    benchmark,
    averageExcessReturn:
      finite(strategy.averageReturn) &&
      finite(benchmark.averageReturn)
        ? strategy.averageReturn - benchmark.averageReturn
        : null,
    compoundedExcessReturn:
      finite(strategy.compoundedReturn) &&
      finite(benchmark.compoundedReturn)
        ? strategy.compoundedReturn -
          benchmark.compoundedReturn
        : null,
    warnings,
  };
}

export function createGlobalEvaluationPlan(
  value,
  {
    period = 5,
    batchId = createGlobalEvaluationBatchId(),
    maximumSymbols = DEFAULT_GLOBAL_EVALUATION_LIMIT,
  } = {},
) {
  const parsed = parseGlobalEvaluationSymbols(value, {
    maximumSymbols,
  });

  return {
    version: GLOBAL_EVALUATION_VERSION,
    batchId,
    period: Number(period),
    createdAt: new Date().toISOString(),
    parsed,
    entries: parsed.symbols.map((symbol, index) => ({
      symbol,
      index,
      status: "queued",
      testSampleCount: 0,
      error: null,
    })),
  };
}

function abortError() {
  const error = new Error("全銘柄評価を停止しました。");

  error.name = "AbortError";
  return error;
}

function historyMetadata(bundle) {
  return {
    adjustmentMethod: bundle.history?.adjustmentMethod,
    meta: bundle.history?.meta,
    sourceQuality: bundle.history?.sourceQuality,
    corporateActions: bundle.history?.corporateActions,
  };
}

function decoratedTestRecords({
  records,
  batchId,
  symbol,
  symbolIndex,
  period,
}) {
  return resolvedTestRecords(records).map((record) => ({
    ...record,
    batchId,
    batchVersion: GLOBAL_EVALUATION_VERSION,
    evaluationScope: "global",
    batchSymbol: symbol,
    batchSymbolIndex: symbolIndex,
    batchPeriod: Number(period),
    benchmarkReturn: finite(record.actualReturn)
      ? Number(record.actualReturn)
      : null,
  }));
}

export async function runGlobalEvaluation({
  symbols,
  period = 5,
  weights,
  maximumSymbols = DEFAULT_GLOBAL_EVALUATION_LIMIT,
  fetchBundle,
  runBacktest,
  signal,
  onProgress = () => {},
  batchId = createGlobalEvaluationBatchId(),
}) {
  if (typeof fetchBundle !== "function") {
    throw new TypeError("fetchBundleが必要です。");
  }

  if (typeof runBacktest !== "function") {
    throw new TypeError("runBacktestが必要です。");
  }

  const plan = createGlobalEvaluationPlan(symbols, {
    period,
    batchId,
    maximumSymbols,
  });

  if (!plan.entries.length) {
    throw new Error("評価対象の銘柄コードがありません。");
  }

  const results = [];
  const records = [];

  for (
    let index = 0;
    index < plan.entries.length;
    index += 1
  ) {
    if (signal?.aborted) {
      throw abortError();
    }

    const entry = plan.entries[index];
    const progressBase = {
      batchId,
      symbol: entry.symbol,
      index,
      completed: results.length,
      total: plan.entries.length,
    };

    onProgress({
      ...progressBase,
      status: "loading",
    });

    try {
      const bundle = await fetchBundle(entry.symbol, signal);

      if (signal?.aborted) {
        throw abortError();
      }

      const result = runBacktest({
        candles: bundle.history?.candles || [],
        symbol: entry.symbol,
        companyName:
          bundle.context?.company?.name || entry.symbol,
        industry: bundle.context?.company?.industry,
        period: Number(period),
        weights,
        historyMetadata: historyMetadata(bundle),
      });

      const testRecords = decoratedTestRecords({
        records: result.records,
        batchId,
        symbol: entry.symbol,
        symbolIndex: index,
        period,
      });

      records.push(...testRecords);

      const item = {
        symbol: entry.symbol,
        status: "completed",
        testSampleCount: testRecords.length,
        selectedModel:
          result.meta?.modelSelection?.selected || null,
        selectedCandidateId:
          result.meta?.modelSelection?.selectedCandidateId || null,
        error: null,
      };

      results.push(item);

      onProgress({
        ...progressBase,
        completed: results.length,
        status: "completed",
        result: item,
      });
    } catch (error) {
      if (error?.name === "AbortError") {
        throw error;
      }

      const item = {
        symbol: entry.symbol,
        status: "failed",
        testSampleCount: 0,
        selectedModel: null,
        selectedCandidateId: null,
        error: error?.message || "評価に失敗しました。",
      };

      results.push(item);

      onProgress({
        ...progressBase,
        completed: results.length,
        status: "failed",
        result: item,
      });
    }
  }

  const deduplicated = deduplicateGlobalEvaluationRecords(records);
  const summary = buildGlobalEvaluationSummary(
    deduplicated.records,
  );

  return {
    version: GLOBAL_EVALUATION_VERSION,
    batchId,
    period: Number(period),
    symbols: plan.parsed.symbols,
    parsed: plan.parsed,
    results,
    records: deduplicated.records,
    duplicateCount: deduplicated.duplicateCount,
    completedCount: results.filter(
      (item) => item.status === "completed",
    ).length,
    failedCount: results.filter(
      (item) => item.status === "failed",
    ).length,
    summary,
    completedAt: new Date().toISOString(),
  };
}

export const GlobalEvaluationInternals = {
  finite,
  average,
  median,
  maximumDrawdown,
  compoundedReturn,
  validSymbol,
  resolvedTestRecords,
  returnMetrics,
  decoratedTestRecords,
  abortError,
};