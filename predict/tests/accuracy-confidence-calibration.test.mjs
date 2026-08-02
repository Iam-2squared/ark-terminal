import test from "node:test";
import assert from "node:assert/strict";

import {
  calculateConfidenceCalibration,
} from "../analysis/accuracy-confidence-calibration.js";

test("Confidence calibration calculates Brier and ECE", () => {
  const result = calculateConfidenceCalibration(
    [
      { confidence: 0.9, correct: true },
      { confidence: 0.8, correct: true },
      { confidence: 0.7, correct: false },
      { confidence: 0.4, correct: false },
    ],
    {
      binCount: 5,
    },
  );

  assert.equal(result.count, 4);
  assert.ok(result.brierScore > 0);
  assert.ok(
    result.expectedCalibrationError >= 0,
  );
  assert.equal(result.bins.length, 5);
});

test("Confidence calibration accepts percent confidence", () => {
  const result = calculateConfidenceCalibration([
    { confidence: 80, correct: true },
  ]);

  assert.equal(result.averageConfidence, 0.8);
  assert.equal(result.observedAccuracy, 1);
  assert.equal(result.state, "underconfident");
});

test("Confidence calibration handles empty rows", () => {
  const result = calculateConfidenceCalibration([]);

  assert.equal(result.count, 0);
  assert.equal(result.state, "insufficient-data");
  assert.deepEqual(result.bins, []);
});

test("Confidence calibration validates rows", () => {
  assert.throws(
    () => calculateConfidenceCalibration(null),
    {
      name: "TypeError",
    },
  );
});

