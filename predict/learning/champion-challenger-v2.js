export const CHAMPION_CHALLENGER_V2_VERSION =
  "champion-challenger-v2";

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
          value -
          mean
        ) ** 2,
      0,
    ) /
    values.length;

  return Math.sqrt(
    variance,
  );
}

function normalizeDirection(value) {
  if (typeof value === "number") {
    if (value > 0) {
      return 1;
    }

    if (value < 0) {
      return -1;
    }

    return 0;
  }

  const text =
    String(value ?? "")
      .trim()
      .toUpperCase();

  if (
    [
      "BUY",
      "LONG",
      "UP",
      "BULLISH",
      "1",
    ].includes(text)
  ) {
    return 1;
  }

  if (
    [
      "SELL",
      "SHORT",
      "DOWN",
      "BEARISH",
      "-1",
    ].includes(text)
  ) {
    return -1;
  }

  return 0;
}

function normalizeModel(
  model,
  role,
) {
  if (
    !model ||
    typeof model !== "object" ||
    Array.isArray(model)
  ) {
    throw new TypeError(
      `${role} model must be an object.`,
    );
  }

  const id =
    String(
      model.id ??
      model.modelId ??
      model.name ??
      "",
    ).trim();

  if (!id) {
    throw new TypeError(
      `${role} model requires an id.`,
    );
  }

  return {
    id,

    version:
      String(
        model.version ??
        "unknown",
      ),

    family:
      String(
        model.family ??
        model.type ??
        "GENERAL",
      )
        .trim()
        .toUpperCase(),

    metadata:
      model.metadata ??
      {},
  };
}

function normalizeRecord(
  record,
  index,
) {
  if (
    !record ||
    typeof record !== "object"
  ) {
    return null;
  }

  const actualReturn =
    finiteOrNull(
      record.actualReturn ??
      record.realizedReturn ??
      record.return ??
      record.pnlPercent,
    );

  const actualDirection =
    actualReturn !== null
      ? actualReturn > 0
        ? 1
        : actualReturn < 0
          ? -1
          : 0
      : normalizeDirection(
          record.actualDirection ??
          record.outcome,
        );

  const championPrediction =
    record.champion ??
    record.championPrediction ??
    {};

  const challengerPrediction =
    record.challenger ??
    record.challengerPrediction ??
    {};

  const championDirection =
    normalizeDirection(
      championPrediction.direction ??
      championPrediction.signal ??
      record.championDirection,
    );

  const challengerDirection =
    normalizeDirection(
      challengerPrediction.direction ??
      challengerPrediction.signal ??
      record.challengerDirection,
    );

  const championConfidence =
    clamp(
      championPrediction.confidence ??
      record.championConfidence ??
      50,
    ) ?? 50;

  const challengerConfidence =
    clamp(
      challengerPrediction.confidence ??
      record.challengerConfidence ??
      50,
    ) ?? 50;

  const timestampValue =
    record.timestamp ??
    record.date ??
    record.createdAt ??
    null;

  const parsedTimestamp =
    timestampValue === null
      ? null
      : Date.parse(
          timestampValue,
        );

  return {
    id:
      String(
        record.id ??
        `record-${index + 1}`,
      ),

    actualReturn:
      actualReturn ?? 0,

    actualDirection,

    championDirection,

    challengerDirection,

    championConfidence,

    challengerConfidence,

    timestamp:
      Number.isFinite(
        parsedTimestamp,
      )
        ? parsedTimestamp
        : index,

    regime:
      String(
        record.regime ??
        "UNKNOWN",
      )
        .trim()
        .toUpperCase(),
  };
}

function normalizeRecords(records) {
  if (!Array.isArray(records)) {
    throw new TypeError(
      "Champion challenger records must be an array.",
    );
  }

  return records
    .map(
      normalizeRecord,
    )
    .filter(Boolean)
    .sort(
      (
        left,
        right,
      ) =>
        left.timestamp -
        right.timestamp,
    );
}

function calculateMaximumDrawdown(
  returns,
) {
  let equity = 100;
  let peak = 100;
  let maximumDrawdown = 0;

  for (
    const value
    of returns
  ) {
    equity *=
      1 +
      value / 100;

    peak =
      Math.max(
        peak,
        equity,
      );

    const drawdown =
      peak > 0
        ? (
            (
              peak -
              equity
            ) /
            peak
          ) *
          100
        : 0;

    maximumDrawdown =
      Math.max(
        maximumDrawdown,
        drawdown,
      );
  }

  return maximumDrawdown;
}

