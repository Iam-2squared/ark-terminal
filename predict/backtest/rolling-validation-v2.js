import {
  createWalkForwardWindows,
  validateWalkForwardWindows,
} from "./walk-forward-splitter-v2.js";

export const ROLLING_VALIDATION_V2_VERSION =
  "rolling-validation-v2";

function finiteOrNull(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const number = Number(value);

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

function average(values) {
  const available =
    values.filter(
      Number.isFinite,
    );

  if (!available.length) {
    return null;
  }

  return (
    available.reduce(
      (
        sum,
        value,
      ) =>
        sum + value,
      0,
    ) /
    available.length
  );
}

function standardDeviation(values) {
  const mean =
    average(values);

  if (mean === null) {
    return null;
  }

  const variance =
    values.reduce(
      (
        sum,
        value,
      ) =>
        sum +
        (
          value - mean
        ) ** 2,
      0,
    ) /
    values.length;

  return Math.sqrt(
    variance,
  );
}

function normalizeDirection(value) {
  const text =
    String(value ?? "")
      .trim()
      .toUpperCase();

  if (
    [
      "BUY",
      "BULLISH",
      "UP",
      "LONG",
      "POSITIVE",
      "1",
    ].includes(text)
  ) {
    return 1;
  }

  if (
    [
      "SELL",
      "BEARISH",
      "DOWN",
      "SHORT",
      "NEGATIVE",
      "-1",
    ].includes(text)
  ) {
    return -1;
  }

  return 0;
}

function timestampOf(record) {
  const raw =
    record?.timestamp ??
    record?.date ??
    record?.datetime ??
    record?.time;

  const timestamp =
    new Date(raw).getTime();

  return Number.isFinite(timestamp)
    ? timestamp
    : null;
}

function closeOf(record) {
  return finiteOrNull(
    record?.close ??
    record?.price ??
    record?.value,
  );
}

function calculateForwardReturn(
  records,
  index,
  horizon,
) {
  const current =
    closeOf(
      records[index],
    );

  const future =
    closeOf(
      records[
        index + horizon
      ],
    );

  if (
    current === null ||
    future === null ||
    current === 0
  ) {
    return null;
  }

  return (
    (
      future -
      current
    ) /
    current
  ) * 100;
}

function normalizePrediction(
  prediction,
  record,
) {
  if (
    prediction === null ||
    prediction === undefined
  ) {
    return {
      direction:
        0,

      confidence:
        0,

      score:
        null,
    };
  }

  if (
    typeof prediction === "number"
  ) {
    return {
      direction:
        prediction > 0
          ? 1
          : prediction < 0
            ? -1
            : 0,

      confidence:
        clamp(
          Math.abs(
            prediction,
          ),
        ) ?? 0,

      score:
        prediction,
    };
  }

  const direction =
    normalizeDirection(
      prediction.direction ??
      prediction.signal ??
      prediction.recommendation,
    );

  const confidence =
    clamp(
      prediction.confidence ??
      prediction.probability ??
      prediction.score ??
      0,
    ) ?? 0;

  return {
    ...prediction,

    direction,
    confidence,

    score:
      finiteOrNull(
        prediction.score,
      ),

    timestamp:
      prediction.timestamp ??
      record?.timestamp ??
      null,
  };
}

function evaluatePrediction({
  prediction,
  forwardReturn,
  neutralThreshold,
}) {
  if (
    forwardReturn === null
  ) {
    return {
      valid:
        false,

      actualDirection:
        null,

      correct:
        null,

      signedReturn:
        null,

      confidenceWeightedReturn:
        null,
    };
  }

  const actualDirection =
    forwardReturn >
      neutralThreshold
      ? 1
      : forwardReturn <
          -neutralThreshold
        ? -1
        : 0;

  const correct =
    prediction.direction ===
    actualDirection;

  const signedReturn =
    prediction.direction === 0
      ? 0
      : forwardReturn *
        prediction.direction;

  const confidenceWeightedReturn =
    signedReturn *
    (
      prediction.confidence /
      100
    );

  return {
    valid:
      true,

    actualDirection,

    correct,

    signedReturn:
      round(
        signedReturn,
      ),

    confidenceWeightedReturn:
      round(
        confidenceWeightedReturn,
      ),
  };
}

function calculateWindowMetrics(
  evaluations,
) {
  const valid =
    evaluations.filter(
      (
        item,
      ) =>
        item.valid,
    );

  if (!valid.length) {
    return {
      sampleSize:
        0,

      accuracy:
        null,

      averageReturn:
        null,

      averageSignedReturn:
        null,

      confidenceWeightedReturn:
        null,

      averageConfidence:
        null,
    };
  }

  const correctCount =
    valid.filter(
      (
        item,
      ) =>
        item.correct,
    ).length;

  return {
    sampleSize:
      valid.length,

    accuracy:
      round(
        (
          correctCount /
          valid.length
        ) *
        100,
        2,
      ),

    averageReturn:
      round(
        average(
          valid.map(
            (
              item,
            ) =>
              item.forwardReturn,
          ),
        ),
      ),

    averageSignedReturn:
      round(
        average(
          valid.map(
            (
              item,
            ) =>
              item.signedReturn,
          ),
        ),
      ),

    confidenceWeightedReturn:
      round(
        average(
          valid.map(
            (
              item,
            ) =>
              item.confidenceWeightedReturn,
          ),
        ),
      ),

    averageConfidence:
      round(
        average(
          valid.map(
            (
              item,
            ) =>
              item.prediction.confidence,
          ),
        ),
        2,
      ),
  };
}

function calculateAggregateMetrics(
  windows,
) {
  const completed =
    windows.filter(
      (
        window,
      ) =>
        window.metrics.sampleSize > 0,
    );

  const accuracies =
    completed
      .map(
        (
          window,
        ) =>
          window.metrics.accuracy,
      )
      .filter(
        Number.isFinite,
      );

  const returns =
    completed
      .map(
        (
          window,
        ) =>
          window.metrics.averageSignedReturn,
      )
      .filter(
        Number.isFinite,
      );

  const meanAccuracy =
    average(
      accuracies,
    );

  const accuracyDeviation =
    standardDeviation(
      accuracies,
    );

  const profitableWindowCount =
    completed.filter(
      (
        window,
      ) =>
        (
          window.metrics.averageSignedReturn ??
          0
        ) > 0,
    ).length;

  return {
    completedWindows:
      completed.length,

    totalSamples:
      completed.reduce(
        (
          sum,
          window,
        ) =>
          sum +
          window.metrics.sampleSize,
        0,
      ),

    meanAccuracy:
      meanAccuracy === null
        ? null
        : round(
            meanAccuracy,
            2,
          ),

    medianAccuracy:
      accuracies.length
        ? round(
            [
              ...accuracies,
            ]
              .sort(
                (
                  left,
                  right,
                ) =>
                  left -
                  right,
              )[
                Math.floor(
                  accuracies.length /
                  2,
                )
              ],
            2,
          )
        : null,

    accuracyStandardDeviation:
      accuracyDeviation === null
        ? null
        : round(
            accuracyDeviation,
            2,
          ),

    meanSignedReturn:
      returns.length
        ? round(
            average(
              returns,
            ),
          )
        : null,

    profitableWindowRate:
      completed.length
        ? round(
            (
              profitableWindowCount /
              completed.length
            ) *
            100,
            2,
          )
        : null,

    stable:
      meanAccuracy !== null &&
      accuracyDeviation !== null &&
      meanAccuracy >= 55 &&
      accuracyDeviation <= 12,
  };
}

export async function runRollingValidation({
  records = [],
  predictor,
  splitter = {},
  predictionHorizon = 1,
  neutralThreshold = 0,
  minimumAccuracy = 50,
} = {}) {
  if (
    typeof predictor !==
    "function"
  ) {
    throw new TypeError(
      "Rolling validation predictor must be a function.",
    );
  }

  const horizon =
    Math.max(
      1,
      Math.floor(
        finiteOrNull(
          predictionHorizon,
        ) ??
        1,
      ),
    );

  const splitReport =
    createWalkForwardWindows(
      records,
      splitter,
    );

  const leakageValidation =
    validateWalkForwardWindows(
      splitReport,
    );

  if (
    !leakageValidation.valid
  ) {
    throw new Error(
      `Walk-forward leakage detected: ${leakageValidation.errors.join(" ")}`,
    );
  }

  const windows = [];

  for (
    const window
    of splitReport.windows
  ) {
    const evaluations = [];

    for (
      let index = 0;
      index <
      window.test.length;
      index += 1
    ) {
      const record =
        window.test[index];

      const absoluteIndex =
        records.findIndex(
          (
            candidate,
          ) =>
            candidate === record ||
            (
              timestampOf(candidate) !== null &&
              timestampOf(candidate) ===
              timestampOf(record)
            ),
        );

      const forwardReturn =
        absoluteIndex >= 0
          ? calculateForwardReturn(
              records,
              absoluteIndex,
              horizon,
            )
          : null;

      const prediction =
        normalizePrediction(
          await predictor({
            record,

            index,

            window,

            training:
              window.training,

            validation:
              window.validation,

            test:
              window.test,
          }),

          record,
        );

      const evaluation =
        evaluatePrediction({
          prediction,

          forwardReturn,

          neutralThreshold:
            Math.abs(
              finiteOrNull(
                neutralThreshold,
              ) ??
              0,
            ),
        });

      evaluations.push({
        ...evaluation,

        timestamp:
          record?.timestamp ??
          null,

        forwardReturn,

        prediction,
      });
    }

    const metrics =
      calculateWindowMetrics(
        evaluations,
      );

    windows.push({
      id:
        window.id,

      index:
        window.index,

      periods:
        window.periods,

      metrics,

      passed:
        metrics.accuracy !== null &&
        metrics.accuracy >=
          minimumAccuracy,

      evaluations,
    });
  }

  const aggregate =
    calculateAggregateMetrics(
      windows,
    );

  return {
    version:
      ROLLING_VALIDATION_V2_VERSION,

    splitter:
      splitReport.config,

    inputSize:
      records.length,

    windowCount:
      windows.length,

    predictionHorizon:
      horizon,

    neutralThreshold:
      Math.abs(
        finiteOrNull(
          neutralThreshold,
        ) ??
        0,
      ),

    minimumAccuracy:
      clamp(
        minimumAccuracy,
      ) ?? 50,

    leakageValidation,

    windows,

    aggregate,

    passed:
      aggregate.meanAccuracy !== null &&
      aggregate.meanAccuracy >=
        (
          clamp(
            minimumAccuracy,
          ) ??
          50
        ),

    ready:
      splitReport.ready &&
      aggregate.totalSamples > 0,
  };
}

export class RollingValidationV2Engine {
  constructor({
    predictor,
    splitter = {},
    predictionHorizon = 1,
    neutralThreshold = 0,
    minimumAccuracy = 50,
  } = {}) {
    if (
      typeof predictor !==
      "function"
    ) {
      throw new TypeError(
        "Rolling validation predictor must be a function.",
      );
    }

    this.predictor =
      predictor;

    this.splitter =
      splitter;

    this.predictionHorizon =
      predictionHorizon;

    this.neutralThreshold =
      neutralThreshold;

    this.minimumAccuracy =
      minimumAccuracy;
  }

  validate(
    records = [],
  ) {
    return runRollingValidation({
      records,

      predictor:
        this.predictor,

      splitter:
        this.splitter,

      predictionHorizon:
        this.predictionHorizon,

      neutralThreshold:
        this.neutralThreshold,

      minimumAccuracy:
        this.minimumAccuracy,
    });
  }
}

export default runRollingValidation;