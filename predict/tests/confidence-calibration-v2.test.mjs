import test from "node:test";
import assert from "node:assert/strict";

import {
  ConfidenceCalibrationV2Engine,
  buildConfidenceCalibrationModel,
  calculateBrierScore,
  calculateExpectedCalibrationError,
  calibrateConfidence,
  evaluateConfidenceCalibration,
} from "../analysis/confidence-calibration-v2.js";

test(
  "Perfect predictions have zero Brier score",
  () => {
    const result =
      calculateBrierScore([
        {
          confidence:
            100,
          outcome:
            1,
        },
        {
          confidence:
            0,
          outcome:
            0,
        },
      ]);

    assert.equal(
      result.score,
      0,
    );

    assert.equal(
      result.quality,
      "EXCELLENT",
    );
  },
);

test(
  "Expected calibration error detects overconfidence",
  () => {
    const result =
      calculateExpectedCalibrationError([
        {
          confidence:
            90,
          outcome:
            1,
        },
        {
          confidence:
            90,
          outcome:
            0,
        },
        {
          confidence:
            90,
          outcome:
            0,
        },
        {
          confidence:
            90,
          outcome:
            0,
        },
      ]);

    assert.equal(
      result.sampleSize,
      4,
    );

    assert.ok(
      result.ece >= 60,
    );
  },
);

test(
  "Calibration model learns actual accuracy per bin",
  () => {
    const model =
      buildConfidenceCalibrationModel([
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
            0,
        },
      ]);

    assert.equal(
      model.sampleSize,
      4,
    );

    assert.equal(
      model.bins[0].calibratedConfidence,
      50,
    );
  },
);

test(
  "Raw confidence is calibrated using learned accuracy",
  () => {
    const model =
      buildConfidenceCalibrationModel([
        {
          confidence:
            70,
          outcome:
            1,
        },
        {
          confidence:
            70,
          outcome:
            0,
        },
      ]);

    const calibrated =
      calibrateConfidence(
        70,
        model,
      );

    assert.equal(
      calibrated,
      50,
    );
  },
);

test(
  "Calibration evaluation reports overconfidence",
  () => {
    const result =
      evaluateConfidenceCalibration([
        {
          confidence:
            90,
          outcome:
            1,
        },
        {
          confidence:
            90,
          outcome:
            0,
        },
        {
          confidence:
            90,
          outcome:
            0,
        },
        {
          confidence:
            90,
          outcome:
            0,
        },
      ]);

    assert.equal(
      result.version,
      "confidence-calibration-v2",
    );

    assert.equal(
      result.accuracy,
      25,
    );

    assert.equal(
      result.averageConfidence,
      90,
    );

    assert.equal(
      result.biasDirection,
      "OVERCONFIDENT",
    );

    assert.equal(
      result.status,
      "POOR",
    );
  },
);

test(
  "Calibration evaluation handles empty input",
  () => {
    const result =
      evaluateConfidenceCalibration();

    assert.equal(
      result.sampleSize,
      0,
    );

    assert.equal(
      result.accuracy,
      null,
    );

    assert.equal(
      result.expectedCalibrationError,
      null,
    );

    assert.equal(
      result.status,
      "UNKNOWN",
    );
  },
);

test(
  "Confidence calibration engine produces deterministic output",
  () => {
    const engine =
      new ConfidenceCalibrationV2Engine({
        binCount:
          5,
      });

    const records = [
      {
        confidence:
          60,
        outcome:
          true,
      },
      {
        confidence:
          60,
        outcome:
          false,
      },
      {
        confidence:
          80,
        outcome:
          true,
      },
    ];

    assert.deepEqual(
      engine.evaluate(records),
      engine.evaluate(records),
    );
  },
);