function calculateProfitFactor(
  returns,
) {
  const grossProfit =
    returns
      .filter(
        (
          value,
        ) =>
          value > 0,
      )
      .reduce(
        (
          sum,
          value,
        ) =>
          sum + value,
        0,
      );

  const grossLoss =
    Math.abs(
      returns
        .filter(
          (
            value,
          ) =>
            value < 0,
        )
        .reduce(
          (
            sum,
            value,
          ) =>
            sum + value,
          0,
        ),
    );

  if (grossLoss === 0) {
    return grossProfit > 0
      ? Infinity
      : 0;
  }

  return (
    grossProfit /
    grossLoss
  );
}

function calculateMetrics(
  records,
  role,
) {
  const directionKey =
    role === "champion"
      ? "championDirection"
      : "challengerDirection";

  const confidenceKey =
    role === "champion"
      ? "championConfidence"
      : "challengerConfidence";

  const correctness =
    records.map(
      (
        record,
      ) =>
        record[
          directionKey
        ] ===
        record.actualDirection,
    );

  const directionalReturns =
    records.map(
      (
        record,
      ) =>
        record[
          directionKey
        ] *
        record.actualReturn,
    );

  const calibrationErrors =
    records.map(
      (
        record,
        index,
      ) =>
        Math.abs(
          (
            correctness[index]
              ? 100
              : 0
          ) -
          record[
            confidenceKey
          ],
        ),
    );

  const wins =
    correctness.filter(Boolean)
      .length;

  const accuracy =
    records.length
      ? (
          wins /
          records.length
        ) *
        100
      : 0;

  const meanReturn =
    average(
      directionalReturns,
    ) ?? 0;

  const volatility =
    standardDeviation(
      directionalReturns,
    ) ?? 0;

  const profitFactor =
    calculateProfitFactor(
      directionalReturns,
    );

  const maximumDrawdown =
    calculateMaximumDrawdown(
      directionalReturns,
    );

  const calibrationError =
    average(
      calibrationErrors,
    ) ?? 100;

  const stabilityScore =
    clamp(
      100 -
      volatility *
        8 -
      maximumDrawdown *
        2,
    ) ?? 0;

  return {
    sampleCount:
      records.length,

    wins,

    losses:
      records.length -
      wins,

    accuracy:
      round(
        accuracy,
        2,
      ),

    averageReturn:
      round(
        meanReturn,
      ),

    volatility:
      round(
        volatility,
      ),

    profitFactor:
      Number.isFinite(
        profitFactor,
      )
        ? round(
            profitFactor,
          )
        : null,

    profitFactorInfinite:
      profitFactor === Infinity,

    maximumDrawdown:
      round(
        maximumDrawdown,
      ),

    calibrationError:
      round(
        calibrationError,
        2,
      ),

    stabilityScore:
      round(
        stabilityScore,
        2,
      ),

    directionalReturns,
  };
}

function percentImprovement(
  challenger,
  champion,
  higherIsBetter = true,
) {
  if (
    !Number.isFinite(challenger) ||
    !Number.isFinite(champion)
  ) {
    return null;
  }

  if (
    Math.abs(champion) <
    0.0000001
  ) {
    const difference =
      challenger -
      champion;

    return higherIsBetter
      ? difference
      : -difference;
  }

  const raw =
    (
      challenger -
      champion
    ) /
    Math.abs(champion) *
    100;

  return higherIsBetter
    ? raw
    : -raw;
}

