export const REALTIME_SIGNAL_MONITOR_V2_VERSION =
  "realtime-signal-monitor-v2";

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

function normalizeDirection(value) {
  if (typeof value === "number") {
    if (value > 0) {
      return "BUY";
    }

    if (value < 0) {
      return "SELL";
    }

    return "NEUTRAL";
  }

  const text =
    String(value ?? "")
      .trim()
      .toUpperCase();

  if (
    [
      "BUY",
      "LONG",
      "BULLISH",
      "UP",
      "1",
    ].includes(text)
  ) {
    return "BUY";
  }

  if (
    [
      "SELL",
      "SHORT",
      "BEARISH",
      "DOWN",
      "-1",
    ].includes(text)
  ) {
    return "SELL";
  }

  return "NEUTRAL";
}

function directionValue(value) {
  const normalized =
    normalizeDirection(value);

  if (normalized === "BUY") {
    return 1;
  }

  if (normalized === "SELL") {
    return -1;
  }

  return 0;
}

function normalizeTimestamp(
  value,
  now,
) {
  const parsed =
    value === null ||
    value === undefined
      ? now()
      : Date.parse(value);

  const timestamp =
    value === null ||
    value === undefined
      ? finiteOrNull(parsed)
      : parsed;

  if (!Number.isFinite(timestamp)) {
    throw new TypeError(
      "Realtime signal timestamp is invalid.",
    );
  }

  return timestamp;
}

function normalizeSignal(
  signal,
  index,
  now,
) {
  if (
    !signal ||
    typeof signal !== "object"
  ) {
    return null;
  }

  const symbol =
    String(
      signal.symbol ??
      signal.code ??
      signal.ticker ??
      "",
    ).trim();

  if (!symbol) {
    return null;
  }

  const direction =
    normalizeDirection(
      signal.direction ??
      signal.signal ??
      signal.recommendation,
    );

  const confidence =
    clamp(
      signal.confidence ??
      signal.probability ??
      50,
    ) ?? 50;

  const score =
    clamp(
      signal.score ??
      signal.aiScore ??
      confidence,
    ) ?? confidence;

  const riskScore =
    clamp(
      signal.riskScore ??
      signal.risk ??
      50,
    ) ?? 50;

  const timestamp =
    normalizeTimestamp(
      signal.timestamp ??
      signal.generatedAt ??
      signal.updatedAt,
      now,
    );

  return {
    id:
      String(
        signal.id ??
        `${symbol}-${timestamp}-${index}`,
      ),

    symbol,

    direction,

    directionValue:
      directionValue(direction),

    confidence,

    score,

    riskScore,

    marketRegime:
      String(
        signal.marketRegime ??
        signal.regime ??
        "UNKNOWN",
      )
        .trim()
        .toUpperCase(),

    price:
      finiteOrNull(
        signal.price ??
        signal.lastPrice ??
        signal.currentPrice,
      ),

    timestamp,

    timestampIso:
      new Date(
        timestamp,
      ).toISOString(),

    metadata:
      signal.metadata ??
      {},
  };
}

