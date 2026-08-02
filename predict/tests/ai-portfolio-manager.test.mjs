import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAiPortfolioPlan,
  buildExecutablePortfolio,
  calculatePortfolioAllocation,
  evaluatePortfolioRisk,
} from "../portfolio/ai-portfolio-manager.js";

const candidates = [
  {
    code: "AAA",
    score: 90,
    price: 500,
    volatility: 8,
    sector: "AI",
    lotSize: 100,
  },
  {
    code: "BBB",
    score: 80,
    price: 200,
    volatility: 10,
    sector: "AI",
    lotSize: 100,
  },
  {
    code: "CCC",
    score: 70,
    price: 100,
    volatility: 6,
    sector: "BANK",
    lotSize: 100,
  },
];

test(
  "Allocation respects position and sector limits",
  () => {
    const result =
      calculatePortfolioAllocation({
        candidates,
        maximumPositionPercent: 25,
        maximumSectorPercent: 40,
        cashReservePercent: 10,
      });

    assert.ok(
      result.allocations.length >
      0,
    );

    assert.ok(
      result.allocations.every(
        (item) =>
          item.allocationPercent <=
          25,
      ),
    );

    const aiTotal =
      result.allocations
        .filter(
          (item) =>
            item.sector === "AI",
        )
        .reduce(
          (sum, item) =>
            sum +
            item.allocationPercent,
          0,
        );

    assert.ok(
      aiTotal <= 40,
    );
  },
);

test(
  "Executable portfolio uses whole lots",
  () => {
    const result =
      buildExecutablePortfolio({
        capital: 100000,
        allocations: [
          {
            code: "AAA",
            allocationPercent: 60,
            price: 500,
            lotSize: 100,
          },
        ],
      });

    assert.equal(
      result.positions[0].shares,
      100,
    );

    assert.equal(
      result.positions[0].investedAmount,
      50000,
    );

    assert.ok(
      result.totalInvested <=
      100000,
    );
  },
);

test(
  "Portfolio risk can reject excessive volatility",
  () => {
    const result =
      evaluatePortfolioRisk({
        capital: 100000,
        maximumPortfolioRiskPercent: 5,
        positions: [
          {
            investedAmount: 80000,
            volatility: 20,
          },
        ],
      });

    assert.equal(
      result.approved,
      false,
    );

    assert.equal(
      result.status,
      "RISK_LIMIT_EXCEEDED",
    );
  },
);

test(
  "AI portfolio plan is generated",
  () => {
    const result =
      buildAiPortfolioPlan({
        capital: 300000,
        candidates,
        settings: {
          maximumPositionPercent: 25,
          maximumSectorPercent: 40,
          cashReservePercent: 15,
          maximumPortfolioRiskPercent: 8,
        },
      });

    assert.equal(
      result.version,
      "ai-portfolio-manager-v1",
    );

    assert.ok(
      result.summary.selectedCount >
      0,
    );

    assert.ok(
      result.summary.totalInvested <=
      300000,
    );

    assert.equal(
      typeof result.approved,
      "boolean",
    );
  },
);