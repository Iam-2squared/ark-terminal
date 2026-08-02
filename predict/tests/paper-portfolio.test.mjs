import test from "node:test";
import assert from "node:assert/strict";

import {
  createPaperPortfolioSummary,
  evaluatePortfolioLimits,
} from "../paper/paper-portfolio.js";

test(
  "ポートフォリオを集計",
  () => {
    const summary =
      createPaperPortfolioSummary({
        account: {
          cash:
            500_000,

          equity:
            1_000_000,

          positions: {
            "7203.T": {
              symbol:
                "7203.T",
              quantity:
                100,
              averagePrice:
                2_000,
              marketPrice:
                2_500,
              marketValue:
                250_000,
              unrealizedPnl:
                50_000,
            },

            "6758.T": {
              symbol:
                "6758.T",
              quantity:
                100,
              averagePrice:
                2_000,
              marketPrice:
                2_500,
              marketValue:
                250_000,
              unrealizedPnl:
                50_000,
            },
          },
        },

        sectorBySymbol: {
          "7203.T":
            "自動車",
          "6758.T":
            "電機",
        },
      });

    assert.equal(
      summary.positionCount,
      2,
    );

    assert.equal(
      summary.marketValue,
      500_000,
    );

    assert.equal(
      summary.cashRatioPercent,
      50,
    );

    assert.equal(
      summary.exposurePercent,
      50,
    );

    assert.equal(
      summary.largestPositionPercent,
      25,
    );

    assert.equal(
      summary.sectors.length,
      2,
    );
  },
);

test(
  "集中リスクを検出",
  () => {
    const summary =
      createPaperPortfolioSummary({
        account: {
          cash:
            100_000,

          equity:
            1_000_000,

          positions: {
            "7203.T": {
              symbol:
                "7203.T",
              marketValue:
                900_000,
            },
          },
        },

        sectorBySymbol: {
          "7203.T":
            "自動車",
        },
      });

    const result =
      evaluatePortfolioLimits({
        summary,
      });

    assert.equal(
      result.passed,
      false,
    );

    assert.ok(
      result.reasons.includes(
        "position_concentration_high",
      ),
    );

    assert.ok(
      result.reasons.includes(
        "sector_concentration_high",
      ),
    );
  },
);