export const PORTFOLIO_OPTIMIZER_V2_VERSION =
  "portfolio-optimizer-v2";

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
  maximum = 1,
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
  digits = 6,
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

function covariance(
  left,
  right,
) {
  const length =
    Math.min(
      left.length,
      right.length,
    );

  if (!length) {
    return null;
  }

  const leftSlice =
    left.slice(
      left.length - length,
    );

  const rightSlice =
    right.slice(
      right.length - length,
    );

  const leftMean =
    average(leftSlice);

  const rightMean =
    average(rightSlice);

  if (
    leftMean === null ||
    rightMean === null
  ) {
    return null;
  }

  return (
    leftSlice.reduce(
      (
        sum,
        value,
        index,
      ) =>
        sum +
        (
          value -
          leftMean
        ) *
        (
          rightSlice[index] -
          rightMean
        ),
      0,
    ) /
    length
  );
}

function normalizeReturns(values = []) {
  if (!Array.isArray(values)) {
    return [];
  }

  return values
    .map(
      (
        value,
      ) =>
        typeof value === "object"
          ? finiteOrNull(
              value.return ??
              value.value ??
              value.pnl,
            )
          : finiteOrNull(value),
    )
    .filter(
      Number.isFinite,
    );
}

function normalizeAssets(
  assets = [],
) {
  if (!Array.isArray(assets)) {
    throw new TypeError(
      "Portfolio optimizer assets must be an array.",
    );
  }

  return assets
    .map(
      (
        asset,
        index,
      ) => {
        if (
          !asset ||
          typeof asset !== "object"
        ) {
          return null;
        }

        const symbol =
          String(
            asset.symbol ??
            asset.code ??
            asset.name ??
            `ASSET-${index + 1}`,
          ).trim();

        const returns =
          normalizeReturns(
            asset.returns,
          );

        const expectedReturn =
          finiteOrNull(
            asset.expectedReturn,
          ) ??
          average(returns);

        const volatility =
          finiteOrNull(
            asset.volatility,
          ) ??
          standardDeviation(
            returns,
          );

        if (
          expectedReturn === null ||
          volatility === null
        ) {
          return null;
        }

        return {
          symbol,

          returns,

          expectedReturn,

          volatility:
            Math.max(
              0,
              volatility,
            ),

          minimumWeight:
            clamp(
              asset.minimumWeight ??
              0,
              0,
              1,
            ) ?? 0,

          maximumWeight:
            clamp(
              asset.maximumWeight ??
              1,
              0,
              1,
            ) ?? 1,

          confidence:
            clamp(
              (
                finiteOrNull(
                  asset.confidence,
                ) ??
                100
              ) / 100,
              0,
              1,
            ) ?? 1,

          score:
            finiteOrNull(
              asset.score,
            ),

          sector:
            String(
              asset.sector ??
              "UNKNOWN",
            ),
        };
      },
    )
    .filter(Boolean);
}

function normalizeWeights(
  weights,
  assets,
) {
  const normalized =
    weights.map(
      (
        weight,
        index,
      ) =>
        clamp(
          weight,
          assets[index].minimumWeight,
          assets[index].maximumWeight,
        ) ?? 0,
    );

  const total =
    normalized.reduce(
      (
        sum,
        value,
      ) =>
        sum + value,
      0,
    );

  if (total <= 0) {
    return assets.map(
      () =>
        1 /
        assets.length,
    );
  }

  return normalized.map(
    (
      value,
    ) =>
      value / total,
  );
}

function expectedPortfolioReturn(
  assets,
  weights,
) {
  return assets.reduce(
    (
      sum,
      asset,
      index,
    ) =>
      sum +
      asset.expectedReturn *
      weights[index],
    0,
  );
}

function covarianceMatrix(
  assets,
) {
  return assets.map(
    (
      left,
      leftIndex,
    ) =>
      assets.map(
        (
          right,
          rightIndex,
        ) => {
          const calculated =
            covariance(
              left.returns,
              right.returns,
            );

          if (
            calculated !== null
          ) {
            return calculated;
          }

          if (
            leftIndex ===
            rightIndex
          ) {
            return (
              left.volatility **
              2
            );
          }

          return 0;
        },
      ),
  );
}

