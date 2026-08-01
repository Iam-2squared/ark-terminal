export const DEFAULT_MODEL_CALIBRATION = Object.freeze({
  bullishThreshold: 55,
  bearishThreshold: 45,
  minimumConfidenceScore: 60,
});

export const MODEL_CALIBRATION_GRID = Object.freeze({
  bullishThresholds: Object.freeze([55, 60, 65, 70]),
  bearishThresholds: Object.freeze([45, 40, 35, 30]),
  minimumConfidenceScores: Object.freeze([60, 65, 70, 75]),
});

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, Number(value)));
}

export function normalizeModelCalibration(
  calibration = DEFAULT_MODEL_CALIBRATION,
) {
  const bullishThreshold = finite(calibration?.bullishThreshold)
    ? clamp(Math.round(Number(calibration.bullishThreshold)), 51, 90)
    : DEFAULT_MODEL_CALIBRATION.bullishThreshold;
  const bearishThreshold = finite(calibration?.bearishThreshold)
    ? clamp(Math.round(Number(calibration.bearishThreshold)), 10, 49)
    : DEFAULT_MODEL_CALIBRATION.bearishThreshold;
  const minimumConfidenceScore = finite(calibration?.minimumConfidenceScore)
    ? clamp(Math.round(Number(calibration.minimumConfidenceScore)), 0, 100)
    : DEFAULT_MODEL_CALIBRATION.minimumConfidenceScore;

  return {
    bullishThreshold,
    bearishThreshold,
    minimumConfidenceScore,
  };
}

export function directionFromScore(
  score,
  calibration = DEFAULT_MODEL_CALIBRATION,
) {
  const normalized = normalizeModelCalibration(calibration);

  if (Number(score) >= normalized.bullishThreshold) {
    return "強気";
  }

  if (Number(score) <= normalized.bearishThreshold) {
    return "弱気";
  }

  return "中立";
}

export function calibrationKey(calibration) {
  const normalized = normalizeModelCalibration(calibration);

  return [
    normalized.bullishThreshold,
    normalized.bearishThreshold,
    normalized.minimumConfidenceScore,
  ].join(":");
}

export function sameCalibration(first, second) {
  return calibrationKey(first) === calibrationKey(second);
}

export function generateCalibrationCandidates(
  baseline = DEFAULT_MODEL_CALIBRATION,
) {
  const candidates = new Map();
  const add = (candidate) => {
    const normalized = normalizeModelCalibration(candidate);
    candidates.set(calibrationKey(normalized), normalized);
  };

  add(baseline);

  MODEL_CALIBRATION_GRID.bullishThresholds.forEach((bullishThreshold) => {
    MODEL_CALIBRATION_GRID.bearishThresholds.forEach((bearishThreshold) => {
      MODEL_CALIBRATION_GRID.minimumConfidenceScores.forEach(
        (minimumConfidenceScore) => {
          add({
            bullishThreshold,
            bearishThreshold,
            minimumConfidenceScore,
          });
        },
      );
    });
  });

  return Array.from(candidates.values());
}

export const ModelCalibrationInternals = {
  finite,
  clamp,
};
