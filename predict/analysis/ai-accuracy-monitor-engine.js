import { summarizePerformance } from "../backtest/engine.js";
import { calculateConfidenceCalibration } from "./accuracy-confidence-calibration.js";

export const AI_ACCURACY_MONITOR_VERSION = "ai-accuracy-monitor-v1";
export const AI_ACCURACY_HORIZONS = Object.freeze([1, 3, 5, 10, 20]);
export const DEFAULT_ACCURACY_WINDOW = 30;

function finiteNumber(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const number = Number(value);

  return Number.isFinite(number) ? number : null;
}

function recordTimestamp(record = {}) {
  for (const value of [record.resolvedAt, record.createdAt]) {
    const timestamp = Date.parse(value);

    if (Number.isFinite(timestamp)) {
      return timestamp;
    }
  }

  const analysisTime = finiteNumber(record.analysisTime);

  if (analysisTime === null) {
    return 0;
  }

  return analysisTime > 1_000_000_000_000
    ? analysisTime
    : analysisTime * 1000;
}

function recordPriority(record = {}) {
  const statusPriority = record.status === "resolved" ? 2 : 1;

  return statusPriority * 10 ** 15 + recordTimestamp(record);
}

function normalizeRecords(records) {
  if (!Array.isArray(records)) {
    throw new TypeError("AI accuracy records must be an array.");
  }

  const identified = new Map();
  const anonymous = [];
  let invalidRecordCount = 0;
  let duplicateRecordCount = 0;

  records.forEach((record) => {
    if (!record || typeof record !== "object" || Array.isArray(record)) {
      invalidRecordCount += 1;
      return;
    }

    const id = String(record.id ?? "").trim();

    if (!id) {
      anonymous.push(record);
      return;
    }

    const current = identified.get(id);

    if (current) {
      duplicateRecordCount += 1;

      if (recordPriority(record) >= recordPriority(current)) {
        identified.set(id, record);
      }

      return;
    }

    identified.set(id, record);
  });

  return {
    records: [...identified.values(), ...anonymous].sort(
      (first, second) => recordTimestamp(first) - recordTimestamp(second),
    ),
    invalidRecordCount,
    duplicateRecordCount,
  };
}

function isWalkForwardRecord(record = {}) {
  const source = String(record.source || "").toLowerCase();

  return source.startsWith("walk-forward");
}

function isDevelopmentPartition(record = {}) {
  return ["training", "validation"].includes(record.partition);
}

function isValidationRecord(record = {}) {
  if (isDevelopmentPartition(record)) {
    return false;
  }

  if (record.evaluationScope === "global") {
    return true;
  }

  return record.partition === "test";
}

function isObservedRecord(record = {}) {
  return (
    record.evaluationScope !== "global" &&
    !isWalkForwardRecord(record) &&
    !["training", "validation", "test"].includes(record.partition)
  );
}

function isResolvedRecord(record = {}) {
  return (
    record.status === "resolved" &&
    finiteNumber(record.actualReturn) !== null
  );
}

function isActionableRecord(record = {}) {
  return record.hit === true || record.hit === false;
}

function actionableCount(records) {
  return records.filter(isActionableRecord).length;
}

function confidenceValue(record = {}) {
  const candidates = [
    record.confidence?.score,
    record.confidenceScore,
    record.confidence,
  ];

  for (const candidate of candidates) {
    const value = finiteNumber(candidate);

    if (value !== null) {
      return value;
    }
  }

  return null;
}

function forecastMetrics(records) {
  const errors = records
    .map((record) => {
      const explicitError = finiteNumber(record.forecastError);

      if (explicitError !== null) {
        return explicitError;
      }

      const actualReturn = finiteNumber(record.actualReturn);
      const expectedReturn = finiteNumber(record.expectedReturn);

      return actualReturn !== null && expectedReturn !== null
        ? actualReturn - expectedReturn
        : null;
    })
    .filter((value) => value !== null);

  if (!errors.length) {
    return {
      count: 0,
      meanAbsoluteError: null,
      rootMeanSquaredError: null,
      bias: null,
    };
  }

  const total = errors.reduce((sum, value) => sum + value, 0);
  const absoluteTotal = errors.reduce(
    (sum, value) => sum + Math.abs(value),
    0,
  );
  const squaredTotal = errors.reduce(
    (sum, value) => sum + value ** 2,
    0,
  );

  return {
    count: errors.length,
    meanAbsoluteError: absoluteTotal / errors.length,
    rootMeanSquaredError: Math.sqrt(squaredTotal / errors.length),
    bias: total / errors.length,
  };
}

function calibrationMetrics(records) {
  const samples = records
    .filter(isActionableRecord)
    .map((record) => ({
      confidence: confidenceValue(record),
      correct: record.hit,
    }))
    .filter((record) => record.confidence !== null);

  if (!samples.length) {
    return {
      count: 0,
      brierScore: null,
      expectedCalibrationError: null,
      averageConfidence: null,
      observedAccuracy: null,
      calibrationGap: null,
      state: "insufficient-data",
    };
  }

  const calibration = calculateConfidenceCalibration(samples);

  return {
    count: calibration.count,
    brierScore: calibration.brierScore,
    expectedCalibrationError: calibration.expectedCalibrationError,
    averageConfidence: calibration.averageConfidence,
    observedAccuracy: calibration.observedAccuracy,
    calibrationGap: calibration.calibrationGap,
    state: calibration.state,
  };
}

