export const AI_CONSENSUS_ENGINE_V3_VERSION =
  "ai-consensus-engine-v3";

const DIRECTIONS =
  new Set([
    "BUY",
    "SELL",
    "HOLD",
    "WAIT",
  ]);

function clone(value) {
  return value === undefined
    ? undefined
    : structuredClone(value);
}

function finiteNumber(
  value,
  fallback = 0,
) {
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
  digits = 2,
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

function normalizeTimestamp(value) {
  const milliseconds =
    typeof value === "number"
      ? value
      : Date.parse(
          value ??
          new Date().toISOString(),
        );

  if (!Number.isFinite(milliseconds)) {
    throw new TypeError(
      "AI consensus timestamp is invalid.",
    );
  }

  return new Date(
    milliseconds,
  ).toISOString();
}

function normalizeDirection(value) {
  const direction =
    String(
      value ??
      "HOLD",
    )
      .trim()
      .toUpperCase();

  return DIRECTIONS.has(
    direction,
  )
    ? direction
    : "HOLD";
}

function directionValue(direction) {
  if (direction === "BUY") {
    return 1;
  }

  if (direction === "SELL") {
    return -1;
  }

  return 0;
}

function normalizeSignal(
  signal = {},
  index = 0,
) {
  const direction =
    normalizeDirection(
      signal.direction ??
      signal.signal ??
      signal.decision,
    );

  return {
    id:
      String(
        signal.id ??
        signal.name ??
        `MODEL_${index + 1}`,
      ).trim() ||
      `MODEL_${index + 1}`,

    direction,

    confidence:
      clamp(
        finiteNumber(
          signal.confidence,
          50,
        ),
        0,
        100,
      ),

    weight:
      Math.max(
        0,
        finiteNumber(
          signal.weight,
          1,
        ),
      ),

    reliability:
      clamp(
        finiteNumber(
          signal.reliability,
          50,
        ),
        0,
        100,
      ),

    risk:
      clamp(
        finiteNumber(
          signal.risk,
          50,
        ),
        0,
        100,
      ),

    veto:
      signal.veto ===
      true,

    reason:
      String(
        signal.reason ??
        "",
      ).trim(),

    score:
      clamp(
        finiteNumber(
          signal.score,
          directionValue(
            direction,
          ) *
            finiteNumber(
              signal.confidence,
              50,
            ),
        ),
        -100,
        100,
      ),
  };
}

function effectiveWeight(signal) {
  const confidenceFactor =
    signal.confidence /
    100;

  const reliabilityFactor =
    signal.reliability /
    100;

  const riskFactor =
    1 -
    signal.risk /
    150;

  return Math.max(
    0,
    signal.weight *
      confidenceFactor *
      reliabilityFactor *
      riskFactor,
  );
}

function calculateEntropy(
  buyWeight,
  sellWeight,
  neutralWeight,
) {
  const total =
    buyWeight +
    sellWeight +
    neutralWeight;

  if (total <= 0) {
    return 1;
  }

  const probabilities = [
    buyWeight / total,
    sellWeight / total,
    neutralWeight / total,
  ];

  let entropy = 0;

  for (
    const probability of
    probabilities
  ) {
    if (probability > 0) {
      entropy -=
        probability *
        Math.log2(
          probability,
        );
    }
  }

  return round(
    entropy /
      Math.log2(3),
    4,
  );
}

function classifyAgreement(
  agreement,
) {
  if (agreement >= 80) {
    return "VERY_HIGH";
  }

  if (agreement >= 65) {
    return "HIGH";
  }

  if (agreement >= 50) {
    return "MODERATE";
  }

  if (agreement >= 35) {
    return "LOW";
  }

  return "VERY_LOW";
}

export function buildAIConsensus({
  signals = [],
  timestamp =
    new Date().toISOString(),
  minimumSignals = 2,
  minimumConfidence = 55,
  minimumAgreement = 50,
  buyThreshold = 20,
  sellThreshold = -20,
  allowVeto = true,
} = {}) {
  const evaluatedAt =
    normalizeTimestamp(
      timestamp,
    );

  const normalized =
    signals.map(
      normalizeSignal,
    );

  if (
    normalized.length <
    minimumSignals
  ) {
    return {
      version:
        AI_CONSENSUS_ENGINE_V3_VERSION,

      evaluatedAt,

      status:
        "INSUFFICIENT_DATA",

      decision:
        "WAIT",

      confidence:
        0,

      agreement:
        0,

      agreementLevel:
        "VERY_LOW",

      consensusScore:
        0,

      signals:
        normalized,

      blockers: [
        "INSUFFICIENT_SIGNALS",
      ],

      summary: {
        totalSignals:
          normalized.length,

        buySignals:
          0,

        sellSignals:
          0,

        neutralSignals:
          normalized.length,
      },
    };
  }

  let buyWeight = 0;
  let sellWeight = 0;
  let neutralWeight = 0;
  let weightedScore = 0;
  let totalWeight = 0;

  const contributions = [];

  for (
    const signal of normalized
  ) {
    const weight =
      effectiveWeight(
        signal,
      );

    const contribution =
      signal.score *
      weight;

    weightedScore +=
      contribution;

    totalWeight +=
      weight;

    if (
      signal.direction ===
      "BUY"
    ) {
      buyWeight +=
        weight;
    }
    else if (
      signal.direction ===
      "SELL"
    ) {
      sellWeight +=
        weight;
    }
    else {
      neutralWeight +=
        weight;
    }

    contributions.push({
      id:
        signal.id,

      direction:
        signal.direction,

      effectiveWeight:
        round(
          weight,
          4,
        ),

      contribution:
        round(
          contribution,
          4,
        ),
    });
  }

  const consensusScore =
    totalWeight === 0
      ? 0
      : clamp(
          weightedScore /
          totalWeight,
          -100,
          100,
        );

  const directionalTotal =
    buyWeight +
    sellWeight +
    neutralWeight;

  const dominantWeight =
    Math.max(
      buyWeight,
      sellWeight,
      neutralWeight,
    );

  const agreement =
    directionalTotal === 0
      ? 0
      : clamp(
          dominantWeight /
            directionalTotal *
            100,
          0,
          100,
        );

  const entropy =
    calculateEntropy(
      buyWeight,
      sellWeight,
      neutralWeight,
    );

  const averageConfidence =
    normalized.reduce(
      (
        total,
        signal,
      ) =>
        total +
        signal.confidence,
      0,
    ) /
    normalized.length;

  const averageReliability =
    normalized.reduce(
      (
        total,
        signal,
      ) =>
        total +
        signal.reliability,
      0,
    ) /
    normalized.length;

  const averageRisk =
    normalized.reduce(
      (
        total,
        signal,
      ) =>
        total +
        signal.risk,
      0,
    ) /
    normalized.length;

  const confidence =
    clamp(
      averageConfidence *
        0.35 +
      averageReliability *
        0.3 +
      agreement *
        0.25 +
      (
        100 -
        averageRisk
      ) *
        0.1 -
      entropy *
        15,
      0,
      100,
    );

  const buySignals =
    normalized.filter(
      (
        signal,
      ) =>
        signal.direction ===
        "BUY",
    );

  const sellSignals =
    normalized.filter(
      (
        signal,
      ) =>
        signal.direction ===
        "SELL",
    );

  const neutralSignals =
    normalized.filter(
      (
        signal,
      ) =>
        [
          "HOLD",
          "WAIT",
        ].includes(
          signal.direction,
        ),
    );

  const buyVeto =
    normalized.some(
      (
        signal,
      ) =>
        signal.veto &&
        signal.direction ===
          "SELL",
    );

  const sellVeto =
    normalized.some(
      (
        signal,
      ) =>
        signal.veto &&
        signal.direction ===
          "BUY",
    );

  const blockers = [];

  if (
    confidence <
    minimumConfidence
  ) {
    blockers.push(
      "LOW_CONFIDENCE",
    );
  }

  if (
    agreement <
    minimumAgreement
  ) {
    blockers.push(
      "LOW_AGREEMENT",
    );
  }

  if (
    averageRisk >= 80
  ) {
    blockers.push(
      "EXCESSIVE_RISK",
    );
  }

  let decision =
    "HOLD";

  if (
    consensusScore >=
    buyThreshold
  ) {
    decision =
      "BUY";
  }
  else if (
    consensusScore <=
    sellThreshold
  ) {
    decision =
      "SELL";
  }

  if (
    allowVeto &&
    decision === "BUY" &&
    buyVeto
  ) {
    blockers.push(
      "SELL_VETO",
    );

    decision =
      "WAIT";
  }

  if (
    allowVeto &&
    decision === "SELL" &&
    sellVeto
  ) {
    blockers.push(
      "BUY_VETO",
    );

    decision =
      "WAIT";
  }

  if (
    blockers.includes(
      "LOW_CONFIDENCE",
    ) ||
    blockers.includes(
      "LOW_AGREEMENT",
    ) ||
    blockers.includes(
      "EXCESSIVE_RISK",
    )
  ) {
    decision =
      "WAIT";
  }

  const status =
    blockers.length === 0
      ? "READY"
      : "BLOCKED";

  const strongestSupport =
    [...contributions]
      .sort(
        (
          left,
          right,
        ) =>
          Math.abs(
            right.contribution,
          ) -
          Math.abs(
            left.contribution,
          ),
      )
      .slice(
        0,
        5,
      );

  return {
    version:
      AI_CONSENSUS_ENGINE_V3_VERSION,

    evaluatedAt,

    status,

    decision,

    confidence:
      round(
        confidence,
      ),

    agreement:
      round(
        agreement,
      ),

    agreementLevel:
      classifyAgreement(
        agreement,
      ),

    entropy,

    consensusScore:
      round(
        consensusScore,
      ),

    averageRisk:
      round(
        averageRisk,
      ),

    signals:
      normalized,

    contributions,

    strongestSupport,

    blockers: [
      ...new Set(
        blockers,
      ),
    ],

    summary: {
      totalSignals:
        normalized.length,

      buySignals:
        buySignals.length,

      sellSignals:
        sellSignals.length,

      neutralSignals:
        neutralSignals.length,

      buyWeight:
        round(
          buyWeight,
          4,
        ),

      sellWeight:
        round(
          sellWeight,
          4,
        ),

      neutralWeight:
        round(
          neutralWeight,
          4,
        ),
    },
  };
}

export function compareConsensus({
  previous,
  current,
} = {}) {
  if (
    !previous ||
    !current
  ) {
    return {
      changed:
        false,

      decisionChanged:
        false,

      confidenceChange:
        0,

      scoreChange:
        0,
    };
  }

  const confidenceChange =
    finiteNumber(
      current.confidence,
      0,
    ) -
    finiteNumber(
      previous.confidence,
      0,
    );

  const scoreChange =
    finiteNumber(
      current.consensusScore,
      0,
    ) -
    finiteNumber(
      previous.consensusScore,
      0,
    );

  return {
    changed:
      previous.decision !==
        current.decision ||
      Math.abs(
        confidenceChange,
      ) >= 5 ||
      Math.abs(
        scoreChange,
      ) >= 10,

    decisionChanged:
      previous.decision !==
      current.decision,

    previousDecision:
      previous.decision,

    currentDecision:
      current.decision,

    confidenceChange:
      round(
        confidenceChange,
      ),

    scoreChange:
      round(
        scoreChange,
      ),
  };
}

export class AIConsensusEngineV3 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };

    this.history = [];
  }

  evaluate(input = {}) {
    const result =
      buildAIConsensus({
        ...this.config,
        ...input,
      });

    this.history.push(
      clone(result),
    );

    return clone(result);
  }

  compareLatest() {
    if (
      this.history.length <
      2
    ) {
      return compareConsensus({
        previous:
          null,

        current:
          this.history.at(-1) ??
          null,
      });
    }

    return compareConsensus({
      previous:
        this.history.at(-2),

      current:
        this.history.at(-1),
    });
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

export const aiConsensusEngineV3 =
  new AIConsensusEngineV3();

export default buildAIConsensus;