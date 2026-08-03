import test from "node:test";
import assert from "node:assert/strict";

import {
  RealtimeMarketContextV2,
  buildRealtimeMarketContext,
} from "../realtime/realtime-market-context-v2.js";

const NOW =
  Date.parse(
    "2026-08-03T10:00:00.000Z",
  );

function healthyInput() {
  return {
    indices: [
      {
        symbol:
          "NIKKEI",

        changePercent:
          1.2,

        timestamp:
          "2026-08-03T09:59:00.000Z",
      },

      {
        symbol:
          "TOPIX",

        changePercent:
          0.8,

        timestamp:
          "2026-08-03T09:59:00.000Z",
      },

      {
        symbol:
          "NASDAQ",

        changePercent:
          1.5,

        timestamp:
          "2026-08-03T09:59:00.000Z",
      },

      {
        symbol:
          "SOX",

        changePercent:
          2,

        timestamp:
          "2026-08-03T09:59:00.000Z",
      },
    ],

    breadth: {
      advancing:
        780,

      declining:
        180,

      unchanged:
        40,
    },

    volatility: {
      value:
        14,
    },

    liquidity: {
      relativeVolume:
        1.4,
    },

    news: {
      sentiment:
        40,

      articleCount:
        10,

      confidence:
        80,
    },

    sourceTimestamps: {
      indices:
        "2026-08-03T09:59:00.000Z",

      breadth:
        "2026-08-03T09:59:00.000Z",

      volatility:
        "2026-08-03T09:59:00.000Z",

      liquidity:
        "2026-08-03T09:59:00.000Z",

      news:
        "2026-08-03T09:59:00.000Z",
    },

    now:
      () => NOW,
  };
}

test(
  "Realtime market context builds healthy risk-on state",
  () => {
    const result =
      buildRealtimeMarketContext(
        healthyInput(),
      );

    assert.equal(
      result.version,
      "realtime-market-context-v2",
    );

    assert.equal(
      result.ready,
      true,
    );

    assert.equal(
      result.regime,
      "RISK_ON",
    );

    assert.ok(
      result.score >= 68,
    );

    assert.equal(
      result.recommendation
        .action,
      "ALLOW_LONG_BIAS",
    );
  },
);

test(
  "Realtime market context calculates breadth",
  () => {
    const result =
      buildRealtimeMarketContext(
        healthyInput(),
      );

    assert.equal(
      result.breadth.total,
      1000,
    );

    assert.equal(
      result.breadth.advanceRatio,
      78,
    );

    assert.equal(
      result.breadth.score,
      78,
    );
  },
);

test(
  "Realtime market context detects risk-off state",
  () => {
    const input =
      healthyInput();

    input.indices =
      input.indices.map(
        (
          index,
        ) => ({
          ...index,

          changePercent:
            -3,
        }),
      );

    input.breadth = {
      advancing:
        200,

      declining:
        750,

      unchanged:
        50,
    };

    input.volatility = {
      value:
        28,
    };

    input.news = {
      sentiment:
        -70,

      articleCount:
        15,
    };

    const result =
      buildRealtimeMarketContext(
        input,
      );

    assert.equal(
      result.regime,
      "RISK_OFF",
    );

    assert.equal(
      result.recommendation
        .action,
      "REDUCE_RISK",
    );
  },
);

test(
  "Realtime market context detects high volatility",
  () => {
    const input =
      healthyInput();

    input.volatility = {
      value:
        36,
    };

    const result =
      buildRealtimeMarketContext(
        input,
      );

    assert.equal(
      result.regime,
      "HIGH_VOLATILITY",
    );

    assert.equal(
      result.recommendation
        .action,
      "TIGHTEN_RISK_LIMITS",
    );
  },
);

test(
  "Realtime market context identifies stale source",
  () => {
    const input =
      healthyInput();

    input.sourceTimestamps.news =
      "2026-08-03T09:40:00.000Z";

    const result =
      buildRealtimeMarketContext({
        ...input,

        staleAfterSeconds:
          300,
      });

    assert.equal(
      result.freshness
        .staleSourceCount,
      1,
    );

    assert.ok(
      result.freshness
        .staleSources.includes(
          "news",
        ),
    );

    assert.equal(
      result.recommendation
        .action,
      "REFRESH",
    );
  },
);

test(
  "Realtime market context handles partial data",
  () => {
    const result =
      buildRealtimeMarketContext({
        indices: [
          {
            symbol:
              "NIKKEI",

            score:
              60,
          },
        ],

        now:
          () => NOW,
      });

    assert.equal(
      result.ready,
      true,
    );

    assert.equal(
      result.diagnostics
        .indexCount,
      1,
    );

    assert.ok(
      Number.isFinite(
        result.score,
      ),
    );
  },
);

test(
  "Realtime market context validates input",
  () => {
    assert.throws(
      () =>
        buildRealtimeMarketContext({
          indices:
            "invalid",

          now:
            () => NOW,
        }),

      /indices must be an array/,
    );

    assert.throws(
      () =>
        buildRealtimeMarketContext({
          now:
            NOW,
        }),

      /clock must be a function/,
    );
  },
);

test(
  "Realtime market context class is deterministic",
  () => {
    const engine =
      new RealtimeMarketContextV2({
        now:
          () => NOW,
      });

    const input =
      healthyInput();

    delete input.now;

    assert.deepEqual(
      engine.build(input),
      engine.build(input),
    );
  },
);