import test from "node:test";
import assert from "node:assert/strict";

import {
  Phase2RuntimeIntegrationV2,
  runPhase2RuntimeIntegration,
} from "../analysis/phase2-runtime-integration-v2.js";

function createRecords(
  count = 80,
) {
  const start =
    Date.parse(
      "2025-01-01T00:00:00.000Z",
    );

  return Array.from(
    {
      length:
        count,
    },
    (
      _,
      index,
    ) => ({
      timestamp:
        new Date(
          start +
          index *
          86400000,
        ).toISOString(),

      close:
        100 +
        index,
    }),
  );
}

function createInput() {
  return {
    records:
      createRecords(),

    predictor:
      async () => ({
        direction:
          "BUY",

        confidence:
          85,
      }),

    splitter: {
      trainingSize:
        40,

      validationSize:
        10,

      testSize:
        10,

      stepSize:
        10,
    },

    minimumAccuracy:
      50,

    returns: [
      2,
      1,
      3,
      -0.5,
      2,
      1.5,
      1,
      -0.2,
    ],

    monteCarlo: {
      iterations:
        100,

      sampleSize:
        20,

      seed:
        42,

      minimumSuccessRate:
        50,
    },

    assets: [
      {
        symbol:
          "AAA",

        sector:
          "Technology",

        returns: [
          2,
          1,
          3,
          -0.5,
          2,
          1.5,
        ],

        score:
          90,

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
          -0.2,
          1,
          0.8,
        ],

        score:
          75,

        confidence:
          80,
      },
    ],

    portfolio: {
      samples:
        500,

      seed:
        5,

      maximumSectorWeight:
        1,
    },

    candidates: [
      {
        symbol:
          "AAA",

        sector:
          "Technology",

        side:
          "BUY",

        price:
          100,

        averageDailyVolume:
          100000,

        requestedQuantity:
          100,

        score:
          90,

        confidence:
          90,

        liquidityScore:
          95,

        volatility:
          2,
      },

      {
        symbol:
          "BBB",

        sector:
          "Finance",

        side:
          "BUY",

        price:
          200,

        averageDailyVolume:
          100000,

        requestedQuantity:
          50,

        score:
          75,

        confidence:
          80,

        liquidityScore:
          90,

        volatility:
          2,
      },
    ],

    capacity: {
      maximumPositionWeight:
        0.4,

      maximumGrossExposure:
        0.8,

      maximumImpactPercent:
        5,

      impactCoefficient:
        0.1,
    },

    marketBySymbol: {
      AAA: {
        bid:
          99.9,

        ask:
          100,

        last:
          100,

        volume:
          100000,

        liquidityScore:
          95,

        volatility:
          2,
      },

      BBB: {
        bid:
          199.8,

        ask:
          200,

        last:
          200,

        volume:
          100000,

        liquidityScore:
          90,

        volatility:
          2,
      },
    },

    execution: {
      impactFactor:
        0,

      baseSlippageBps:
        1,
    },

    equity:
      100000,

    risk: {
      maximumPositionWeight:
        0.8,

      maximumSectorWeight:
        1,

      maximumValueAtRisk:
        10,

      maximumAllowedDrawdown:
        30,
    },
  };
}

test(
  "Phase2 runtime integrates all validation layers",
  async () => {
    const result =
      await runPhase2RuntimeIntegration(
        createInput(),
      );

    assert.equal(
      result.version,
      "phase2-runtime-integration-v2",
    );

    assert.equal(
      result.ready,
      true,
    );

    assert.equal(
      result.gate.totalChecks,
      6,
    );

    assert.equal(
      result.rollingValidation.ready,
      true,
    );

    assert.equal(
      result.monteCarloValidation.ready,
      true,
    );

    assert.equal(
      result.portfolioOptimization.ready,
      true,
    );

    assert.equal(
      result.capacityPlan.ready,
      true,
    );

    assert.ok(
      result.executionSimulation.orderCount >
      0,
    );
  },
);

test(
  "Phase2 runtime approves healthy pipeline",
  async () => {
    const result =
      await runPhase2RuntimeIntegration(
        createInput(),
      );

    assert.equal(
      result.approved,
      true,
    );

    assert.deepEqual(
      result.gate.blockers,
      [],
    );

    assert.equal(
      result.gate.score,
      100,
    );
  },
);

test(
  "Phase2 runtime exposes summary metrics",
  async () => {
    const result =
      await runPhase2RuntimeIntegration(
        createInput(),
      );

    assert.equal(
      result.summary.rollingAccuracy,
      100,
    );

    assert.ok(
      result.summary.monteCarloSuccessRate >
      50,
    );

    assert.ok(
      Number.isFinite(
        result.summary.riskScore,
      ),
    );

    assert.ok(
      result.summary.execution.filledCount >
      0,
    );
  },
);

test(
  "Phase2 runtime blocks weak Monte Carlo result",
  async () => {
    const input =
      createInput();

    input.returns = [
      -5,
      -4,
      -3,
      0.2,
      -2,
      -6,
    ];

    input.monteCarlo = {
      iterations:
        100,

      sampleSize:
        20,

      seed:
        9,

      minimumSuccessRate:
        80,
    };

    const result =
      await runPhase2RuntimeIntegration(
        input,
      );

    assert.equal(
      result.approved,
      false,
    );

    assert.ok(
      result.gate.blockers.includes(
        "monteCarlo",
      ),
    );
  },
);

test(
  "Phase2 runtime requires predictor",
  async () => {
    const input =
      createInput();

    delete input.predictor;

    await assert.rejects(
      () =>
        runPhase2RuntimeIntegration(
          input,
        ),

      /predictor must be a function/,
    );
  },
);

test(
  "Phase2 runtime rejects invalid equity",
  async () => {
    const input =
      createInput();

    input.equity = 0;

    await assert.rejects(
      () =>
        runPhase2RuntimeIntegration(
          input,
        ),

      /equity must be greater than zero/,
    );
  },
);

test(
  "Phase2 runtime class is deterministic",
  async () => {
    const engine =
      new Phase2RuntimeIntegrationV2();

    const input =
      createInput();

    assert.deepEqual(
      await engine.run(input),
      await engine.run(input),
    );
  },
);