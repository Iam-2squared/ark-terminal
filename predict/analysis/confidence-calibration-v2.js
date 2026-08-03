export const CONFIDENCE_CALIBRATION_V2_VERSION =
  "confidence-calibration-v2";

function finiteOrNull(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const number =
    Number(value);

  return Number.isFinite(number)
    ? number
    : null;
}

function clamp(
  value,
  minimum = 0,
  maximum = 100,
) {
  const number =
    finiteOrNull(value);

  if (number === null) {
    return null;
  }

  return Math.min(
    maximum,
    Math.max(
      minimum,
      number,
    ),
  );
}

function round(
  value,
  digits = 4,
) {
  if (!Number.isFinite(value)) {
    return value;
  }

  const factor =
    10 ** digits;

  return (
    Math.round(
      value * factor,
    ) / factor
  );
}

function normalizeOutcome(value) {
  if (
    value === true ||
    value === 1 ||
    value === "1"
  ) {
    return 1;
  }

  if (
    value === false ||
    value === 0 ||
    value === "0"
  ) {
    return 0;
  }

  const text =
    String(value ?? "")
      .trim()
      .toUpperCase();

  if (
    [
      "CORRECT",
      "WIN",
      "SUCCESS",
      "HIT",
      "TRUE",
    ].includes(text)
  ) {
    return 1;
  }

  if (
    [
      "WRONG",
      "LOSS",
      "FAIL",
      "MISS",
      "FALSE",
    ].includes(text)
  ) {
    return 0;
  }

  return null;
}

function normalizeRecord(
  record,
) {
  if (
    !record ||
    typeof record !== "object" ||
    Array.isArray(record)
  ) {
    return null;
  }

  const confidence =
    clamp(
      record.confidence ??
      record.predictedConfidence ??
      record.probability,
    );

  const outcome =
    normalizeOutcome(
      record.outcome ??
      record.correct ??
      record.actual,
    );

  if (
    confidence === null ||
    outcome === null
  ) {
    return null;
  }

  return {
    confidence,
    probability:
      confidence / 100,
    outcome,
    weight:
      Math.max(
        0,
        finiteOrNull(
          record.weight,
        ) ??
        1,
      ),
  };
}

function weightedAverage(
  values,
) {
  const available =
    values.filter(
      (
        item,
      ) =>
        Number.isFinite(
          item.value,
        ) &&
        Number.isFinite(
          item.weight,
        ) &&
        item.weight > 0,
    );

  const weightTotal =
    available.reduce(
      (
        sum,
        item,
      ) =>
        sum + item.weight,
      0,
    );

  if (!weightTotal) {
    return null;
  }

  return available.reduce(
    (
      sum,
      item,
    ) =>
      sum +
      item.value *
      item.weight,
    0,
  ) / weightTotal;
}

function createBins(
  binCount,
) {
  return Array.from(
    {
      length:
        binCount,
    },
    (
      _,
      index,
    ) => ({
      index,
      minimum:
        index *
        (
          100 /
          binCount
        ),
      maximum:
        (
          index + 1
        ) *
        (
          100 /
          binCount
        ),
      records:
        [],
    }),
  );
}

function assignBin(
  confidence,
  binCount,
) {
  return Math.min(
    binCount - 1,
    Math.floor(
      confidence /
      (
        100 /
        binCount
      ),
    ),
  );
}

export function calculateBrierScore(
  records = [],
) {
  const normalized =
    records
      .map(
        normalizeRecord,
      )
      .filter(Boolean);

  const score =
    weightedAverage(
      normalized.map(
        (
          record,
        ) => ({
          value:
            (
              record.probability -
              record.outcome
            ) ** 2,
          weight:
            record.weight,
        }),
      ),
    );

  return {
    score:
      score === null
        ? null
        : round(
            score,
          ),

    sampleSize:
      normalized.length,

    quality:
      score === null
        ? "UNKNOWN"
        : score <= 0.1
          ? "EXCELLENT"
          : score <= 0.18
            ? "GOOD"
            : score <= 0.25
              ? "FAIR"
              : "POOR",
  };
}

