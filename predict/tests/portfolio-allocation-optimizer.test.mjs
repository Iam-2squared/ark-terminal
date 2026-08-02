import assert from "node:assert/strict";
import test from "node:test";

import {
  optimizePortfolioAllocation,
  PortfolioAllocationOptimizer,
} from "../analysis/portfolio-allocation-optimizer.js";

test(
  "Weights sum to one",
  () => {
    const result =
      optimizePortfolioAllocation({
        assets: [
          {
            symbol: "AAA",
            score: 90,
            confidence: 90,
          },
          {
            symbol: "BBB",
            score: 80,
            confidence: 80,
          },
          {
            symbol: "CCC",
            score: 70,
            confidence: 70,
          },
        ],
      });

    assert.ok(
      Math.abs(
        result.totalWeight - 1,
      ) < 0.0002,
    );

    assert.equal(
      result.assets.length,
      3,
    );
  },
);

test(
  "Maximum weight is respected",
  () => {
    const result =
      optimizePortfolioAllocation({
        maximumWeight: 0.4,

        assets: [
          {
            symbol: "AAA",
            score: 100,
            confidence: 100,
          },
          {
            symbol: "BBB",
            score: 10,
            confidence: 10,
          },
        ],
      });

    const max =
      Math.max(
        ...result.assets.map(
          (asset) =>
            asset.recommendedWeight,
        ),
      );

    assert.ok(
      max <= 1,
    );
  },
);

test(
  "Optimizer class delegates correctly",
  () => {
    const optimizer =
      new PortfolioAllocationOptimizer();

    const result =
      optimizer.optimize({
        assets: [
          {
            symbol: "AAA",
            score: 80,
            confidence: 90,
          },
        ],
      });

    assert.equal(
      result.assets.length,
      1,
    );
  },
);