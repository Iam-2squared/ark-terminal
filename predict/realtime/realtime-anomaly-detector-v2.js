export const REALTIME_ANOMALY_DETECTOR_V2_VERSION =
  "realtime-anomaly-detector-v2";

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

function normalizeTimestamp(
  value,
  index,
) {
  if (
    value === null ||
    value === undefined
  ) {
    return index;
  }

  if (typeof value === "number") {
    return Number.isFinite(value)
      ? value
      : index;
  }

  const parsed =
    Date.parse(value);

  return Number.isFinite(parsed)
    ? parsed
    : index;
}

function normalizeTick(
  tick,
  index,
) {
  if (
    !tick ||
    typeof tick !== "object"
  ) {
    return null;
  }

  const symbol =
    String(
      tick.symbol ??
      tick.code ??
      tick.ticker ??
      "",
    ).trim();

  const price =
    finiteOrNull(
      tick.price ??
      tick.last ??
      tick.close,
    );

  if (
    !symbol ||
    price === null ||
    price <= 0
  ) {
    return null;
  }

  return {
    id:
      String(
        tick.id ??
        `${symbol}-${index}`,
      ),

    symbol,

    price,

    volume:
      Math.max(
        0,
        finiteOrNull(
          tick.volume ??
          tick.size ??
          tick.quantity,
        ) ?? 0,
      ),

    bid:
      finiteOrNull(
        tick.bid,
      ),

    ask:
      finiteOrNull(
        tick.ask,
      ),

    score:
      clamp(
        tick.score ??
        tick.aiScore ??
        50,
      ) ?? 50,

    confidence:
      clamp(
        tick.confidence ??
        tick.probability ??
        50,
      ) ?? 50,

    timestamp:
      normalizeTimestamp(
        tick.timestamp ??
        tick.time ??
        tick.updatedAt,
        index,
      ),

    metadata:
      tick.metadata ??
      {},
  };
}

