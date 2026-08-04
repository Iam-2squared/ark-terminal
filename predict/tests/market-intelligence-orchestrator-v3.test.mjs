import test from "node:test";
import assert from "node:assert/strict";

import {
  MarketIntelligenceOrchestratorV3,
  runMarketIntelligence,
} from "../market-intelligence/market-intelligence-orchestrator-v3.js";

const NOW =
  "2026-08-04T10:00:00.000Z";

function bullishInput() {
  return {
    timestamp:
      NOW,

    regimeInput: {
      symbol:
        "NIKKEI",

      price:
        42000,

      sma5:
        41800,

      sma25:
        40500,

      sma75:
        39000,

      rsi:
        65,

      macd:
        200,

      macdSignal:
        100,

      atrPercent:
        1.5,

      changePercent:
        2,

      marketBreadth:
        60,

      indexTrendScore:
        15,
    },

    breadthStocks:
      Array.from(
        {
          length:
            10,
        },

        (
          _,
          index,
        ) => ({
          symbol:
            `BULL-${index}`,

          changePercent:
            index < 9
              ? 2
              : -0.2,

          volumeRatio:
            index < 9
              ? 2
              : 0.5,

          aboveSma25:
            index < 9,

          aboveSma75:
            index < 8,

          newHigh:
            index < 4,
        }),
      ),

    indexChangePercent:
      2,

    sectors: [
      {
        name:
          "Semiconductors",

        return1d:
          2.5,

        return5d:
          8,

        return20d:
          14,

        relativeStrength:
          20,

        breadthScore:
          70,

        volumeRatio:
          2,

        momentum:
          40,

        earningsRevision:
          20,

        riskScore:
          35,
      },

      {
        name:
          "Banks",

        return1d:
          1,

        return5d:
          3,

        return20d:
          5,

        relativeStrength:
          8,

        breadthScore:
          35,

        volumeRatio:
          1.2,

        momentum:
          15,

        riskScore:
          40,
      },

      {
        name:
          "Utilities",

        return1d:
          0,

        return5d:
          0,

        return20d:
          1,

        relativeStrength:
          0,

        breadthScore:
          0,

        volumeRatio:
          1,

        momentum:
          0,

        riskScore:
          35,
      },
    ],

    macroInput: {
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
        1,

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
    },

    liquidityInput: {
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
    },
  };
}

test(
  "Produces bullish integrated decision",
  () => {
    const result =
      runMarketIntelligence(
        bullishInput(),
      );

    assert.ok(
      [
        "BUY",
        "HOLD",
      ].includes(
        result.decision,
      ),
    );

    assert.notEqual(
      result.status,
      "BLOCKED",
    );

    assert.ok(
      result.positionMultiplier >
      0,
    );

    assert.equal(
      result.modules.regime
        .regime,
      "STRONG_BULL",
    );
  },
);

test(
  "Blocks trading during severe macro stress",
  () => {
    const input =
      bullishInput();

    input.macroInput = {
      growthScore:
        5,

      inflationScore:
        95,

      policyTightness:
        95,

      liquidityScore:
        5,

      creditStress:
        98,

      volatilityIndex:
        60,

      yieldCurveSpread:
        -2,

      currencyStress:
        95,

      commodityShock:
        95,

      geopoliticalRisk:
        95,

      earningsRevision:
        5,

      marketBreadth:
        5,

      regime:
        "CRASH",
    };

    const result =
      runMarketIntelligence(
        input,
      );

    assert.equal(
      result.status,
      "BLOCKED",
    );

    assert.equal(
      result.decision,
      "BLOCK",
    );

    assert.equal(
      result.positionMultiplier,
      0,
    );
  },
);

test(
  "Blocks trading during severe liquidity contraction",
  () => {
    const input =
      bullishInput();

    input.liquidityInput = {
      centralBankBalanceSheetGrowth:
        -10,

      moneySupplyGrowth:
        -10,

      realRate:
        5,

      policyRateChange:
        5,

      creditGrowth:
        -10,

      dollarIndexChange:
        8,

      yenLiquidityChange:
        -10,

      treasuryLiquidityChange:
        -10,

      reverseRepoChange:
        10,

      fundingStress:
        98,

      creditSpread:
        7,

      volatilityIndex:
        60,

      foreignFlow:
        -10,

      equityFlow:
        -10,

      bondFlow:
        -10,

      cryptoLiquidity:
        -10,

      emergingMarketFlow:
        -10,
    };

    const result =
      runMarketIntelligence(
        input,
      );

    assert.equal(
      result.status,
      "BLOCKED",
    );

    assert.equal(
      result.positionMultiplier,
      0,
    );
  },
);

test(
  "Returns all intelligence modules",
  () => {
    const result =
      runMarketIntelligence(
        bullishInput(),
      );

    assert.ok(
      result.modules.regime,
    );

    assert.ok(
      result.modules.correlation,
    );

    assert.ok(
      result.modules.breadth,
    );

    assert.ok(
      result.modules.sectorRotation,
    );

    assert.ok(
      result.modules.macroRisk,
    );

    assert.ok(
      result.modules.liquidity,
    );

    assert.ok(
      result.consensus,
    );
  },
);

test(
  "Orchestrator stores history",
  () => {
    const engine =
      new MarketIntelligenceOrchestratorV3();

    engine.run(
      bullishInput(),
    );

    assert.equal(
      engine.getHistory().length,
      1,
    );

    assert.ok(
      engine.latest(),
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
        runMarketIntelligence({
          ...bullishInput(),

          timestamp:
            "invalid-date",
        }),

      /timestamp is invalid/,
    );
  },
);