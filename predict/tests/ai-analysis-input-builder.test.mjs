import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAIAnalysisInput,
  buildMarketIntelligenceInput,
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

    assert.equal(
      result
        .captureMarketIntelligenceSnapshot,
      false,
    );
  },
);

test(
  "AI input carries point-in-time Market Intelligence sources",
  () => {
    const state = {
      symbol:
        "7203.T",

      period:
        10,

      marketEnvironment: {
        score:
          76,

        availableCount:
          2,

        requestedCount:
          4,
      },

      context: {
        news: [
          {
            title:
              "上方修正",
          },
        ],

        disclosures: [
          {
            title:
              "決算発表",
          },
        ],
      },

      quote: {
        changePercent:
          1.5,
      },

      indicators: {
        atr: {
          percent:
            2.2,
        },
      },
    };

    const marketIntelligence =
      buildMarketIntelligenceInput(
        state,
      );

    const result =
      buildAIAnalysisInput({
        state,
      });

    assert.equal(
      marketIntelligence
        .compositeMarket
        .score,
      76,
    );

    assert.equal(
      marketIntelligence
        .compositeMarket
        .coverage,
      50,
    );

    assert.equal(
      marketIntelligence
        .newsItems
        .length,
      2,
    );

    assert.equal(
      marketIntelligence
        .newsItems[1]
        .type,
      "tdnet",
    );

    assert.equal(
      result.predictionHorizon,
      10,
    );

    assert.equal(
      result.marketIntelligence
        .technical
        .atrPercent,
      2.2,
    );

    assert.equal(
      result
        .captureMarketIntelligenceSnapshot,
      true,
    );
  },
);

test(
  "Explicit Market Intelligence input is reused without rewriting",
  () => {
    const explicit = {
      breadth: {
        score:
          80,
      },
    };

    assert.equal(
      buildMarketIntelligenceInput({
        marketIntelligenceInput:
          explicit,
      }),
      explicit,
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
