import assert from "node:assert/strict";
import test from "node:test";

import {
  normalizeAnalysisEventSource,
} from "../analysis/analysis-event-bridge.js";

test(
  "Analysis event source is normalized",
  () => {
    const result =
      normalizeAnalysisEventSource({
        symbol: "2410.T",

        totalScore: 84,

        confidence: 91,

        indicators: {
          rsi: 62,

          adx: {
            value: 30,
          },

          atr: {
            percent: 2,
          },
        },

        macro: {
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
      84,
    );

    assert.equal(
      result.state.prediction
        .confidence,
      91,
    );

    assert.equal(
      result.marketInput.rsi,
      62,
    );

    assert.equal(
      result.macroInput.sox,
      3,
    );
  },
);

test(
  "Analysis event source uses safe defaults",
  () => {
    const result =
      normalizeAnalysisEventSource({});

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
      result.marketInput.adx,
      20,
    );

    assert.equal(
      result.macroInput.vix,
      20,
    );
  },
);