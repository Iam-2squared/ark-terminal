import test from "node:test";
import assert from "node:assert/strict";

import {
  MacroRiskEngineV3,
  compareMacroRisk,
  evaluateMacroRisk,
} from "../market-intelligence/macro-risk-engine-v3.js";

const NOW =
  "2026-08-04T08:00:00.000Z";

function healthyMacro() {
  return {
    growthScore:
      75,

    inflationScore:
      25,

    policyTightness:
      30,

    liquidityScore:
      75,

    creditStress:
      15,

    volatilityIndex:
      14,

    yieldCurveSpread:
      1.2,

    currencyStress:
      15,

    commodityShock:
      15,

    geopoliticalRisk:
      20,

    earningsRevision:
      70,

    marketBreadth:
      75,

    regime:
      "BULL",
  };
}

function stressedMacro() {
  return {
    growthScore:
      15,

    inflationScore:
      90,

    policyTightness:
      90,

    liquidityScore:
      10,

    creditStress:
      95,

    volatilityIndex:
      55,

    yieldCurveSpread:
      -1.5,

    currencyStress:
      85,

    commodityShock:
      90,

    geopoliticalRisk:
      95,

    earningsRevision:
      15,

    marketBreadth:
      10,

    regime:
      "CRASH",
  };
}

test(
  "Evaluates low macro risk",
  () => {
    const result =
      evaluateMacroRisk({
        input:
          healthyMacro(),

        timestamp:
          NOW,
      });

    assert.equal(
      result.status,
      "READY",
    );

    assert.ok(
      [
        "VERY_LOW",
        "LOW",
      ].includes(
        result.level,
      ),
    );

    assert.ok(
      result.action
        .positionMultiplier >=
      0.85,
    );
  },
);

test(
  "Evaluates critical macro risk",
  () => {
    const result =
      evaluateMacroRisk({
        input:
          stressedMacro(),

        timestamp:
          NOW,
      });

    assert.equal(
      result.level,
      "CRITICAL",
    );

    assert.equal(
      result.status,
      "BLOCKED",
    );

    assert.equal(
      result.action.newTrades,
      "BLOCK",
    );

    assert.equal(
      result.action
        .positionMultiplier,
      0,
    );
  },
);

test(
  "Detects credit stress blocker",
  () => {
    const result =
      evaluateMacroRisk({
        input:
          stressedMacro(),

        timestamp:
          NOW,
      });

    assert.ok(
      result.blockers.includes(
        "SYSTEMIC_CREDIT_STRESS",
      ),
    );
  },
);

test(
  "Detects extreme volatility blocker",
  () => {
    const result =
      evaluateMacroRisk({
        input:
          stressedMacro(),

        timestamp:
          NOW,
      });

    assert.ok(
      result.blockers.includes(
        "EXTREME_MARKET_VOLATILITY",
      ),
    );
  },
);

test(
  "Detects inverted yield curve",
  () => {
    const result =
      evaluateMacroRisk({
        input: {
          ...healthyMacro(),

          yieldCurveSpread:
            -1,
        },

        timestamp:
          NOW,
      });

    assert.ok(
      result.reasons.includes(
        "INVERTED_YIELD_CURVE",
      ),
    );
  },
);

test(
  "Compares worsening macro risk",
  () => {
    const previous =
      evaluateMacroRisk({
        input:
          healthyMacro(),

        timestamp:
          NOW,
      });

    const current =
      evaluateMacroRisk({
        input:
          stressedMacro(),

        timestamp:
          "2026-08-05T08:00:00.000Z",
      });

    const comparison =
      compareMacroRisk({
        previous,
        current,
      });

    assert.equal(
      comparison.changed,
      true,
    );

    assert.equal(
      comparison.trend,
      "DETERIORATING",
    );

    assert.ok(
      comparison.scoreChange >
      0,
    );
  },
);

test(
  "Macro risk class stores history",
  () => {
    const engine =
      new MacroRiskEngineV3();

    engine.evaluate({
      input:
        healthyMacro(),

      timestamp:
        NOW,
    });

    engine.evaluate({
      input:
        stressedMacro(),

      timestamp:
        "2026-08-05T08:00:00.000Z",
    });

    assert.equal(
      engine.getHistory().length,
      2,
    );

    assert.equal(
      engine.compareLatest().trend,
      "DETERIORATING",
    );

    engine.reset();

    assert.equal(
      engine.getHistory().length,
      0,
    );
  },
);

test(
  "Validates timestamp",
  () => {
    assert.throws(
      () =>
        evaluateMacroRisk({
          input:
            healthyMacro(),

          timestamp:
            "invalid-date",
        }),

      /timestamp is invalid/,
    );
  },
);