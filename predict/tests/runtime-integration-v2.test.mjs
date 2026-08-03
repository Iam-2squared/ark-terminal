import test from "node:test";
import assert from "node:assert/strict";

import {
  RuntimeIntegrationV2Engine,
  buildRuntimeIntegrationV2,
} from "../analysis/runtime-integration-v2.js";

const NOW =
  Date.parse(
    "2026-08-03T09:00:00.000Z",
  );

function createInput() {
  return {
    prediction: {
      direction:
        "BUY",

      score:
        78,

      confidence:
        80,
    },

    features: {
      rsi:
        0.8,

      macd:
        1.2,

      volume:
        -0.4,
    },

    marketBreadth: {
      advancing:
        780,

      declining:
        180,

      unchanged:
        40,

      upVolume:
        850000,

      downVolume:
        150000,

      newHighs:
        120,

      newLows:
        20,

      percentAbove20:
        78,

      percentAbove50:
        72,

      percentAbove200:
        68,
    },

    sectors: [
      {
        name:
          "Technology",

        return5d:
          5,

        return20d:
          10,

        return60d:
          20,

        percentAbove20:
          85,

        percentAbove50:
          80,

        advanceDeclineRatio:
          4,

        relativeVolume:
          1.8,

        upVolumeRatio:
          0.82,

        volatility20d:
          4,

        maxDrawdown60d:
          -4,
      },

      {
        name:
          "Utilities",

        return5d:
          -4,

        return20d:
          -8,

        return60d:
          -14,

        percentAbove20:
          20,

        percentAbove50:
          25,

        advanceDeclineRatio:
          0.3,

        relativeVolume:
          0.7,

        upVolumeRatio:
          0.25,

        volatility20d:
          16,

        maxDrawdown60d:
          -24,
      },
    ],

    benchmark: {
      return20d:
        2,
    },

    liquidity: {
      score:
        70,

      confidence:
        90,

      coverage:
        100,
    },

    volatility: {
      score:
        65,

      confidence:
        90,

      coverage:
        100,
    },

    news: {
      score:
        60,

      confidence:
        80,

      coverage:
        100,
    },

    confidenceHistory: [
      {
        confidence:
          80,

        outcome:
          1,
      },
      {
        confidence:
          80,

        outcome:
          1,
      },
      {
        confidence:
          80,

        outcome:
          0,
      },
      {
        confidence:
          80,

        outcome:
          1,
      },
    ],
  };
}

test(
  "Runtime Integration v2 combines Phase1 engines",
  () => {
    const result =
      buildRuntimeIntegrationV2({
        ...createInput(),

        now:
          () => NOW,
      });

    assert.equal(
      result.version,
      "runtime-integration-v2",
    );

    assert.equal(
      result.timestamp,
      "2026-08-03T09:00:00.000Z",
    );

    assert.ok(
      result.featureImportance.length >= 3,
    );

    assert.ok(
      result.market.breadth.score >= 65,
    );

    assert.equal(
      result.market.sectors.summary.strongest.sector,
      "Technology",
    );

    assert.ok(
      Number.isFinite(
        result.market.composite.score,
      ),
    );

    assert.equal(
      result.explainability.version,
      "explainability-v2",
    );
  },
);

test(
  "Runtime Integration v2 applies confidence calibration",
  () => {
    const result =
      buildRuntimeIntegrationV2({
        ...createInput(),

        now:
          () => NOW,
      });

    assert.equal(
      result.prediction.calibratedConfidence,
      75,
    );

    assert.equal(
      result.decisionSupport.confidence,
      75,
    );
  },
);

test(
  "Runtime Integration v2 handles minimal input",
  () => {
    const result =
      buildRuntimeIntegrationV2({
        now:
          () => NOW,
      });

    assert.equal(
      result.version,
      "runtime-integration-v2",
    );

    assert.equal(
      result.featureImportance.length,
      0,
    );

    assert.equal(
      result.market.breadth.score,
      null,
    );

    assert.equal(
      result.market.sectors.summary.sectorCount,
      0,
    );

    assert.equal(
      result.diagnostics.compositeMarketAvailable,
      false,
    );
  },
);

test(
  "Runtime Integration v2 is deterministic",
  () => {
    const engine =
      new RuntimeIntegrationV2Engine({
        now:
          () => NOW,
      });

    const input =
      createInput();

    assert.deepEqual(
      engine.run(input),
      engine.run(input),
    );
  },
);

test(
  "Runtime Integration v2 validates clock and timestamp",
  () => {
    assert.throws(
      () =>
        buildRuntimeIntegrationV2({
          now:
            NOW,
        }),
      /clock must be a function/,
    );

    assert.throws(
      () =>
        buildRuntimeIntegrationV2({
          timestamp:
            "invalid",
        }),
      /timestamp is invalid/,
    );
  },
);