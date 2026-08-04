import test from "node:test";
import assert from "node:assert/strict";

import {
  RollingValidationV2Engine,
  runRollingValidation,
} from "../backtest/rolling-validation-v2.js";

function createRecords(count) {
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

const alwaysBullish =
  async () => ({
    direction:
      "BUY",

    confidence:
      80,
  });

test(
  "Rolling validation evaluates walk-forward windows",
  async () => {
    const result =
      await runRollingValidation({
        records:
          createRecords(80),

        predictor:
          alwaysBullish,

        splitter: {
          trainingSize:
            40,

          validationSize:
            10,

          testSize:
            10,

          stepSize:
            10,

          expanding:
            false,
        },

        minimumAccuracy:
          60,
      });

    assert.equal(
      result.version,
      "rolling-validation-v2",
    );

    assert.equal(
      result.windowCount,
      3,
    );

    assert.equal(
      result.aggregate.meanAccuracy,
      100,
    );

    assert.equal(
      result.passed,
      true,
    );

    assert.equal(
      result.leakageValidation.valid,
      true,
    );
  },
);

test(
  "Rolling validation calculates signed returns",
  async () => {
    const result =
      await runRollingValidation({
        records:
          createRecords(40),

        predictor:
          alwaysBullish,

        splitter: {
          trainingSize:
            20,

          validationSize:
            5,

          testSize:
            5,
        },
      });

    assert.ok(
      result.windows[0].metrics.averageSignedReturn >
      0,
    );

    assert.ok(
      result.aggregate.meanSignedReturn >
      0,
    );
  },
);

test(
  "Rolling validation detects incorrect bearish predictions",
  async () => {
    const result =
      await runRollingValidation({
        records:
          createRecords(40),

        predictor:
          async () => ({
            direction:
              "SELL",

            confidence:
              90,
          }),

        splitter: {
          trainingSize:
            20,

          validationSize:
            5,

          testSize:
            5,
        },

        minimumAccuracy:
          50,
      });

    assert.equal(
      result.aggregate.meanAccuracy,
      0,
    );

    assert.equal(
      result.passed,
      false,
    );
  },
);

test(
  "Rolling validation passes window data to predictor",
  async () => {
    const received = [];

    await runRollingValidation({
      records:
        createRecords(35),

      predictor:
        async (context) => {
          received.push(
            context,
          );

          return {
            direction:
              "BUY",

            confidence:
              70,
          };
        },

      splitter: {
        trainingSize:
          20,

        validationSize:
          5,

        testSize:
          5,
      },
    });

    assert.ok(
      received.length > 0,
    );

    assert.equal(
      received[0].training.length,
      20,
    );

    assert.equal(
      received[0].validation.length,
      5,
    );

    assert.equal(
      received[0].test.length,
      5,
    );
  },
);

test(
  "Rolling validation reports insufficient data",
  async () => {
    const result =
      await runRollingValidation({
        records:
          createRecords(10),

        predictor:
          alwaysBullish,

        splitter: {
          trainingSize:
            20,

          validationSize:
            5,

          testSize:
            5,
        },
      });

    assert.equal(
      result.ready,
      false,
    );

    assert.equal(
      result.windowCount,
      0,
    );

    assert.equal(
      result.aggregate.meanAccuracy,
      null,
    );
  },
);

test(
  "Rolling validation requires predictor function",
  async () => {
    await assert.rejects(
      () =>
        runRollingValidation({
          records:
            createRecords(30),
        }),

      /predictor must be a function/,
    );
  },
);

test(
  "Rolling validation engine is deterministic",
  async () => {
    const engine =
      new RollingValidationV2Engine({
        predictor:
          alwaysBullish,

        splitter: {
          trainingSize:
            20,

          validationSize:
            5,

          testSize:
            5,
        },
      });

    const records =
      createRecords(40);

    assert.deepEqual(
      await engine.validate(
        records,
      ),

      await engine.validate(
        records,
      ),
    );
  },
);