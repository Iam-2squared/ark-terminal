import test from "node:test";
import assert from "node:assert/strict";

import {
  buildMarketBreadthV2,
  calculateAdvanceDecline,
  calculateBreadthThrust,
  calculateMcClellanOscillator,
  calculateVolumeBreadth,
} from "../market-intelligence/market-breadth-v2.js";

test(
  "Advance decline breadth is calculated",
  () => {
    const result =
      calculateAdvanceDecline({
        advancing: 700,
        declining: 200,
        unchanged: 100,
      });

    assert.equal(result.total, 1000);
    assert.equal(result.netAdvances, 500);
    assert.equal(result.advancePercent, 70);
    assert.equal(result.advanceDeclineRatio, 3.5);
  },
);

test(
  "Volume breadth is calculated",
  () => {
    const result =
      calculateVolumeBreadth({
        upVolume: 800,
        downVolume: 200,
      });

    assert.equal(result.netVolume, 600);
    assert.equal(result.upDownVolumeRatio, 4);
    assert.equal(result.upVolumePercent, 80);
  },
);

test(
  "Bullish breadth thrust is detected",
  () => {
    const result =
      calculateBreadthThrust({
        advancing: 650,
        declining: 350,
      });

    assert.equal(result.value, 65);
    assert.equal(result.signal, "bullish-thrust");
  },
);

test(
  "McClellan oscillator becomes ready after 39 samples",
  () => {
    const history =
      Array.from(
        { length: 39 },
        (_, index) => ({
          advancing: 600 + index,
          declining: 400 - index,
        }),
      );

    const result =
      calculateMcClellanOscillator(history);

    assert.equal(result.ready, true);
    assert.equal(result.sampleSize, 39);
    assert.ok(Number.isFinite(result.oscillator));
  },
);

test(
  "Healthy market produces broad strength",
  () => {
    const result =
      buildMarketBreadthV2({
        snapshot: {
          advancing: 780,
          declining: 180,
          unchanged: 40,
          upVolume: 850000,
          downVolume: 150000,
          newHighs: 120,
          newLows: 20,
          percentAbove20: 78,
          percentAbove50: 72,
          percentAbove200: 68,
        },
      });

    assert.equal(
      result.version,
      "market-breadth-v2",
    );

    assert.equal(
      result.regime,
      "broad-strength",
    );

    assert.ok(result.score >= 65);
    assert.equal(
      result.quality.hasIssueBreadth,
      true,
    );
  },
);

test(
  "Empty input is handled safely",
  () => {
    const result =
      buildMarketBreadthV2();

    assert.equal(result.score, null);
    assert.equal(result.regime, "neutral");
    assert.equal(
      result.quality.hasIssueBreadth,
      false,
    );
  },
);