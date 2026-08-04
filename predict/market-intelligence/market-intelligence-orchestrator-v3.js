import {
  detectMarketRegime,
} from "./market-regime-intelligence-v3.js";

import {
  analyzeCrossMarketNetwork,
} from "./cross-market-correlation-v3.js";

import {
  analyzeMarketBreadth,
} from "./market-breadth-v3.js";

import {
  analyzeSectorRotation,
} from "./sector-rotation-v3.js";

import {
  buildAIConsensus,
} from "./ai-consensus-engine-v3.js";

import {
  evaluateMacroRisk,
} from "./macro-risk-engine-v3.js";

import {
  evaluateGlobalLiquidity,
} from "./global-liquidity-engine-v3.js";

export const MARKET_INTELLIGENCE_ORCHESTRATOR_V3_VERSION =
  "market-intelligence-orchestrator-v3";

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
      "Market intelligence timestamp is invalid.",
    );
  }

  return new Date(
    milliseconds,
  ).toISOString();
}

function regimeToSignal(
  result,
) {
  const mapping = {
    STRONG_BULL: {
      direction: "BUY",
      score: 85,
    },

    BULL: {
      direction: "BUY",
      score: 55,
    },

    RANGE: {
      direction: "HOLD",
      score: 0,
    },

    BEAR: {
      direction: "SELL",
      score: -55,
    },

    STRONG_BEAR: {
      direction: "SELL",
      score: -85,
    },

    HIGH_VOLATILITY: {
      direction: "WAIT",
      score: -15,
    },

    CRASH: {
      direction: "SELL",
      score: -100,
    },

    INSUFFICIENT_DATA: {
      direction: "WAIT",
      score: 0,
    },
  };

  const selected =
    mapping[result.regime] ??
    mapping.INSUFFICIENT_DATA;

  return {
    id:
      "market-regime",

    direction:
      selected.direction,

    score:
      selected.score,

    confidence:
      finiteNumber(
        result.confidence,
        0,
      ),

    reliability:
      80,

    risk:
      finiteNumber(
        result.scores?.risk,
        50,
      ),

    weight:
      1.2,

    veto:
      result.regime ===
        "CRASH",

    reason:
      result.regime,
  };
}

function breadthToSignal(
  result,
) {
  let direction =
    "HOLD";

  if (
    [
      "STRONG",
      "VERY_STRONG",
      "POSITIVE",
    ].includes(
      result.classification,
    )
  ) {
    direction =
      "BUY";
  }

  if (
    [
      "NEGATIVE",
      "WEAK",
      "CAPITULATION",
    ].includes(
      result.classification,
    )
  ) {
    direction =
      "SELL";
  }

  if (
    result.status !==
    "READY"
  ) {
    direction =
      "WAIT";
  }

  return {
    id:
      "market-breadth",

    direction,

    score:
      clamp(
        finiteNumber(
          result.score,
          0,
        ),
        -100,
        100,
      ),

    confidence:
      finiteNumber(
        result.confidence,
        0,
      ),

    reliability:
      75,

    risk:
      result.divergence
        ?.type ===
        "BEARISH_DIVERGENCE"
          ? 75
          : 35,

    weight:
      1,

    veto:
      false,

    reason:
      result.classification,
  };
}

function sectorToSignal(
  result,
) {
  if (
    result.status !==
    "READY"
  ) {
    return {
      id:
        "sector-rotation",

      direction:
        "WAIT",

      score:
        0,

      confidence:
        0,

      reliability:
        70,

      risk:
        50,

      weight:
        0.8,
    };
  }

  const direction =
    result.rotation
      ?.direction ===
    "RISK_ON"
      ? "BUY"
      : result.rotation
            ?.direction ===
          "RISK_OFF"
        ? "SELL"
        : "HOLD";

  const sign =
    direction === "BUY"
      ? 1
      : direction === "SELL"
        ? -1
        : 0;

  return {
    id:
      "sector-rotation",

    direction,

    score:
      sign *
      finiteNumber(
        result.rotation
          ?.strength,
        0,
      ),

    confidence:
      clamp(
        50 +
        finiteNumber(
          result.rotation
            ?.strength,
          0,
        ) /
        2,
        0,
        100,
      ),

    reliability:
      72,

    risk:
      35,

    weight:
      0.8,

    veto:
      false,

    reason:
      result.rotation
        ?.direction ??
      "UNKNOWN",
  };
}