function reliabilityFor(sampleCount) {
  if (sampleCount === 0) {
    return {
      code: "no-data",
      label: "評価データなし",
    };
  }

  if (sampleCount < 10) {
    return {
      code: "very-low",
      label: "ごく少数・参考値",
    };
  }

  if (sampleCount < 30) {
    return {
      code: "low",
      label: "少数・暫定値",
    };
  }

  if (sampleCount < 100) {
    return {
      code: "medium",
      label: "中程度",
    };
  }

  return {
    code: "high",
    label: "十分な件数",
  };
}

function sourceComparison(source, records) {
  const performance = summarizePerformance(records);

  return {
    source,
    resolvedCount: performance.resolvedCount,
    sampleCount: performance.sampleCount,
    abstainCount: performance.abstainCount,
    coverageRate: performance.coverageRate,
    accuracy: performance.winRate,
    confidenceInterval: performance.winRateConfidenceInterval,
  };
}

function horizonMetrics(records, horizons) {
  return horizons.map((horizon) => {
    const performance = summarizePerformance(
      records.filter((record) => Number(record.period) === horizon),
    );

    return {
      horizon,
      resolvedCount: performance.resolvedCount,
      sampleCount: performance.sampleCount,
      coverageRate: performance.coverageRate,
      accuracy: performance.winRate,
      confidenceInterval: performance.winRateConfidenceInterval,
    };
  });
}

function statusFor(sampleCount) {
  if (sampleCount === 0) return "unavailable";
  if (sampleCount < 30) return "preliminary";
  return "ready";
}

export function buildAIAccuracyMonitorReport(
  records = [],
  {
    recentWindow = DEFAULT_ACCURACY_WINDOW,
    horizons = AI_ACCURACY_HORIZONS,
    generatedAt = Date.now(),
  } = {},
) {
  const normalizedWindow = Math.max(1, Math.floor(Number(recentWindow) || 0));
  const normalizedHorizons = [...new Set(horizons.map(Number))].filter(
    (horizon) => Number.isInteger(horizon) && horizon > 0,
  );
  const normalized = normalizeRecords(records);
  const observedResolved = normalized.records.filter(
    (record) => isObservedRecord(record) && isResolvedRecord(record),
  );
  const validationResolved = normalized.records.filter(
    (record) => isValidationRecord(record) && isResolvedRecord(record),
  );
  const observedSampleCount = actionableCount(observedResolved);
  const validationSampleCount = actionableCount(validationResolved);
  const source =
    observedSampleCount > 0
      ? "observed"
      : validationSampleCount > 0
        ? "walk-forward-test"
        : "none";
  const selectedRecords =
    source === "observed"
      ? observedResolved
      : source === "walk-forward-test"
        ? validationResolved
        : [];
  const recentRecords = selectedRecords.slice(-normalizedWindow);
  const current = summarizePerformance(recentRecords);
  const allTime = summarizePerformance(selectedRecords);
  const reliability = reliabilityFor(current.sampleCount);
  const pendingCount = normalized.records.filter(
    (record) => isObservedRecord(record) && record.status === "pending",
  ).length;
  const excludedTrainingValidationCount = normalized.records.filter(
    isDevelopmentPartition,
  ).length;

  return {
    version: AI_ACCURACY_MONITOR_VERSION,
    generatedAt: new Date(generatedAt).toISOString(),
    status: statusFor(current.sampleCount),
    source,
    recentWindow: normalizedWindow,
    current: {
      resolvedCount: current.resolvedCount,
      sampleCount: current.sampleCount,
      abstainCount: current.abstainCount,
      coverageRate: current.coverageRate,
      accuracy: current.winRate,
      confidenceInterval: current.winRateConfidenceInterval,
    },
    allTime: {
      resolvedCount: allTime.resolvedCount,
      sampleCount: allTime.sampleCount,
      abstainCount: allTime.abstainCount,
      coverageRate: allTime.coverageRate,
      accuracy: allTime.winRate,
      confidenceInterval: allTime.winRateConfidenceInterval,
    },
    horizons: horizonMetrics(selectedRecords, normalizedHorizons),
    forecastError: forecastMetrics(selectedRecords),
    calibration: calibrationMetrics(selectedRecords),
    reliability,
    evidence: {
      observed: sourceComparison("observed", observedResolved),
      validation: sourceComparison(
        "walk-forward-test",
        validationResolved,
      ),
    },
    audit: {
      inputRecordCount: records.length,
      normalizedRecordCount: normalized.records.length,
      invalidRecordCount: normalized.invalidRecordCount,
      duplicateRecordCount: normalized.duplicateRecordCount,
      excludedTrainingValidationCount,
      pendingCount,
      selectedResolvedCount: selectedRecords.length,
      recentResolvedCount: recentRecords.length,
      futureInformationIncluded: false,
    },
    metricDefinition: {
      accuracy: "確定済みで採用された予測の方向的中率",
      confidence: "予測時のデータ品質であり、的中確率ではない",
      primaryEvidence: "実績予測を優先し、不足時のみ最終テストを使用",
    },
    executionAllowed: false,
  };
}

export const AIAccuracyMonitorInternals = Object.freeze({
  finiteNumber,
  recordTimestamp,
  isWalkForwardRecord,
  isDevelopmentPartition,
  isValidationRecord,
  isObservedRecord,
  isResolvedRecord,
  forecastMetrics,
  calibrationMetrics,
  reliabilityFor,
});
