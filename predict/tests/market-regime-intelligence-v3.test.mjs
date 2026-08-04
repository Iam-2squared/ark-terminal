import test from "node:test";
import assert from "node:assert/strict";

import {
  MarketRegimeIntelligenceV3,
  detectMarketRegime,
  detectMultiMarketRegime,
} from "../market-intelligence/market-regime-intelligence-v3.js";

const NOW =
  "2026-08-04T04:00:00.000Z";

test(
  "Detects strong bull regime",
  () => {
    const result =
      detectMarketRegime({
        input: {
          symbol:
            "NIKKEI",

          timestamp:
            NOW,

          price:
            42000,

          sma5:
            41800,

          sma25:
            40500,

          sma75:
            39000,

          rsi:
            65,

          macd:
            200,

          macdSignal:
            100,

          adx:
            35,

          atrPercent:
            1.5,

          changePercent:
            2,

          marketBreadth:
            60,

          indexTrendScore:
            15,
        },
      });

    assert.equal(
      result.regime,
      "STRONG_BULL",
    );

    assert.equal(
      result.strategy.bias,
      "LONG",
    );

    assert.ok(
      result.confidence >
      50,
    );
  },
);

test(
  "Detects bear regime",
  () => {
    const result =
      detectMarketRegime({
        input: {
          symbol:
            "TOPIX",

          timestamp:
            NOW,

          price:
            2700,

          sma5:
            2750,

          sma25:
            2800,

          sma75:
            2900,

          rsi:
            38,

          macd:
            -50,

          macdSignal:
            -20,

          atrPercent:
            2,

          changePercent:
            -1.5,

          marketBreadth:
            -50,

          indexTrendScore:
            -15,
        },
      });

    assert.ok(
      [
        "BEAR",
        "STRONG_BEAR",
      ].includes(
        result.regime,
      ),
    );

    assert.equal(
      result.strategy.bias,
      "DEFENSIVE",
    );
  },
);

test(
  "Detects crash regime",
  () => {
    const result =
      detectMarketRegime({
        input: {
          symbol:
            "MARKET",

          timestamp:
            NOW,

          price:
            30000,

          sma25:
            35000,

          rsi:
            20,

          changePercent:
            -10,

          atrPercent:
            9,

          drawdownPercent:
            -18,

          volumeRatio:
            3,
        },
      });

    assert.equal(
      result.regime,
      "CRASH",
    );

    assert.equal(
      result.strategy
        .positionMultiplier,
      0,
    );

    assert.equal(
      result.strategy.entryMode,
      "BLOCK_NEW_TRADES",
    );
  },
);

test(
  "Detects range regime",
  () => {
    const result =
      detectMarketRegime({
        input: {
          symbol:
            "RANGE",

          timestamp:
            NOW,

          price:
            1000,

          sma5:
            1001,

          sma25:
            1000,

          sma75:
            999,

          rsi:
            50,

          macd:
            0,

          macdSignal:
            0,

          atrPercent:
            1,

          changePercent:
            0,

          marketBreadth:
            0,

          indexTrendScore:
            0,
        },
      });

    assert.equal(
      result.regime,
      "RANGE",
    );

    assert.equal(
      result.strategy
        .preferredStrategy,
      "MEAN_REVERSION",
    );
  },
);

test(
  "Returns insufficient data safely",
  () => {
    const result =
      detectMarketRegime({
        input: {
          symbol:
            "EMPTY",

          timestamp:
            NOW,
        },
      });

    assert.equal(
      result.regime,
      "INSUFFICIENT_DATA",
    );

    assert.equal(
      result.confidence,
      0,
    );
  },
);

test(
  "Creates multi-market consensus",
  () => {
    const result =
      detectMultiMarketRegime({
        markets: [
          {
            symbol:
              "NIKKEI",

            timestamp:
              NOW,

            price:
              42000,

            sma5:
              41800,

            sma25:
              40500,

            sma75:
              39000,

            rsi:
              65,

            macd:
              100,

            macdSignal:
              50,

            changePercent:
              2,

            marketBreadth:
              60,

            indexTrendScore:
              15,
          },

          {
            symbol:
              "TOPIX",

            timestamp:
              NOW,

            price:
              3000,

            sma5:
              2980,

            sma25:
              2900,

            sma75:
              2800,

            rsi:
              62,

            macd:
              20,

            macdSignal:
              10,

            changePercent:
              1.5,

            marketBreadth:
              45,

            indexTrendScore:
              10,
          },
        ],
      });

    assert.ok(
      [
        "BULL",
        "STRONG_BULL",
      ].includes(
        result.regime,
      ),
    );

    assert.equal(
      result.markets.length,
      2,
    );
  },
);

test(
  "Market regime class stores history",
  () => {
    const intelligence =
      new MarketRegimeIntelligenceV3();

    intelligence.detect({
      symbol:
        "TEST",

      timestamp:
        NOW,

      price:
        100,

      sma25:
        95,

      rsi:
        60,
    });

    assert.equal(
      intelligence
        .getHistory()
        .length,
      1,
    );

    assert.equal(
      intelligence.latest()
        .symbol,
      "TEST",
    );

    intelligence.reset();

    assert.equal(
      intelligence
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
        detectMarketRegime({
          input: {
            timestamp:
              "invalid-date",

            price:
              100,

            sma25:
              90,
          },
        }),

      /timestamp is invalid/,
    );
  },
);