function macroToSignal(
  result,
) {
  const buy =
    [
      "VERY_LOW",
      "LOW",
    ].includes(
      result.level,
    );

  const sell =
    [
      "HIGH",
      "CRITICAL",
    ].includes(
      result.level,
    );

  return {
    id:
      "macro-risk",

    direction:
      result.status ===
      "BLOCKED"
        ? "SELL"
        : buy
          ? "BUY"
          : sell
            ? "SELL"
            : "HOLD",

    score:
      clamp(
        50 -
        finiteNumber(
          result.score,
          50,
        ),
        -100,
        100,
      ) *
      1.5,

    confidence:
      finiteNumber(
        result.confidence,
        50,
      ),

    reliability:
      85,

    risk:
      finiteNumber(
        result.score,
        50,
      ),

    weight:
      1.25,

    veto:
      result.status ===
      "BLOCKED",

    reason:
      result.level,
  };
}

function liquidityToSignal(
  result,
) {
  const expansionary =
    [
      "EXPANSIONARY",
      "STRONGLY_EXPANSIONARY",
    ].includes(
      result.regime,
    );

  const contractionary =
    [
      "CONTRACTIONARY",
      "SEVERELY_CONTRACTIONARY",
    ].includes(
      result.regime,
    );

  return {
    id:
      "global-liquidity",

    direction:
      result.status ===
      "BLOCKED"
        ? "SELL"
        : expansionary
          ? "BUY"
          : contractionary
            ? "SELL"
            : "HOLD",

    score:
      clamp(
        finiteNumber(
          result.score,
          0,
        ),
        -100,
        100,
      ),

    confidence:
      finiteNumber(
        result.confidence,
        50,
      ),

    reliability:
      82,

    risk:
      result.status ===
      "BLOCKED"
        ? 95
        : clamp(
            50 -
            finiteNumber(
              result.score,
              0,
            ) /
            2,
            0,
            100,
          ),

    weight:
      1.15,

    veto:
      result.status ===
      "BLOCKED",

    reason:
      result.regime,
  };
}

function finalAction({
  consensus,
  macroRisk,
  liquidity,
}) {
  const blockers = [
    ...(consensus.blockers ?? []),
    ...(macroRisk.blockers ?? []),
    ...(liquidity.blockers ?? []),
  ];

  if (
    macroRisk.status ===
      "BLOCKED" ||
    liquidity.status ===
      "BLOCKED"
  ) {
    return {
      decision:
        "BLOCK",

      positionMultiplier:
        0,

      blockers: [
        ...new Set(
          blockers,
        ),
      ],
    };
  }

  const macroMultiplier =
    finiteNumber(
      macroRisk.action
        ?.positionMultiplier,
      0.5,
    );

  const liquidityMultiplier =
    finiteNumber(
      liquidity.action
        ?.positionMultiplier,
      0.5,
    );

  const consensusMultiplier =
    consensus.decision ===
      "BUY"
      ? 1
      : consensus.decision ===
          "SELL"
        ? 0.2
        : 0.5;

  return {
    decision:
      consensus.decision,

    positionMultiplier:
      round(
        clamp(
          Math.min(
            macroMultiplier,
            liquidityMultiplier,
            consensusMultiplier,
          ),
          0,
          1,
        ),
      ),

    blockers: [
      ...new Set(
        blockers,
      ),
    ],
  };
}

