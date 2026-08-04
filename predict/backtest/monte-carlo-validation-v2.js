export const MONTE_CARLO_VALIDATION_V2_VERSION =
  "monte-carlo-validation-v2";

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

function finiteInteger(
  value,
  fallback,
  minimum = 1,
) {
  const number =
    finiteOrNull(value);

  if (number === null) {
    return fallback;
  }

  return Math.max(
    minimum,
    Math.floor(number),
  );
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

function percentile(
  values,
  probability,
) {
  const available =
    values
      .filter(
        Number.isFinite,
      )
      .sort(
        (
          left,
          right,
        ) =>
          left - right,
      );

  if (!available.length) {
    return null;
  }

  const bounded =
    Math.min(
      1,
      Math.max(
        0,
        probability,
      ),
    );

  const index =
    (
      available.length - 1
    ) *
    bounded;

  const lower =
    Math.floor(index);

  const upper =
    Math.ceil(index);

  if (lower === upper) {
    return available[lower];
  }

  const weight =
    index - lower;

  return (
    available[lower] *
      (
        1 - weight
      ) +
    available[upper] *
      weight
  );
}

function normalizeReturns(
  returns = [],
) {
  if (!Array.isArray(returns)) {
    throw new TypeError(
      "Monte Carlo returns must be an array.",
    );
  }

  return returns
    .map(
      (
        value,
      ) =>
        typeof value === "object"
          ? finiteOrNull(
              value.return ??
              value.pnl ??
              value.result ??
              value.value,
            )
          : finiteOrNull(value),
    )
    .filter(
      Number.isFinite,
    );
}

export function createSeededRandom(
  seed = 1,
) {
  let state =
    finiteInteger(
      seed,
      1,
      0,
    ) >>> 0;

  return function random() {
    state +=
      0x6D2B79F5;

    let value =
      state;

    value =
      Math.imul(
        value ^
        (
          value >>> 15
        ),
        value | 1,
      );

    value ^=
      value +
      Math.imul(
        value ^
        (
          value >>> 7
        ),
        value | 61,
      );

    return (
      (
        value ^
        (
          value >>> 14
        )
      ) >>> 0
    ) / 4294967296;
  };
}

function shuffledCopy(
  values,
  random,
) {
  const copy =
    [
      ...values,
    ];

  for (
    let index =
      copy.length - 1;
    index > 0;
    index -= 1
  ) {
    const swapIndex =
      Math.floor(
        random() *
        (
          index + 1
        ),
      );

    [
      copy[index],
      copy[swapIndex],
    ] = [
      copy[swapIndex],
      copy[index],
    ];
  }

  return copy;
}

function bootstrapSample(
  values,
  sampleSize,
  random,
) {
  return Array.from(
    {
      length:
        sampleSize,
    },
    () =>
      values[
        Math.floor(
          random() *
          values.length
        )
      ],
  );
}

function calculatePath(
  returns,
  {
    initialCapital,
    compounding,
  },
) {
  let equity =
    initialCapital;

  let peak =
    equity;

  let maximumDrawdown =
    0;

  let winningTrades =
    0;

  let losingTrades =
    0;

  const equityCurve = [
    round(
      equity,
      6,
    ),
  ];

  for (
    const tradeReturn
    of returns
  ) {
    if (tradeReturn > 0) {
      winningTrades += 1;
    } else if (tradeReturn < 0) {
      losingTrades += 1;
    }

    if (compounding) {
      equity *=
        1 +
        (
          tradeReturn /
          100
        );
    } else {
      equity +=
        initialCapital *
        (
          tradeReturn /
          100
        );
    }

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

    equityCurve.push(
      round(
        equity,
        6,
      ),
    );
  }

  const totalReturn =
    initialCapital !== 0
      ? (
          (
            equity -
            initialCapital
          ) /
          initialCapital
        ) *
        100
      : 0;

  return {
    endingCapital:
      round(
        equity,
        6,
      ),

    totalReturn:
      round(
        totalReturn,
        6,
      ),

    maximumDrawdown:
      round(
        maximumDrawdown,
        6,
      ),

    winningTrades,

    losingTrades,

    winRate:
      returns.length
        ? round(
            (
              winningTrades /
              returns.length
            ) *
            100,
            4,
          )
        : 0,

    equityCurve,
  };
}

function calculateRiskOfRuin(
  paths,
  ruinThreshold,
) {
  if (!paths.length) {
    return null;
  }

  const ruined =
    paths.filter(
      (
        path,
      ) =>
        path.maximumDrawdown >=
          ruinThreshold ||
        path.endingCapital <= 0,
    ).length;

  return (
    ruined /
    paths.length
  ) *
  100;
}

function summarizeMetric(
  values,
) {
  const mean =
    average(values);

  const deviation =
    standardDeviation(values);

  return {
    minimum:
      values.length
        ? round(
            Math.min(
              ...values,
            ),
          )
        : null,

    percentile05:
      round(
        percentile(
          values,
          0.05,
        ),
      ),

    percentile25:
      round(
        percentile(
          values,
          0.25,
        ),
      ),

    median:
      round(
        percentile(
          values,
          0.5,
        ),
      ),

    percentile75:
      round(
        percentile(
          values,
          0.75,
        ),
      ),

    percentile95:
      round(
        percentile(
          values,
          0.95,
        ),
      ),

    maximum:
      values.length
        ? round(
            Math.max(
              ...values,
            ),
          )
        : null,

    mean:
      mean === null
        ? null
        : round(mean),

    standardDeviation:
      deviation === null
        ? null
        : round(deviation),
  };
}

export function runMonteCarloValidation({
  returns = [],
  iterations = 1000,
  sampleSize = null,
  seed = 42,
  method = "bootstrap",
  initialCapital = 100000,
  compounding = true,
  ruinThreshold = 50,
  minimumSuccessRate = 60,
} = {}) {
  const normalizedReturns =
    normalizeReturns(
      returns,
    );

  const normalizedIterations =
    finiteInteger(
      iterations,
      1000,
    );

  const normalizedSampleSize =
    finiteInteger(
      sampleSize,
      normalizedReturns.length || 1,
    );

  const normalizedInitialCapital =
    finiteOrNull(
      initialCapital,
    );

  if (
    normalizedInitialCapital === null ||
    normalizedInitialCapital <= 0
  ) {
    throw new TypeError(
      "Monte Carlo initial capital must be greater than zero.",
    );
  }

  const normalizedMethod =
    String(
      method ??
      "bootstrap",
    )
      .trim()
      .toLowerCase();

  if (
    ![
      "bootstrap",
      "shuffle",
    ].includes(
      normalizedMethod,
    )
  ) {
    throw new TypeError(
      "Monte Carlo method must be bootstrap or shuffle.",
    );
  }

  const normalizedRuinThreshold =
    clamp(
      ruinThreshold,
      0,
      100,
    ) ?? 50;

  const normalizedMinimumSuccessRate =
    clamp(
      minimumSuccessRate,
      0,
      100,
    ) ?? 60;

  if (!normalizedReturns.length) {
    return {
      version:
        MONTE_CARLO_VALIDATION_V2_VERSION,

      ready:
        false,

      passed:
        false,

      inputSize:
        0,

      iterations:
        normalizedIterations,

      sampleSize:
        normalizedSampleSize,

      method:
        normalizedMethod,

      seed,

      paths:
        [],

      summary: {
        totalReturn:
          summarizeMetric([]),

        endingCapital:
          summarizeMetric([]),

        maximumDrawdown:
          summarizeMetric([]),

        successRate:
          null,

        riskOfRuin:
          null,
      },
    };
  }

  const random =
    createSeededRandom(seed);

  const paths = [];

  for (
    let iteration = 0;
    iteration <
      normalizedIterations;
    iteration += 1
  ) {
    const sampledReturns =
      normalizedMethod ===
      "shuffle"
        ? shuffledCopy(
            normalizedReturns,
            random,
          ).slice(
            0,
            Math.min(
              normalizedSampleSize,
              normalizedReturns.length,
            ),
          )
        : bootstrapSample(
            normalizedReturns,
            normalizedSampleSize,
            random,
          );

    const path =
      calculatePath(
        sampledReturns,
        {
          initialCapital:
            normalizedInitialCapital,

          compounding:
            Boolean(
              compounding,
            ),
        },
      );

    paths.push({
      iteration:
        iteration + 1,

      ...path,
    });
  }

  const totalReturns =
    paths.map(
      (
        path,
      ) =>
        path.totalReturn,
    );

  const endingCapitals =
    paths.map(
      (
        path,
      ) =>
        path.endingCapital,
    );

  const drawdowns =
    paths.map(
      (
        path,
      ) =>
        path.maximumDrawdown,
    );

  const successful =
    paths.filter(
      (
        path,
      ) =>
        path.totalReturn > 0,
    ).length;

  const successRate =
    (
      successful /
      paths.length
    ) *
    100;

  const riskOfRuin =
    calculateRiskOfRuin(
      paths,
      normalizedRuinThreshold,
    );

  const returnSummary =
    summarizeMetric(
      totalReturns,
    );

  const drawdownSummary =
    summarizeMetric(
      drawdowns,
    );

  return {
    version:
      MONTE_CARLO_VALIDATION_V2_VERSION,

    ready:
      true,

    passed:
      successRate >=
        normalizedMinimumSuccessRate &&
      (
        riskOfRuin ??
        100
      ) <= 10 &&
      (
        returnSummary.percentile05 ??
        -Infinity
      ) > -20,

    inputSize:
      normalizedReturns.length,

    iterations:
      normalizedIterations,

    sampleSize:
      normalizedSampleSize,

    method:
      normalizedMethod,

    seed:

      finiteInteger(
        seed,
        42,
        0,
      ),

    initialCapital:
      normalizedInitialCapital,

    compounding:
      Boolean(
        compounding,
      ),

    ruinThreshold:
      normalizedRuinThreshold,

    minimumSuccessRate:
      normalizedMinimumSuccessRate,

    paths,

    summary: {
      totalReturn:
        returnSummary,

      endingCapital:
        summarizeMetric(
          endingCapitals,
        ),

      maximumDrawdown:
        drawdownSummary,

      successRate:
        round(
          successRate,
          2,
        ),

      failureRate:
        round(
          100 -
          successRate,
          2,
        ),

      riskOfRuin:
        riskOfRuin === null
          ? null
          : round(
              riskOfRuin,
              2,
            ),

      profitablePaths:
        successful,

      losingPaths:
        paths.length -
        successful,

      stabilityScore:
        clamp(
          100 -
          (
            returnSummary.standardDeviation ??
            100
          ) -
          (
            drawdownSummary.percentile95 ??
            100
          ) *
          0.5,
        ),
    },
  };
}

export class MonteCarloValidationV2Engine {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  validate(
    returns = [],
    overrides = {},
  ) {
    return runMonteCarloValidation({
      ...this.config,

      ...overrides,

      returns,
    });
  }
}

export default runMonteCarloValidation;