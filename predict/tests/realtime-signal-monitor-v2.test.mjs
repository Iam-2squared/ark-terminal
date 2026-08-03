import test from "node:test";
import assert from "node:assert/strict";

import {
  RealtimeSignalMonitorV2,
  monitorRealtimeSignals,
} from "../realtime/realtime-signal-monitor-v2.js";

const NOW =
  Date.parse(
    "2026-08-03T10:00:00.000Z",
  );

function createSignals() {
  return [
    {
      symbol:
        "285A",

      direction:
        "BUY",

      confidence:
        70,

      score:
        72,

      riskScore:
        35,

      timestamp:
        "2026-08-03T09:58:00.000Z",
    },

    {
      symbol:
        "285A",

      direction:
        "BUY",

      confidence:
        78,

      score:
        80,

      riskScore:
        30,

      timestamp:
        "2026-08-03T09:59:30.000Z",
    },

    {
      symbol:
        "7203",

      direction:
        "SELL",

      confidence:
        65,

      score:
        62,

      riskScore:
        40,

      timestamp:
        "2026-08-03T09:59:00.000Z",
    },
  ];
}

test(
  "Realtime monitor analyzes current signals",
  () => {
    const result =
      monitorRealtimeSignals({
        signals:
          createSignals(),

        now:
          () => NOW,
      });

    assert.equal(
      result.version,
      "realtime-signal-monitor-v2",
    );

    assert.equal(
      result.ready,
      true,
    );

    assert.equal(
      result.signalCount,
      3,
    );

    assert.equal(
      result.symbolCount,
      2,
    );
  },
);

test(
  "Realtime monitor identifies high-priority signal",
  () => {
    const result =
      monitorRealtimeSignals({
        signals:
          createSignals(),

        now:
          () => NOW,
      });

    const monitor =
      result.monitors.find(
        (
          item,
        ) =>
          item.symbol ===
          "285A",
      );

    assert.equal(
      monitor.alertLevel,
      "HIGH_PRIORITY",
    );

    assert.equal(
      monitor.recommendation
        .tradable,
      true,
    );

    assert.equal(
      monitor.recommendation
        .action,
      "BUY",
    );
  },
);

test(
  "Realtime monitor detects direction change",
  () => {
    const signals = [
      {
        symbol:
          "AAA",

        direction:
          "BUY",

        confidence:
          70,

        score:
          70,

        riskScore:
          20,

        timestamp:
          "2026-08-03T09:58:00.000Z",
      },

      {
        symbol:
          "AAA",

        direction:
          "SELL",

        confidence:
          75,

        score:
          75,

        riskScore:
          20,

        timestamp:
          "2026-08-03T09:59:30.000Z",
      },
    ];

    const result =
      monitorRealtimeSignals({
        signals,

        now:
          () => NOW,
      });

    assert.equal(
      result.monitors[0]
        .directionChanged,
      true,
    );

    assert.equal(
      result.monitors[0]
        .alertLevel,
      "DIRECTION_CHANGE",
    );

    assert.equal(
      result.monitors[0]
        .recommendation
        .tradable,
      false,
    );
  },
);

test(
  "Realtime monitor blocks high-risk signal",
  () => {
    const result =
      monitorRealtimeSignals({
        signals: [
          {
            symbol:
              "RISK",

            direction:
              "BUY",

            confidence:
              90,

            score:
              90,

            riskScore:
              95,

            timestamp:
              "2026-08-03T09:59:30.000Z",
          },
        ],

        now:
          () => NOW,

        maximumRiskScore:
          70,
      });

    assert.equal(
      result.monitors[0]
        .alertLevel,
      "BLOCKED",
    );

    assert.equal(
      result.monitors[0]
        .recommendation
        .action,
      "BLOCK",
    );
  },
);

test(
  "Realtime monitor marks old signal stale",
  () => {
    const result =
      monitorRealtimeSignals({
        signals: [
          {
            symbol:
              "OLD",

            direction:
              "BUY",

            confidence:
              90,

            score:
              90,

            riskScore:
              20,

            timestamp:
              "2026-08-03T09:30:00.000Z",
          },
        ],

        now:
          () => NOW,

        staleWindowSeconds:
          600,
      });

    assert.equal(
      result.monitors[0]
        .freshness,
      "STALE",
    );

    assert.equal(
      result.monitors[0]
        .recommendation
        .action,
      "REFRESH",
    );
  },
);

test(
  "Realtime monitor handles empty signals",
  () => {
    const result =
      monitorRealtimeSignals({
        signals:
          [],

        now:
          () => NOW,
      });

    assert.equal(
      result.ready,
      false,
    );

    assert.equal(
      result.signalCount,
      0,
    );

    assert.deepEqual(
      result.monitors,
      [],
    );
  },
);

test(
  "Realtime monitor validates input",
  () => {
    assert.throws(
      () =>
        monitorRealtimeSignals({
          signals:
            "invalid",

          now:
            () => NOW,
        }),

      /signals must be an array/,
    );

    assert.throws(
      () =>
        monitorRealtimeSignals({
          signals:
            [],

          now:
            NOW,
        }),

      /clock must be a function/,
    );
  },
);

test(
  "Realtime monitor class is deterministic",
  () => {
    const monitor =
      new RealtimeSignalMonitorV2({
        now:
          () => NOW,

        minimumConfidence:
          55,
      });

    const signals =
      createSignals();

    assert.deepEqual(
      monitor.monitor(
        signals,
      ),

      monitor.monitor(
        signals,
      ),
    );
  },
);