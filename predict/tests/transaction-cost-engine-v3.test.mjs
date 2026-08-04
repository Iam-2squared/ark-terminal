import test from "node:test";
import assert from "node:assert/strict";

import {
  TransactionCostEngineV3,
  compareTransactionCosts,
  estimateTransactionCost,
} from "../paper/transaction-cost-engine-v3.js";

const NOW =
  "2026-08-04T15:00:00.000Z";

function trade(
  overrides = {},
) {
  return {
    symbol:
      "7203.T",

    side:
      "BUY",

    market:
      "JP",

    quantity:
      100,

    price:
      1000,

    referencePrice:
      1000,

    bid:
      999,

    ask:
      1001,

    dailyVolume:
      1000000,

    volatilityPercent:
      2,

    settlementCurrency:
      "JPY",

    fxRate:
      1,

    ...overrides,
  };
}

test(
  "Calculates commission",
  () => {
    const result =
      estimateTransactionCost({
        trade:
          trade({
            bid:
              1000,

            ask:
              1000,

            volatilityPercent:
              0,

            dailyVolume:
              0,
          }),

        config: {
          commissionRate:
            0.001,

          includeSpread:
            false,

          includeSlippage:
            false,

          includeMarketImpact:
            false,
        },

        timestamp:
          NOW,
      });

    assert.equal(
      result.components
        .commission,
      100,
    );

    assert.equal(
      result.totalCost,
      100,
    );
  },
);

test(
  "Applies minimum commission",
  () => {
    const result =
      estimateTransactionCost({
        trade:
          trade({
            quantity:
              1,

            price:
              100,

            referencePrice:
              100,

            bid:
              100,

            ask:
              100,
          }),

        config: {
          commissionRate:
            0.001,

          minimumCommission:
            50,

          includeSpread:
            false,

          includeSlippage:
            false,

          includeMarketImpact:
            false,
        },

        timestamp:
          NOW,
      });

    assert.equal(
      result.components
        .commission,
      50,
    );
  },
);

test(
  "Applies maximum commission",
  () => {
    const result =
      estimateTransactionCost({
        trade:
          trade(),

        config: {
          commissionRate:
            0.01,

          maximumCommission:
            500,

          includeSpread:
            false,

          includeSlippage:
            false,

          includeMarketImpact:
            false,
        },

        timestamp:
          NOW,
      });

    assert.equal(
      result.components
        .commission,
      500,
    );
  },
);

test(
  "Calculates spread cost",
  () => {
    const result =
      estimateTransactionCost({
        trade:
          trade({
            price:
              1001,

            referencePrice:
              1000,
          }),

        config: {
          commissionRate:
            0,

          includeSlippage:
            false,

          includeMarketImpact:
            false,
        },

        timestamp:
          NOW,
      });

    assert.equal(
      result.components
        .spreadCost,
      100,
    );
  },
);

test(
  "Calculates buy slippage",
  () => {
    const result =
      estimateTransactionCost({
        trade:
          trade({
            price:
              1002,

            referencePrice:
              1000,

            bid:
              1000,

            ask:
              1000,
          }),

        config: {
          commissionRate:
            0,

          includeSpread:
            false,

          includeMarketImpact:
            false,
        },

        timestamp:
          NOW,
      });

    assert.equal(
      result.components
        .slippageCost,
      200,
    );
  },
);

test(
  "Calculates sell slippage",
  () => {
    const result =
      estimateTransactionCost({
        trade:
          trade({
            side:
              "SELL",

            price:
              998,

            referencePrice:
              1000,

            bid:
              1000,

            ask:
              1000,
          }),

        config: {
          commissionRate:
            0,

          includeSpread:
            false,

          includeMarketImpact:
            false,
        },

        timestamp:
          NOW,
      });

    assert.equal(
      result.components
        .slippageCost,
      200,
    );
  },
);

test(
  "Calculates market impact",
  () => {
    const result =
      estimateTransactionCost({
        trade:
          trade({
            quantity:
              10000,

            dailyVolume:
              100000,

            volatilityPercent:
              2,
          }),

        config: {
          commissionRate:
            0,

          includeSpread:
            false,

          includeSlippage:
            false,

          impactCoefficient:
            0.1,
        },

        timestamp:
          NOW,
      });

    assert.ok(
      result.components
        .marketImpactCost >
      0,
    );
  },
);

test(
  "Calculates exchange fee",
  () => {
    const result =
      estimateTransactionCost({
        trade:
          trade(),

        config: {
          commissionRate:
            0,

          exchangeFeeRate:
            0.0001,

          includeSpread:
            false,

          includeSlippage:
            false,

          includeMarketImpact:
            false,
        },

        timestamp:
          NOW,
      });

    assert.equal(
      result.components
        .exchangeFee,
      10,
    );
  },
);

