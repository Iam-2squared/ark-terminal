import assert from "node:assert/strict";
import test from "node:test";

import {
  buildDashboardInput,
} from "../analysis/live-dashboard-controller.js";

test(
  "Dashboard input normalizes analysis data",
  () => {
    const result =
      buildDashboardInput({
        state: {
          symbol: "2410.T",

          analysis: {
            technicalScore: 82,
            dataQualityScore: 90,
          },

          prediction: {
            confidence: 88,
          },

          indicators: {
            rsi: 61,

            adx: {
              value: 29,
            },

            atr: {
              percent: 2.2,
            },
          },
        },

        macroInput: {
          nikkei: 1,
          nasdaq: 2,
          sox: 3,
          vix: 18,
        },
      });

    assert.equal(
      result.state.symbol,
      "2410.T",
    );

    assert.equal(
      result.state.analysis
        .technicalScore,
      82,
    );

    assert.equal(
      result.state.prediction
        .confidence,
      88,
    );

    assert.equal(
      result.marketInput.rsi,
      61,
    );

    assert.equal(
      result.macroInput.sox,
      3,
    );
  },
);

test(
  "Dashboard input supplies safe defaults",
  () => {
    const result =
      buildDashboardInput({});

    assert.equal(
      result.state.analysis
        .technicalScore,
      50,
    );

    assert.equal(
      result.state.prediction
        .confidence,
      50,
    );

    assert.equal(
      result.marketInput.rsi,
      50,
    );

    assert.equal(
      result.macroInput.vix,
      20,
    );
  },
);