export function calculateCalibrationBins(
  records = [],
  {
    binCount = 10,
  } = {},
) {
  const normalizedBinCount =
    Math.max(
      2,
      Math.min(
        20,
        Math.floor(
          finiteOrNull(
            binCount,
          ) ??
          10,
        ),
      ),
    );

  const normalized =
    records
      .map(
        normalizeRecord,
      )
      .filter(Boolean);

  const bins =
    createBins(
      normalizedBinCount,
    );

  for (
    const record
    of normalized
  ) {
    bins[
      assignBin(
        record.confidence,
        normalizedBinCount,
      )
    ].records.push(
      record,
    );
  }

  return bins.map(
    (
      bin,
    ) => {
      const weightTotal =
        bin.records.reduce(
          (
            sum,
            record,
          ) =>
            sum +
            record.weight,
          0,
        );

      const averageConfidence =
        weightTotal > 0
          ? bin.records.reduce(
              (
                sum,
                record,
              ) =>
                sum +
                record.confidence *
                record.weight,
              0,
            ) /
            weightTotal
          : null;

      const actualAccuracy =
        weightTotal > 0
          ? bin.records.reduce(
              (
                sum,
                record,
              ) =>
                sum +
                record.outcome *
                record.weight,
              0,
            ) /
            weightTotal *
            100
          : null;

      const calibrationGap =
        averageConfidence !== null &&
        actualAccuracy !== null
          ? actualAccuracy -
            averageConfidence
          : null;

      return {
        index:
          bin.index,

        minimum:
          round(
            bin.minimum,
            2,
          ),

        maximum:
          round(
            bin.maximum,
            2,
          ),

        sampleSize:
          bin.records.length,

        weightTotal:
          round(
            weightTotal,
          ),

        averageConfidence:
          averageConfidence === null
            ? null
            : round(
                averageConfidence,
                2,
              ),

        actualAccuracy:
          actualAccuracy === null
            ? null
            : round(
                actualAccuracy,
                2,
              ),

        calibrationGap:
          calibrationGap === null
            ? null
            : round(
                calibrationGap,
                2,
              ),
      };
    },
  );
}

export function calculateExpectedCalibrationError(
  records = [],
  options = {},
) {
  const bins =
    calculateCalibrationBins(
      records,
      options,
    );

  const totalWeight =
    bins.reduce(
      (
        sum,
        bin,
      ) =>
        sum +
        bin.weightTotal,
      0,
    );

  if (!totalWeight) {
    return {
      ece:
        null,

      maximumCalibrationError:
        null,

      sampleSize:
        0,

      bins,
    };
  }

  const available =
    bins.filter(
      (
        bin,
      ) =>
        bin.calibrationGap !== null &&
        bin.weightTotal > 0,
    );

  const ece =
    available.reduce(
      (
        sum,
        bin,
      ) =>
        sum +
        Math.abs(
          bin.calibrationGap,
        ) *
        (
          bin.weightTotal /
          totalWeight
        ),
      0,
    );

  const maximumCalibrationError =
    available.length
      ? Math.max(
          ...available.map(
            (
              bin,
            ) =>
              Math.abs(
                bin.calibrationGap,
              ),
          ),
        )
      : null;

  return {
    ece:
      round(
        ece,
        2,
      ),

    maximumCalibrationError:
      maximumCalibrationError === null
        ? null
        : round(
            maximumCalibrationError,
            2,
          ),

    sampleSize:
      bins.reduce(
        (
          sum,
          bin,
        ) =>
          sum +
          bin.sampleSize,
        0,
      ),

    bins,
  };
}

export function buildConfidenceCalibrationModel(
  records = [],
  options = {},
) {
  const bins =
    calculateCalibrationBins(
      records,
      options,
    );

  const populated =
    bins.filter(
      (
        bin,
      ) =>
        bin.sampleSize > 0 &&
        bin.actualAccuracy !== null,
    );

  return {
    version:
      CONFIDENCE_CALIBRATION_V2_VERSION,

    binCount:
      bins.length,

    sampleSize:
      populated.reduce(
        (
          sum,
          bin,
        ) =>
          sum +
          bin.sampleSize,
        0,
      ),

    bins:
      populated.map(
        (
          bin,
        ) => ({
          minimum:
            bin.minimum,

          maximum:
            bin.maximum,

          calibratedConfidence:
            bin.actualAccuracy,

          rawAverageConfidence:
            bin.averageConfidence,

          sampleSize:
            bin.sampleSize,
        }),
      ),
  };
}

