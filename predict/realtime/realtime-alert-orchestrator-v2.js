import {
  monitorRealtimeSignals,
} from "./realtime-signal-monitor-v2.js";

import {
  buildRealtimeMarketContext,
} from "./realtime-market-context-v2.js";

import {
  detectRealtimeAnomalies,
} from "./realtime-anomaly-detector-v2.js";

export const REALTIME_ALERT_ORCHESTRATOR_V2_VERSION =
  "realtime-alert-orchestrator-v2";

const PRIORITY_SCORE = {
  CRITICAL:
    100,

  BLOCKED:
    95,

  HIGH:
    85,

  DIRECTION_CHANGE:
    80,

  HIGH_PRIORITY:
    75,

  MEDIUM:
    55,

  LOW_CONFIDENCE:
    45,

  UNSTABLE:
    40,

  STALE:
    35,

  NORMAL:
    10,
};

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

function safeArray(value) {
  return Array.isArray(value)
    ? value
    : [];
}

function normalizeTimestamp(
  value,
  now,
) {
  const raw =
    value ??
    now();

  const parsed =
    typeof raw === "number"
      ? raw
      : Date.parse(raw);

  if (!Number.isFinite(parsed)) {
    throw new TypeError(
      "Realtime alert timestamp is invalid.",
    );
  }

  return parsed;
}

function severityRank(value) {
  return (
    PRIORITY_SCORE[
      String(value ?? "")
        .trim()
        .toUpperCase()
    ] ??
    0
  );
}

function normalizeChannels(
  channels = [],
) {
  if (!Array.isArray(channels)) {
    throw new TypeError(
      "Realtime alert channels must be an array.",
    );
  }

  return [
    ...new Set(
      channels
        .map(
          (
            channel,
          ) =>
            String(channel)
              .trim()
              .toUpperCase(),
        )
        .filter(Boolean),
    ),
  ];
}

function marketRiskMultiplier(
  marketContext,
) {
  return (
    finiteOrNull(
      marketContext
        ?.recommendation
        ?.riskMultiplier,
    ) ??
    0.5
  );
}

function signalAlertToEvent(
  alert,
  marketContext,
) {
  const marketMultiplier =
    marketRiskMultiplier(
      marketContext,
    );

  const basePriority =
    severityRank(
      alert.level,
    );

  const adjustedPriority =
    clamp(
      basePriority *
      (
        1.2 -
        marketMultiplier *
        0.2
      ),
    ) ?? basePriority;

  return {
    id:
      `signal:${alert.symbol}:${alert.timestamp}`,

    symbol:
      alert.symbol,

    source:
      "SIGNAL_MONITOR",

    type:
      alert.level,

    severity:
      alert.level ===
        "BLOCKED"
        ? "CRITICAL"
        : alert.level ===
            "DIRECTION_CHANGE"
          ? "HIGH"
          : alert.level ===
              "HIGH_PRIORITY"
            ? "HIGH"
            : "MEDIUM",

    priority:
      round(
        adjustedPriority,
        2,
      ),

    direction:
      alert.direction,

    confidence:
      alert.confidence,

    riskScore:
      alert.riskScore,

    title:
      `${alert.symbol} realtime signal alert`,

    message:
      `${alert.symbol} signal state changed to ${alert.level}.`,

    recommendation:
      alert.recommendation,

    timestamp:
      alert.timestamp,

    metadata: {
      marketRegime:
        marketContext
          ?.regime ??
        "UNKNOWN",

      marketScore:
        marketContext
          ?.score ??
        null,
    },
  };
}

function anomalyAlertToEvent(
  alert,
  nowTimestamp,
) {
  return {
    id:
      `anomaly:${alert.symbol}:${nowTimestamp}`,

    symbol:
      alert.symbol,

    source:
      "ANOMALY_DETECTOR",

    type:
      "REALTIME_ANOMALY",

    severity:
      alert.severity,

    priority:
      round(
        severityRank(
          alert.severity,
        ) +
        (
          finiteOrNull(
            alert.anomalyScore,
          ) ??
          0
        ) *
        0.1,
        2,
      ),

    direction:
      null,

    confidence:
      null,

    riskScore:
      alert.anomalyScore,

    title:
      `${alert.symbol} market anomaly`,

    message:
      `${alert.symbol} detected: ${safeArray(alert.anomalyTypes).join(", ")}.`,

    recommendation:
      alert.recommendation,

    timestamp:
      new Date(
        nowTimestamp,
      ).toISOString(),

    metadata: {
      anomalyTypes:
        safeArray(
          alert.anomalyTypes,
        ),

      anomalyScore:
        alert.anomalyScore,
    },
  };
}

