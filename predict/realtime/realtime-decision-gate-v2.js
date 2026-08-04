export const REALTIME_DECISION_GATE_V2_VERSION =
  "realtime-decision-gate-v2";

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

function normalizeSignal(signal = {}) {
  return {
    symbol:
      String(
        signal.symbol ??
        signal.code ??
        signal.ticker ??
        "",
      ).trim(),

    direction:
      normalizeDirection(
        signal.direction ??
        signal.signal ??
        signal.recommendation
          ?.action,
      ),

    confidence:
      clamp(
        signal.confidence ??
        signal.probability ??
        0,
      ) ?? 0,

    score:
      clamp(
        signal.score ??
        signal.aiScore ??
        signal.confidence ??
        0,
      ) ?? 0,

    riskScore:
      clamp(
        signal.riskScore ??
        signal.risk ??
        50,
      ) ?? 50,

    freshness:
      String(
        signal.freshness ??
        "UNKNOWN",
      )
        .trim()
        .toUpperCase(),

    tradable:
      signal.tradable ??
      signal.recommendation
        ?.tradable ??
      false,
  };
}

function normalizeMarketContext(
  marketContext = {},
) {
  return {
    ready:
      marketContext.ready === true,

    score:
      clamp(
        marketContext.score,
      ),

    regime:
      String(
        marketContext.regime ??
        "UNKNOWN",
      )
        .trim()
        .toUpperCase(),

    action:
      String(
        marketContext
          ?.recommendation
          ?.action ??
        "UNKNOWN",
      )
        .trim()
        .toUpperCase(),

    riskMultiplier:
      Math.max(
        0,
        finiteOrNull(
          marketContext
            ?.recommendation
            ?.riskMultiplier,
        ) ?? 0.5,
      ),

    stale:
      marketContext
        ?.diagnostics
        ?.stale === true ||
      (
        finiteOrNull(
          marketContext
            ?.freshness
            ?.staleSourceCount,
        ) ?? 0
      ) > 0,
  };
}

function normalizeAnomaly(
  anomaly = {},
) {
  return {
    ready:
      anomaly.ready === true,

    detected:
      anomaly.anomalyDetected === true,

    severity:
      String(
        anomaly.severity ??
        "LOW",
      )
        .trim()
        .toUpperCase(),

    score:
      clamp(
        anomaly.anomalyScore,
      ) ?? 0,

    action:
      String(
        anomaly
          ?.recommendation
          ?.action ??
        "CONTINUE",
      )
        .trim()
        .toUpperCase(),

    tradable:
      anomaly
        ?.recommendation
        ?.tradable ??
      true,
  };
}

function normalizePortfolio(
  portfolio = {},
) {
  return {
    exposurePercent:
      clamp(
        portfolio.exposurePercent ??
        portfolio.exposure ??
        0,
      ) ?? 0,

    dailyLossPercent:
      Math.abs(
        finiteOrNull(
          portfolio.dailyLossPercent ??
          portfolio.dailyLoss ??
          0,
        ) ?? 0,
      ),

    openPositions:
      Math.max(
        0,
        Math.floor(
          finiteOrNull(
            portfolio.openPositions ??
            portfolio.positionCount ??
            0,
          ) ?? 0,
        ),
      ),

    symbolExposurePercent:
      clamp(
        portfolio.symbolExposurePercent ??
        portfolio.positionExposure ??
        0,
      ) ?? 0,

    availableCashPercent:
      clamp(
        portfolio.availableCashPercent ??
        portfolio.cashPercent ??
        100,
      ) ?? 100,
  };
}

function createCheck({
  name,
  passed,
  severity,
  value,
  threshold,
  reason,
}) {
  return {
    name,

    passed:
      passed === true,

    severity,

    value,

    threshold,

    reason:
      passed
        ? "PASSED"
        : reason,
  };
}