function pairedBootstrap({
  records,
  iterations,
  seed,
}) {
  let state =
    Math.abs(
      Math.floor(
        finiteOrNull(seed) ??
        42,
      ),
    ) || 42;

  function random() {
    state =
      (
        state *
        1664525 +
        1013904223
      ) %
      4294967296;

    return (
      state /
      4294967296
    );
  }

  const differences = [];

  for (
    let iteration = 0;
    iteration < iterations;
    iteration += 1
  ) {
    let championCorrect = 0;
    let challengerCorrect = 0;

    for (
      let index = 0;
      index < records.length;
      index += 1
    ) {
      const sampled =
        records[
          Math.floor(
            random() *
            records.length
          )
        ];

      if (
        sampled.championDirection ===
        sampled.actualDirection
      ) {
        championCorrect += 1;
      }

      if (
        sampled.challengerDirection ===
        sampled.actualDirection
      ) {
        challengerCorrect += 1;
      }
    }

    differences.push(
      (
        challengerCorrect -
        championCorrect
      ) /
      records.length *
      100,
    );
  }

  differences.sort(
    (
      left,
      right,
    ) =>
      left -
      right,
  );

  const lowerIndex =
    Math.max(
      0,
      Math.floor(
        iterations *
        0.025,
      ),
    );

  const upperIndex =
    Math.min(
      differences.length - 1,
      Math.floor(
        iterations *
        0.975,
      ),
    );

  const probabilityPositive =
    differences.filter(
      (
        difference,
      ) =>
        difference > 0,
    ).length /
    differences.length *
    100;

  return {
    iterations,

    meanDifference:
      round(
        average(
          differences,
        ) ?? 0,
      ),

    lower95:
      round(
        differences[
          lowerIndex
        ] ?? 0,
      ),

    upper95:
      round(
        differences[
          upperIndex
        ] ?? 0,
      ),

    probabilityPositive:
      round(
        probabilityPositive,
        2,
      ),
  };
}

function buildChecks({
  champion,
  challenger,
  bootstrap,
  minimumSamples,
  minimumAccuracyImprovement,
  minimumReturnImprovement,
  maximumDrawdownRegression,
  maximumCalibrationRegression,
  minimumWinProbability,
}) {
  const accuracyImprovement =
    challenger.accuracy -
    champion.accuracy;

  const returnImprovement =
    percentImprovement(
      challenger.averageReturn,
      champion.averageReturn,
      true,
    );

  const drawdownImprovement =
    percentImprovement(
      challenger.maximumDrawdown,
      champion.maximumDrawdown,
      false,
    );

  const calibrationImprovement =
    champion.calibrationError -
    challenger.calibrationError;

  return [
    {
      name:
        "MINIMUM_SAMPLES",

      passed:
        challenger.sampleCount >=
        minimumSamples,

      value:
        challenger.sampleCount,

      threshold:
        minimumSamples,

      reason:
        challenger.sampleCount >=
        minimumSamples
          ? "PASSED"
          : "INSUFFICIENT_SAMPLES",
    },

    {
      name:
        "ACCURACY_IMPROVEMENT",

      passed:
        accuracyImprovement >=
        minimumAccuracyImprovement,

      value:
        round(
          accuracyImprovement,
          2,
        ),

      threshold:
        minimumAccuracyImprovement,

      reason:
        accuracyImprovement >=
        minimumAccuracyImprovement
          ? "PASSED"
          : "ACCURACY_IMPROVEMENT_NOT_MET",
    },

    {
      name:
        "RETURN_IMPROVEMENT",

      passed:
        returnImprovement !== null &&
        returnImprovement >=
          minimumReturnImprovement,

      value:
        returnImprovement === null
          ? null
          : round(
              returnImprovement,
            ),

      threshold:
        minimumReturnImprovement,

      reason:
        returnImprovement !== null &&
        returnImprovement >=
          minimumReturnImprovement
          ? "PASSED"
          : "RETURN_IMPROVEMENT_NOT_MET",
    },

    {
      name:
        "DRAWDOWN_REGRESSION",

      passed:
        drawdownImprovement !== null &&
        drawdownImprovement >=
          -maximumDrawdownRegression,

      value:
        drawdownImprovement === null
          ? null
          : round(
              drawdownImprovement,
            ),

      threshold:
        -maximumDrawdownRegression,

      reason:
        drawdownImprovement !== null &&
        drawdownImprovement >=
          -maximumDrawdownRegression
          ? "PASSED"
          : "DRAWDOWN_REGRESSION_TOO_LARGE",
    },

    {
      name:
        "CALIBRATION_REGRESSION",

      passed:
        calibrationImprovement >=
        -maximumCalibrationRegression,

      value:
        round(
          calibrationImprovement,
          2,
        ),

      threshold:
        -maximumCalibrationRegression,

      reason:
        calibrationImprovement >=
        -maximumCalibrationRegression
          ? "PASSED"
          : "CALIBRATION_REGRESSION_TOO_LARGE",
    },

    {
      name:
        "BOOTSTRAP_WIN_PROBABILITY",

      passed:
        bootstrap.probabilityPositive >=
        minimumWinProbability,

      value:
        bootstrap.probabilityPositive,

      threshold:
        minimumWinProbability,

      reason:
        bootstrap.probabilityPositive >=
        minimumWinProbability
          ? "PASSED"
          : "STATISTICAL_CONFIDENCE_NOT_MET",
    },
  ];
}

