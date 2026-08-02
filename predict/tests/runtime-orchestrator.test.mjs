import assert from "node:assert/strict";
import test from "node:test";

import {
  executeAiRuntime,
  normalizeRuntimeInput,
} from "../analysis/runtime-orchestrator.js";

test(
  "Runtime input is normalized",
  () => {
    const result =
      normalizeRuntimeInput({
        state: {
          symbol: "2410.T",

          analysis: {
            technicalScore: 85,
            dataQualityScore: 90,
          },

          prediction: {
            confidence: 88,
          },

          indicators: {
            rsi: 62,

            adx: {
              value: 30,
            },

            atr: {
              percent: 2,
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
      85,
    );

    assert.equal(
      result.state.prediction
        .confidence,
      88,
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
  "AI runtime produces analysis and HTML",
  () => {
    const result =
      executeAiRuntime({
        state: {
          analysis: {
            technicalScore: 88,
            totalScore: 90,
            dataQualityScore: 95,
          },

          prediction: {
            confidence: 90,
          },

          indicators: {
            rsi: 65,

            adx: {
              value: 32,
            },

            atr: {
              percent: 2,
            },
          },
        },

        macroInput: {
          nikkei: 1,
          nasdaq: 2,
          sox: 3,
          vix: 18,
        },

        marketInput: {
          trendScore: 85,
          volatility: 15,
          adx: 32,
          rsi: 65,
          vix: 18,
        },
      });

    assert.equal(
      result.status,
      "ready",
    );

    assert.equal(
      result.version,
      "ark-ai-runtime-v1",
    );

    assert.ok(
      result.analysis
        .dashboard
        .score > 0,
    );

    assert.ok(
      result.html.includes(
        "AI Analysis",
      ),
    );

    assert.ok(
      result.html.includes(
        "Buy Factors",
      ),
    );
  },
);

test(
  "AI runtime works with empty input",
  () => {
    const result =
      executeAiRuntime({});

    assert.equal(
      result.status,
      "ready",
    );

    assert.equal(
      typeof result.html,
      "string",
    );

    assert.ok(
      result.html.length > 0,
    );
  },
);