function buildChecks({
  signal,
  market,
  anomaly,
  portfolio,
  minimumConfidence,
  minimumScore,
  maximumSignalRisk,
  maximumPortfolioExposure,
  maximumDailyLoss,
  maximumOpenPositions,
  maximumSymbolExposure,
}) {
  return [
    createCheck({
      name:
        "SYMBOL_PRESENT",

      passed:
        signal.symbol.length > 0,

      severity:
        "CRITICAL",

      value:
        signal.symbol,

      threshold:
        "NON_EMPTY",

      reason:
        "SIGNAL_SYMBOL_MISSING",
    }),

    createCheck({
      name:
        "DIRECTIONAL_SIGNAL",

      passed:
        signal.direction !==
        "NEUTRAL",

      severity:
        "HIGH",

      value:
        signal.direction,

      threshold:
        "BUY_OR_SELL",

      reason:
        "SIGNAL_HAS_NO_DIRECTION",
    }),

    createCheck({
      name:
        "SIGNAL_TRADABLE",

      passed:
        signal.tradable === true,

      severity:
        "HIGH",

      value:
        signal.tradable,

      threshold:
        true,

      reason:
        "SIGNAL_MONITOR_BLOCKED_TRADE",
    }),

    createCheck({
      name:
        "SIGNAL_FRESHNESS",

      passed:
        signal.freshness !==
          "STALE" &&
        signal.freshness !==
          "UNKNOWN",

      severity:
        "HIGH",

      value:
        signal.freshness,

      threshold:
        "FRESH_OR_AGING",

      reason:
        "SIGNAL_IS_STALE_OR_UNKNOWN",
    }),

    createCheck({
      name:
        "MINIMUM_CONFIDENCE",

      passed:
        signal.confidence >=
        minimumConfidence,

      severity:
        "MEDIUM",

      value:
        signal.confidence,

      threshold:
        minimumConfidence,

      reason:
        "SIGNAL_CONFIDENCE_TOO_LOW",
    }),

    createCheck({
      name:
        "MINIMUM_SCORE",

      passed:
        signal.score >=
        minimumScore,

      severity:
        "MEDIUM",

      value:
        signal.score,

      threshold:
        minimumScore,

      reason:
        "AI_SCORE_TOO_LOW",
    }),

    createCheck({
      name:
        "SIGNAL_RISK_LIMIT",

      passed:
        signal.riskScore <=
        maximumSignalRisk,

      severity:
        "CRITICAL",

      value:
        signal.riskScore,

      threshold:
        maximumSignalRisk,

      reason:
        "SIGNAL_RISK_TOO_HIGH",
    }),

    createCheck({
      name:
        "MARKET_CONTEXT_READY",

      passed:
        market.ready === true,

      severity:
        "MEDIUM",

      value:
        market.ready,

      threshold:
        true,

      reason:
        "MARKET_CONTEXT_NOT_READY",
    }),

    createCheck({
      name:
        "MARKET_CONTEXT_FRESH",

      passed:
        market.stale === false,

      severity:
        "HIGH",

      value:
        market.stale,

      threshold:
        false,

      reason:
        "MARKET_CONTEXT_IS_STALE",
    }),

    createCheck({
      name:
        "MARKET_RISK_GATE",

      passed:
        ![
          "REFRESH",
          "REDUCE_RISK",
          "TIGHTEN_RISK_LIMITS",
        ].includes(
          market.action,
        ),

      severity:
        market.action ===
        "REFRESH"
          ? "CRITICAL"
          : "HIGH",

      value:
        market.action,

      threshold:
        "NORMAL_OR_ALLOW_LONG_BIAS",

      reason:
        "MARKET_CONTEXT_BLOCKS_NEW_RISK",
    }),

    createCheck({
      name:
        "REALTIME_ANOMALY_GATE",

      passed:
        anomaly.action !==
          "BLOCK" &&
        anomaly.severity !==
          "CRITICAL" &&
        anomaly.tradable !==
          false,

      severity:
        "CRITICAL",

      value:
        anomaly.severity,

      threshold:
        "BELOW_CRITICAL",

      reason:
        "CRITICAL_REALTIME_ANOMALY",
    }),

    createCheck({
      name:
        "PORTFOLIO_EXPOSURE",

      passed:
        portfolio.exposurePercent <=
        maximumPortfolioExposure,

      severity:
        "HIGH",

      value:
        portfolio.exposurePercent,

      threshold:
        maximumPortfolioExposure,

      reason:
        "PORTFOLIO_EXPOSURE_LIMIT_REACHED",
    }),

    createCheck({
      name:
        "DAILY_LOSS_LIMIT",

      passed:
        portfolio.dailyLossPercent <=
        maximumDailyLoss,

      severity:
        "CRITICAL",

      value:
        portfolio.dailyLossPercent,

      threshold:
        maximumDailyLoss,

      reason:
        "DAILY_LOSS_LIMIT_REACHED",
    }),

    createCheck({
      name:
        "OPEN_POSITION_LIMIT",

      passed:
        portfolio.openPositions <
        maximumOpenPositions,

      severity:
        "HIGH",

      value:
        portfolio.openPositions,

      threshold:
        maximumOpenPositions,

      reason:
        "OPEN_POSITION_LIMIT_REACHED",
    }),

    createCheck({
      name:
        "SYMBOL_EXPOSURE_LIMIT",

      passed:
        portfolio.symbolExposurePercent <=
        maximumSymbolExposure,

      severity:
        "HIGH",

      value:
        portfolio.symbolExposurePercent,

      threshold:
        maximumSymbolExposure,

      reason:
        "SYMBOL_EXPOSURE_LIMIT_REACHED",
    }),

    createCheck({
      name:
        "AVAILABLE_CASH",

      passed:
        portfolio.availableCashPercent >
        0,

      severity:
        "HIGH",

      value:
        portfolio.availableCashPercent,

      threshold:
        "> 0",

      reason:
        "NO_AVAILABLE_CASH",
    }),
  ];
}

