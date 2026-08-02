function round(value, digits = 6) {
  if (!Number.isFinite(value)) {
    return 0;
  }

  const factor = 10 ** digits;
  return Math.round((value + Number.EPSILON) * factor) / factor;
}

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function normalizeConfidence(value) {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return 0;
  }

  return clamp(number > 1 ? number / 100 : number, 0, 1);
}

function readConfidence(row) {
  const candidates = [
    row?.confidence,
    row?.confidenceScore,
    row?.probability,
    row?.score,
    row?.result?.confidence,
    row?.analysis?.confidence,
  ];

  for (const candidate of candidates) {
    const value = Number(candidate);

    if (Number.isFinite(value)) {
      return normalizeConfidence(value);
    }
  }

  return 0;
}

function readCorrect(row) {
  const candidates = [
    row?.correct,
    row?.isCorrect,
    row?.hit,
    row?.result?.correct,
    row?.outcome?.correct,
  ];

  for (const candidate of candidates) {
    if (typeof candidate === "boolean") {
      return candidate;
    }
  }

  const profitCandidates = [
    row?.profit,
    row?.pnl,
    row?.return,
    row?.result?.profit,
  ];

  for (const candidate of profitCandidates) {
    const profit = Number(candidate);

    if (Number.isFinite(profit)) {
      return profit > 0;
    }
  }

  return false;
}

function calibrationState(gap, threshold) {
  if (gap > threshold) {
    return "underconfident";
  }

  if (gap < -threshold) {
    return "overconfident";
  }

  return "calibrated";
}

export function calculateConfidenceCalibration(
  rows = [],
  options = {},
) {
  if (!Array.isArray(rows)) {
    throw new TypeError("rows must be an array");
  }

  const binCount = Number.isInteger(options.binCount)
    ? Math.max(1, options.binCount)
    : 10;

  const threshold = Number.isFinite(
    Number(options.threshold),
  )
    ? Math.max(0, Number(options.threshold))
    : 0.05;

  const normalized = rows.map((row) => ({
    confidence: readConfidence(row),
    correct: readCorrect(row),
  }));

  if (normalized.length === 0) {
    return {
      count: 0,
      brierScore: 0,
      expectedCalibrationError: 0,
      averageConfidence: 0,
      observedAccuracy: 0,
      calibrationGap: 0,
      state: "insufficient-data",
      bins: [],
    };
  }

  const bins = Array.from({ length: binCount }, (_, index) => ({
    index,
    minimum: index / binCount,
    maximum: (index + 1) / binCount,
    count: 0,
    confidenceTotal: 0,
    correctTotal: 0,
  }));

  let brierTotal = 0;
  let confidenceTotal = 0;
  let correctTotal = 0;

  for (const row of normalized) {
    const outcome = row.correct ? 1 : 0;
    const binIndex = Math.min(
      binCount - 1,
      Math.floor(row.confidence * binCount),
    );

    const bin = bins[binIndex];

    bin.count += 1;
    bin.confidenceTotal += row.confidence;
    bin.correctTotal += outcome;

    brierTotal += (row.confidence - outcome) ** 2;
    confidenceTotal += row.confidence;
    correctTotal += outcome;
  }

  const resultBins = bins.map((bin) => {
    const averageConfidence =
      bin.count > 0
        ? bin.confidenceTotal / bin.count
        : 0;

    const observedAccuracy =
      bin.count > 0
        ? bin.correctTotal / bin.count
        : 0;

    const gap = observedAccuracy - averageConfidence;

    return {
      index: bin.index,
      minimum: round(bin.minimum),
      maximum: round(bin.maximum),
      count: bin.count,
      averageConfidence: round(averageConfidence),
      observedAccuracy: round(observedAccuracy),
      calibrationGap: round(gap),
      state:
        bin.count > 0
          ? calibrationState(gap, threshold)
          : "empty",
    };
  });

  const expectedCalibrationError = resultBins.reduce(
    (sum, bin) =>
      sum +
      (bin.count / normalized.length) *
        Math.abs(bin.calibrationGap),
    0,
  );

  const averageConfidence =
    confidenceTotal / normalized.length;

  const observedAccuracy =
    correctTotal / normalized.length;

  const calibrationGap =
    observedAccuracy - averageConfidence;

  return {
    count: normalized.length,
    brierScore: round(
      brierTotal / normalized.length,
    ),
    expectedCalibrationError: round(
      expectedCalibrationError,
    ),
    averageConfidence: round(averageConfidence),
    observedAccuracy: round(observedAccuracy),
    calibrationGap: round(calibrationGap),
    state: calibrationState(calibrationGap, threshold),
    bins: resultBins,
  };
}

export default calculateConfidenceCalibration;
