import test from "node:test";
import assert from "node:assert/strict";

import {
  RealtimeAlertOrchestratorV2,
  orchestrateRealtimeAlerts,
} from "../realtime/realtime-alert-orchestrator-v2.js";

const NOW =
  Date.parse(
    "2026-08-03T10:00:00.000Z",
  );

function marketInput() {
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
    ],

    breadth: {
      advancing:
        700,

      declining:
        250,

      unchanged:
        50,
    },

    volatility: {
      value:
        14,
    },

    liquidity: {
      relativeVolume:
        1.3,
    },

    news: {
      sentiment:
        30,

      articleCount:
        8,
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
  };
}

function stableTicks() {
  return Array.from(
    {
      length:
        10,
    },
    (
      _,
      index,
    ) => ({
      symbol:
        "285A",

      price:
        100 +
        index *
        0.01,

      volume:
        1000,

      bid:
        99.9,

      ask:
        100.1,

      score:
        65,

      confidence:
        70,

      timestamp:
        NOW -
        (
          10 -
          index
        ) *
        60000,
    }),
  );
}

test(
  "Alert orchestrator combines realtime engines",
  () => {
    const result =
      orchestrateRealtimeAlerts({
        signals: [
          {
            symbol:
              "285A",

            direction:
              "BUY",

            confidence:
              82,

            score:
              85,

            riskScore:
              20,

            timestamp:
              "2026-08-03T09:59:30.000Z",
          },
        ],

        ticks:
          stableTicks(),

        market:
          marketInput(),

        now:
          () => NOW,
      });

    assert.equal(
      result.version,
      "realtime-alert-orchestrator-v2",
    );

    assert.equal(
      result.ready,
      true,
    );

    assert.equal(
      result.signalMonitor.ready,
      true,
    );

    assert.equal(
      result.marketContext.ready,
      true,
    );

    assert.equal(
      result.anomalyDetection.ready,
      true,
    );
  },
);

test(
  "Alert orchestrator creates dispatch queue",
  () => {
    const result =
      orchestrateRealtimeAlerts({
        signals: [
          {
            symbol:
              "285A",

            direction:
              "BUY",

            confidence:
              85,

            score:
              88,

            riskScore:
              20,

            timestamp:
              "2026-08-03T09:59:30.000Z",
          },
        ],

        market:
          marketInput(),

        now:
          () => NOW,
      });

    assert.ok(
      result.dispatchQueue.length >
      0,
    );

    assert.ok(
      result.dispatchQueue[0]
        .channels.includes(
          "IN_APP",
        ),
    );

    assert.ok(
      result.dispatchQueue[0]
        .channels.includes(
          "PUSH",
        ),
    );
  },
);

test(
  "Alert orchestrator blocks critical anomaly",
  () => {
    const ticks =
      stableTicks();

    ticks.push({
      symbol:
        "285A",

      price:
        140,

      volume:
        100000,

      bid:
        130,

      ask:
        150,

      score:
        95,

      confidence:
        95,

      timestamp:
        NOW,
    });

    const result =
      orchestrateRealtimeAlerts({
        ticks,

        market:
          marketInput(),

        now:
          () => NOW,

        anomalyConfig: {
          minimumSamples:
            8,

          priceZThreshold:
            2,

          volumeZThreshold:
            2,

          spreadThresholdPercent:
            2,
        },
      });

    const anomaly =
      result.events.find(
        (
          event,
        ) =>
          event.source ===
          "ANOMALY_DETECTOR",
      );

    assert.ok(anomaly);

    assert.ok(
      [
        "HIGH",
        "CRITICAL",
      ].includes(
        anomaly.severity,
      ),
    );

    assert.equal(
      anomaly.recommendation
        .tradable,
      false,
    );
  },
);

test(
  "Alert orchestrator suppresses repeated event during cooldown",
  () => {
    const signals = [
      {
        symbol:
          "285A",

        direction:
          "BUY",

        confidence:
          90,

        score:
          90,

        riskScore:
          20,

        timestamp:
          "2026-08-03T09:59:30.000Z",
      },
    ];

    const first =
      orchestrateRealtimeAlerts({
        signals,

        market:
          marketInput(),

        now:
          () => NOW,
      });

    const firstEvent =
      first.events.find(
        (
          event,
        ) =>
          event.source ===
          "SIGNAL_MONITOR",
      );

    const second =
      orchestrateRealtimeAlerts({
        signals,

        market:
          marketInput(),

        history: [
          {
            ...firstEvent,

            timestamp:
              "2026-08-03T09:59:45.000Z",
          },
        ],

        cooldownSeconds:
          300,

        now:
          () => NOW,
      });

    const repeated =
      second.events.find(
        (
          event,
        ) =>
          event.source ===
          "SIGNAL_MONITOR",
      );

    assert.equal(
      repeated.suppressed,
      true,
    );

    assert.equal(
      repeated.dispatchable,
      false,
    );
  },
);

test(
  "Alert orchestrator emits market risk event",
  () => {
    const market =
      marketInput();

    market.indices =
      market.indices.map(
        (
          index,
        ) => ({
          ...index,

          changePercent:
            -4,
        }),
      );

    market.breadth = {
      advancing:
        150,

      declining:
        800,

      unchanged:
        50,
    };

    market.volatility = {
      value:
        32,
    };

    market.news = {
      sentiment:
        -80,

      articleCount:
        15,
    };

    const result =
      orchestrateRealtimeAlerts({
        market,

        now:
          () => NOW,
      });

    const event =
      result.events.find(
        (
          item,
        ) =>
          item.source ===
          "MARKET_CONTEXT",
      );

    assert.ok(event);

    assert.equal(
      event.severity,
      "HIGH",
    );
  },
);

test(
  "Alert orchestrator supports channel restriction",
  () => {
    const result =
      orchestrateRealtimeAlerts({
        signals: [
          {
            symbol:
              "285A",

            direction:
              "BUY",

            confidence:
              90,

            score:
              90,

            riskScore:
              20,

            timestamp:
              "2026-08-03T09:59:30.000Z",
          },
        ],

        market:
          marketInput(),

        channels: [
          "IN_APP",
        ],

        now:
          () => NOW,
      });

    assert.deepEqual(
      result.dispatchQueue[0]
        .channels,
      [
        "IN_APP",
      ],
    );
  },
);

test(
  "Alert orchestrator validates clock",
  () => {
    assert.throws(
      () =>
        orchestrateRealtimeAlerts({
          now:
            NOW,
        }),

      /clock must be a function/,
    );
  },
);

test(
  "Alert orchestrator class is deterministic",
  () => {
    const orchestrator =
      new RealtimeAlertOrchestratorV2({
        now:
          () => NOW,
      });

    const input = {
      signals: [
        {
          symbol:
            "285A",

          direction:
            "BUY",

          confidence:
            90,

          score:
            90,

          riskScore:
            20,

          timestamp:
            "2026-08-03T09:59:30.000Z",
        },
      ],

      market:
        marketInput(),
    };

    assert.deepEqual(
      orchestrator.run(input),
      orchestrator.run(input),
    );
  },
);