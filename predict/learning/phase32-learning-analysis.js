const PHASE32_SAFETY = Object.freeze({
  mode: "LEARNING_ANALYSIS_ONLY",
  automaticCandidateCreationAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  brokerWriteAllowed: false,
  liveTradingAllowed: false,
  orderCreationAllowed: false,
  orderTransmissionAllowed: false,
  orderCancellationAllowed: false,
  orderModificationAllowed: false,
  humanApprovalRequired: true,
});

function finiteNumber(value, fallback = null) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function normalizeSignal(value) {
  const signal = String(value ?? "").toUpperCase();
  return ["BUY", "SELL", "HOLD", "NO_TRADE"].includes(signal) ? signal : "NO_TRADE";
}

function normalizeRow(row, index) {
  if (!row || typeof row !== "object") throw new TypeError(`row ${index} is required`);
  const symbol = String(row.symbol ?? "UNKNOWN").toUpperCase();
  const sector = String(row.sector ?? "UNKNOWN").toUpperCase();
  const regime = String(row.regime ?? "UNKNOWN").toUpperCase();
  const signal = normalizeSignal(row.signal);
  const confidence = finiteNumber(row.confidence, null);
  const actualReturn = finiteNumber(row.actualReturn, 0);
  const netReturn = finiteNumber(row.netReturn, actualReturn);
  const directionCorrect = row.directionCorrect === true
    ? true
    : row.directionCorrect === false
      ? false
      : signal === "BUY"
        ? actualReturn > 0
        : signal === "SELL"
          ? actualReturn < 0
          : null;
  return {
    id: row.id ?? `${symbol}-${index}`,
    symbol,
    sector,
    regime,
    signal,
    confidence,
    actualReturn,
    netReturn,
    directionCorrect,
    dataQualityPassed: row.dataQualityPassed !== false,
    costEstimatePassed: row.costEstimatePassed !== false,
    liquidityPassed: row.liquidityPassed !== false,
  };
}

export function classifyPhase32Failures(rows = [], options = {}) {
  const lossThreshold = Math.abs(finiteNumber(options.lossThreshold, 0.02));
  const highConfidence = finiteNumber(options.highConfidence, 0.75);
  return rows.map(normalizeRow).map((row) => {
    const reasons = [];
    if (!row.dataQualityPassed) reasons.push("DATA_QUALITY_FAILURE");
    if (!row.costEstimatePassed) reasons.push("COST_ESTIMATE_FAILURE");
    if (!row.liquidityPassed) reasons.push("LIQUIDITY_FAILURE");
    if (row.directionCorrect === false) reasons.push("DIRECTION_MISS");
    if (row.netReturn <= -lossThreshold) reasons.push("LOSS_THRESHOLD_BREACH");
    if ((row.confidence ?? 0) >= highConfidence && (row.directionCorrect === false || row.netReturn < 0)) {
      reasons.push("HIGH_CONFIDENCE_FAILURE");
    }
    if (row.signal === "NO_TRADE" && row.actualReturn >= lossThreshold) reasons.push("MISSED_UPSIDE");
    return {
      ...row,
      isFailure: reasons.length > 0,
      failureReasons: reasons,
    };
  });
}

function aggregateBy(rows, key) {
  const groups = new Map();
  for (const row of rows) {
    const value = row[key] || "UNKNOWN";
    if (!groups.has(value)) groups.set(value, []);
    groups.get(value).push(row);
  }
  return [...groups.entries()].map(([name, items]) => {
    const failures = items.filter((item) => item.isFailure);
    const totalNetReturn = items.reduce((sum, item) => sum + item.netReturn, 0);
    const avgConfidence = items.filter((item) => item.confidence != null).length
      ? items.filter((item) => item.confidence != null).reduce((sum, item) => sum + item.confidence, 0) /
        items.filter((item) => item.confidence != null).length
      : null;
    return {
      name,
      sampleCount: items.length,
      failureCount: failures.length,
      failureRate: items.length ? failures.length / items.length : 0,
      totalNetReturn,
      averageNetReturn: items.length ? totalNetReturn / items.length : null,
      averageConfidence: avgConfidence,
      highConfidenceFailures: failures.filter((item) => item.failureReasons.includes("HIGH_CONFIDENCE_FAILURE")).length,
    };
  }).sort((a, b) => b.failureRate - a.failureRate || a.averageNetReturn - b.averageNetReturn);
}