function marketContextToEvent(
  marketContext,
) {
  if (
    marketContext
      ?.recommendation
      ?.action ===
      "NORMAL" ||
    marketContext
      ?.recommendation
      ?.action ===
      "ALLOW_LONG_BIAS"
  ) {
    return null;
  }

  const severe =
    marketContext.regime ===
      "HIGH_VOLATILITY" ||
    marketContext.regime ===
      "RISK_OFF";

  return {
    id:
      `market:${marketContext.generatedAt}`,

    symbol:
      "MARKET",

    source:
      "MARKET_CONTEXT",

    type:
      marketContext.regime,

    severity:
      severe
        ? "HIGH"
        : "MEDIUM",

    priority:
      severe
        ? 82
        : 55,

    direction:
      null,

    confidence:
      marketContext.score,

    riskScore:
      marketContext.score === null
        ? null
        : round(
            100 -
            marketContext.score,
            2,
          ),

    title:
      "Market context alert",

    message:
      `Market regime changed to ${marketContext.regime}.`,

    recommendation:
      marketContext.recommendation,

    timestamp:
      marketContext.generatedAt,

    metadata: {
      staleSources:
        marketContext.freshness
          ?.staleSources ??
        [],

      score:
        marketContext.score,
    },
  };
}

function deduplicateEvents(
  events,
  cooldownSeconds,
  history,
  nowTimestamp,
) {
  const latestByKey =
    new Map();

  for (
    const item
    of safeArray(history)
  ) {
    if (
      !item ||
      typeof item !== "object"
    ) {
      continue;
    }

    const key =
      String(
        item.deduplicationKey ??
        `${item.source}:${item.symbol}:${item.type}`,
      );

    const timestamp =
      Date.parse(
        item.timestamp ??
        item.createdAt ??
        "",
      );

    if (
      Number.isFinite(timestamp)
    ) {
      latestByKey.set(
        key,
        timestamp,
      );
    }
  }

  return events.map(
    (
      event,
    ) => {
      const deduplicationKey =
        `${event.source}:${event.symbol}:${event.type}`;

      const previousTimestamp =
        latestByKey.get(
          deduplicationKey,
        );

      const suppressed =
        Number.isFinite(
          previousTimestamp,
        ) &&
        (
          nowTimestamp -
          previousTimestamp
        ) /
        1000 <
        cooldownSeconds;

      return {
        ...event,

        deduplicationKey,

        suppressed,

        suppressionReason:
          suppressed
            ? "COOLDOWN_ACTIVE"
            : null,
      };
    },
  );
}

function routeEvent(
  event,
  channels,
) {
  const routedChannels = [];

  if (
    event.severity ===
      "CRITICAL" ||
    event.priority >= 90
  ) {
    for (
      const channel
      of [
        "IN_APP",
        "PUSH",
        "EMAIL",
      ]
    ) {
      if (
        channels.includes(
          channel,
        )
      ) {
        routedChannels.push(
          channel,
        );
      }
    }
  } else if (
    event.severity ===
      "HIGH" ||
    event.priority >= 70
  ) {
    for (
      const channel
      of [
        "IN_APP",
        "PUSH",
      ]
    ) {
      if (
        channels.includes(
          channel,
        )
      ) {
        routedChannels.push(
          channel,
        );
      }
    }
  } else if (
    channels.includes(
      "IN_APP",
    )
  ) {
    routedChannels.push(
      "IN_APP",
    );
  }

  return {
    ...event,

    channels:
      routedChannels,

    dispatchable:
      !event.suppressed &&
      routedChannels.length > 0,
  };
}