function calculateGateScore(
  checks,
) {
  const weights = {
    CRITICAL:
      4,

    HIGH:
      2,

    MEDIUM:
      1,

    LOW:
      0.5,
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
            check.severity
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
                check.severity
              ] ?? 1
            : 0
        ),
      0,
    );

  return totalWeight > 0
    ? (
        passedWeight /
        totalWeight
      ) *
      100
    : 0;
}

function determineDecision({
  checks,
  gateScore,
  minimumGateScore,
}) {
  const failed =
    checks.filter(
      (
        check,
      ) =>
        !check.passed,
    );

  const critical =
    failed.filter(
      (
        check,
      ) =>
        check.severity ===
        "CRITICAL",
    );

  const high =
    failed.filter(
      (
        check,
      ) =>
        check.severity ===
        "HIGH",
    );

  const medium =
    failed.filter(
      (
        check,
      ) =>
        check.severity ===
        "MEDIUM",
    );

  if (critical.length > 0) {
    return {
      decision:
        "BLOCK",

      tradable:
        false,

      reason:
        critical[0].reason,
    };
  }

  if (
    high.length > 0 ||
    medium.length > 0 ||
    gateScore <
      minimumGateScore
  ) {
    return {
      decision:
        "WAIT",

      tradable:
        false,

      reason:
        high[0]?.reason ??
        medium[0]?.reason ??
        "REALTIME_GATE_SCORE_TOO_LOW",
    };
  }

  return {
    decision:
      "ALLOW",

    tradable:
      true,

    reason:
      "ALL_REALTIME_DECISION_GATES_PASSED",
  };
}

function calculatePositionMultiplier({
  signal,
  market,
  anomaly,
  gateScore,
}) {
  const confidenceFactor =
    signal.confidence /
    100;

  const scoreFactor =
    signal.score /
    100;

  const marketFactor =
    Math.min(
      1,
      Math.max(
        0,
        market.riskMultiplier,
      ),
    );

  const anomalyFactor =
    anomaly.detected
      ? Math.max(
          0,
          1 -
          anomaly.score /
          100,
        )
      : 1;

  const gateFactor =
    gateScore /
    100;

  return clamp(
    confidenceFactor *
      scoreFactor *
      marketFactor *
      anomalyFactor *
      gateFactor *
      100,
  ) ?? 0;
}

