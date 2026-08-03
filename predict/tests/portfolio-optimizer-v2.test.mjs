import test from "node:test";
import assert from "node:assert/strict";

import {
  PortfolioOptimizerV2Engine,
  createSeededRandom,
  optimizePortfolio,
} from "../portfolio/portfolio-optimizer-v2.js";

function createAssets() {
  return [
    {
      symbol:
        "AAA",

      sector:
        "Technology",

      returns: [
        2,
        1,
        3,
        -1,
        2,
        1.5,
      ],

      score:
        85,

      confidence:
        90,
    },

    {
      symbol:
        "BBB",

      sector:
        "Finance",

      returns: [
        1,
        0.5,
        1.5,
        -0.5,
        1,
        0.8,
      ],

      score:
        70,

      confidence:
        80,
    },

    {
      symbol:
        "CCC",

      sector:
        "Utilities",

      returns: [
        0.3,
        0.2,
        0.4,
        0.1,
        0.3,
        0.2,
      ],

      score:
        55,

      confidence:
        75,
    },
  ];
}

test(
  "Seeded optimizer random source is deterministic",
  () => {
    const first =
      createSeededRandom(10);

    const second =
      createSeededRandom(10);

    assert.deepEqual(
      Array.from(
        {
          length:
            10,
        },
        () =>
          first(),
      ),

      Array.from(
        {
          length:
            10,
        },
        () =>
          second(),
      ),
    );
  },
);

test(
  "Portfolio optimizer creates valid allocations",
  () => {
    const result =
      optimizePortfolio({
        assets:
          createAssets(),

        samples:
          1000,

        seed:
          7,
      });

    assert.equal(
      result.version,
      "portfolio-optimizer-v2",
    );

    assert.equal(
      result.ready,
      true,
    );

    assert.equal(
      result.assetCount,
      3,
    );

    assert.ok(
      Math.abs(
        result.diagnostics.totalWeight -
        1,
      ) <
      0.000001,
    );

    assert.equal(
      result.allocations.length,
      3,
    );
  },
);

test(
  "Portfolio optimizer is deterministic",
  () => {
    const input = {
      assets:
        createAssets(),

      samples:
        500,

      seed:
        25,
    };

    assert.deepEqual(
      optimizePortfolio(
        input,
      ),

      optimizePortfolio(
        input,
      ),
    );
  },
);

test(
  "Minimum volatility favors lower volatility asset",
  () => {
    const result =
      optimizePortfolio({
        assets:
          createAssets(),

        objective:
          "min-volatility",

        samples:
          1500,

        seed:
          4,
      });

    assert.equal(
      result.allocations[0].symbol,
      "CCC",
    );

    assert.ok(
      result.allocations[0].weight >
      0.4,
    );
  },
);

test(
  "Portfolio optimizer respects asset maximum weight",
  () => {
    const assets =
      createAssets();

    assets[0].maximumWeight =
      0.4;

    const result =
      optimizePortfolio({
        assets,

        samples:
          1000,

        seed:
          9,
      });

    const first =
      result.allocations.find(
        (
          allocation,
        ) =>
          allocation.symbol ===
          "AAA",
      );

    assert.ok(
      first.weight <=
      0.400001,
    );
  },
);

test(
  "Portfolio optimizer respects sector limit",
  () => {
    const assets = [
      ...createAssets(),

      {
        symbol:
          "DDD",

        sector:
          "Technology",

        returns: [
          2,
          2,
          1,
          -1,
          2,
          3,
        ],

        score:
          90,

        confidence:
          90,
      },
    ];

    const result =
      optimizePortfolio({
        assets,

        samples:
          3000,

        seed:
          12,

        maximumSectorWeight:
          0.6,
      });

    assert.ok(
      result.sectorWeights.Technology <=
      0.600001,
    );
  },
);

test(
  "Portfolio optimizer handles empty assets",
  () => {
    const result =
      optimizePortfolio();

    assert.equal(
      result.ready,
      false,
    );

    assert.equal(
      result.assetCount,
      0,
    );

    assert.deepEqual(
      result.allocations,
      [],
    );
  },
);

test(
  "Portfolio optimizer rejects invalid objective",
  () => {
    assert.throws(
      () =>
        optimizePortfolio({
          assets:
            createAssets(),

          objective:
            "invalid",
        }),

      /objective must be/,
    );
  },
);

test(
  "Portfolio optimizer engine accepts overrides",
  () => {
    const engine =
      new PortfolioOptimizerV2Engine({
        objective:
          "min-volatility",

        samples:
          300,

        seed:
          3,
      });

    const result =
      engine.optimize(
        createAssets(),

        {
          samples:
            400,
        },
      );

    assert.equal(
      result.objective,
      "min-volatility",
    );

    assert.ok(
      result.samples >= 400,
    );
  },
);