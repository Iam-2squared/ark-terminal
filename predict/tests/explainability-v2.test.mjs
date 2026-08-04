import test from "node:test";
import assert from "node:assert/strict";

import {
  ExplainabilityV2Engine,
  buildExplainabilityReport,
} from "../analysis/explainability-v2.js";

const NOW =
  Date.parse(
    "2026-08-03T09:00:00.000Z",
  );

test(
  "Explainability v2 ranks strongest feature first",
  () => {
    const result =
      buildExplainabilityReport({
        prediction: {
          direction:
            "BUY",
          confidence:
            78,
        },
        features: [
          {
            name:
              "RSI",
            contribution:
              12,
          },
          {
            name:
              "MACD",
            contribution:
              28,
          },
          {
            name:
              "Volume",
            contribution:
              -8,
          },
        ],
        now:
          () => NOW,
      });

    assert.equal(
      result.version,
      "explainability-v2",
    );

    assert.equal(
      result.rankedFeatures[0].name,
      "MACD",
    );

    assert.equal(
      result.rankedFeatures[0].rank,
      1,
    );

    assert.equal(
      result.agreement,
      "AGREES",
    );
  },
);

test(
  "Explainability v2 detects prediction conflicts",
  () => {
    const result =
      buildExplainabilityReport({
        prediction: {
          direction:
            "BUY",
          confidence:
            60,
        },
        features: [
          {
            name:
              "Trend",
            contribution:
              -30,
          },
          {
            name:
              "Volume",
            contribution:
              -20,
          },
          {
            name:
              "RSI",
            contribution:
              5,
          },
        ],
        now:
          () => NOW,
      });

    assert.equal(
      result.agreement,
      "CONFLICTS",
    );

    assert.equal(
      result.conflicts.length,
      2,
    );

    assert.ok(
      result.warnings.length >= 1,
    );
  },
);

test(
  "Explainability v2 identifies strongest bullish and bearish factors",
  () => {
    const result =
      buildExplainabilityReport({
        prediction: {
          direction:
            "SELL",
          confidence:
            70,
        },
        features: [
          {
            name:
              "MACD",
            contribution:
              18,
          },
          {
            name:
              "Trend",
            contribution:
              -25,
          },
          {
            name:
              "Liquidity",
            contribution:
              -10,
          },
        ],
        now:
          () => NOW,
      });

    assert.equal(
      result.strongestBullish.name,
      "MACD",
    );

    assert.equal(
      result.strongestBearish.name,
      "Trend",
    );

    assert.equal(
      result.prediction.direction,
      "BEARISH",
    );
  },
);

test(
  "Explainability v2 handles empty features",
  () => {
    const result =
      buildExplainabilityReport({
        prediction: {
          direction:
            "NEUTRAL",
          confidence:
            30,
        },
        now:
          () => NOW,
      });

    assert.equal(
      result.featureCount,
      0,
    );

    assert.equal(
      result.explanationQuality,
      "UNAVAILABLE",
    );

    assert.equal(
      result.strongestBullish,
      null,
    );

    assert.equal(
      result.strongestBearish,
      null,
    );
  },
);

test(
  "Explainability v2 produces deterministic reports",
  () => {
    const engine =
      new ExplainabilityV2Engine({
        now:
          () => NOW,
      });

    const input = {
      prediction: {
        direction:
          "BUY",
        confidence:
          75,
      },
      features: {
        rsi: {
          contribution:
            10,
        },
        macd: {
          contribution:
            20,
        },
      },
    };

    assert.deepEqual(
      engine.explain(input),
      engine.explain(input),
    );
  },
);

test(
  "Explainability v2 validates clock and timestamp",
  () => {
    assert.throws(
      () =>
        buildExplainabilityReport({
          now:
            NOW,
        }),
      /clock must be a function/,
    );

    assert.throws(
      () =>
        buildExplainabilityReport({
          timestamp:
            "invalid",
        }),
      /timestamp is invalid/,
    );
  },
);