import test from "node:test";
import assert from "node:assert/strict";

import {
  StrategyEngineV3,
  evaluateStrategy,
  rankStrategies,
} from "../analysis/strategy-engine-v3.js";

const NOW =
  "2026-08-04T17:00:00.000Z";

function bullishContext(
  overrides = {},
) {
  return {
    symbol:
      "7203.T",

    price:
      3000,

    regime:
      "BULL",

    riskScore:
      20,

    marketScore:
      80,

    liquidityScore:
      80,

    portfolioExposurePercent:
      20,

    drawdownPercent:
      2,

    volatilityPercent:
      15,

    currentPosition:
      0,

    signals: [
      {
        name:
          "RSI",

        score:
          80,

        confidence:
          85,

        weight:
          1,

        direction:
          "BULLISH",
      },
      {
        name:
          "MACD",

        score:
          75,

        confidence:
          80,

        weight:
          1,

        direction:
          "BULLISH",
      },
      {
        name:
          "TREND",

        score:
          85,

        confidence:
          90,

        weight:
          1.5,

        direction:
          "BULLISH",
      },
    ],

    ...overrides,
  };
}

test(
  "Produces buy decision for bullish context",
  () => {
    const result =
      evaluateStrategy({
        context:
          bullishContext(),

        timestamp:
          NOW,
      });

    assert.equal(
      result.action,
      "BUY",
    );

    assert.ok(
      result.finalScore >=
      65,
    );
  },
);

test(
  "Produces sell decision for bearish held position",
  () => {
    const result =
      evaluateStrategy({
        context:
          bullishContext({
            regime:
              "BEAR",

            marketScore:
              20,

            liquidityScore:
              60,

            riskScore:
              40,

            currentPosition:
              100,

            signals: [
              {
                name:
                  "RSI",

                score:
                  15,

                confidence:
                  90,

                weight:
                  1,

                direction:
                  "BEARISH",
              },
              {
                name:
                  "MACD",

                score:
                  20,

                confidence:
                  85,

                weight:
                  1,

                direction:
                  "BEARISH",
              },
            ],
          }),

        timestamp:
          NOW,
      });

    assert.equal(
      result.action,
      "SELL",
    );
  },
);

test(
  "Holds bearish signal without position",
  () => {
    const result =
      evaluateStrategy({
        context:
          bullishContext({
            regime:
              "BEAR",

            marketScore:
              20,

            riskScore:
              40,

            currentPosition:
              0,

            signals: [
              {
                name:
                  "MACD",

                score:
                  10,

                confidence:
                  90,

                direction:
                  "BEARISH",
              },
            ],
          }),

        timestamp:
          NOW,
      });

    assert.equal(
      result.action,
      "HOLD",
    );
  },
);

test(
  "Blocks excessive risk",
  () => {
    const result =
      evaluateStrategy({
        context:
          bullishContext({
            riskScore:
              90,
          }),

        timestamp:
          NOW,
      });

    assert.equal(
      result.action,
      "BLOCK",
    );

    assert.ok(
      result.blockers.includes(
        "RISK_SCORE_TOO_HIGH",
      ),
    );
  },
);

test(
  "Blocks excessive drawdown",
  () => {
    const result =
      evaluateStrategy({
        context:
          bullishContext({
            drawdownPercent:
              20,
          }),

        timestamp:
          NOW,
      });

    assert.ok(
      result.blockers.includes(
        "DRAWDOWN_LIMIT_REACHED",
      ),
    );
  },
);

test(
  "Blocks excessive exposure",
  () => {
    const result =
      evaluateStrategy({
        context:
          bullishContext({
            portfolioExposurePercent:
              95,
          }),

        timestamp:
          NOW,
      });

    assert.ok(
      result.blockers.includes(
        "PORTFOLIO_EXPOSURE_LIMIT_REACHED",
      ),
    );
  },
);

test(
  "Blocks insufficient liquidity",
  () => {
    const result =
      evaluateStrategy({
        context:
          bullishContext({
            liquidityScore:
              10,
          }),

        timestamp:
          NOW,
      });

    assert.ok(
      result.blockers.includes(
        "INSUFFICIENT_LIQUIDITY",
      ),
    );
  },
);

test(
  "Warns for low signal confidence",
  () => {
    const result =
      evaluateStrategy({
        context:
          bullishContext({
            signals: [
              {
                name:
                  "RSI",

                score:
                  70,

                confidence:
                  20,

                direction:
                  "BULLISH",
              },
            ],
          }),

        timestamp:
          NOW,
      });

    assert.ok(
      result.warnings.includes(
        "LOW_SIGNAL_CONFIDENCE",
      ),
    );
  },
);

test(
  "Warns in high volatility regime",
  () => {
    const result =
      evaluateStrategy({
        context:
          bullishContext({
            regime:
              "HIGH_VOLATILITY",
          }),

        timestamp:
          NOW,
      });

    assert.ok(
      result.warnings.includes(
        "HIGH_VOLATILITY_REGIME",
      ),
    );
  },
);

test(
  "Ranks strongest strategy first",
  () => {
    const ranked =
      rankStrategies({
        candidates: [
          bullishContext({
            symbol:
              "WEAK",

            marketScore:
              45,
          }),

          bullishContext({
            symbol:
              "STRONG",

            marketScore:
              90,
          }),
        ],

        timestamp:
          NOW,
      });

    assert.equal(
      ranked[0].symbol,
      "STRONG",
    );
  },
);

test(
  "Engine stores history",
  () => {
    const engine =
      new StrategyEngineV3();

    engine.evaluate({
      context:
        bullishContext(),

      timestamp:
        NOW,
    });

    assert.equal(
      engine.getHistory().length,
      1,
    );

    assert.ok(
      engine.latest(),
    );
  },
);

test(
  "Disabled engine blocks strategy",
  () => {
    const engine =
      new StrategyEngineV3();

    engine.disable();

    const result =
      engine.evaluate({
        context:
          bullishContext(),

      timestamp:
        NOW,
    });

    assert.equal(
      result.action,
      "BLOCK",
    );

    assert.ok(
      result.blockers.includes(
        "STRATEGY_ENGINE_DISABLED",
      ),
    );
  },
);

test(
  "Engine can be re-enabled",
  () => {
    const engine =
      new StrategyEngineV3();

    engine.disable();
    engine.enable();

    assert.equal(
      engine.getState()
        .enabled,
      true,
    );
  },
);

test(
  "Snapshot restore is deterministic",
  () => {
    const original =
      new StrategyEngineV3();

    original.evaluate({
      context:
        bullishContext(),

      timestamp:
        NOW,
    });

    const snapshot =
      original.snapshot();

    const restored =
      new StrategyEngineV3();

    restored.restore(
      snapshot,
    );

    assert.deepEqual(
      restored.snapshot(),
      snapshot,
    );
  },
);

test(
  "Reset clears history",
  () => {
    const engine =
      new StrategyEngineV3();

    engine.evaluate({
      context:
        bullishContext(),

      timestamp:
        NOW,
    });

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
        evaluateStrategy({
          context:
            bullishContext(),

          timestamp:
            "invalid-date",
        }),

      /timestamp is invalid/,
    );
  },
);