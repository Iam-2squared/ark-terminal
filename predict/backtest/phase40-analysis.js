const PHASE40_ANALYSIS_SAFETY = Object.freeze({
  mode: "HISTORICAL_BACKTEST_ANALYSIS_ONLY",
  brokerWriteAllowed: false,
  liveTradingAllowed: false,
  orderCreationAllowed: false,
  orderTransmissionAllowed: false,
  orderCancellationAllowed: false,
  orderModificationAllowed: false,
  excelOrderWriteAllowed: false,
  orderTriggerWriteAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanReviewRequired: true,
});

function finiteNumber(value, fallback = null) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function average(values) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
}

function standardDeviation(values) {
  if (values.length < 2) return null;
  const mean = average(values);
  return Math.sqrt(average(values.map((value) => (value - mean) ** 2)));
}

function percentile(sorted, p) {
  if (!sorted.length) return null;
  const index = Math.min(sorted.length - 1, Math.max(0, (sorted.length - 1) * p));
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  if (lower === upper) return sorted[lower];
  const weight = index - lower;
  return sorted[lower] * (1 - weight) + sorted[upper] * weight;
}

function normalizeResult(row, index) {
  if (!row || typeof row !== "object") throw new TypeError(`result ${index} is required`);
  return {
    id: row.id ?? `result-${index}`,
    symbol: String(row.symbol ?? "UNKNOWN").toUpperCase(),
    sector: String(row.sector ?? "UNKNOWN").toUpperCase(),
    regime: String(row.regime ?? "UNKNOWN").toUpperCase(),
    horizonDays: Math.max(1, Math.trunc(finiteNumber(row.horizonDays, 1))),
    modelRole: String(row.modelRole ?? "CHAMPION").toUpperCase(),
    partition: String(row.partition ?? "test").toLowerCase(),
    netReturn: finiteNumber(row.netReturn, 0),
    drawdown: Math.max(0, finiteNumber(row.drawdown, 0)),
    hit: row.hit === true ? true : row.hit === false ? false : null,
    confidence: finiteNumber(row.confidence, null),
    runId: row.runId ?? null,
  };
}

function summarize(rows) {
  const returns = rows.map((row) => row.netReturn);
  const wins = returns.filter((value) => value > 0);
  const losses = returns.filter((value) => value < 0);
  const directional = rows.filter((row) => row.hit !== null);
  const grossProfit = wins.reduce((sum, value) => sum + value, 0);
  const grossLoss = Math.abs(losses.reduce((sum, value) => sum + value, 0));
  const stdev = standardDeviation(returns);
  return {
    sampleCount: rows.length,
    winRate: directional.length ? directional.filter((row) => row.hit).length / directional.length : null,
    averageNetReturn: average(returns),
    medianNetReturn: returns.length ? percentile([...returns].sort((a, b) => a - b), 0.5) : null,
    totalNetReturn: returns.reduce((sum, value) => sum + value, 0),
    profitFactor: grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? Infinity : null,
    maxDrawdown: rows.reduce((max, row) => Math.max(max, row.drawdown), 0),
    sharpeApprox: stdev && stdev > 0 ? average(returns) / stdev : null,
  };
}

function groupBy(rows, key) {
  const groups = new Map();
  for (const row of rows) {
    const value = row[key] ?? "UNKNOWN";
    if (!groups.has(value)) groups.set(value, []);
    groups.get(value).push(row);
  }
  return [...groups.entries()].map(([name, items]) => ({ name, ...summarize(items) }));
}

export function buildPhase40BacktestDashboard(results = []) {
  const rows = results.map(normalizeResult);
  return {
    status: rows.length ? "READY_FOR_HUMAN_REVIEW" : "NO_RESULTS",
    overall: summarize(rows),
    bySymbol: groupBy(rows, "symbol"),
    bySector: groupBy(rows, "sector"),
    byRegime: groupBy(rows, "regime"),
    byHorizon: groupBy(rows, "horizonDays"),
    byPartition: groupBy(rows, "partition"),
    safety: { ...PHASE40_ANALYSIS_SAFETY },
  };
}

export function comparePhase40ChampionCandidate(results = []) {
  const rows = results.map(normalizeResult);
  const championRows = rows.filter((row) => row.modelRole === "CHAMPION");
  const candidateRows = rows.filter((row) => row.modelRole === "CANDIDATE");
  const champion = summarize(championRows);
  const candidate = summarize(candidateRows);
  const blockers = [];
  if (!champion.sampleCount) blockers.push("NO_CHAMPION_RESULTS");
  if (!candidate.sampleCount) blockers.push("NO_CANDIDATE_RESULTS");
  return {
    status: blockers.length ? "BLOCKED" : "READY_FOR_HUMAN_REVIEW",
    champion,
    candidate,
    deltas: {
      winRate: (candidate.winRate ?? 0) - (champion.winRate ?? 0),
      averageNetReturn: (candidate.averageNetReturn ?? 0) - (champion.averageNetReturn ?? 0),
      totalNetReturn: candidate.totalNetReturn - champion.totalNetReturn,
      profitFactor: (candidate.profitFactor ?? 0) - (champion.profitFactor ?? 0),
      maxDrawdown: candidate.maxDrawdown - champion.maxDrawdown,
    },
    blockers,
    promotionAllowed: false,
    safety: { ...PHASE40_ANALYSIS_SAFETY },
  };
}