function normalizeSignals(
  signals,
  now,
) {
  if (!Array.isArray(signals)) {
    throw new TypeError(
      "Realtime signals must be an array.",
    );
  }

  return signals
    .map(
      (
        signal,
        index,
      ) =>
        normalizeSignal(
          signal,
          index,
          now,
        ),
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
  signals,
) {
  const groups =
    new Map();

  for (
    const signal
    of signals
  ) {
    if (
      !groups.has(
        signal.symbol,
      )
    ) {
      groups.set(
        signal.symbol,
        [],
      );
    }

    groups.get(
      signal.symbol,
    ).push(
      signal,
    );
  }

  return groups;
}

function calculateSignalAgeSeconds(
  signal,
  nowTimestamp,
) {
  return Math.max(
    0,
    (
      nowTimestamp -
      signal.timestamp
    ) /
    1000,
  );
}

function determineFreshness({
  ageSeconds,
  freshWindowSeconds,
  staleWindowSeconds,
}) {
  if (
    ageSeconds <=
    freshWindowSeconds
  ) {
    return "FRESH";
  }

  if (
    ageSeconds <=
    staleWindowSeconds
  ) {
    return "AGING";
  }

  return "STALE";
}

function calculateDirectionStability(
  history,
  latestDirection,
) {
  if (!history.length) {
    return 0;
  }

  const matching =
    history.filter(
      (
        signal,
      ) =>
        signal.direction ===
        latestDirection,
    ).length;

  return (
    matching /
    history.length *
    100
  );
}

function calculateConfidenceTrend(
  history,
) {
  if (history.length < 2) {
    return 0;
  }

  const first =
    history[0].confidence;

  const last =
    history[
      history.length - 1
    ].confidence;

  return last - first;
}

function calculateScoreTrend(
  history,
) {
  if (history.length < 2) {
    return 0;
  }

  return (
    history[
      history.length - 1
    ].score -
    history[0].score
  );
}

function detectDirectionChange(
  history,
) {
  if (history.length < 2) {
    return false;
  }

  const previous =
    history[
      history.length - 2
    ];

  const latest =
    history[
      history.length - 1
    ];

  return (
    previous.direction !==
    latest.direction
  );
}

function buildAlertLevel({
  latest,
  freshness,
  directionChanged,
  minimumConfidence,
  maximumRiskScore,
  stability,
}) {
  if (
    freshness === "STALE"
  ) {
    return "STALE";
  }

  if (
    latest.riskScore >
    maximumRiskScore
  ) {
    return "BLOCKED";
  }

  if (
    latest.confidence <
    minimumConfidence
  ) {
    return "LOW_CONFIDENCE";
  }

  if (
    directionChanged
  ) {
    return "DIRECTION_CHANGE";
  }

  if (
    stability < 60
  ) {
    return "UNSTABLE";
  }

  if (
    latest.confidence >= 75 &&
    latest.score >= 70
  ) {
    return "HIGH_PRIORITY";
  }

  return "NORMAL";
}

function buildRecommendation({
  latest,
  alertLevel,
}) {
  if (
    alertLevel === "STALE"
  ) {
    return {
      action:
        "REFRESH",

      tradable:
        false,

      reason:
        "SIGNAL_DATA_STALE",
    };
  }

  if (
    alertLevel === "BLOCKED"
  ) {
    return {
      action:
        "BLOCK",

      tradable:
        false,

      reason:
        "RISK_LIMIT_EXCEEDED",
    };
  }

  if (
    alertLevel ===
      "LOW_CONFIDENCE" ||
    alertLevel ===
      "UNSTABLE"
  ) {
    return {
      action:
        "WAIT",

      tradable:
        false,

      reason:
        "SIGNAL_NOT_RELIABLE_ENOUGH",
    };
  }

  if (
    alertLevel ===
    "DIRECTION_CHANGE"
  ) {
    return {
      action:
        "REVIEW",

      tradable:
        false,

      reason:
        "SIGNAL_DIRECTION_CHANGED",
    };
  }

  if (
    latest.direction ===
    "NEUTRAL"
  ) {
    return {
      action:
        "HOLD",

      tradable:
        false,

      reason:
        "NO_DIRECTIONAL_EDGE",
    };
  }

  return {
    action:
      latest.direction,

    tradable:
      true,

    reason:
      alertLevel ===
      "HIGH_PRIORITY"
        ? "HIGH_CONFIDENCE_SIGNAL"
        : "SIGNAL_PASSED_MONITORING_GATES",
  };
}

function analyzeSymbolSignals({
  symbol,
  signals,
  nowTimestamp,
  freshWindowSeconds,
  staleWindowSeconds,
  minimumConfidence,
  maximumRiskScore,
  historyLimit,
}) {
  const history =
    signals.slice(
      -historyLimit,
    );

  const latest =
    history[
      history.length - 1
    ];

  const ageSeconds =
    calculateSignalAgeSeconds(
      latest,
      nowTimestamp,
    );

  const freshness =
    determineFreshness({
      ageSeconds,

      freshWindowSeconds,

      staleWindowSeconds,
    });

  const directionChanged =
    detectDirectionChange(
      history,
    );

  const stability =
    calculateDirectionStability(
      history,
      latest.direction,
    );

  const confidenceTrend =
    calculateConfidenceTrend(
      history,
    );

  const scoreTrend =
    calculateScoreTrend(
      history,
    );

  const alertLevel =
    buildAlertLevel({
      latest,

      freshness,

      directionChanged,

      minimumConfidence,

      maximumRiskScore,

      stability,
    });

  const recommendation =
    buildRecommendation({
      latest,

      alertLevel,
    });

  return {
    symbol,

    latest,

    historyCount:
      history.length,

    ageSeconds:
      round(
        ageSeconds,
        2,
      ),

    freshness,

    directionChanged,

    stability:
      round(
        stability,
        2,
      ),

    confidenceTrend:
      round(
        confidenceTrend,
        2,
      ),

    scoreTrend:
      round(
        scoreTrend,
        2,
      ),

    alertLevel,

    recommendation,

    history,
  };
}

function sortMonitors(
  monitors,
) {
  const priority = {
    HIGH_PRIORITY:
      0,

    DIRECTION_CHANGE:
      1,

    BLOCKED:
      2,

    LOW_CONFIDENCE:
      3,

    UNSTABLE:
      4,

    NORMAL:
      5,

    STALE:
      6,
  };

  return monitors.sort(
    (
      left,
      right,
    ) =>
      (
        priority[
          left.alertLevel
        ] ?? 99
      ) -
      (
        priority[
          right.alertLevel
        ] ?? 99
      ) ||
      right.latest.confidence -
      left.latest.confidence,
  );
}

export function monitorRealtimeSignals({
  signals = [],
  now = Date.now,
  freshWindowSeconds = 120,
  staleWindowSeconds = 600,
  minimumConfidence = 55,
  maximumRiskScore = 70,
  historyLimit = 20,
} = {}) {
  if (
    typeof now !== "function"
  ) {
    throw new TypeError(
      "Realtime signal clock must be a function.",
    );
  }

  const nowTimestamp =
    finiteOrNull(
      now(),
    );

  if (
    nowTimestamp === null
  ) {
    throw new TypeError(
      "Realtime signal clock returned an invalid value.",
    );
  }

  const normalizedSignals =
    normalizeSignals(
      signals,
      now,
    );

  const normalizedFreshWindow =
    Math.max(
      1,
      finiteOrNull(
        freshWindowSeconds,
      ) ?? 120,
    );

  const normalizedStaleWindow =
    Math.max(
      normalizedFreshWindow,
      finiteOrNull(
        staleWindowSeconds,
      ) ?? 600,
    );

  const normalizedHistoryLimit =
    Math.max(
      1,
      Math.floor(
        finiteOrNull(
          historyLimit,
        ) ?? 20,
      ),
    );

  if (!normalizedSignals.length) {
    return {
      version:
        REALTIME_SIGNAL_MONITOR_V2_VERSION,

      ready:
        false,

      generatedAt:
        new Date(
          nowTimestamp,
        ).toISOString(),

      signalCount:
        0,

      symbolCount:
        0,

      monitors:
        [],

      alerts:
        [],

      summary: {
        tradableCount:
          0,

        blockedCount:
          0,

        staleCount:
          0,

        directionChangeCount:
          0,
      },
    };
  }

  const groups =
    groupBySymbol(
      normalizedSignals,
    );

  const monitors =
    sortMonitors(
      Array.from(
        groups.entries(),
      ).map(
        (
          [
            symbol,
            symbolSignals,
          ],
        ) =>
          analyzeSymbolSignals({
            symbol,

            signals:
              symbolSignals,

            nowTimestamp,

            freshWindowSeconds:
              normalizedFreshWindow,

            staleWindowSeconds:
              normalizedStaleWindow,

            minimumConfidence:
              clamp(
                minimumConfidence,
              ) ?? 55,

            maximumRiskScore:
              clamp(
                maximumRiskScore,
              ) ?? 70,

            historyLimit:
              normalizedHistoryLimit,
          }),
      ),
    );

  const alerts =
    monitors
      .filter(
        (
          monitor,
        ) =>
          monitor.alertLevel !==
          "NORMAL",
      )
      .map(
        (
          monitor,
        ) => ({
          symbol:
            monitor.symbol,

          level:
            monitor.alertLevel,

          direction:
            monitor.latest.direction,

          confidence:
            monitor.latest.confidence,

          riskScore:
            monitor.latest.riskScore,

          recommendation:
            monitor.recommendation,

          timestamp:
            monitor.latest.timestampIso,
        }),
      );

  return {
    version:
      REALTIME_SIGNAL_MONITOR_V2_VERSION,

    ready:
      true,

    generatedAt:
      new Date(
        nowTimestamp,
      ).toISOString(),

    signalCount:
      normalizedSignals.length,

    symbolCount:
      groups.size,

    configuration: {
      freshWindowSeconds:
        normalizedFreshWindow,

      staleWindowSeconds:
        normalizedStaleWindow,

      minimumConfidence:
        clamp(
          minimumConfidence,
        ) ?? 55,

      maximumRiskScore:
        clamp(
          maximumRiskScore,
        ) ?? 70,

      historyLimit:
        normalizedHistoryLimit,
    },

    monitors,

    alerts,

    summary: {
      tradableCount:
        monitors.filter(
          (
            monitor,
          ) =>
            monitor.recommendation
              .tradable,
        ).length,

      blockedCount:
        monitors.filter(
          (
            monitor,
          ) =>
            monitor.alertLevel ===
            "BLOCKED",
        ).length,

      staleCount:
        monitors.filter(
          (
            monitor,
          ) =>
            monitor.freshness ===
            "STALE",
        ).length,

      directionChangeCount:
        monitors.filter(
          (
            monitor,
          ) =>
            monitor.directionChanged,
        ).length,

      highPriorityCount:
        monitors.filter(
          (
            monitor,
          ) =>
            monitor.alertLevel ===
            "HIGH_PRIORITY",
        ).length,

      averageConfidence:
        round(
          monitors.reduce(
            (
              sum,
              monitor,
            ) =>
              sum +
              monitor.latest
                .confidence,
            0,
          ) /
          monitors.length,
          2,
        ),
    },
  };
}

export class RealtimeSignalMonitorV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  monitor(
    signals = [],
    overrides = {},
  ) {
    return monitorRealtimeSignals({
      ...this.config,

      ...overrides,

      signals,
    });
  }
}

export const realtimeSignalMonitorV2 =
  new RealtimeSignalMonitorV2();

export default monitorRealtimeSignals;