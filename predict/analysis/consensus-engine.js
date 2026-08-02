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

function round(value, digits = 2) {
  const factor = 10 ** digits;

  return (
    Math.round(
      finiteNumber(value) * factor,
    ) / factor
  );
}

function normalizeAction(action = "HOLD") {
  const normalized =
    String(action)
      .trim()
      .toUpperCase();

  const aliases = {
    STRONG_BUY: "STRONG BUY",
    STRONGBUY: "STRONG BUY",
    BUY: "BUY",
    WATCH: "WATCH",
    HOLD: "HOLD",
    NEUTRAL: "HOLD",
    REDUCE: "REDUCE",
    SELL: "SELL",
    STRONG_SELL: "SELL",
  };

  return (
    aliases[
      normalized.replace(
        /\s+/g,
        "_",
      )
    ] ??
    aliases[normalized] ??
    "HOLD"
  );
}

function actionScore(action = "HOLD") {
  const scores = {
    "STRONG BUY": 100,
    BUY: 80,
    WATCH: 60,
    HOLD: 50,
    REDUCE: 30,
    SELL: 10,
  };

  return scores[
    normalizeAction(action)
  ] ?? 50;
}

function scoreAction(score = 50) {
  const safeScore =
    clamp(score);

  if (safeScore >= 85) {
    return "STRONG BUY";
  }

  if (safeScore >= 68) {
    return "BUY";
  }

  if (safeScore >= 56) {
    return "WATCH";
  }

  if (safeScore >= 42) {
    return "HOLD";
  }

  if (safeScore >= 25) {
    return "REDUCE";
  }

  return "SELL";
}

function extractEngineDecision(engine = {}) {
  const result =
    engine.result ??
    engine;

  const action =
    normalizeAction(
      result.action ??
      result.recommendation?.action ??
      result.dashboard?.action ??
      "HOLD",
    );

  const score =
    clamp(
      result.score ??
      result.totalScore ??
      result.recommendation?.score ??
      result.dashboard?.score ??
      actionScore(action),
    );

  const confidence =
    clamp(
      result.confidence ??
      result.recommendation?.confidence ??
      result.dashboard?.confidence ??
      50,
    );

  const weight =
    Math.max(
      0,
      finiteNumber(
        engine.weight ??
        result.weight,
        1,
      ),
    );

  return {
    name:
      String(
        engine.name ??
        result.name ??
        "unknown",
      ),

    action,

    score,

    confidence,

    weight,
  };
}

export function buildConsensus({
  engines = [],
  minimumEngines = 1,
} = {}) {
  const normalized =
    engines.map(
      extractEngineDecision,
    );

  if (
    normalized.length <
    Math.max(
      1,
      Math.floor(
        finiteNumber(
          minimumEngines,
          1,
        ),
      ),
    )
  ) {
    return {
      ready: false,

      action: "HOLD",

      score: 50,

      confidence: 0,

      agreementRate: 0,

      engineCount:
        normalized.length,

      engines:
        normalized,

      reason:
        "insufficient_engines",
    };
  }

  const totalWeight =
    normalized.reduce(
      (sum, engine) =>
        sum +
        engine.weight,
      0,
    ) || normalized.length;

  const weightedScore =
    normalized.reduce(
      (sum, engine) =>
        sum +
        engine.score *
        (
          engine.weight || 1
        ),
      0,
    ) / totalWeight;

  const weightedConfidence =
    normalized.reduce(
      (sum, engine) =>
        sum +
        engine.confidence *
        (
          engine.weight || 1
        ),
      0,
    ) / totalWeight;

  const action =
    scoreAction(
      weightedScore,
    );

  const matchingCount =
    normalized.filter(
      (engine) =>
        engine.action === action,
    ).length;

  const nearMatchingCount =
    normalized.filter(
      (engine) =>
        Math.abs(
          engine.score -
          weightedScore,
        ) <= 15,
    ).length;

  const agreementRate =
    round(
      (
        Math.max(
          matchingCount,
          nearMatchingCount,
        ) /
        normalized.length
      ) * 100,
      2,
    );

  const confidence =
    round(
      clamp(
        weightedConfidence * 0.7 +
        agreementRate * 0.3,
      ),
      2,
    );

  return {
    ready: true,

    action,

    score:
      round(
        weightedScore,
        2,
      ),

    confidence,

    agreementRate,

    engineCount:
      normalized.length,

    engines:
      normalized,

    reason:
      agreementRate >= 70
        ? "strong_consensus"
        : agreementRate >= 45
          ? "moderate_consensus"
          : "weak_consensus",
  };
}

export function buildConsensusReport({
  symbol = null,
  engines = [],
  minimumEngines = 1,
} = {}) {
  const consensus =
    buildConsensus({
      engines,
      minimumEngines,
    });

  return {
    version:
      "consensus-engine-v1",

    generatedAt:
      new Date().toISOString(),

    symbol,

    consensus,

    summary:
      consensus.ready
        ? `${consensus.action}・総合${consensus.score}点・合意率${consensus.agreementRate}%`
        : "分析エンジン数が不足しています。",
  };
}

export const ConsensusEngineInternals = {
  actionScore,
  extractEngineDecision,
  normalizeAction,
  scoreAction,
};