export function analyzePhase32Weaknesses(classifiedRows = [], options = {}) {
  const minSamples = Math.max(1, Math.trunc(finiteNumber(options.minSamples, 5)));
  const byRegime = aggregateBy(classifiedRows, "regime");
  const bySymbol = aggregateBy(classifiedRows, "symbol");
  const bySector = aggregateBy(classifiedRows, "sector");
  const flagged = [...byRegime.map((x) => ({ dimension: "REGIME", ...x })),
    ...bySymbol.map((x) => ({ dimension: "SYMBOL", ...x })),
    ...bySector.map((x) => ({ dimension: "SECTOR", ...x }))]
    .filter((item) => item.sampleCount >= minSamples && (item.failureRate >= 0.5 || item.averageNetReturn < 0));
  return {
    byRegime,
    bySymbol,
    bySector,
    flagged,
    status: flagged.length ? "WEAKNESSES_FOUND" : "NO_CONFIRMED_WEAKNESS",
    safety: { ...PHASE32_SAFETY },
  };
}

export function analyzePhase32ConfidenceCalibration(classifiedRows = [], options = {}) {
  const bins = Array.isArray(options.bins) && options.bins.length ? options.bins : [0, 0.5, 0.65, 0.8, 1.000001];
  const result = [];
  for (let i = 0; i < bins.length - 1; i += 1) {
    const lower = bins[i];
    const upper = bins[i + 1];
    const items = classifiedRows.filter((row) => row.confidence != null && row.confidence >= lower && row.confidence < upper);
    if (!items.length) continue;
    const directional = items.filter((row) => row.directionCorrect != null);
    const observedAccuracy = directional.length
      ? directional.filter((row) => row.directionCorrect === true).length / directional.length
      : null;
    const averageConfidence = items.reduce((sum, row) => sum + row.confidence, 0) / items.length;
    const calibrationGap = observedAccuracy == null ? null : averageConfidence - observedAccuracy;
    result.push({
      lower,
      upper: upper > 1 ? 1 : upper,
      sampleCount: items.length,
      averageConfidence,
      observedAccuracy,
      calibrationGap,
      overconfident: calibrationGap != null && calibrationGap > 0.15,
      underconfident: calibrationGap != null && calibrationGap < -0.15,
    });
  }
  return {
    bins: result,
    overconfidenceDetected: result.some((item) => item.overconfident),
    underconfidenceDetected: result.some((item) => item.underconfident),
    safety: { ...PHASE32_SAFETY },
  };
}

export function buildPhase32ImprovementProposals({ classifiedRows = [], weaknessReport, calibrationReport } = {}) {
  const proposals = [];
  for (const item of weaknessReport?.flagged ?? []) {
    proposals.push({
      type: "REVIEW_THRESHOLD_OR_FEATURES",
      scope: item.dimension,
      target: item.name,
      rationale: `failureRate=${item.failureRate.toFixed(3)}, averageNetReturn=${item.averageNetReturn.toFixed(6)}`,
      candidatePatchCreated: false,
      productionChangeAllowed: false,
      humanReviewRequired: true,
    });
  }
  for (const bin of calibrationReport?.bins ?? []) {
    if (bin.overconfident) {
      proposals.push({
        type: "REVIEW_CONFIDENCE_CALIBRATION",
        scope: "CONFIDENCE_BIN",
        target: `${bin.lower}-${bin.upper}`,
        rationale: `calibrationGap=${bin.calibrationGap.toFixed(3)}`,
        candidatePatchCreated: false,
        productionChangeAllowed: false,
        humanReviewRequired: true,
      });
    }
  }
  const reasonCounts = new Map();
  for (const row of classifiedRows) {
    for (const reason of row.failureReasons ?? []) reasonCounts.set(reason, (reasonCounts.get(reason) ?? 0) + 1);
  }
  for (const [reason, count] of reasonCounts.entries()) {
    proposals.push({
      type: "REVIEW_FAILURE_CLUSTER",
      scope: "FAILURE_REASON",
      target: reason,
      rationale: `count=${count}`,
      candidatePatchCreated: false,
      productionChangeAllowed: false,
      humanReviewRequired: true,
    });
  }
  return {
    status: proposals.length ? "READY_FOR_HUMAN_REVIEW" : "CONTINUE_DATA_COLLECTION",
    proposals,
    automaticCandidateCreationAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...PHASE32_SAFETY },
  };
}

export function runPhase32LearningAnalysis({ rows = [], options = {} } = {}) {
  const classifiedRows = classifyPhase32Failures(rows, options);
  const weaknessReport = analyzePhase32Weaknesses(classifiedRows, options);
  const calibrationReport = analyzePhase32ConfidenceCalibration(classifiedRows, options);
  const improvementReview = buildPhase32ImprovementProposals({ classifiedRows, weaknessReport, calibrationReport });
  return {
    status: improvementReview.status,
    classifiedRows,
    weaknessReport,
    calibrationReport,
    improvementReview,
    automaticCandidateCreationAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...PHASE32_SAFETY },
  };
}

export { PHASE32_SAFETY };
