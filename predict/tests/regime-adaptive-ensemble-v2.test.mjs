import test from "node:test";
import assert from "node:assert/strict";

import {
  RegimeAdaptiveEnsembleV2,
  combineRegimeAdaptivePredictions,
  inferRegime,
  normalizeRegime,
} from "../analysis/regime-adaptive-ensemble-v2.js";

function bullishModels() {
  return [
    {
      id:
        "trend-model",

      family:
        "TREND",

      prediction: {
        direction:
          "BUY",

        confidence:
          82,
      },

      historicalAccuracy:
        68,

      weight:
        1,
    },

    {
      id:
        "momentum-model",

      family:
        "MOMENTUM",

      prediction: {
        direction:
          "BUY",

        confidence:
          76,
      },

      historicalAccuracy:
        64,

      weight:
        1,
    },

    {
      id:
        "mean-reversion-model",

      family:
        "MEAN_REVERSION",

      prediction: {
        direction:
          "SELL",

        confidence:
          55,
      },

      historicalAccuracy:
        54,

      weight:
        1,
    },
  ];
}

test(
  "Regime detector identifies bullish trend",
  () => {
    const result =
      inferRegime({
        returns: [
          0.5,
          0.8,
          1,
          0.4,
          1.2,
        ],

        trendScore:
          35,

        adx:
          28,

        movingAverageSlope:
          0.8,
      });

    assert.equal(
      result.regime,
      "TRENDING_BULL",
    );

    assert.ok(
      result.confidence >
      50,
    );
  },
);

test(
  "Regime detector identifies bearish trend",
  () => {
    const result =
      inferRegime({
        returns: [
          -0.5,
          -1,
          -0.7,
          -1.2,
        ],

        trendScore:
          -32,

        adx:
          30,

        movingAverageSlope:
          -0.9,
      });

    assert.equal(
      result.regime,
      "TRENDING_BEAR",
    );
  },
);

test(
  "Regime detector identifies high volatility",
  () => {
    const result =
      inferRegime({
        returns: [
          8,
          -7,
          6,
          -9,
          5,
        ],
      });

    assert.equal(
      result.regime,
      "HIGH_VOLATILITY",
    );
  },
);

test(
  "Regime aliases are normalized",
  () => {
    assert.equal(
      normalizeRegime(
        "bullish",
      ),
      "TRENDING_BULL",
    );

    assert.equal(
      normalizeRegime(
        "sideways",
      ),
      "RANGE",
    );

    assert.equal(
      normalizeRegime(
        "high-vol",
      ),
      "HIGH_VOLATILITY",
    );
  },
);

test(
  "Ensemble produces bullish decision",
  () => {
    const result =
      combineRegimeAdaptivePredictions({
        models:
          bullishModels(),

        regime:
          "TRENDING_BULL",

        minimumConfidence:
          40,

        minimumAgreement:
          40,
      });

    assert.equal(
      result.version,
      "regime-adaptive-ensemble-v2",
    );

    assert.equal(
      result.ready,
      true,
    );

    assert.equal(
      result.direction,
      "BUY",
    );

    assert.equal(
      result.approved,
      true,
    );

    assert.ok(
      result.score > 0,
    );

    assert.ok(
      result.agreement > 50,
    );
  },
);

test(
  "Trend model receives larger weight during trend",
  () => {
    const result =
      combineRegimeAdaptivePredictions({
        models:
          bullishModels(),

        regime:
          "TRENDING_BULL",

        minimumConfidence:
          0,

        minimumAgreement:
          0,
      });

    const trend =
      result.contributors.find(
        (
          model,
        ) =>
          model.id ===
          "trend-model",
      );

    const meanReversion =
      result.contributors.find(
        (
          model,
        ) =>
          model.id ===
          "mean-reversion-model",
      );

    assert.ok(
      trend.regimeMultiplier >
      meanReversion.regimeMultiplier,
    );

    assert.ok(
      trend.weight >
      meanReversion.weight,
    );
  },
);

test(
  "Mean reversion receives larger regime multiplier in range",
  () => {
    const result =
      combineRegimeAdaptivePredictions({
        models:
          bullishModels(),

        regime:
          "RANGE",

        minimumConfidence:
          0,

        minimumAgreement:
          0,
      });

    const trend =
      result.contributors.find(
        (
          model,
        ) =>
          model.id ===
          "trend-model",
      );

    const meanReversion =
      result.contributors.find(
        (
          model,
        ) =>
          model.id ===
          "mean-reversion-model",
      );

    assert.ok(
      meanReversion.regimeMultiplier >
      trend.regimeMultiplier,
    );
  },
);

test(
  "Explicit regime performance changes model weight",
  () => {
    const result =
      combineRegimeAdaptivePredictions({
        regime:
          "TRENDING_BULL",

        minimumConfidence:
          0,

        minimumAgreement:
          0,

        models: [
          {
            id:
              "strong",

            prediction: {
              direction:
                "BUY",

              confidence:
                70,
            },

            regimePerformance: {
              TRENDING_BULL:
                80,
            },
          },

          {
            id:
              "weak",

            prediction: {
              direction:
                "BUY",

              confidence:
                70,
            },

            regimePerformance: {
              TRENDING_BULL:
                40,
            },
          },
        ],
      });

    const strong =
      result.contributors.find(
        (
          model,
        ) =>
          model.id ===
          "strong",
      );

    const weak =
      result.contributors.find(
        (
          model,
        ) =>
          model.id ===
          "weak",
      );

    assert.ok(
      strong.weight >
      weak.weight,
    );
  },
);

test(
  "Ensemble blocks low agreement",
  () => {
    const result =
      combineRegimeAdaptivePredictions({
        regime:
          "RANGE",

        minimumAgreement:
          80,

        minimumConfidence:
          0,

        models: [
          {
            id:
              "bull",

            prediction: {
              direction:
                "BUY",

              confidence:
                80,
            },
          },

          {
            id:
              "bear",

            prediction: {
              direction:
                "SELL",

              confidence:
                75,
            },
          },
        ],
      });

    assert.equal(
      result.approved,
      false,
    );

    assert.ok(
      result.blockers.includes(
        "LOW_MODEL_AGREEMENT",
      ) ||
      result.blockers.includes(
        "SIGNAL_BELOW_THRESHOLD",
      ),
    );
  },
);

test(
  "Ensemble handles no active models",
  () => {
    const result =
      combineRegimeAdaptivePredictions({
        models: [
          {
            id:
              "disabled",

            enabled:
              false,

            prediction: {
              direction:
                "BUY",

              confidence:
                90,
            },
          },
        ],
      });

    assert.equal(
      result.ready,
      false,
    );

    assert.equal(
      result.direction,
      "NEUTRAL",
    );

    assert.ok(
      result.blockers.includes(
        "NO_ACTIVE_MODELS",
      ),
    );
  },
);

test(
  "Ensemble weights sum to one",
  () => {
    const result =
      combineRegimeAdaptivePredictions({
        models:
          bullishModels(),

        regime:
          "TRENDING_BULL",

        minimumConfidence:
          0,

        minimumAgreement:
          0,
      });

    assert.ok(
      Math.abs(
        result.diagnostics.weightTotal -
        1,
      ) <
      0.000001,
    );
  },
);

test(
  "Ensemble class is deterministic",
  () => {
    const engine =
      new RegimeAdaptiveEnsembleV2({
        regime:
          "TRENDING_BULL",

        minimumConfidence:
          0,

        minimumAgreement:
          0,
      });

    const models =
      bullishModels();

    assert.deepEqual(
      engine.combine(
        models,
      ),

      engine.combine(
        models,
      ),
    );
  },
);