function seededRandom(seed) {
  let state = Math.max(1, Math.trunc(finiteNumber(seed, 12345))) % 2147483647;
  return () => {
    state = (state * 16807) % 2147483647;
    return (state - 1) / 2147483646;
  };
}

export function bootstrapPhase40Advantage(results = [], options = {}) {
  const rows = results.map(normalizeResult);
  const champion = rows.filter((row) => row.modelRole === "CHAMPION").map((row) => row.netReturn);
  const candidate = rows.filter((row) => row.modelRole === "CANDIDATE").map((row) => row.netReturn);
  const sampleSize = Math.min(champion.length, candidate.length);
  if (!sampleSize) {
    return { status: "BLOCKED", blockers: ["INSUFFICIENT_PAIRED_RESULTS"], safety: { ...PHASE40_ANALYSIS_SAFETY } };
  }
  const iterations = Math.max(100, Math.trunc(finiteNumber(options.iterations, 1000)));
  const random = seededRandom(options.seed ?? 12345);
  const diffs = [];
  for (let i = 0; i < iterations; i += 1) {
    let diffSum = 0;
    for (let j = 0; j < sampleSize; j += 1) {
      const index = Math.floor(random() * sampleSize);
      diffSum += candidate[index] - champion[index];
    }
    diffs.push(diffSum / sampleSize);
  }
  const sorted = diffs.sort((a, b) => a - b);
  return {
    status: "READY_FOR_HUMAN_REVIEW",
    iterations,
    meanAdvantage: average(diffs),
    lower95: percentile(sorted, 0.025),
    upper95: percentile(sorted, 0.975),
    probabilityCandidateBetter: diffs.filter((value) => value > 0).length / diffs.length,
    promotionAllowed: false,
    safety: { ...PHASE40_ANALYSIS_SAFETY },
  };
}

export function detectPhase40Overfitting(results = [], options = {}) {
  const rows = results.map(normalizeResult);
  const training = rows.filter((row) => row.partition === "training");
  const validation = rows.filter((row) => row.partition === "validation");
  const test = rows.filter((row) => row.partition === "test");
  const minSamples = Math.max(1, Math.trunc(finiteNumber(options.minSamples, 20)));
  const trainMetrics = summarize(training);
  const validationMetrics = summarize(validation);
  const testMetrics = summarize(test);
  const warnings = [];
  if (training.length < minSamples || validation.length < minSamples || test.length < minSamples) {
    warnings.push("INSUFFICIENT_PARTITION_SAMPLES");
  }
  if ((trainMetrics.averageNetReturn ?? 0) > 0 && (testMetrics.averageNetReturn ?? 0) <= 0) {
    warnings.push("TRAIN_POSITIVE_TEST_NONPOSITIVE");
  }
  if ((trainMetrics.winRate ?? 0) - (testMetrics.winRate ?? 0) > 0.15) {
    warnings.push("WIN_RATE_DECAY");
  }
  if ((testMetrics.maxDrawdown ?? 0) > (trainMetrics.maxDrawdown ?? 0) * 1.5 && testMetrics.maxDrawdown > 0) {
    warnings.push("TEST_DRAWDOWN_EXPANSION");
  }
  if (validationMetrics.sampleCount && testMetrics.sampleCount && Math.sign(validationMetrics.averageNetReturn ?? 0) !== Math.sign(testMetrics.averageNetReturn ?? 0)) {
    warnings.push("VALIDATION_TEST_SIGN_FLIP");
  }
  return {
    status: warnings.length ? "OVERFIT_WARNING" : "NO_CONFIRMED_OVERFIT",
    training: trainMetrics,
    validation: validationMetrics,
    test: testMetrics,
    warnings,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    safety: { ...PHASE40_ANALYSIS_SAFETY },
  };
}

export function runPhase40Analysis(results = [], options = {}) {
  const dashboard = buildPhase40BacktestDashboard(results);
  const comparison = comparePhase40ChampionCandidate(results);
  const bootstrap = bootstrapPhase40Advantage(results, options.bootstrap ?? {});
  const overfitting = detectPhase40Overfitting(results, options.overfitting ?? {});
  const blockers = [
    ...(comparison.blockers ?? []),
    ...(bootstrap.blockers ?? []),
  ];
  return {
    status: blockers.length ? "BLOCKED" : "READY_FOR_HUMAN_REVIEW",
    dashboard,
    comparison,
    bootstrap,
    overfitting,
    blockers,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...PHASE40_ANALYSIS_SAFETY },
  };
}

export { PHASE40_ANALYSIS_SAFETY };