test(
  "Applies sell regulatory fee only",
  () => {
    const buy =
      estimateTransactionCost({
        trade:
          trade({
            side:
              "BUY",
          }),

        config: {
          commissionRate:
            0,

          regulatoryFeeRate:
            0.001,

          includeSpread:
            false,

          includeSlippage:
            false,

          includeMarketImpact:
            false,
        },

        timestamp:
          NOW,
      });

    const sell =
      estimateTransactionCost({
        trade:
          trade({
            side:
              "SELL",
          }),

        config: {
          commissionRate:
            0,

          regulatoryFeeRate:
            0.001,

          includeSpread:
            false,

          includeSlippage:
            false,

          includeMarketImpact:
            false,
        },

        timestamp:
          NOW,
      });

    assert.equal(
      buy.components
        .regulatoryFee,
      0,
    );

    assert.equal(
      sell.components
        .regulatoryFee,
      100,
    );
  },
);

test(
  "Applies sell transaction tax",
  () => {
    const result =
      estimateTransactionCost({
        trade:
          trade({
            side:
              "SELL",
          }),

        config: {
          commissionRate:
            0,

          taxRate:
            0.001,

          includeSpread:
            false,

          includeSlippage:
            false,

          includeMarketImpact:
            false,
        },

        timestamp:
          NOW,
      });

    assert.equal(
      result.components
        .tax,
      100,
    );
  },
);

test(
  "Calculates fx cost",
  () => {
    const result =
      estimateTransactionCost({
        trade:
          trade({
            settlementCurrency:
              "USD",

            fxRate:
              150,
          }),

        config: {
          commissionRate:
            0,

          fxFeeRate:
            0.002,

          includeSpread:
            false,

          includeSlippage:
            false,

          includeMarketImpact:
            false,
        },

        timestamp:
          NOW,
      });

    assert.equal(
      result.components
        .fxCost,
      200,
    );
  },
);

test(
  "Calculates buy net cash flow",
  () => {
    const result =
      estimateTransactionCost({
        trade:
          trade({
            bid:
              1000,

            ask:
              1000,
          }),

        config: {
          commissionRate:
            0.001,

          includeSpread:
            false,

          includeSlippage:
            false,

          includeMarketImpact:
            false,
        },

        timestamp:
          NOW,
      });

    assert.equal(
      result.netCashFlow,
      -100100,
    );
  },
);

test(
  "Calculates sell net cash flow",
  () => {
    const result =
      estimateTransactionCost({
        trade:
          trade({
            side:
              "SELL",

            bid:
              1000,

            ask:
              1000,
          }),

        config: {
          commissionRate:
            0.001,

          includeSpread:
            false,

          includeSlippage:
            false,

          includeMarketImpact:
            false,
        },

        timestamp:
          NOW,
      });

    assert.equal(
      result.netCashFlow,
      99900,
    );
  },
);

test(
  "Warns about high participation rate",
  () => {
    const result =
      estimateTransactionCost({
        trade:
          trade({
            quantity:
              20000,

            dailyVolume:
              100000,
          }),

        config: {
          commissionRate:
            0,

          includeSpread:
            false,

          includeSlippage:
            false,
        },

        timestamp:
          NOW,
      });

    assert.ok(
      result.warnings.includes(
        "HIGH_PARTICIPATION_RATE",
      ),
    );
  },
);

test(
  "Compares transaction costs",
  () => {
    const baseline = {
      totalCost:
        100,
    };

    const candidate = {
      totalCost:
        80,
    };

    const comparison =
      compareTransactionCosts({
        baseline,
        candidate,
      });

    assert.equal(
      comparison.cheaper,
      "CANDIDATE",
    );

    assert.equal(
      comparison.difference,
      -20,
    );
  },
);

test(
  "Engine stores history",
  () => {
    const engine =
      new TransactionCostEngineV3({
        commissionRate:
          0.001,

        includeSpread:
          false,

        includeSlippage:
          false,

        includeMarketImpact:
          false,
      });

    engine.estimate({
      trade:
        trade(),

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
  "Calculates round trip cost",
  () => {
    const engine =
      new TransactionCostEngineV3({
        commissionRate:
          0.001,

        includeSpread:
          false,

        includeSlippage:
          false,

        includeMarketImpact:
          false,
      });

    const result =
      engine.estimateRoundTrip({
        entry:
          trade({
            side:
              "BUY",
          }),

        exit:
          trade({
            side:
              "SELL",
          }),

        timestamp:
          NOW,
      });

    assert.equal(
      result.totalCost,
      200,
    );
  },
);

test(
  "Reset clears history",
  () => {
    const engine =
      new TransactionCostEngineV3();

    engine.estimate({
      trade:
        trade(),

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
        estimateTransactionCost({
          trade:
            trade(),

          timestamp:
            "invalid-date",
        }),

      /timestamp is invalid/,
    );
  },
);