function calculateScore(
  checks,
) {
  const weights = {
    MINIMUM_SAMPLES:
      1,

    ACCURACY_IMPROVEMENT:
      3,

    RETURN_IMPROVEMENT:
      2,

    DRAWDOWN_REGRESSION:
      2,

    CALIBRATION_REGRESSION:
      1,

    BOOTSTRAP_WIN_PROBABILITY:
      3,
  };

  const totalWeight =
    checks.reduce(
      (
        sum,
        check,
      ) =>
        sum +
        (
          weights[
            check.name
          ] ?? 1
        ),
      0,
    );

  const passedWeight =
    checks.reduce(
      (
        sum,
        check,
      ) =>
        sum +
        (
          check.passed
            ? weights[
                check.name
              ] ?? 1
            : 0
        ),
      0,
    );

  return (
    passedWeight /
    totalWeight *
    100
  );
}

function determineDecision({
  checks,
  score,
  minimumPromotionScore,
}) {
  const blockers =
    checks
      .filter(
        (
          check,
        ) =>
          !check.passed,
      )
      .map(
        (
          check,
        ) =>
          check.name,
      );

  if (
    blockers.includes(
      "MINIMUM_SAMPLES",
    )
  ) {
    return {
      decision:
        "CONTINUE_SHADOW",

      reason:
        "MORE_SHADOW_DATA_REQUIRED",

      blockers,
    };
  }

  if (
    blockers.includes(
      "DRAWDOWN_REGRESSION",
    ) ||
    blockers.includes(
      "CALIBRATION_REGRESSION",
    )
  ) {
    return {
      decision:
        "REJECT_CHALLENGER",

      reason:
        "RISK_OR_CALIBRATION_REGRESSION",

      blockers,
    };
  }

  if (
    blockers.length > 0 ||
    score <
      minimumPromotionScore
  ) {
    return {
      decision:
        "CONTINUE_SHADOW",

      reason:
        "CHALLENGER_ADVANTAGE_NOT_CONFIRMED",

      blockers,
    };
  }

  return {
    decision:
      "PROMOTE_CHALLENGER",

    reason:
      "CHALLENGER_OUTPERFORMED_CHAMPION",

    blockers:
      [],
  };
}