function interpolateCalibration(
  confidence,
  bins,
) {
  if (!bins.length) {
    return confidence;
  }

  const direct =
    bins.find(
      (
        bin,
      ) =>
        confidence >=
          bin.minimum &&
        confidence <=
          bin.maximum,
    );

  if (direct) {
    return direct.calibratedConfidence;
  }

  const sorted =
    [
      ...bins,
    ].sort(
      (
        left,
        right,
      ) =>
        left.rawAverageConfidence -
        right.rawAverageConfidence,
    );

  if (
    confidence <=
    sorted[0].rawAverageConfidence
  ) {
    return sorted[0].calibratedConfidence;
  }

  if (
    confidence >=
    sorted[
      sorted.length - 1
    ].rawAverageConfidence
  ) {
    return sorted[
      sorted.length - 1
    ].calibratedConfidence;
  }

  for (
    let index = 0;
    index < sorted.length - 1;
    index += 1
  ) {
    const left =
      sorted[index];

    const right =
      sorted[
        index + 1
      ];

    if (
      confidence >=
        left.rawAverageConfidence &&
      confidence <=
        right.rawAverageConfidence
    ) {
      const denominator =
        right.rawAverageConfidence -
        left.rawAverageConfidence;

      if (denominator === 0) {
        return (
          left.calibratedConfidence +
          right.calibratedConfidence
        ) / 2;
      }

      const ratio =
        (
          confidence -
          left.rawAverageConfidence
        ) /
        denominator;

      return (
        left.calibratedConfidence +
        (
          right.calibratedConfidence -
          left.calibratedConfidence
        ) *
        ratio
      );
    }
  }

  return confidence;
}

export function calibrateConfidence(
  confidence,
  model,
) {
  const normalized =
    clamp(
      confidence,
    );

  if (normalized === null) {
    return null;
  }

  if (
    !model ||
    !Array.isArray(
      model.bins,
    ) ||
    !model.bins.length
  ) {
    return round(
      normalized,
      2,
    );
  }

  return round(
    clamp(
      interpolateCalibration(
        normalized,
        model.bins,
      ),
    ),
    2,
  );
}

export function evaluateConfidenceCalibration(
  records = [],
  options = {},
) {
  const normalized =
    records
      .map(
        normalizeRecord,
      )
      .filter(Boolean);

  const brier =
    calculateBrierScore(
      normalized,
    );

  const calibration =
    calculateExpectedCalibrationError(
      normalized,
      options,
    );

  const averageConfidence =
    weightedAverage(
      normalized.map(
        (
          record,
        ) => ({
          value:
            record.confidence,
          weight:
            record.weight,
        }),
      ),
    );

  const accuracy =
    weightedAverage(
      normalized.map(
        (
          record,
        ) => ({
          value:
            record.outcome *
            100,
          weight:
            record.weight,
        }),
      ),
    );

  const bias =
    averageConfidence !== null &&
    accuracy !== null
      ? averageConfidence -
        accuracy
      : null;

  let status =
    "UNKNOWN";

  if (
    calibration.ece !== null
  ) {
    status =
      calibration.ece <= 5
        ? "WELL_CALIBRATED"
        : calibration.ece <= 10
          ? "ACCEPTABLE"
          : calibration.ece <= 20
            ? "NEEDS_IMPROVEMENT"
            : "POOR";
  }

  return {
    version:
      CONFIDENCE_CALIBRATION_V2_VERSION,

    sampleSize:
      normalized.length,

    averageConfidence:
      averageConfidence === null
        ? null
        : round(
            averageConfidence,
            2,
          ),

    accuracy:
      accuracy === null
        ? null
        : round(
            accuracy,
            2,
          ),

    bias:
      bias === null
        ? null
        : round(
            bias,
            2,
          ),

    biasDirection:
      bias === null
        ? "UNKNOWN"
        : bias > 2
          ? "OVERCONFIDENT"
          : bias < -2
            ? "UNDERCONFIDENT"
            : "BALANCED",

    brierScore:
      brier.score,

    brierQuality:
      brier.quality,

    expectedCalibrationError:
      calibration.ece,

    maximumCalibrationError:
      calibration.maximumCalibrationError,

    status,

    bins:
      calibration.bins,

    model:
      buildConfidenceCalibrationModel(
        normalized,
        options,
      ),
  };
}

export class ConfidenceCalibrationV2Engine {
  constructor({
    binCount = 10,
  } = {}) {
    this.binCount =
      binCount;
  }

  evaluate(
    records = [],
  ) {
    return evaluateConfidenceCalibration(
      records,
      {
        binCount:
          this.binCount,
      },
    );
  }

  train(
    records = [],
  ) {
    return buildConfidenceCalibrationModel(
      records,
      {
        binCount:
          this.binCount,
      },
    );
  }

  calibrate(
    confidence,
    model,
  ) {
    return calibrateConfidence(
      confidence,
      model,
    );
  }
}

export const confidenceCalibrationV2Engine =
  new ConfidenceCalibrationV2Engine();

export default evaluateConfidenceCalibration;