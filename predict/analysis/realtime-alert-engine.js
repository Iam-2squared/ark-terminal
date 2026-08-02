function finiteNumber(value, fallback = 0) {
  const parsed = Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : fallback;
}

function clamp(value, minimum = 0, maximum = 100) {
  return Math.min(
    maximum,
    Math.max(
      minimum,
      finiteNumber(value),
    ),
  );
}

function normalizeAction(action = "HOLD") {
  return String(action)
    .trim()
    .toUpperCase();
}

function createAlertId() {
  return (
    globalThis.crypto?.randomUUID?.() ??
    [
      "alert",
      Date.now().toString(36),
      Math.random()
        .toString(36)
        .slice(2, 10),
    ].join("-")
  );
}

export function evaluateRealtimeAlert({
  symbol = null,
  current = {},
  previous = {},
  thresholds = {},
} = {}) {
  const minimumScore =
    clamp(
      thresholds.minimumScore ?? 75,
    );

  const minimumConfidence =
    clamp(
      thresholds.minimumConfidence ?? 70,
    );

  const maximumRiskPercent =
    Math.max(
      0,
      finiteNumber(
        thresholds.maximumRiskPercent,
        6,
      ),
    );

  const minimumScoreChange =
    Math.max(
      0,
      finiteNumber(
        thresholds.minimumScoreChange,
        5,
      ),
    );

  const currentScore =
    clamp(
      current.score ?? 50,
    );

  const previousScore =
    clamp(
      previous.score ?? currentScore,
    );

  const confidence =
    clamp(
      current.confidence ?? 0,
    );

  const riskPercent =
    Math.max(
      0,
      finiteNumber(
        current.riskPercent,
        0,
      ),
    );

  const action =
    normalizeAction(
      current.action,
    );

  const previousAction =
    normalizeAction(
      previous.action,
    );

  const scoreChange =
    currentScore -
    previousScore;

  const reasons = [];
  let severity = "INFO";
  let triggered = false;

  if (
    [
      "BUY",
      "STRONG BUY",
    ].includes(action) &&
    currentScore >= minimumScore &&
    confidence >= minimumConfidence &&
    riskPercent <= maximumRiskPercent
  ) {
    triggered = true;
    severity =
      action === "STRONG BUY"
        ? "HIGH"
        : "MEDIUM";

    reasons.push(
      "buy_conditions_met",
    );
  }

  if (
    previousAction !== action
  ) {
    triggered = true;

    severity =
      severity === "HIGH"
        ? "HIGH"
        : "MEDIUM";

    reasons.push(
      "action_changed",
    );
  }

  if (
    Math.abs(scoreChange) >=
    minimumScoreChange
  ) {
    triggered = true;

    reasons.push(
      scoreChange > 0
        ? "score_improved"
        : "score_deteriorated",
    );

    if (
      scoreChange < 0 &&
      severity !== "HIGH"
    ) {
      severity = "MEDIUM";
    }
  }

  if (
    riskPercent >
    maximumRiskPercent
  ) {
    triggered = true;
    severity = "HIGH";

    reasons.push(
      "risk_limit_exceeded",
    );
  }

  return {
    triggered,

    severity,

    symbol,

    action,

    previousAction,

    score:
      currentScore,

    previousScore,

    scoreChange,

    confidence,

    riskPercent,

    reasons:
      [...new Set(reasons)],

    message:
      triggered
        ? `${symbol ?? "UNKNOWN"} ${action}・Score ${currentScore}・Confidence ${confidence}%`
        : "No alert condition met.",
  };
}

export function createRealtimeAlert(
  evaluation = {},
) {
  if (
    evaluation.triggered !== true
  ) {
    return null;
  }

  return {
    id:
      createAlertId(),

    createdAt:
      new Date()
        .toISOString(),

    acknowledged:
      false,

    ...evaluation,
  };
}

export function appendRealtimeAlert({
  alerts = [],
  alert,
  limit = 100,
} = {}) {
  const safeAlerts =
    Array.isArray(alerts)
      ? alerts
      : [];

  if (!alert) {
    return [
      ...safeAlerts,
    ];
  }

  const next = [
    alert,
    ...safeAlerts.filter(
      (item) =>
        item.id !== alert.id,
    ),
  ];

  return next.slice(
    0,
    Math.max(
      1,
      Math.floor(
        finiteNumber(
          limit,
          100,
        ),
      ),
    ),
  );
}

export function acknowledgeRealtimeAlert({
  alerts = [],
  alertId,
} = {}) {
  return alerts.map(
    (alert) =>
      alert.id === alertId
        ? {
            ...alert,

            acknowledged:
              true,

            acknowledgedAt:
              new Date()
                .toISOString(),
          }
        : alert,
  );
}

export function summarizeRealtimeAlerts(
  alerts = [],
) {
  const safeAlerts =
    Array.isArray(alerts)
      ? alerts
      : [];

  return {
    total:
      safeAlerts.length,

    unread:
      safeAlerts.filter(
        (alert) =>
          alert.acknowledged !== true,
      ).length,

    highSeverity:
      safeAlerts.filter(
        (alert) =>
          alert.severity === "HIGH",
      ).length,

    latest:
      safeAlerts[0] ??
      null,
  };
}

export class RealtimeAlertEngine {
  constructor({
    thresholds = {},
    limit = 100,
  } = {}) {
    this.thresholds =
      thresholds;

    this.limit =
      limit;

    this.alerts = [];
    this.previousBySymbol =
      new Map();
  }

  update({
    symbol,
    current = {},
  } = {}) {
    const previous =
      this.previousBySymbol.get(
        symbol,
      ) ?? {};

    const evaluation =
      evaluateRealtimeAlert({
        symbol,
        current,
        previous,
        thresholds:
          this.thresholds,
      });

    this.previousBySymbol.set(
      symbol,
      {
        ...current,
      },
    );

    const alert =
      createRealtimeAlert(
        evaluation,
      );

    this.alerts =
      appendRealtimeAlert({
        alerts:
          this.alerts,

        alert,

        limit:
          this.limit,
      });

    return {
      evaluation,
      alert,
      alerts:
        [...this.alerts],

      summary:
        summarizeRealtimeAlerts(
          this.alerts,
        ),
    };
  }

  acknowledge(alertId) {
    this.alerts =
      acknowledgeRealtimeAlert({
        alerts:
          this.alerts,

        alertId,
      });

    return [
      ...this.alerts,
    ];
  }

  clear() {
    this.alerts = [];
  }
}

export const realtimeAlertEngine =
  new RealtimeAlertEngine();