export function evaluateRealtimeDecisionGate({
  signal = {},
  marketContext = {},
  anomaly = {},
  portfolio = {},

  minimumConfidence = 60,
  minimumScore = 60,
  maximumSignalRisk = 70,
  maximumPortfolioExposure = 80,
  maximumDailyLoss = 3,
  maximumOpenPositions = 10,
  maximumSymbolExposure = 25,
  minimumGateScore = 80,
} = {}) {
  const normalizedSignal =
    normalizeSignal(
      signal,
    );

  const normalizedMarket =
    normalizeMarketContext(
      marketContext,
    );

  const normalizedAnomaly =
    normalizeAnomaly(
      anomaly,
    );

  const normalizedPortfolio =
    normalizePortfolio(
      portfolio,
    );

  const checks =
    buildChecks({
      signal:
        normalizedSignal,

      market:
        normalizedMarket,

      anomaly:
        normalizedAnomaly,

      portfolio:
        normalizedPortfolio,

      minimumConfidence:
        clamp(
          minimumConfidence,
        ) ?? 60,

      minimumScore:
        clamp(
          minimumScore,
        ) ?? 60,

      maximumSignalRisk:
        clamp(
          maximumSignalRisk,
        ) ?? 70,

      maximumPortfolioExposure:
        clamp(
          maximumPortfolioExposure,
        ) ?? 80,

      maximumDailyLoss:
        Math.max(
          0,
          finiteOrNull(
            maximumDailyLoss,
          ) ?? 3,
        ),

      maximumOpenPositions:
        Math.max(
          1,
          Math.floor(
            finiteOrNull(
              maximumOpenPositions,
            ) ?? 10,
          ),
        ),

      maximumSymbolExposure:
        clamp(
          maximumSymbolExposure,
        ) ?? 25,
    });

  const gateScore =
    calculateGateScore(
      checks,
    );

  const decision =
    determineDecision({
      checks,

      gateScore,

      minimumGateScore:
        clamp(
          minimumGateScore,
        ) ?? 80,
    });

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

  const positionMultiplier =
    decision.tradable
      ? calculatePositionMultiplier({
          signal:
            normalizedSignal,

          market:
            normalizedMarket,

          anomaly:
            normalizedAnomaly,

          gateScore,
        })
      : 0;

  return {
    version:
      REALTIME_DECISION_GATE_V2_VERSION,

    ready:
      normalizedSignal.symbol
        .length > 0,

    decision:
      decision.decision,

    tradable:
      decision.tradable,

    reason:
      decision.reason,

    symbol:
      normalizedSignal.symbol,

    direction:
      normalizedSignal.direction,

    gateScore:
      round(
        gateScore,
        2,
      ),

    minimumGateScore:
      clamp(
        minimumGateScore,
      ) ?? 80,

    positionMultiplier:
      round(
        positionMultiplier,
        2,
      ),

    blockers,

    checks,

    signal:
      normalizedSignal,

    marketContext:
      normalizedMarket,

    anomaly:
      normalizedAnomaly,

    portfolio:
      normalizedPortfolio,

    executionPlan:
      decision.tradable
        ? {
            action:
              normalizedSignal.direction,

            allowed:
              true,

            sizeMultiplier:
              round(
                positionMultiplier /
                100,
                4,
              ),

            requireHumanConfirmation:
              true,

            reason:
              decision.reason,
          }
        : {
            action:
              "NONE",

            allowed:
              false,

            sizeMultiplier:
              0,

            requireHumanConfirmation:
              false,

            reason:
              decision.reason,
          },

    audit: {
      evaluatedAt:
        new Date().toISOString(),

      checkCount:
        checks.length,

      passedCheckCount:
        checks.filter(
          (
            check,
          ) =>
            check.passed,
        ).length,

      failedCheckCount:
        blockers.length,
    },
  };
}

export class RealtimeDecisionGateV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  evaluate(input = {}) {
    return evaluateRealtimeDecisionGate({
      ...this.config,

      ...input,
    });
  }
}

export const realtimeDecisionGateV2 =
  new RealtimeDecisionGateV2();

export default evaluateRealtimeDecisionGate;