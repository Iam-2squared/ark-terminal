import test from "node:test";
import assert from "node:assert/strict";

import {
  WalkForwardSplitterV2,
  createWalkForwardWindows,
  validateWalkForwardWindows,
} from "../backtest/walk-forward-splitter-v2.js";

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

test(
  "Walk-forward splitter creates chronological windows",
  () => {
    const result =
      createWalkForwardWindows(
        createRecords(100),
        {
          trainingSize:
            50,

          validationSize:
            10,

          testSize:
            10,

          stepSize:
            10,

          expanding:
            false,
        },
      );

    assert.equal(
      result.version,
      "walk-forward-splitter-v2",
    );

    assert.equal(
      result.windowCount,
      4,
    );

    assert.equal(
      result.windows[0].training.length,
      50,
    );

    assert.equal(
      result.windows[0].validation.length,
      10,
    );

    assert.equal(
      result.windows[0].test.length,
      10,
    );
  },
);

test(
  "Expanding windows retain earlier training records",
  () => {
    const result =
      createWalkForwardWindows(
        createRecords(90),
        {
          trainingSize:
            40,

          validationSize:
            10,

          testSize:
            10,

          stepSize:
            10,

          expanding:
            true,
        },
      );

    assert.equal(
      result.windows[0].training.length,
      40,
    );

    assert.equal(
      result.windows[1].training.length,
      50,
    );

    assert.equal(
      result.windows[2].training.length,
      60,
    );
  },
);

test(
  "Walk-forward splitter sorts records chronologically",
  () => {
    const records =
      createRecords(30)
        .reverse();

    const result =
      createWalkForwardWindows(
        records,
        {
          trainingSize:
            10,

          validationSize:
            5,

          testSize:
            5,
        },
      );

    assert.ok(
      new Date(
        result.windows[0].periods.training.start,
      ).getTime() <
      new Date(
        result.windows[0].periods.training.end,
      ).getTime(),
    );
  },
);

test(
  "Invalid timestamps are excluded safely",
  () => {
    const records = [
      ...createRecords(20),
      {
        timestamp:
          "invalid",
      },
    ];

    const result =
      createWalkForwardWindows(
        records,
        {
          trainingSize:
            10,

          validationSize:
            5,

          testSize:
            5,
        },
      );

    assert.equal(
      result.invalidRecordCount,
      1,
    );

    assert.equal(
      result.validRecordCount,
      20,
    );
  },
);

test(
  "Window validator detects no leakage",
  () => {
    const report =
      createWalkForwardWindows(
        createRecords(60),
        {
          trainingSize:
            30,

          validationSize:
            10,

          testSize:
            10,
        },
      );

    const validation =
      validateWalkForwardWindows(
        report,
      );

    assert.equal(
      validation.valid,
      true,
    );

    assert.deepEqual(
      validation.errors,
      [],
    );
  },
);

test(
  "Walk-forward splitter reports insufficient data",
  () => {
    const result =
      createWalkForwardWindows(
        createRecords(10),
        {
          trainingSize:
            20,

          validationSize:
            5,

          testSize:
            5,
        },
      );

    assert.equal(
      result.ready,
      false,
    );

    assert.equal(
      result.windowCount,
      0,
    );
  },
);

test(
  "Walk-forward splitter class is deterministic",
  () => {
    const splitter =
      new WalkForwardSplitterV2({
        trainingSize:
          20,

        validationSize:
          5,

        testSize:
          5,
      });

    const records =
      createRecords(50);

    assert.deepEqual(
      splitter.split(records),
      splitter.split(records),
    );
  },
);