function portfolioVariance(
  weights,
  matrix,
) {
  let variance = 0;

  for (
    let row = 0;
    row <
      weights.length;
    row += 1
  ) {
    for (
      let column = 0;
      column <
        weights.length;
      column += 1
    ) {
      variance +=
        weights[row] *
        weights[column] *
        matrix[row][column];
    }
  }

  return Math.max(
    0,
    variance,
  );
}

function portfolioVolatility(
  weights,
  matrix,
) {
  return Math.sqrt(
    portfolioVariance(
      weights,
      matrix,
    ),
  );
}

function concentration(
  weights,
) {
  return weights.reduce(
    (
      sum,
      weight,
    ) =>
      sum +
      weight ** 2,
    0,
  );
}

function sectorWeights(
  assets,
  weights,
) {
  const sectors = {};

  assets.forEach(
    (
      asset,
      index,
    ) => {
      sectors[
        asset.sector
      ] =
        (
          sectors[
            asset.sector
          ] ??
          0
        ) +
        weights[index];
    },
  );

  return Object.fromEntries(
    Object.entries(
      sectors,
    ).map(
      (
        [
          key,
          value,
        ],
      ) => [
        key,
        round(value),
      ],
    ),
  );
}

function objectiveValue({
  assets,
  weights,
  matrix,
  riskFreeRate,
  riskAversion,
  concentrationPenalty,
}) {
  const expectedReturn =
    expectedPortfolioReturn(
      assets,
      weights,
    );

  const volatility =
    portfolioVolatility(
      weights,
      matrix,
    );

  const sharpe =
    volatility > 0
      ? (
          expectedReturn -
          riskFreeRate
        ) /
        volatility
      : expectedReturn >
          riskFreeRate
        ? Infinity
        : 0;

  const utility =
    (
      expectedReturn -
      riskAversion *
      (
        volatility ** 2
      ) -
      concentrationPenalty *
      concentration(
        weights,
      )
    );

  return {
    expectedReturn,
    volatility,
    sharpe,
    utility,
  };
}

function generateCandidateWeights(
  assets,
  samples,
  random,
) {
  const candidates = [];

  candidates.push(
    normalizeWeights(
      assets.map(
        () => 1,
      ),
      assets,
    ),
  );

  for (
    let index = 0;
    index < samples;
    index += 1
  ) {
    const randomWeights =
      assets.map(
        (
          asset,
        ) => {
          const confidenceBias =
            0.5 +
            asset.confidence;

          const scoreBias =
            asset.score === null
              ? 1
              : Math.max(
                  0.1,
                  asset.score /
                  100,
                );

          return (
            Math.max(
              0.000001,
              random(),
            ) *
            confidenceBias *
            scoreBias
          );
        },
      );

    candidates.push(
      normalizeWeights(
        randomWeights,
        assets,
      ),
    );
  }

  return candidates;
}