function summarize(
  events,
) {
  const dispatchable =
    events.filter(
      (
        event,
      ) =>
        event.dispatchable,
    );

  return {
    total:
      events.length,

    dispatchable:
      dispatchable.length,

    suppressed:
      events.filter(
        (
          event,
        ) =>
          event.suppressed,
      ).length,

    critical:
      events.filter(
        (
          event,
        ) =>
          event.severity ===
          "CRITICAL",
      ).length,

    high:
      events.filter(
        (
          event,
        ) =>
          event.severity ===
          "HIGH",
      ).length,

    symbols:
      [
        ...new Set(
          events.map(
            (
              event,
            ) =>
              event.symbol,
          ),
        ),
      ],

    channels:
      Object.fromEntries(
        [
          "IN_APP",
          "PUSH",
          "EMAIL",
        ].map(
          (
            channel,
          ) => [
            channel,

            dispatchable.filter(
              (
                event,
              ) =>
                event.channels
                  .includes(
                    channel,
                  ),
            ).length,
          ],
        ),
      ),
  };
}

export function orchestrateRealtimeAlerts({
  signals = [],
  ticks = [],
  market = {},
  history = [],
  channels = [
    "IN_APP",
    "PUSH",
    "EMAIL",
  ],
  cooldownSeconds = 300,
  now = Date.now,
  signalConfig = {},
  anomalyConfig = {},
  marketConfig = {},
} = {}) {
  if (
    typeof now !== "function"
  ) {
    throw new TypeError(
      "Realtime alert clock must be a function.",
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
      "Realtime alert clock returned an invalid value.",
    );
  }

  const normalizedChannels =
    normalizeChannels(
      channels,
    );

  const signalMonitor =
    monitorRealtimeSignals({
      ...signalConfig,

      signals:
        safeArray(
          signals,
        ),

      now:
        () => nowTimestamp,
    });

  const marketContext =
    buildRealtimeMarketContext({
      ...marketConfig,

      ...market,

      now:
        () => nowTimestamp,
    });

  const anomalyDetection =
    detectRealtimeAnomalies({
      ...anomalyConfig,

      ticks:
        safeArray(
          ticks,
        ),
    });

  const events = [
    ...safeArray(
      signalMonitor.alerts,
    ).map(
      (
        alert,
      ) =>
        signalAlertToEvent(
          alert,
          marketContext,
        ),
    ),

    ...safeArray(
      anomalyDetection.alerts,
    ).map(
      (
        alert,
      ) =>
        anomalyAlertToEvent(
          alert,
          nowTimestamp,
        ),
    ),
  ];

  const marketEvent =
    marketContextToEvent(
      marketContext,
    );

  if (marketEvent) {
    events.push(
      marketEvent,
    );
  }

  const deduplicated =
    deduplicateEvents(
      events,
      Math.max(
        0,
        finiteOrNull(
          cooldownSeconds,
        ) ?? 300,
      ),
      history,
      nowTimestamp,
    );

  const routed =
    deduplicated
      .map(
        (
          event,
        ) =>
          routeEvent(
            event,
            normalizedChannels,
          ),
      )
      .sort(
        (
          left,
          right,
        ) =>
          right.priority -
          left.priority,
      );

  return {
    version:
      REALTIME_ALERT_ORCHESTRATOR_V2_VERSION,

    ready:
      signalMonitor.ready ||
      anomalyDetection.ready ||
      marketContext.ready,

    generatedAt:
      new Date(
        nowTimestamp,
      ).toISOString(),

    events:
      routed,

    dispatchQueue:
      routed.filter(
        (
          event,
        ) =>
          event.dispatchable,
      ),

    signalMonitor,

    marketContext,

    anomalyDetection,

    summary:
      summarize(
        routed,
      ),

    configuration: {
      channels:
        normalizedChannels,

      cooldownSeconds:
        Math.max(
          0,
          finiteOrNull(
            cooldownSeconds,
          ) ?? 300,
        ),
    },
  };
}

export class RealtimeAlertOrchestratorV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  run(input = {}) {
    return orchestrateRealtimeAlerts({
      ...this.config,

      ...input,
    });
  }
}

export const realtimeAlertOrchestratorV2 =
  new RealtimeAlertOrchestratorV2();

export default orchestrateRealtimeAlerts;