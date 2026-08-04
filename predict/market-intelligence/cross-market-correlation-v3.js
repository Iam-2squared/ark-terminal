export const CROSS_MARKET_CORRELATION_V3_VERSION =
  "cross-market-correlation-v3";

function clone(value) {
  return value === undefined
    ? undefined
    : structuredClone(value);
}

function finiteNumber(
  value,
  fallback = null,
) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return fallback;
  }

  const number =
    Number(value);

  return Number.isFinite(number)
    ? number
    : fallback;
}

function clamp(
  value,
  minimum,
  maximum,
) {
  return Math.min(
    maximum,
    Math.max(
      minimum,
      value,
    ),
  );
}

function round(
  value,
  digits = 4,
) {
  if (!Number.isFinite(value)) {
    return null;
  }

  const factor =
    10 ** digits;

  return (
    Math.round(
      value *
      factor,
    ) /
    factor
  );
}

function normalizeText(
  value,
  fallback = "",
) {
  const text =
    String(
      value ??
      fallback,
    ).trim();

  return text || fallback;
}

function normalizeSeries(
  series,
) {
  if (!Array.isArray(series)) {
    return [];
  }

  return series
    .map(
      (
        value,
      ) =>
        finiteNumber(
          value,
          null,
        ),
    )
    .filter(
      (
        value,
      ) =>
        value !== null,
    );
}

function mean(values) {
  if (values.length === 0) {
    return null;
  }

  return (
    values.reduce(
      (
        total,
        value,
      ) =>
        total +
        value,
      0,
    ) /
    values.length
  );
}

function standardDeviation(values) {
  if (values.length < 2) {
    return 0;
  }

  const average =
    mean(
      values,
    );

  const variance =
    values.reduce(
      (
        total,
        value,
      ) =>
        total +
        (
          value -
          average
        ) ** 2,
      0,
    ) /
    (
      values.length -
      1
    );

  return Math.sqrt(
    variance,
  );
}

export function calculateReturns(
  prices = [],
) {
  const normalized =
    normalizeSeries(
      prices,
    );

  const returns = [];

  for (
    let index = 1;
    index <
    normalized.length;
    index += 1
  ) {
    const previous =
      normalized[
        index -
        1
      ];

    const current =
      normalized[
        index
      ];

    if (previous === 0) {
      continue;
    }

    returns.push(
      (
        current -
        previous
      ) /
      previous,
    );
  }

  return returns;
}

export function calculatePearsonCorrelation(
  seriesA = [],
  seriesB = [],
) {
  const normalizedA =
    normalizeSeries(
      seriesA,
    );

  const normalizedB =
    normalizeSeries(
      seriesB,
    );

  const length =
    Math.min(
      normalizedA.length,
      normalizedB.length,
    );

  if (length < 2) {
    return null;
  }

  const valuesA =
    normalizedA.slice(
      normalizedA.length -
      length,
    );

  const valuesB =
    normalizedB.slice(
      normalizedB.length -
      length,
    );

  const meanA =
    mean(
      valuesA,
    );

  const meanB =
    mean(
      valuesB,
    );

  let covariance = 0;
  let varianceA = 0;
  let varianceB = 0;

  for (
    let index = 0;
    index < length;
    index += 1
  ) {
    const differenceA =
      valuesA[index] -
      meanA;

    const differenceB =
      valuesB[index] -
      meanB;

    covariance +=
      differenceA *
      differenceB;

    varianceA +=
      differenceA ** 2;

    varianceB +=
      differenceB ** 2;
  }

  if (
    varianceA === 0 ||
    varianceB === 0
  ) {
    return 0;
  }

  return round(
    clamp(
      covariance /
      Math.sqrt(
        varianceA *
        varianceB,
      ),
      -1,
      1,
    ),
  );
}

function classifyCorrelation(
  correlation,
) {
  if (correlation === null) {
    return "INSUFFICIENT_DATA";
  }

  const absolute =
    Math.abs(
      correlation,
    );

  if (absolute >= 0.8) {
    return correlation > 0
      ? "VERY_STRONG_POSITIVE"
      : "VERY_STRONG_NEGATIVE";
  }

  if (absolute >= 0.6) {
    return correlation > 0
      ? "STRONG_POSITIVE"
      : "STRONG_NEGATIVE";
  }

  if (absolute >= 0.35) {
    return correlation > 0
      ? "MODERATE_POSITIVE"
      : "MODERATE_NEGATIVE";
  }

  if (absolute >= 0.15) {
    return correlation > 0
      ? "WEAK_POSITIVE"
      : "WEAK_NEGATIVE";
  }

  return "NEUTRAL";
}