export function evaluateChampionChallenger({
  champion,
  challenger,
  records = [],
  minimumSamples = 100,
  minimumAccuracyImprovement = 1,
  minimumReturnImprovement = 0,
  maximumDrawdownRegression = 10,
  maximumCalibrationRegression = 5,
  minimumWinProbability = 65,
  minimumPromotionScore = 85,
  bootstrapIterations = 1000,
  bootstrapSeed = 42,
  requireHumanApproval = true,
} = {}) {
  const normalizedChampion =
    normalizeModel(
      champion,
      "Champion",
    );

  const normalizedChallenger =
    normalizeModel(
      challenger,
      "Challenger",
    );

  if (
    normalizedChampion.id ===
    normalizedChallenger.id &&
    normalizedChampion.version ===
    normalizedChallenger.version
  ) {
    throw new TypeError(
      "Champion and challenger must be different models.",
    );
  }

  const normalizedRecords =
    normalizeRecords(
      records,
    );

  if (!normalizedRecords.length) {
    return {
      version:
        CHAMPION_CHALLENGER_V2_VERSION,

      ready:
        false,

      decision:
        "CONTINUE_SHADOW",

      reason:
        "NO_COMPARISON_RECORDS",

      champion:
        normalizedChampion,

      challenger:
        normalizedChallenger,

      recordCount:
        0,

      checks:
        [],

      blockers: [
        "NO_COMPARISON_RECORDS",
      ],

      approved:
        false,

      humanApprovalRequired:
        false,
    };
  }

  const championMetrics =
    calculateMetrics(
      normalizedRecords,
      "champion",
    );

  const challengerMetrics =
    calculateMetrics(
      normalizedRecords,
      "challenger",
    );

  const normalizedIterations =
    Math.max(
      100,
      Math.floor(
        finiteOrNull(
          bootstrapIterations,
        ) ?? 1000,
      ),
    );

  const bootstrap =
    pairedBootstrap({
      records:
        normalizedRecords,

      iterations:
        normalizedIterations,

      seed:
        bootstrapSeed,
    });

  const checks =
    buildChecks({
      champion:
        championMetrics,

      challenger:
        challengerMetrics,

      bootstrap,

      minimumSamples:
        Math.max(
          1,
          Math.floor(
            finiteOrNull(
              minimumSamples,
            ) ?? 100,
          ),
        ),

      minimumAccuracyImprovement:
        finiteOrNull(
          minimumAccuracyImprovement,
        ) ?? 1,

      minimumReturnImprovement:
        finiteOrNull(
          minimumReturnImprovement,
        ) ?? 0,

      maximumDrawdownRegression:
        Math.max(
          0,
          finiteOrNull(
            maximumDrawdownRegression,
          ) ?? 10,
        ),

      maximumCalibrationRegression:
        Math.max(
          0,
          finiteOrNull(
            maximumCalibrationRegression,
          ) ?? 5,
        ),

      minimumWinProbability:
        clamp(
          minimumWinProbability,
        ) ?? 65,
    });

  const score =
    calculateScore(
      checks,
    );

  const decision =
    determineDecision({
      checks,

      score,

      minimumPromotionScore:
        clamp(
          minimumPromotionScore,
        ) ?? 85,
    });

  const humanApprovalRequired =
    decision.decision ===
      "PROMOTE_CHALLENGER" &&
    requireHumanApproval;

  return {
    version:
      CHAMPION_CHALLENGER_V2_VERSION,

    ready:
      true,

    decision:
      decision.decision,

    reason:
      decision.reason,

    champion:
      normalizedChampion,

    challenger:
      normalizedChallenger,

    recordCount:
      normalizedRecords.length,

    comparisonScore:
      round(
        score,
        2,
      ),

    minimumPromotionScore:
      clamp(
        minimumPromotionScore,
      ) ?? 85,

    approved:
      decision.decision ===
        "PROMOTE_CHALLENGER" &&
      !humanApprovalRequired,

    humanApprovalRequired,

    checks,

    blockers:
      decision.blockers,

    metrics: {
      champion:
        {
          ...championMetrics,

          directionalReturns:
            undefined,
        },

      challenger:
        {
          ...challengerMetrics,

          directionalReturns:
            undefined,
        },
    },

    improvements: {
      accuracyPoints:
        round(
          challengerMetrics.accuracy -
          championMetrics.accuracy,
          2,
        ),

      averageReturnPercent:
        percentImprovement(
          challengerMetrics.averageReturn,
          championMetrics.averageReturn,
          true,
        ),

      drawdownPercent:
        percentImprovement(
          challengerMetrics.maximumDrawdown,
          championMetrics.maximumDrawdown,
          false,
        ),

      calibrationPoints:
        round(
          championMetrics.calibrationError -
          challengerMetrics.calibrationError,
          2,
        ),
    },

    bootstrap,

    audit: {
      evaluatedAt:
        new Date().toISOString(),

      championId:
        normalizedChampion.id,

      championVersion:
        normalizedChampion.version,

      challengerId:
        normalizedChallenger.id,

      challengerVersion:
        normalizedChallenger.version,

      requireHumanApproval,
    },
  };
}

export function approveChallengerPromotion({
  evaluation,
  approvedBy,
  note = null,
} = {}) {
  if (
    !evaluation ||
    typeof evaluation !== "object"
  ) {
    throw new TypeError(
      "Champion challenger evaluation is required.",
    );
  }

  if (
    evaluation.decision !==
    "PROMOTE_CHALLENGER"
  ) {
    return {
      version:
        CHAMPION_CHALLENGER_V2_VERSION,

      promoted:
        false,

      reason:
        "CHALLENGER_NOT_PROMOTABLE",

      evaluation,
    };
  }

  const approver =
    String(
      approvedBy ??
      "",
    ).trim();

  if (!approver) {
    throw new TypeError(
      "Challenger promotion requires approvedBy.",
    );
  }

  return {
    version:
      CHAMPION_CHALLENGER_V2_VERSION,

    promoted:
      true,

    previousChampion:
      evaluation.champion,

    newChampion:
      evaluation.challenger,

    approvedBy:
      approver,

    approvedAt:
      new Date().toISOString(),

    note,

    comparisonScore:
      evaluation.comparisonScore,

    evaluation,
  };
}

export class ChampionChallengerV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  evaluate(input = {}) {
    return evaluateChampionChallenger({
      ...this.config,

      ...input,
    });
  }

  approve(input = {}) {
    return approveChallengerPromotion(
      input,
    );
  }
}

export const championChallengerV2 =
  new ChampionChallengerV2();

export default evaluateChampionChallenger;