export function createSeededRandom(
  seed = 42,
) {
  let state =
    (
      Number(seed) ||
      42
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

export function optimizePortfolio({
  assets = [],
  objective = "max-sharpe",
  riskFreeRate = 0,
  riskAversion = 1,
  concentrationPenalty = 0.1,
  samples = 5000,
  seed = 42,
  maximumSectorWeight = 1,
} = {}) {
  const normalizedAssets =
    normalizeAssets(
      assets,
    );

  if (!normalizedAssets.length) {
    return {
      version:
        PORTFOLIO_OPTIMIZER_V2_VERSION,

      ready:
        false,

      assetCount:
        0,

      allocations:
        [],

      metrics: {
        expectedReturn:
          null,

        volatility:
          null,

        sharpeRatio:
          null,

        concentration:
          null,
      },
    };
  }

  const normalizedObjective =
    String(
      objective ??
      "max-sharpe",
    )
      .trim()
      .toLowerCase();

  if (
    ![
      "max-sharpe",
      "min-volatility",
      "max-utility",
    ].includes(
      normalizedObjective,
    )
  ) {
    throw new TypeError(
      "Portfolio objective must be max-sharpe, min-volatility, or max-utility.",
    );
  }

  const matrix =
    covarianceMatrix(
      normalizedAssets,
    );

  const random =
    createSeededRandom(
      seed,
    );

  const candidateWeights =
    generateCandidateWeights(
      normalizedAssets,
      Math.max(
        100,
        Math.floor(
          finiteOrNull(
            samples,
          ) ??
          5000,
        ),
      ),
      random,
    );

  const sectorLimit =
    clamp(
      maximumSectorWeight,
      0,
      1,
    ) ?? 1;

  let best = null;

  for (
    const weights
    of candidateWeights
  ) {
    const sectors =
      sectorWeights(
        normalizedAssets,
        weights,
      );

    const sectorLimitExceeded =
      Object.values(
        sectors,
      ).some(
        (
          value,
        ) =>
          value >
          sectorLimit +
          1e-9,
      );

    if (sectorLimitExceeded) {
      continue;
    }

    const metrics =
      objectiveValue({
        assets:
          normalizedAssets,

        weights,

        matrix,

        riskFreeRate:
          finiteOrNull(
            riskFreeRate,
          ) ?? 0,

        riskAversion:
          Math.max(
            0,
            finiteOrNull(
              riskAversion,
            ) ?? 1,
          ),

        concentrationPenalty:
          Math.max(
            0,
            finiteOrNull(
              concentrationPenalty,
            ) ?? 0.1,
          ),
      });

    let score;

    if (
      normalizedObjective ===
      "min-volatility"
    ) {
      score =
        -metrics.volatility;
    } else if (
      normalizedObjective ===
      "max-utility"
    ) {
      score =
        metrics.utility;
    } else {
      score =
        metrics.sharpe;
    }

    if (
      best === null ||
      score >
      best.score
    ) {
      best = {
        score,
        weights,
        metrics,
        sectors,
      };
    }
  }

  if (best === null) {
    return {
      version:
        PORTFOLIO_OPTIMIZER_V2_VERSION,

      ready:
        false,

      assetCount:
        normalizedAssets.length,

      allocations:
        [],

      reason:
        "No feasible portfolio satisfied the constraints.",

      metrics: {
        expectedReturn:
          null,

        volatility:
          null,

        sharpeRatio:
          null,

        concentration:
          null,
      },
    };
  }

  const allocations =
    normalizedAssets
      .map(
        (
          asset,
          index,
        ) => ({
          symbol:
            asset.symbol,

          sector:
            asset.sector,

          weight:
            round(
              best.weights[index],
            ),

          weightPercent:
            round(
              best.weights[index] *
              100,
              2,
            ),

          expectedReturn:
            round(
              asset.expectedReturn,
            ),

          volatility:
            round(
              asset.volatility,
            ),

          confidence:
            round(
              asset.confidence *
              100,
              2,
            ),

          score:
            asset.score,
        }),
      )
      .sort(
        (
          left,
          right,
        ) =>
          right.weight -
          left.weight,
      );

  return {
    version:
      PORTFOLIO_OPTIMIZER_V2_VERSION,

    ready:
      true,

    objective:
      normalizedObjective,

    seed:
      Number(seed) ||
      42,

    samples:
      candidateWeights.length,

    assetCount:
      normalizedAssets.length,

    allocations,

    sectorWeights:
      best.sectors,

    metrics: {
      expectedReturn:
        round(
          best.metrics.expectedReturn,
        ),

      volatility:
        round(
          best.metrics.volatility,
        ),

      sharpeRatio:
        Number.isFinite(
          best.metrics.sharpe,
        )
          ? round(
              best.metrics.sharpe,
            )
          : null,

      utility:
        round(
          best.metrics.utility,
        ),

      concentration:
        round(
          concentration(
            best.weights,
          ),
        ),

      effectiveAssetCount:
        round(
          1 /
          concentration(
            best.weights,
          ),
        ),
    },

    diagnostics: {
      covarianceMatrix:
        matrix.map(
          (
            row,
          ) =>
            row.map(
              (
                value,
              ) =>
                round(value),
            ),
        ),

      totalWeight:
        round(
          best.weights.reduce(
            (
              sum,
              value,
            ) =>
              sum + value,
            0,
          ),
        ),

      maximumSectorWeight:
        sectorLimit,
    },
  };
}

export class PortfolioOptimizerV2Engine {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  optimize(
    assets = [],
    overrides = {},
  ) {
    return optimizePortfolio({
      ...this.config,

      ...overrides,

      assets,
    });
  }
}

export default optimizePortfolio;