function leadLagCorrelation({
  seriesA,
  seriesB,
  maximumLag = 5,
}) {
  const correlations = [];

  for (
    let lag =
      -maximumLag;
    lag <=
    maximumLag;
    lag += 1
  ) {
    let shiftedA;
    let shiftedB;

    if (lag > 0) {
      shiftedA =
        seriesA.slice(
          0,
          -lag,
        );

      shiftedB =
        seriesB.slice(
          lag,
        );
    }
    else if (lag < 0) {
      shiftedA =
        seriesA.slice(
          -lag,
        );

      shiftedB =
        seriesB.slice(
          0,
          lag,
        );
    }
    else {
      shiftedA =
        seriesA;

      shiftedB =
        seriesB;
    }

    const correlation =
      calculatePearsonCorrelation(
        shiftedA,
        shiftedB,
      );

    if (correlation !== null) {
      correlations.push({
        lag,
        correlation,
        strength:
          Math.abs(
            correlation,
          ),
      });
    }
  }

  correlations.sort(
    (
      left,
      right,
    ) =>
      right.strength -
      left.strength,
  );

  return correlations[0] ?? {
    lag:
      0,

    correlation:
      null,

    strength:
      0,
  };
}

export function analyzeMarketPair({
  primary,
  secondary,
  useReturns = true,
  maximumLag = 5,
} = {}) {
  if (
    !primary ||
    !secondary
  ) {
    throw new TypeError(
      "Primary and secondary markets are required.",
    );
  }

  const primarySymbol =
    normalizeText(
      primary.symbol,
      "PRIMARY",
    );

  const secondarySymbol =
    normalizeText(
      secondary.symbol,
      "SECONDARY",
    );

  const primaryPrices =
    normalizeSeries(
      primary.prices,
    );

  const secondaryPrices =
    normalizeSeries(
      secondary.prices,
    );

  const seriesA =
    useReturns
      ? calculateReturns(
          primaryPrices,
        )
      : primaryPrices;

  const seriesB =
    useReturns
      ? calculateReturns(
          secondaryPrices,
        )
      : secondaryPrices;

  const correlation =
    calculatePearsonCorrelation(
      seriesA,
      seriesB,
    );

  const leadLag =
    leadLagCorrelation({
      seriesA,
      seriesB,
      maximumLag:
        Math.max(
          0,
          Math.floor(
            finiteNumber(
              maximumLag,
              5,
            ),
          ),
        ),
    });

  const volatilityA =
    standardDeviation(
      seriesA,
    );

  const volatilityB =
    standardDeviation(
      seriesB,
    );

  let leader =
    "NONE";

  if (
    leadLag.correlation !==
      null &&
    Math.abs(
      leadLag.correlation,
    ) >= 0.35
  ) {
    if (leadLag.lag > 0) {
      leader =
        primarySymbol;
    }
    else if (
      leadLag.lag < 0
    ) {
      leader =
        secondarySymbol;
    }
  }

  return {
    version:
      CROSS_MARKET_CORRELATION_V3_VERSION,

    primarySymbol,

    secondarySymbol,

    sampleSize:
      Math.min(
        seriesA.length,
        seriesB.length,
      ),

    correlation,

    classification:
      classifyCorrelation(
        correlation,
      ),

    leadLag: {
      lag:
        leadLag.lag,

      correlation:
        leadLag.correlation,

      leader,
    },

    volatility: {
      primary:
        round(
          volatilityA,
          6,
        ),

      secondary:
        round(
          volatilityB,
          6,
        ),

      ratio:
        volatilityB === 0
          ? null
          : round(
              volatilityA /
              volatilityB,
            ),
    },

    risk: {
      concentrationRisk:
        correlation !==
          null &&
        correlation >=
          0.75
          ? "HIGH"
          : correlation !==
              null &&
            correlation >=
              0.5
            ? "MEDIUM"
            : "LOW",

      hedgePotential:
        correlation !==
          null &&
        correlation <=
          -0.5
          ? "HIGH"
          : correlation !==
              null &&
            correlation <=
              -0.25
            ? "MEDIUM"
            : "LOW",
    },
  };
}

