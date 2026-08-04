import test from "node:test";
import assert from "node:assert/strict";

import {
  GlobalLiquidityEngineV3,
  compareGlobalLiquidity,
  evaluateGlobalLiquidity,
} from "../market-intelligence/global-liquidity-engine-v3.js";

const NOW =
  "2026-08-04T09:00:00.000Z";

function expansionaryInput() {
  return {
    centralBankBalanceSheetGrowth:
      8,

    moneySupplyGrowth:
      7,

    realRate:
      -1,

    policyRateChange:
      -1,

    creditGrowth:
      8,

    dollarIndexChange:
      -2,

    yenLiquidityChange:
      5,

    treasuryLiquidityChange:
      6,

    reverseRepoChange:
      -5,

    fundingStress:
      10,

    creditSpread:
      0.8,

    volatilityIndex:
      13,

    foreignFlow:
      8,

    equityFlow:
      7,

    bondFlow:
      3,

    cryptoLiquidity:
      5,

    emergingMarketFlow:
      6,
  };
}

function contractionaryInput() {
  return {
    centralBankBalanceSheetGrowth:
      -8,

    moneySupplyGrowth:
      -6,

    realRate:
      4,

    policyRateChange:
      3,

    creditGrowth:
      -8,

    dollarIndexChange:
      6,

    yenLiquidityChange:
      -7,

    treasuryLiquidityChange:
      -8,

    reverseRepoChange:
      7,

    fundingStress:
      95,

    creditSpread:
      6,

    volatilityIndex:
      55,

    foreignFlow:
      -10,

    equityFlow:
      -9,

    bondFlow:
      -5,

    cryptoLiquidity:
      -8,

    emergingMarketFlow:
      -9,
  };
}

test(
  "Evaluates expansionary liquidity",
  () => {
    const result =
      evaluateGlobalLiquidity({
        input:
          expansionaryInput(),

        timestamp:
          NOW,
      });

    assert.equal(
      result.status,
      "READY",
    );

    assert.ok(
      [
        "EXPANSIONARY",
        "STRONGLY_EXPANSIONARY",
      ].includes(
        result.regime,
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
  "Evaluates severe liquidity contraction",
  () => {
    const result =
      evaluateGlobalLiquidity({
        input:
          contractionaryInput(),

        timestamp:
          NOW,
      });

    assert.equal(
      result.regime,
      "SEVERELY_CONTRACTIONARY",
    );

    assert.equal(
      result.status,
      "BLOCKED",
    );

    assert.equal(
      result.action
        .positionMultiplier,
      0,
    );
  },
);

test(
  "Detects systemic funding stress",
  () => {
    const result =
      evaluateGlobalLiquidity({
        input:
          contractionaryInput(),

        timestamp:
          NOW,
      });

    assert.ok(
      result.blockers.includes(
        "SYSTEMIC_FUNDING_STRESS",
      ),
    );
  },
);

test(
  "Detects credit market dislocation",
  () => {
    const result =
      evaluateGlobalLiquidity({
        input:
          contractionaryInput(),

        timestamp:
          NOW,
      });

    assert.ok(
      result.blockers.includes(
        "CREDIT_MARKET_DISLOCATION",
      ),
    );
  },
);

test(
  "Detects dollar liquidity pressure",
  () => {
    const result =
      evaluateGlobalLiquidity({
        input: {
          ...expansionaryInput(),

          dollarIndexChange:
            5,
        },

        timestamp:
          NOW,
      });

    assert.ok(
      result.reasons.includes(
        "DOLLAR_LIQUIDITY_PRESSURE",
      ),
    );
  },
);

test(
  "Compares deteriorating liquidity",
  () => {
    const previous =
      evaluateGlobalLiquidity({
        input:
          expansionaryInput(),

        timestamp:
          NOW,
      });

    const current =
      evaluateGlobalLiquidity({
        input:
          contractionaryInput(),

        timestamp:
          "2026-08-05T09:00:00.000Z",
      });

    const comparison =
      compareGlobalLiquidity({
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
      comparison.scoreChange <
      0,
    );
  },
);

test(
  "Global liquidity class stores history",
  () => {
    const engine =
      new GlobalLiquidityEngineV3();

    engine.evaluate({
      input:
        expansionaryInput(),

      timestamp:
        NOW,
    });

    engine.evaluate({
      input:
        contractionaryInput(),

      timestamp:
        "2026-08-05T09:00:00.000Z",
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
        evaluateGlobalLiquidity({
          input:
            expansionaryInput(),

          timestamp:
            "invalid-date",
        }),

      /timestamp is invalid/,
    );
  },
);