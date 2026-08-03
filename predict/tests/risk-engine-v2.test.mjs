import test from "node:test";
import assert from "node:assert/strict";

import {
  RiskEngineV2,
  evaluatePortfolioRisk,
} from "../portfolio/risk-engine-v2.js";

function createSafeInput() {
  return {
    equity:
      100000,

    maximumPositionWeight:
      0.45,

    returns: [
      1,
      -0.5,
      0.8,
      1.2,
      -0.3,
      0.6,
    ],

    positions: [
      {
        symbol:
          "AAA",

        sector:
          "Technology",

        marketValue:
          25000,

        beta:
          1.1,

        liquidityScore:
          90,
      },

      {
        symbol:
          "BBB",

        sector:
          "Finance",

        marketValue:
          20000,

        beta:
          0.9,

        liquidityScore:
          85,
      },

      {
        symbol:
          "CCC",

        sector:
          "Utilities",

        marketValue:
          15000,

        beta:
          0.7,

        liquidityScore:
          80,
      },
    ],
  };
}

test(
  "Risk Engine v2 evaluates safe portfolio",
  () => {
    const result =
      evaluatePortfolioRisk(
        createSafeInput(),
      );

    assert.equal(
      result.version,
      "risk-engine-v2",
    );

    assert.equal(
      result.ready,
      true,
    );

    assert.equal(
      result.approved,
      true,
    );

    assert.equal(
      result.breaches.length,
      0,
    );

    assert.ok(
      result.riskScore < 65,
    );
  },
);

test(
  "Risk Engine v2 calculates VaR and CVaR",
  () => {
    const result =
      evaluatePortfolioRisk({
        ...createSafeInput(),

        returns: [
          2,
          -1,
          -4,
          1,
          -2,
          3,
          -6,
          1,
          2,
          -3,
        ],
      });

    assert.ok(
      Number.isFinite(
        result.returnRisk.valueAtRisk,
      ),
    );

    assert.ok(
      Number.isFinite(
        result.returnRisk.conditionalValueAtRisk,
      ),
    );

    assert.ok(
      result.returnRisk.conditionalValueAtRisk >=
      result.returnRisk.valueAtRisk,
    );
  },
);

test(
  "Risk Engine v2 detects leverage breach",
  () => {
    const result =
      evaluatePortfolioRisk({
        equity:
          100000,

        positions: [
          {
            symbol:
              "AAA",

            marketValue:
              200000,
          },
        ],

        maximumLeverage:
          1.5,
      });

    assert.equal(
      result.approved,
      false,
    );

    assert.ok(
      result.breaches.some(
        (
          breach,
        ) =>
          breach.code ===
          "LEVERAGE_LIMIT",
      ),
    );
  },
);

test(
  "Risk Engine v2 detects position concentration",
  () => {
    const result =
      evaluatePortfolioRisk({
        equity:
          100000,

        positions: [
          {
            symbol:
              "AAA",

            sector:
              "Technology",

            marketValue:
              80000,
          },

          {
            symbol:
              "BBB",

            sector:
              "Finance",

            marketValue:
              20000,
          },
        ],

        maximumPositionWeight:
          0.5,
      });

    assert.ok(
      result.breaches.some(
        (
          breach,
        ) =>
          breach.code ===
          "POSITION_CONCENTRATION",
      ),
    );
  },
);

test(
  "Risk Engine v2 detects sector concentration",
  () => {
    const result =
      evaluatePortfolioRisk({
        equity:
          100000,

        positions: [
          {
            symbol:
              "AAA",

            sector:
              "Technology",

            marketValue:
              40000,
          },

          {
            symbol:
              "BBB",

            sector:
              "Technology",

            marketValue:
              30000,
          },

          {
            symbol:
              "CCC",

            sector:
              "Finance",

            marketValue:
              30000,
          },
        ],

        maximumSectorWeight:
          0.6,
      });

    assert.ok(
      result.breaches.some(
        (
          breach,
        ) =>
          breach.code ===
          "SECTOR_CONCENTRATION",
      ),
    );
  },
);

test(
  "Risk Engine v2 detects liquidity risk",
  () => {
    const result =
      evaluatePortfolioRisk({
        equity:
          100000,

        positions: [
          {
            symbol:
              "AAA",

            marketValue:
              20000,

            liquidityScore:
              20,
          },
        ],

        minimumLiquidityScore:
          40,
      });

    assert.ok(
      result.breaches.some(
        (
          breach,
        ) =>
          breach.code ===
          "LIQUIDITY_LIMIT",
      ),
    );
  },
);

test(
  "Risk Engine v2 calculates portfolio beta",
  () => {
    const result =
      evaluatePortfolioRisk(
        createSafeInput(),
      );

    assert.ok(
      result.exposure.portfolioBeta >
      0,
    );

    assert.ok(
      result.exposure.portfolioBeta <
      1.2,
    );
  },
);

test(
  "Risk Engine v2 handles empty data",
  () => {
    const result =
      evaluatePortfolioRisk();

    assert.equal(
      result.ready,
      false,
    );

    assert.equal(
      result.exposure.gross,
      0,
    );

    assert.equal(
      result.returnRisk.valueAtRisk,
      null,
    );
  },
);

test(
  "Risk Engine v2 rejects invalid equity",
  () => {
    assert.throws(
      () =>
        evaluatePortfolioRisk({
          equity:
            0,
        }),

      /equity must be greater than zero/,
    );
  },
);

test(
  "Risk Engine v2 class is deterministic",
  () => {
    const engine =
      new RiskEngineV2({
        maximumLeverage:
          1.5,
      });

    const input =
      createSafeInput();

    assert.deepEqual(
      engine.evaluate(input),
      engine.evaluate(input),
    );
  },
);