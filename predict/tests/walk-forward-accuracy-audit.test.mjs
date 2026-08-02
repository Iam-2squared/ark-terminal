import assert from "node:assert/strict";
import test from "node:test";

import {
  evaluateWalkForwardPrediction,
  runWalkForwardAudit,
  summarizeWalkForwardAudit,
} from "../analysis/walk-forward-accuracy-audit.js";

function sampleRows(
  count = 30,
) {
  const start =
    new Date(
      "2026-01-01T00:00:00.000Z",
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
      date:
        new Date(
          start.getTime() +
          index *
          86400000,
        )
          .toISOString()
          .slice(0, 10),

      symbol:
        "AAA",

      close:
        100 + index,

      features: {
        momentum:
          index,
      },
    }),
  );
}

test(
  "Prediction is compared with future close",
  () => {
    const result =
      evaluateWalkForwardPrediction({
        prediction: {
          action:
            "BUY",

          score:
            80,

          confidence:
            75,
        },

        entryRow: {
          date:
            "2026-01-01",

          symbol:
            "AAA",

          close:
            100,
        },

        exitRow: {
          date:
            "2026-01-06",

          close:
            110,
        },

        horizon:
          5,
      });

    assert.equal(
      result.actualDirection,
      "UP",
    );

    assert.equal(
      result.correct,
      true,
    );

    assert.equal(
      result.returnPercent,
      10,
    );
  },
);

test(
  "Walk-forward audit blocks future leakage",
  async () => {
    const rows =
      sampleRows(
        30,
      );

    const result =
      await runWalkForwardAudit({
        rows,

        horizon:
          5,

        minimumHistory:
          10,

        predictor:
          async (input) => {
            const finalVisibleRow =
              input.history.at(-1);

            assert.equal(
              finalVisibleRow.date,
              input.date,
            );

            assert.equal(
              finalVisibleRow.close,
              input.price,
            );

            return {
              action:
                "BUY",

              score:
                80,

              confidence:
                75,
            };
          },
      });

    assert.equal(
      result.predictions.length,
      16,
    );

    assert.equal(
      result.summary.accuracy,
      100,
    );
  },
);

test(
  "Audit summary calculates performance",
  () => {
    const result =
      summarizeWalkForwardAudit([
        {
          action:
            "BUY",

          actualDirection:
            "UP",

          correct:
            true,

          confidence:
            80,

          returnPercent:
            5,

          strategyReturn:
            5,
        },

        {
          action:
            "BUY",

          actualDirection:
            "DOWN",

          correct:
            false,

          confidence:
            70,

          returnPercent:
            -2,

          strategyReturn:
            -2,
        },
      ]);

    assert.equal(
      result.total,
      2,
    );

    assert.equal(
      result.accuracy,
      50,
    );

    assert.equal(
      result.buyPrecision,
      50,
    );

    assert.equal(
      result.profitFactor,
      2.5,
    );
  },
);

test(
  "Predictor is required",
  async () => {
    await assert.rejects(
      () =>
        runWalkForwardAudit({
          rows:
            sampleRows(),
        }),

      {
        name:
          "TypeError",
      },
    );
  },
);