import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAIAnalysisInput,
  installAIAnalysisInputProvider,
} from "../analysis/ai-analysis-input-builder.js";

test(
  "AI input is built from analysis state",
  () => {
    const result =
      buildAIAnalysisInput({
        state: {
          symbol:
            "7203.T",

          price:
            1000,

          analysis: {
            technicalScore:
              82,

            confidence:
              88,
          },

          aiAnalysis: {
            overallAiScore:
              85,
          },

          macro: {
            score:
              75,

            sentiment:
              "BULLISH",
          },

          regime: {
            regime:
              "BULL",
          },
        },

        settings: {
          capital:
            500000,

          allocation:
            0.4,

          lotSize:
            100,
        },
      });

    assert.equal(
      result.symbol,
      "7203.T",
    );

    assert.equal(
      result.price,
      1000,
    );

    assert.equal(
      result.engines.length,
      3,
    );

    assert.equal(
      result.engines[0]
        .result
        .action,
      "BUY",
    );

    assert.equal(
      result.capital,
      500000,
    );

    assert.equal(
      result.regime,
      "BULL",
    );
  },
);

test(
  "AI input uses safe defaults",
  () => {
    const result =
      buildAIAnalysisInput({});

    assert.equal(
      result.engines.length,
      3,
    );

    assert.equal(
      result.engines[0]
        .result
        .score,
      50,
    );

    assert.equal(
      result.lotSize,
      100,
    );

    assert.equal(
      result.regime,
      "RANGE",
    );
  },
);

test(
  "Input provider is installed on window",
  () => {
    const windowRef = {
      __ARK_LATEST_ANALYSIS__: {
        symbol:
          "AAA",

        price:
          500,

        score:
          80,
      },

      __ARK_ANALYSIS_SETTINGS__: {
        capital:
          100000,
      },
    };

    const installed =
      installAIAnalysisInputProvider({
        windowRef,
      });

    assert.equal(
      installed,
      true,
    );

    assert.equal(
      windowRef
        .__ARK_ANALYSIS_INPUT__
        .symbol,
      "AAA",
    );

    assert.equal(
      windowRef
        .__ARK_ANALYSIS_INPUT__
        .capital,
      100000,
    );
  },
);