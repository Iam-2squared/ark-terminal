import test from "node:test";
import assert from "node:assert/strict";

import {
  MonteCarloValidationV2Engine,
  createSeededRandom,
  runMonteCarloValidation,
} from "../backtest/monte-carlo-validation-v2.js";

test(
  "Seeded random generator is deterministic",
  () => {
    const first =
      createSeededRandom(42);

    const second =
      createSeededRandom(42);

    const firstValues =
      Array.from(
        {
          length:
            10,
        },
        () =>
          first(),
      );

    const secondValues =
      Array.from(
        {
          length:
            10,
        },
        () =>
          second(),
      );

    assert.deepEqual(
      firstValues,
      secondValues,
    );
  },
);

test(
  "Monte Carlo validation produces deterministic paths",
  () => {
    const input = {
      returns: [
        2,
        -1,
        3,
        1,
        -0.5,
        2.5,
      ],

      iterations:
        100,

      sampleSize:
        20,

      seed:
        7,
    };

    assert.deepEqual(
      runMonteCarloValidation(
        input,
      ),

      runMonteCarloValidation(
        input,
      ),
    );
  },
);

test(
  "Monte Carlo validation summarizes profitable strategy",
  () => {
    const result =
      runMonteCarloValidation({
        returns: [
          2,
          1,
          3,
          -0.5,
          2,
          1.5,
        ],

        iterations:
          200,

        sampleSize:
          30,

        seed:
          11,

        minimumSuccessRate:
          60,
      });

    assert.equal(
      result.version,
      "monte-carlo-validation-v2",
    );

    assert.equal(
      result.ready,
      true,
    );

    assert.equal(
      result.iterations,
      200,
    );

    assert.ok(
      result.summary.successRate >
      90,
    );

    assert.ok(
      result.summary.totalReturn.median >
      0,
    );

    assert.equal(
      result.passed,
      true,
    );
  },
);

test(
  "Monte Carlo validation detects weak strategy",
  () => {
    const result =
      runMonteCarloValidation({
        returns: [
          -4,
          -3,
          1,
          -2,
          -5,
          0.5,
        ],

        iterations:
          200,

        sampleSize:
          25,

        seed:
          15,

        minimumSuccessRate:
          60,
      });

    assert.ok(
      result.summary.successRate <
      50,
    );

    assert.equal(
      result.passed,
      false,
    );
  },
);

test(
  "Monte Carlo validation calculates drawdown distribution",
  () => {
    const result =
      runMonteCarloValidation({
        returns: [
          5,
          -10,
          4,
          -3,
          6,
          -8,
          7,
        ],

        iterations:
          100,

        sampleSize:
          20,

        seed:
          123,
      });

    assert.ok(
      Number.isFinite(
        result.summary.maximumDrawdown.median,
      ),
    );

    assert.ok(
      result.summary.maximumDrawdown.percentile95 >=
      result.summary.maximumDrawdown.median,
    );
  },
);

test(
  "Monte Carlo validation supports shuffled paths",
  () => {
    const result =
      runMonteCarloValidation({
        returns: [
          1,
          2,
          3,
          -1,
          -2,
        ],

        iterations:
          20,

        sampleSize:
          5,

        method:
          "shuffle",

        seed:
          22,
      });

    assert.equal(
      result.method,
      "shuffle",
    );

    assert.equal(
      result.paths.length,
      20,
    );
  },
);

test(
  "Monte Carlo validation handles empty input",
  () => {
    const result =
      runMonteCarloValidation({
        returns:
          [],

        iterations:
          50,
      });

    assert.equal(
      result.ready,
      false,
    );

    assert.equal(
      result.passed,
      false,
    );

    assert.equal(
      result.summary.successRate,
      null,
    );

    assert.deepEqual(
      result.paths,
      [],
    );
  },
);

test(
  "Monte Carlo validation rejects invalid configuration",
  () => {
    assert.throws(
      () =>
        runMonteCarloValidation({
          returns: [
            1,
            2,
          ],

          initialCapital:
            0,
        }),

      /initial capital must be greater than zero/,
    );

    assert.throws(
      () =>
        runMonteCarloValidation({
          returns: [
            1,
            2,
          ],

          method:
            "invalid",
        }),

      /method must be bootstrap or shuffle/,
    );
  },
);

test(
  "Monte Carlo validation engine accepts overrides",
  () => {
    const engine =
      new MonteCarloValidationV2Engine({
        iterations:
          50,

        sampleSize:
          10,

        seed:
          5,
      });

    const result =
      engine.validate(
        [
          1,
          2,
          -1,
          3,
        ],

        {
          iterations:
            25,
        },
      );

    assert.equal(
      result.iterations,
      25,
    );

    assert.equal(
      result.sampleSize,
      10,
    );
  },
);