import test from "node:test";
import assert from "node:assert/strict";

import {
  PortfolioEngineV3,
  createPortfolio,
} from "../portfolio/portfolio-engine-v3.js";

const NOW =
  "2026-08-04T12:00:00.000Z";

function engine(
  options = {},
) {
  return new PortfolioEngineV3({
    initialCash:
      100000,

    maximumPositionPercent:
      100,

    maximumSectorPercent:
      100,

    timestamp:
      NOW,

    ...options,
  });
}

test(
  "Creates portfolio with initial cash",
  () => {
    const portfolio =
      createPortfolio({
        initialCash:
          50000,

        timestamp:
          NOW,
      });

    const statistics =
      portfolio
        .calculateStatistics();

    assert.equal(
      statistics.account.cash,
      50000,
    );

    assert.equal(
      statistics.account.equity,
      50000,
    );
  },
);

test(
  "Buys position and updates average cost",
  () => {
    const portfolio =
      engine();

    portfolio.buy({
      symbol:
        "7203.T",

      quantity:
        10,

      price:
        1000,

      sector:
        "AUTO",

      timestamp:
        NOW,
    });

    portfolio.buy({
      symbol:
        "7203.T",

      quantity:
        10,

      price:
        1200,

      sector:
        "AUTO",

      timestamp:
        NOW,
    });

    const position =
      portfolio.getPosition(
        "7203.T",
      );

    assert.equal(
      position.quantity,
      20,
    );

    assert.equal(
      position.averagePrice,
      1100,
    );
  },
);

test(
  "Rejects buy without enough cash",
  () => {
    const portfolio =
      engine({
        initialCash:
          1000,
      });

    assert.throws(
      () =>
        portfolio.buy({
          symbol:
            "TEST",

          quantity:
            100,

          price:
            100,

          timestamp:
            NOW,
        }),

      /Insufficient portfolio cash/,
    );
  },
);

test(
  "Rejects sell above owned quantity",
  () => {
    const portfolio =
      engine();

    portfolio.buy({
      symbol:
        "TEST",

      quantity:
        10,

      price:
        100,

      timestamp:
        NOW,
    });

    assert.throws(
      () =>
        portfolio.sell({
          symbol:
            "TEST",

          quantity:
            11,

          price:
            120,

          timestamp:
            NOW,
        }),

      /Insufficient portfolio position/,
    );
  },
);

test(
  "Calculates realized profit",
  () => {
    const portfolio =
      engine();

    portfolio.buy({
      symbol:
        "TEST",

      quantity:
        10,

      price:
        100,

      timestamp:
        NOW,
    });

    const result =
      portfolio.sell({
        symbol:
          "TEST",

        quantity:
          10,

        price:
          120,

        timestamp:
          NOW,
      });

    assert.equal(
      result.realizedPnl,
      200,
    );

    assert.equal(
      portfolio
        .getPosition(
          "TEST",
        )
        .quantity,
      0,
    );
  },
);

test(
  "Calculates unrealized pnl",
  () => {
    const portfolio =
      engine();

    portfolio.buy({
      symbol:
        "TEST",

      quantity:
        10,

      price:
        100,

      timestamp:
        NOW,
    });

    portfolio.updateMarketPrice({
      symbol:
        "TEST",

      price:
        125,

      timestamp:
        "2026-08-05T12:00:00.000Z",
    });

    assert.equal(
      portfolio
        .calculateStatistics()
        .account
        .unrealizedPnl,
      250,
    );
  },
);

test(
  "Calculates portfolio exposure",
  () => {
    const portfolio =
      engine();

    portfolio.buy({
      symbol:
        "TEST",

      quantity:
        100,

      price:
        100,

      timestamp:
        NOW,
    });

    assert.equal(
      portfolio
        .calculateRisk()
        .exposurePercent,
      10,
    );
  },
);

test(
  "Calculates sector allocation",
  () => {
    const portfolio =
      engine();

    portfolio.buy({
      symbol:
        "AAA",

      quantity:
        100,

      price:
        100,

      sector:
        "TECH",

      timestamp:
        NOW,
    });

    portfolio.buy({
      symbol:
        "BBB",

      quantity:
        100,

      price:
        100,

      sector:
        "BANKS",

      timestamp:
        NOW,
    });

    const allocation =
      portfolio
        .calculateSectorAllocation();

    assert.equal(
      allocation.TECH,
      10,
    );

    assert.equal(
      allocation.BANKS,
      10,
    );
  },
);

