import test from "node:test";
import assert from "node:assert/strict";

import {
  MarketBreadthV3,
  analyzeBreadthHistory,
  analyzeMarketBreadth,
  calculateAdvanceDecline,
  calculateBreadthIndicators,
} from "../market-intelligence/market-breadth-v3.js";

const NOW =
  "2026-08-04T05:00:00.000Z";

function bullishStocks() {
  return Array.from(
    {
      length:
        20,
    },

    (
      _,
      index,
    ) => ({
      symbol:
        `BULL-${index}`,

      changePercent:
        index < 17
          ? 2
          : -0.5,

      volumeRatio:
        index < 17
          ? 2
          : 0.7,

      aboveSma25:
        index < 18,

      aboveSma75:
        index < 16,

      newHigh:
        index < 8,

      newLow:
        false,

      limitUp:
        index < 2,

      limitDown:
        false,
    }),
  );
}

function bearishStocks() {
  return Array.from(
    {
      length:
        20,
    },

    (
      _,
      index,
    ) => ({
      symbol:
        `BEAR-${index}`,

      changePercent:
        index < 17
          ? -2
          : 0.4,

      volumeRatio:
        index < 17
          ? 2
          : 0.6,

      aboveSma25:
        index >= 17,

      aboveSma75:
        index >= 18,

      newHigh:
        false,

      newLow:
        index < 9,

      limitUp:
        false,

      limitDown:
        index < 2,
    }),
  );
}

test(
  "Calculates advance decline statistics",
  () => {
    const result =
      calculateAdvanceDecline({
        stocks: [
          {
            changePercent:
              1,
          },

          {
            changePercent:
              2,
          },

          {
            changePercent:
              -1,
          },

          {
            changePercent:
              0,
          },
        ],
      });

    assert.equal(
      result.advancing,
      2,
    );

    assert.equal(
      result.declining,
      1,
    );

    assert.equal(
      result.unchanged,
      1,
    );

    assert.equal(
      result.ratio,
      2,
    );
  },
);

test(
  "Calculates breadth indicators",
  () => {
    const result =
      calculateBreadthIndicators({
        stocks:
          bullishStocks(),
      });

    assert.ok(
      result
        .aboveSma25Percent >
      80,
    );

    assert.ok(
      result
        .upVolumePercent >
      80,
    );

    assert.ok(
      result.newHighLowNet >
      0,
    );
  },
);

test(
  "Detects strong bullish breadth",
  () => {
    const result =
      analyzeMarketBreadth({
        stocks:
          bullishStocks(),

        indexChangePercent:
          2,

        timestamp:
          NOW,
      });

    assert.equal(
      result.status,
      "READY",
    );

    assert.ok(
      [
        "STRONG",
        "VERY_STRONG",
      ].includes(
        result.classification,
      ),
    );

    assert.equal(
      result.recommendation,
      "RISK_ON",
    );

    assert.ok(
      result.score >
      35,
    );
  },
);

test(
  "Detects weak bearish breadth",
  () => {
    const result =
      analyzeMarketBreadth({
        stocks:
          bearishStocks(),

        indexChangePercent:
          -2,

        timestamp:
          NOW,
      });

    assert.ok(
      [
        "WEAK",
        "CAPITULATION",
      ].includes(
        result.classification,
      ),
    );

    assert.equal(
      result.recommendation,
      "RISK_OFF",
    );

    assert.ok(
      result.score <
      -35,
    );
  },
);

test(
  "Detects bearish breadth divergence",
  () => {
    const result =
      analyzeMarketBreadth({
        stocks:
          bearishStocks(),

        indexChangePercent:
          1.5,

        timestamp:
          NOW,
      });

    assert.equal(
      result.divergence
        .detected,
      true,
    );

    assert.equal(
      result.divergence.type,
      "BEARISH_DIVERGENCE",
    );

    assert.equal(
      result.recommendation,
      "REDUCE_EXPOSURE",
    );
  },
);

test(
  "Returns insufficient data safely",
  () => {
    const result =
      analyzeMarketBreadth({
        stocks: [
          {
            changePercent:
              1,
          },
        ],

        timestamp:
          NOW,
      });

    assert.equal(
      result.status,
      "INSUFFICIENT_DATA",
    );

    assert.equal(
      result.confidence,
      0,
    );
  },
);

test(
  "Analyzes breadth history",
  () => {
    const result =
      analyzeBreadthHistory({
        history: [
          {
            score:
              10,
          },

          {
            score:
              20,
          },

          {
            score:
              35,
          },
        ],
      });

    assert.equal(
      result.trend,
      "IMPROVING",
    );

    assert.equal(
      result.improving,
      true,
    );

    assert.equal(
      result.latestScore,
      35,
    );
  },
);

test(
  "Market breadth class stores history",
  () => {
    const engine =
      new MarketBreadthV3();

    engine.analyze({
      stocks:
        bullishStocks(),

      timestamp:
        NOW,
    });

    assert.equal(
      engine
        .getHistory()
        .length,
      1,
    );

    assert.ok(
      engine.latest()
        .score >
      0,
    );

    engine.reset();

    assert.equal(
      engine
        .getHistory()
        .length,
      0,
    );
  },
);

test(
  "Validates timestamp",
  () => {
    assert.throws(
      () =>
        analyzeMarketBreadth({
          stocks:
            bullishStocks(),

          timestamp:
            "invalid-date",
        }),

      /timestamp is invalid/,
    );
  },
);