export function runMarketIntelligence({
  timestamp =
    new Date().toISOString(),
  regimeInput = {},
  correlationMarkets = [],
  breadthStocks = [],
  indexChangePercent = 0,
  sectors = [],
  macroInput = {},
  liquidityInput = {},
  externalSignals = [],
} = {}) {
  const evaluatedAt =
    normalizeTimestamp(
      timestamp,
    );

  const regime =
    detectMarketRegime({
      input: {
        ...regimeInput,
        timestamp:
          evaluatedAt,
      },
    });

  const correlation =
    analyzeCrossMarketNetwork({
      markets:
        correlationMarkets,
    });

  const breadth =
    analyzeMarketBreadth({
      stocks:
        breadthStocks,

      indexChangePercent,

      timestamp:
        evaluatedAt,

      minimumSampleSize:
        breadthStocks.length === 0
          ? 1
          : Math.min(
              5,
              breadthStocks.length,
            ),
    });

  const sectorRotation =
    analyzeSectorRotation({
      sectors,

      timestamp:
        evaluatedAt,

      minimumSectorCount:
        sectors.length === 0
          ? 1
          : Math.min(
              3,
              sectors.length,
            ),
    });

  const macroRisk =
    evaluateMacroRisk({
      input:
        macroInput,

      timestamp:
        evaluatedAt,
    });

  const liquidity =
    evaluateGlobalLiquidity({
      input:
        liquidityInput,

      timestamp:
        evaluatedAt,
    });

  const internalSignals = [
    regimeToSignal(
      regime,
    ),

    breadthToSignal(
      breadth,
    ),

    sectorToSignal(
      sectorRotation,
    ),

    macroToSignal(
      macroRisk,
    ),

    liquidityToSignal(
      liquidity,
    ),
  ];

  const consensus =
    buildAIConsensus({
      signals: [
        ...internalSignals,
        ...externalSignals,
      ],

      timestamp:
        evaluatedAt,

      minimumSignals:
        3,

      minimumConfidence:
        45,

      minimumAgreement:
        35,
    });

  const action =
    finalAction({
      consensus,
      macroRisk,
      liquidity,
    });

  const confidence =
    round(
      clamp(
        finiteNumber(
          consensus.confidence,
          0,
        ) *
          0.5 +
        finiteNumber(
          regime.confidence,
          0,
        ) *
          0.15 +
        finiteNumber(
          breadth.confidence,
          0,
        ) *
          0.1 +
        finiteNumber(
          macroRisk.confidence,
          0,
        ) *
          0.125 +
        finiteNumber(
          liquidity.confidence,
          0,
        ) *
          0.125,
        0,
        100,
      ),
    );

  return {
    version:
      MARKET_INTELLIGENCE_ORCHESTRATOR_V3_VERSION,

    evaluatedAt,

    status:
      action.decision ===
      "BLOCK"
        ? "BLOCKED"
        : consensus.status,

    decision:
      action.decision,

    confidence,

    positionMultiplier:
      action.positionMultiplier,

    blockers:
      action.blockers,

    consensus,

    modules: {
      regime,
      correlation,
      breadth,
      sectorRotation,
      macroRisk,
      liquidity,
    },

    summary: {
      regime:
        regime.regime,

      breadth:
        breadth.classification,

      sectorLeader:
        sectorRotation.rotation
          ?.leadingSector ??
        null,

      macroRisk:
        macroRisk.level,

      liquidity:
        liquidity.regime,

      consensusDecision:
        consensus.decision,

      consensusScore:
        consensus.consensusScore,
    },
  };
}

export class MarketIntelligenceOrchestratorV3 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };

    this.history = [];
  }

  run(input = {}) {
    const result =
      runMarketIntelligence({
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

export const marketIntelligenceOrchestratorV3 =
  new MarketIntelligenceOrchestratorV3();

export default runMarketIntelligence;