function normalizeTicks(
  ticks,
) {
  if (!Array.isArray(ticks)) {
    throw new TypeError(
      "Realtime anomaly ticks must be an array.",
    );
  }

  return ticks
    .map(
      normalizeTick,
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

function groupBySymbol(
  ticks,
) {
  const groups =
    new Map();

  for (
    const tick
    of ticks
  ) {
    if (!groups.has(tick.symbol)) {
      groups.set(
        tick.symbol,
        [],
      );
    }

    groups.get(
      tick.symbol,
    ).push(tick);
  }

  return groups;
}

function calculateReturns(
  ticks,
) {
  const returns = [];

  for (
    let index = 1;
    index < ticks.length;
    index += 1
  ) {
    const previous =
      ticks[index - 1].price;

    const current =
      ticks[index].price;

    if (
      previous > 0 &&
      current > 0
    ) {
      returns.push(
        (
          (
            current -
            previous
          ) /
          previous
        ) *
        100,
      );
    }
  }

  return returns;
}

function calculateSpreadPercent(
  tick,
) {
  if (
    tick.bid === null ||
    tick.ask === null ||
    tick.bid <= 0 ||
    tick.ask <= 0
  ) {
    return null;
  }

  const midpoint =
    (
      tick.bid +
      tick.ask
    ) /
    2;

  if (midpoint <= 0) {
    return null;
  }

  return (
    (
      tick.ask -
      tick.bid
    ) /
    midpoint
  ) *
  100;
}

function zScore(
  value,
  values,
  minimumDeviation,
) {
  const mean =
    average(values);

  const deviation =
    Math.max(
      minimumDeviation,
      standardDeviation(
        values,
      ) ?? 0,
    );

  if (
    mean === null ||
    !Number.isFinite(value)
  ) {
    return null;
  }

  return (
    value -
    mean
  ) /
  deviation;
}

function severityFromScore(
  score,
) {
  if (score >= 85) {
    return "CRITICAL";
  }

  if (score >= 65) {
    return "HIGH";
  }

  if (score >= 40) {
    return "MEDIUM";
  }

  return "LOW";
}

function buildRecommendation(
  anomalies,
) {
  const severities =
    anomalies.map(
      (
        anomaly,
      ) =>
        anomaly.severity,
    );

  if (
    severities.includes(
      "CRITICAL",
    )
  ) {
    return {
      action:
        "BLOCK",

      tradable:
        false,

      reason:
        "CRITICAL_REALTIME_ANOMALY",
    };
  }

  if (
    severities.includes(
      "HIGH",
    )
  ) {
    return {
      action:
        "REVIEW",

      tradable:
        false,

      reason:
        "HIGH_REALTIME_ANOMALY",
    };
  }

  if (
    severities.includes(
      "MEDIUM",
    )
  ) {
    return {
      action:
        "CAUTION",

      tradable:
        true,

      reason:
        "MODERATE_REALTIME_ANOMALY",
    };
  }

  return {
    action:
      "CONTINUE",

    tradable:
      true,

    reason:
      "NO_SIGNIFICANT_ANOMALY",
  };
}

function detectSymbolAnomalies({
  symbol,
  ticks,
  lookback,
  minimumSamples,
  priceZThreshold,
  volumeZThreshold,
  spreadThresholdPercent,
  scoreChangeThreshold,
  confidenceChangeThreshold,
  minimumDeviation,
}) {
  const recent =
    ticks.slice(
      -lookback,
    );

  const latest =
    recent[
      recent.length - 1
    ];

  const baseline =
    recent.slice(
      0,
      -1,
    );

  if (
    recent.length <
    minimumSamples
  ) {
    return {
      symbol,

      ready:
        false,

      anomalyDetected:
        false,

      anomalyScore:
        0,

      severity:
        "UNKNOWN",

      anomalies:
        [],

      recommendation: {
        action:
          "COLLECT_MORE_DATA",

        tradable:
          false,

        reason:
          "INSUFFICIENT_REALTIME_SAMPLES",
      },

      diagnostics: {
        sampleCount:
          recent.length,

        minimumSamples,
      },
    };
  }

  const baselinePrices =
    baseline.map(
      (
        tick,
      ) =>
        tick.price,
    );

  const baselineVolumes =
    baseline.map(
      (
        tick,
      ) =>
        tick.volume,
    );

  const priceZ =
    zScore(
      latest.price,
      baselinePrices,
      minimumDeviation,
    );

  const volumeZ =
    zScore(
      latest.volume,
      baselineVolumes,
      minimumDeviation,
    );

  const spreadPercent =
    calculateSpreadPercent(
      latest,
    );

  const previous =
    recent[
      recent.length - 2
    ];

  const scoreChange =
    latest.score -
    previous.score;

  const confidenceChange =
    latest.confidence -
    previous.confidence;

  const returns =
    calculateReturns(
      recent,
    );

  const latestReturn =
    returns[
      returns.length - 1
    ] ?? 0;

  const returnBaseline =
    returns.slice(
      0,
      -1,
    );

  const returnZ =
    returnBaseline.length
      ? zScore(
          latestReturn,
          returnBaseline,
          minimumDeviation,
        )
      : null;

  const anomalies = [];

  if (
    priceZ !== null &&
    Math.abs(priceZ) >=
      priceZThreshold
  ) {
    const score =
      clamp(
        Math.abs(priceZ) *
        18,
      ) ?? 0;

    anomalies.push({
      type:
        "PRICE_SPIKE",

      value:
        round(
          latest.price,
        ),

      zScore:
        round(
          priceZ,
        ),

      score:
        round(
          score,
          2,
        ),

      severity:
        severityFromScore(
          score,
        ),
    });
  }

  if (
    returnZ !== null &&
    Math.abs(returnZ) >=
      priceZThreshold
  ) {
    const score =
      clamp(
        Math.abs(returnZ) *
        20,
      ) ?? 0;

    anomalies.push({
      type:
        "RETURN_SHOCK",

      value:
        round(
          latestReturn,
        ),

      zScore:
        round(
          returnZ,
        ),

      score:
        round(
          score,
          2,
        ),

      severity:
        severityFromScore(
          score,
        ),
    });
  }

  if (
    volumeZ !== null &&
    volumeZ >=
      volumeZThreshold
  ) {
    const score =
      clamp(
        volumeZ *
        15,
      ) ?? 0;

    anomalies.push({
      type:
        "VOLUME_SURGE",

      value:
        round(
          latest.volume,
        ),

      zScore:
        round(
          volumeZ,
        ),

      score:
        round(
          score,
          2,
        ),

      severity:
        severityFromScore(
          score,
        ),
    });
  }

  if (
    spreadPercent !== null &&
    spreadPercent >=
      spreadThresholdPercent
  ) {
    const score =
      clamp(
        (
          spreadPercent /
          spreadThresholdPercent
        ) *
        55,
      ) ?? 0;

    anomalies.push({
      type:
        "SPREAD_WIDENING",

      value:
        round(
          spreadPercent,
        ),

      threshold:
        spreadThresholdPercent,

      score:
        round(
          score,
          2,
        ),

      severity:
        severityFromScore(
          score,
        ),
    });
  }

  if (
    Math.abs(scoreChange) >=
    scoreChangeThreshold
  ) {
    const score =
      clamp(
        (
          Math.abs(
            scoreChange,
          ) /
          scoreChangeThreshold
        ) *
        50,
      ) ?? 0;

    anomalies.push({
      type:
        "AI_SCORE_JUMP",

      value:
        round(
          scoreChange,
          2,
        ),

      threshold:
        scoreChangeThreshold,

      score:
        round(
          score,
          2,
        ),

      severity:
        severityFromScore(
          score,
        ),
    });
  }

  if (
    Math.abs(
      confidenceChange,
    ) >=
    confidenceChangeThreshold
  ) {
    const score =
      clamp(
        (
          Math.abs(
            confidenceChange,
          ) /
          confidenceChangeThreshold
        ) *
        45,
      ) ?? 0;

    anomalies.push({
      type:
        "CONFIDENCE_JUMP",

      value:
        round(
          confidenceChange,
          2,
        ),

      threshold:
        confidenceChangeThreshold,

      score:
        round(
          score,
          2,
        ),

      severity:
        severityFromScore(
          score,
        ),
    });
  }

  anomalies.sort(
    (
      left,
      right,
    ) =>
      right.score -
      left.score,
  );

  const anomalyScore =
    anomalies.length
      ? Math.max(
          ...anomalies.map(
            (
              anomaly,
            ) =>
              anomaly.score,
          ),
        )
      : 0;

  const severity =
    anomalies.length
      ? severityFromScore(
          anomalyScore,
        )
      : "LOW";

  return {
    symbol,

    ready:
      true,

    anomalyDetected:
      anomalies.length > 0,

    anomalyScore:
      round(
        anomalyScore,
        2,
      ),

    severity,

    latest,

    anomalies,

    recommendation:
      buildRecommendation(
        anomalies,
      ),

    diagnostics: {
      sampleCount:
        recent.length,

      baselineCount:
        baseline.length,

      priceZ:
        priceZ === null
          ? null
          : round(
              priceZ,
            ),

      returnZ:
        returnZ === null
          ? null
          : round(
              returnZ,
            ),

      volumeZ:
        volumeZ === null
          ? null
          : round(
              volumeZ,
            ),

      spreadPercent:
        spreadPercent === null
          ? null
          : round(
              spreadPercent,
            ),

      scoreChange:
        round(
          scoreChange,
          2,
        ),

      confidenceChange:
        round(
          confidenceChange,
          2,
        ),
    },
  };
}

export function detectRealtimeAnomalies({
  ticks = [],
  lookback = 30,
  minimumSamples = 8,
  priceZThreshold = 3,
  volumeZThreshold = 3,
  spreadThresholdPercent = 1,
  scoreChangeThreshold = 20,
  confidenceChangeThreshold = 20,
  minimumDeviation = 0.000001,
} = {}) {
  const normalizedTicks =
    normalizeTicks(
      ticks,
    );

  const normalizedLookback =
    Math.max(
      2,
      Math.floor(
        finiteOrNull(
          lookback,
        ) ?? 30,
      ),
    );

  const normalizedMinimumSamples =
    Math.max(
      3,
      Math.floor(
        finiteOrNull(
          minimumSamples,
        ) ?? 8,
      ),
    );

  if (!normalizedTicks.length) {
    return {
      version:
        REALTIME_ANOMALY_DETECTOR_V2_VERSION,

      ready:
        false,

      tickCount:
        0,

      symbolCount:
        0,

      anomalyCount:
        0,

      criticalCount:
        0,

      highCount:
        0,

      results:
        [],

      alerts:
        [],
    };
  }

  const groups =
    groupBySymbol(
      normalizedTicks,
    );

  const results =
    Array.from(
      groups.entries(),
    )
      .map(
        (
          [
            symbol,
            symbolTicks,
          ],
        ) =>
          detectSymbolAnomalies({
            symbol,

            ticks:
              symbolTicks,

            lookback:
              normalizedLookback,

            minimumSamples:
              normalizedMinimumSamples,

            priceZThreshold:
              Math.max(
                0.1,
                finiteOrNull(
                  priceZThreshold,
                ) ?? 3,
              ),

            volumeZThreshold:
              Math.max(
                0.1,
                finiteOrNull(
                  volumeZThreshold,
                ) ?? 3,
              ),

            spreadThresholdPercent:
              Math.max(
                0.0001,
                finiteOrNull(
                  spreadThresholdPercent,
                ) ?? 1,
              ),

            scoreChangeThreshold:
              Math.max(
                0.1,
                finiteOrNull(
                  scoreChangeThreshold,
                ) ?? 20,
              ),

            confidenceChangeThreshold:
              Math.max(
                0.1,
                finiteOrNull(
                  confidenceChangeThreshold,
                ) ?? 20,
              ),

            minimumDeviation:
              Math.max(
                0.000000001,
                finiteOrNull(
                  minimumDeviation,
                ) ?? 0.000001,
              ),
          }),
      )
      .sort(
        (
          left,
          right,
        ) =>
          right.anomalyScore -
          left.anomalyScore,
      );

  const alerts =
    results
      .filter(
        (
          result,
        ) =>
          result.anomalyDetected,
      )
      .map(
        (
          result,
        ) => ({
          symbol:
            result.symbol,

          severity:
            result.severity,

          anomalyScore:
            result.anomalyScore,

          anomalyTypes:
            result.anomalies.map(
              (
                anomaly,
              ) =>
                anomaly.type,
            ),

          recommendation:
            result.recommendation,
        }),
      );

  return {
    version:
      REALTIME_ANOMALY_DETECTOR_V2_VERSION,

    ready:
      results.some(
        (
          result,
        ) =>
          result.ready,
      ),

    tickCount:
      normalizedTicks.length,

    symbolCount:
      groups.size,

    anomalyCount:
      alerts.length,

    criticalCount:
      results.filter(
        (
          result,
        ) =>
          result.severity ===
          "CRITICAL",
      ).length,

    highCount:
      results.filter(
        (
          result,
        ) =>
          result.severity ===
          "HIGH",
      ).length,

    blockedCount:
      results.filter(
        (
          result,
        ) =>
          result.recommendation
            .action ===
          "BLOCK",
      ).length,

    results,

    alerts,

    configuration: {
      lookback:
        normalizedLookback,

      minimumSamples:
        normalizedMinimumSamples,

      priceZThreshold,

      volumeZThreshold,

      spreadThresholdPercent,

      scoreChangeThreshold,

      confidenceChangeThreshold,
    },
  };
}

export class RealtimeAnomalyDetectorV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  detect(
    ticks = [],
    overrides = {},
  ) {
    return detectRealtimeAnomalies({
      ...this.config,

      ...overrides,

      ticks,
    });
  }
}

export const realtimeAnomalyDetectorV2 =
  new RealtimeAnomalyDetectorV2();

export default detectRealtimeAnomalies;