test(
  "Rejects maximum position breach",
  () => {
    const portfolio =
      engine({
        maximumPositionPercent:
          10,
      });

    assert.throws(
      () =>
        portfolio.buy({
          symbol:
            "TEST",

          quantity:
            200,

          price:
            100,

          timestamp:
            NOW,
        }),

      /Maximum portfolio position exceeded/,
    );
  },
);

test(
  "Rejects maximum sector breach",
  () => {
    const portfolio =
      engine({
        maximumSectorPercent:
          15,
      });

    portfolio.buy({
      symbol:
        "AAA",

      quantity:
        100,

      price:
        100,

      sector:
        "TECH",

      timestamp:
        NOW,
    });

    assert.throws(
      () =>
        portfolio.buy({
          symbol:
            "BBB",

          quantity:
            100,

          price:
            100,

          sector:
            "TECH",

          timestamp:
            NOW,
        }),

      /Maximum sector exposure exceeded/,
    );
  },
);

test(
  "Calculates winning trade statistics",
  () => {
    const portfolio =
      engine();

    portfolio.buy({
      symbol:
        "AAA",

      quantity:
        10,

      price:
        100,

      timestamp:
        NOW,
    });

    portfolio.sell({
      symbol:
        "AAA",

      quantity:
        10,

      price:
        120,

      timestamp:
        NOW,
    });

    const performance =
      portfolio
        .calculatePerformance();

    assert.equal(
      performance.winRate,
      100,
    );

    assert.equal(
      performance.closedTradeCount,
      1,
    );

    assert.equal(
      performance.profitFactor,
      "Infinity",
    );
  },
);

test(
  "Calculates losing trade profit factor",
  () => {
    const portfolio =
      engine();

    portfolio.buy({
      symbol:
        "AAA",

      quantity:
        10,

      price:
        100,

      timestamp:
        NOW,
    });

    portfolio.sell({
      symbol:
        "AAA",

      quantity:
        10,

      price:
        90,

      timestamp:
        NOW,
    });

    const performance =
      portfolio
        .calculatePerformance();

    assert.equal(
      performance.winRate,
      0,
    );

    assert.equal(
      performance.profitFactor,
      0,
    );
  },
);

test(
  "Snapshot restore is deterministic",
  () => {
    const original =
      engine();

    original.buy({
      symbol:
        "AAA",

      quantity:
        20,

      price:
        100,

      sector:
        "TECH",

      beta:
        1.2,

      volatility:
        25,

      timestamp:
        NOW,
    });

    const snapshot =
      original.snapshot();

    const restored =
      engine();

    restored.restore(
      snapshot,
    );

    assert.deepEqual(
      restored.snapshot(),
      snapshot,
    );

    assert.deepEqual(
      restored
        .calculateStatistics(),
      original
        .calculateStatistics(),
    );
  },
);

test(
  "Calculates portfolio beta",
  () => {
    const portfolio =
      engine();

    portfolio.buy({
      symbol:
        "AAA",

      quantity:
        100,

      price:
        100,

      beta:
        1.5,

      timestamp:
        NOW,
    });

    assert.equal(
      portfolio
        .calculateRisk()
        .portfolioBeta,
      0.15,
    );
  },
);

test(
  "Calculates maximum drawdown",
  () => {
    const portfolio =
      engine();

    portfolio.buy({
      symbol:
        "AAA",

      quantity:
        100,

      price:
        100,

      timestamp:
        NOW,
    });

    portfolio.updateMarketPrice({
      symbol:
        "AAA",

      price:
        50,

      timestamp:
        "2026-08-05T12:00:00.000Z",
    });

    assert.ok(
      portfolio
        .calculateRisk()
        .maximumDrawdownPercent >
      0,
    );
  },
);

test(
  "Reset restores initial state",
  () => {
    const portfolio =
      engine();

    portfolio.buy({
      symbol:
        "AAA",

      quantity:
        10,

      price:
        100,

      timestamp:
        NOW,
    });

    portfolio.reset({
      timestamp:
        NOW,
    });

    const statistics =
      portfolio
        .calculateStatistics();

    assert.equal(
      statistics.account.cash,
      100000,
    );

    assert.equal(
      portfolio
        .getPositions()
        .length,
      0,
    );
  },
);

test(
  "Validates timestamp",
  () => {
    assert.throws(
      () =>
        new PortfolioEngineV3({
          timestamp:
            "invalid-date",
        }),

      /timestamp is invalid/,
    );
  },
);