export function buildCorrelationMatrix({
  markets = [],
  useReturns = true,
} = {}) {
  const normalizedMarkets =
    markets.map(
      (
        market,
      ) => ({
        symbol:
          normalizeText(
            market.symbol,
            "UNKNOWN",
          ),

        prices:
          normalizeSeries(
            market.prices,
          ),
      }),
    );

  const symbols =
    normalizedMarkets.map(
      (
        market,
      ) =>
        market.symbol,
    );

  const matrix = {};

  for (
    const marketA of normalizedMarkets
  ) {
    matrix[
      marketA.symbol
    ] = {};

    for (
      const marketB of normalizedMarkets
    ) {
      if (
        marketA.symbol ===
        marketB.symbol
      ) {
        matrix[
          marketA.symbol
        ][
          marketB.symbol
        ] = 1;

        continue;
      }

      const seriesA =
        useReturns
          ? calculateReturns(
              marketA.prices,
            )
          : marketA.prices;

      const seriesB =
        useReturns
          ? calculateReturns(
              marketB.prices,
            )
          : marketB.prices;

      matrix[
        marketA.symbol
      ][
        marketB.symbol
      ] =
        calculatePearsonCorrelation(
          seriesA,
          seriesB,
        );
    }
  }

  return {
    version:
      CROSS_MARKET_CORRELATION_V3_VERSION,

    symbols,

    matrix,
  };
}

export function analyzeCrossMarketNetwork({
  markets = [],
  correlationThreshold = 0.6,
} = {}) {
  const matrixResult =
    buildCorrelationMatrix({
      markets,
    });

  const links = [];

  for (
    let leftIndex = 0;
    leftIndex <
    matrixResult.symbols.length;
    leftIndex += 1
  ) {
    for (
      let rightIndex =
        leftIndex +
        1;
      rightIndex <
      matrixResult.symbols.length;
      rightIndex += 1
    ) {
      const left =
        matrixResult.symbols[
          leftIndex
        ];

      const right =
        matrixResult.symbols[
          rightIndex
        ];

      const correlation =
        matrixResult.matrix[
          left
        ][
          right
        ];

      if (
        correlation !== null &&
        Math.abs(
          correlation,
        ) >=
          correlationThreshold
      ) {
        links.push({
          source:
            left,

          target:
            right,

          correlation,

          direction:
            correlation >= 0
              ? "POSITIVE"
              : "NEGATIVE",
        });
      }
    }
  }

  const exposureGroups = [];

  const visited =
    new Set();

  for (
    const symbol of matrixResult.symbols
  ) {
    if (
      visited.has(
        symbol,
      )
    ) {
      continue;
    }

    const group =
      new Set([
        symbol,
      ]);

    for (
      const link of links
    ) {
      if (
        link.direction !==
        "POSITIVE"
      ) {
        continue;
      }

      if (
        link.source ===
        symbol
      ) {
        group.add(
          link.target,
        );
      }

      if (
        link.target ===
        symbol
      ) {
        group.add(
          link.source,
        );
      }
    }

    for (
      const member of group
    ) {
      visited.add(
        member,
      );
    }

    exposureGroups.push([
      ...group,
    ]);
  }

  return {
    version:
      CROSS_MARKET_CORRELATION_V3_VERSION,

    matrix:
      matrixResult,

    links,

    exposureGroups,

    summary: {
      marketCount:
        matrixResult.symbols.length,

      strongLinkCount:
        links.length,

      concentrationGroupCount:
        exposureGroups.filter(
          (
            group,
          ) =>
            group.length >
            1,
        ).length,
    },
  };
}

export class CrossMarketCorrelationV3 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };

    this.history = [];
  }

  analyzePair(input = {}) {
    const result =
      analyzeMarketPair({
        ...this.config,
        ...input,
      });

    this.history.push(
      clone(result),
    );

    return clone(result);
  }

  matrix(input = {}) {
    const result =
      buildCorrelationMatrix({
        ...this.config,
        ...input,
      });

    this.history.push(
      clone(result),
    );

    return clone(result);
  }

  network(input = {}) {
    const result =
      analyzeCrossMarketNetwork({
        ...this.config,
        ...input,
      });

    this.history.push(
      clone(result),
    );

    return clone(result);
  }

  getHistory() {
    return clone(
      this.history,
    );
  }

  latest() {
    return clone(
      this.history.at(-1) ??
      null,
    );
  }

  reset() {
    this.history = [];

    return [];
  }
}

export const crossMarketCorrelationV3 =
  new CrossMarketCorrelationV3();

export default analyzeMarketPair;