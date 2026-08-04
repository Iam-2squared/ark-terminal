import test from "node:test";
import assert from "node:assert/strict";

import {
  FinalTradingOrchestratorV3,
} from "../paper/final-trading-orchestrator-v3.js";

const NOW =
  "2026-08-04T18:00:00.000Z";

function bullishSignals() {
  return [
    {
      name:
        "TREND",

      score:
        90,

      confidence:
        95,

      weight:
        2,

      direction:
        "BULLISH",
    },
    {
      name:
        "MACD",

      score:
        85,

      confidence:
        90,

      weight:
        1,

      direction:
        "BULLISH",
    },
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
  ];
}

function orchestrator(
  overrides = {},
) {
  return new FinalTradingOrchestratorV3({
    initialCash:
      1000000,

    portfolioConfig: {
      maximumPositionPercent:
        100,

      maximumSectorPercent:
        100,
    },

    riskConfig: {
      maximumPositionPercent:
        100,

      maximumSectorPercent:
        100,

      maximumExposurePercent:
        100,

      maximumOrderRiskPercent:
        100,
    },

    executionConfig: {
      commissionRate:
        0,

      baseSlippageRate:
        0,

      marketImpactFactor:
        0,

      maximumParticipationRate:
        1,

      fillProbability:
        1,
    },

    transactionCostConfig: {
      commissionRate:
        0,

      includeSpread:
        false,

      includeSlippage:
        false,

      includeMarketImpact:
        false,
    },

    ...overrides,
  });
}

test(
  "Creates final orchestrator",
  () => {
    const engine =
      orchestrator();

    const state =
      engine.getState();

    assert.equal(
      state.enabled,
      true,
    );

    assert.equal(
      state.state,
      "IDLE",
    );
  },
);

test(
  "Creates buy order proposal",
  () => {
    const engine =
      orchestrator();

    const result =
      engine.analyze({
        symbol:
          "7203.T",

        price:
          1000,

        sector:
          "AUTO",

        regime:
          "BULL",

        marketScore:
          90,

        liquidityScore:
          90,

        riskScore:
          10,

        volatilityPercent:
          5,

        stopPrice:
          950,

        requestedQuantity:
          10,

        signals:
          bullishSignals(),

        timestamp:
          NOW,
      });

    assert.equal(
      result.state,
      "ORDER_READY",
    );

    assert.equal(
      result.decision,
      "BUY",
    );

    assert.equal(
      result.order.quantity,
      10,
    );
  },
);

test(
  "Submits proposed order",
  () => {
    const engine =
      orchestrator();

    const cycle =
      engine.analyze({
        symbol:
          "7203.T",

        price:
          1000,

        sector:
          "AUTO",

        regime:
          "BULL",

        marketScore:
          90,

        liquidityScore:
          90,

        riskScore:
          10,

        stopPrice:
          950,

        requestedQuantity:
          10,

        signals:
          bullishSignals(),

        timestamp:
          NOW,
      });

    const submitted =
      engine.submit({
        cycleId:
          cycle.id,

        timestamp:
          NOW,
      });

    assert.equal(
      submitted.order.status,
      "OPEN",
    );

    assert.equal(
      submitted.cycle.state,
      "ORDER_OPEN",
    );
  },
);

test(
  "Processes fill and updates portfolio",
  () => {
    const engine =
      orchestrator();

    const cycle =
      engine.analyze({
        symbol:
          "7203.T",

        price:
          1000,

        sector:
          "AUTO",

        regime:
          "BULL",

        marketScore:
          90,

        liquidityScore:
          90,

        riskScore:
          10,

        stopPrice:
          950,

        requestedQuantity:
          10,

        signals:
          bullishSignals(),

        timestamp:
          NOW,
      });

    engine.submit({
      cycleId:
        cycle.id,

      timestamp:
        NOW,
    });

    const results =
      engine.processMarket({
        symbol:
          "7203.T",

        bid:
          1000,

        ask:
          1000,

        last:
          1000,

        volume:
          100000,

        availableLiquidity:
          1000,

        timestamp:
          NOW,
      });

    assert.equal(
      results.length,
      1,
    );

    assert.equal(
      results[0].order.status,
      "FILLED",
    );

    assert.equal(
      engine.portfolio
        .getPosition(
          "7203.T",
        )
        .quantity,
      10,
    );
  },
);

test(
  "Blocks high-risk strategy",
  () => {
    const engine =
      orchestrator();

    const result =
      engine.analyze({
        symbol:
          "7203.T",

        price:
          1000,

        regime:
          "BULL",

        marketScore:
          90,

        liquidityScore:
          90,

        riskScore:
          95,

        requestedQuantity:
          10,

        signals:
          bullishSignals(),

        timestamp:
          NOW,
      });

    assert.equal(
      result.state,
      "BLOCKED",
    );
  },
);

test(
  "Kill switch blocks analysis",
  () => {
    const engine =
      orchestrator();

    engine.activateKillSwitch(
      "TEST",
    );

    const result =
      engine.analyze({
        symbol:
          "7203.T",

        price:
          1000,

        requestedQuantity:
          10,

        timestamp:
          NOW,
      });

    assert.equal(
      result.state,
      "BLOCKED",
    );

    assert.ok(
      result.blockers.includes(
        "KILL_SWITCH_ACTIVE",
      ),
    );
  },
);

test(
  "Kill switch can be deactivated",
  () => {
    const engine =
      orchestrator();

    engine.activateKillSwitch();
    engine.deactivateKillSwitch();

    assert.equal(
      engine.getState()
        .killSwitch,
      false,
    );

    assert.equal(
      engine.getState()
        .enabled,
      true,
    );
  },
);

test(
  "Stores cycles and events",
  () => {
    const engine =
      orchestrator();

    engine.analyze({
      symbol:
        "7203.T",

      price:
        1000,

      regime:
        "BULL",

      marketScore:
        90,

      liquidityScore:
        90,

      riskScore:
        10,

      requestedQuantity:
        10,

      signals:
        bullishSignals(),

      timestamp:
        NOW,
    });

    assert.equal(
      engine.getCycles().length,
      1,
    );

    assert.ok(
      engine.getEvents().length >
      0,
    );
  },
);

test(
  "Snapshot restore is deterministic",
  () => {
    const original =
      orchestrator();

    original.analyze({
      symbol:
        "7203.T",

      price:
        1000,

      regime:
        "BULL",

      marketScore:
        90,

      liquidityScore:
        90,

      riskScore:
        10,

      requestedQuantity:
        10,

      signals:
        bullishSignals(),

      timestamp:
        NOW,
    });

    const snapshot =
      original.snapshot();

    const restored =
      orchestrator();

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
  "Reset clears orchestrator state",
  () => {
    const engine =
      orchestrator();

    engine.analyze({
      symbol:
        "7203.T",

      price:
        1000,

      requestedQuantity:
        10,

      timestamp:
        NOW,
    });

    engine.reset({
      timestamp:
        NOW,
    });

    assert.equal(
      engine.getCycles().length,
      0,
    );

    assert.equal(
      engine.getEvents().length,
      0,
    );

    assert.equal(
      engine.getState()
        .state,
      "IDLE",
    );
  },
);

test(
  "Validates timestamp",
  () => {
    const engine =
      orchestrator();

    assert.throws(
      () =>
        engine.analyze({
          symbol:
            "7203.T",

          price:
            1000,

          timestamp:
            "invalid-date",
        }),

      /timestamp is invalid/,
    );
  },
);