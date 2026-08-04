import test from "node:test";
import assert from "node:assert/strict";

import {
  RealtimeAnomalyDetectorV2,
  detectRealtimeAnomalies,
} from "../realtime/realtime-anomaly-detector-v2.js";

function createStableTicks(
  symbol = "285A",
  count = 20,
) {
  return Array.from(
    {
      length:
        count,
    },
    (
      _,
      index,
    ) => ({
      symbol,

      price:
        100 +
        (
          index % 3
        ) *
        0.1,

      volume:
        1000 +
        (
          index % 4
        ) *
        10,

      bid:
        99.9,

      ask:
        100.1,

      score:
        65,

      confidence:
        70,

      timestamp:
        Date.parse(
          "2026-08-03T09:00:00.000Z",
        ) +
        index *
        60000,
    }),
  );
}

test(
  "Realtime anomaly detector handles stable ticks",
  () => {
    const result =
      detectRealtimeAnomalies({
        ticks:
          createStableTicks(),
      });

    assert.equal(
      result.version,
      "realtime-anomaly-detector-v2",
    );

    assert.equal(
      result.ready,
      true,
    );

    assert.equal(
      result.symbolCount,
      1,
    );

    assert.equal(
      result.results[0]
        .recommendation
        .tradable,
      true,
    );
  },
);

test(
  "Realtime anomaly detector finds price spike",
  () => {
    const ticks =
      createStableTicks();

    ticks.push({
      symbol:
        "285A",

      price:
        130,

      volume:
        1000,

      bid:
        129.8,

      ask:
        130.2,

      score:
        65,

      confidence:
        70,

      timestamp:
        Date.parse(
          "2026-08-03T10:00:00.000Z",
        ),
    });

    const result =
      detectRealtimeAnomalies({
        ticks,

        priceZThreshold:
          2,
      });

    assert.equal(
      result.results[0]
        .anomalyDetected,
      true,
    );

    assert.ok(
      result.results[0]
        .anomalies.some(
          (
            anomaly,
          ) =>
            anomaly.type ===
            "PRICE_SPIKE" ||
            anomaly.type ===
            "RETURN_SHOCK",
        ),
    );
  },
);

test(
  "Realtime anomaly detector finds volume surge",
  () => {
    const ticks =
      createStableTicks();

    ticks.push({
      symbol:
        "285A",

      price:
        100,

      volume:
        50000,

      bid:
        99.9,

      ask:
        100.1,

      score:
        65,

      confidence:
        70,

      timestamp:
        Date.parse(
          "2026-08-03T10:00:00.000Z",
        ),
    });

    const result =
      detectRealtimeAnomalies({
        ticks,

        volumeZThreshold:
          2,
      });

    assert.ok(
      result.results[0]
        .anomalies.some(
          (
            anomaly,
          ) =>
            anomaly.type ===
            "VOLUME_SURGE",
        ),
    );
  },
);

test(
  "Realtime anomaly detector finds spread widening",
  () => {
    const ticks =
      createStableTicks();

    ticks.push({
      symbol:
        "285A",

      price:
        100,

      volume:
        1000,

      bid:
        95,

      ask:
        105,

      score:
        65,

      confidence:
        70,

      timestamp:
        Date.parse(
          "2026-08-03T10:00:00.000Z",
        ),
    });

    const result =
      detectRealtimeAnomalies({
        ticks,

        spreadThresholdPercent:
          2,
      });

    assert.ok(
      result.results[0]
        .anomalies.some(
          (
            anomaly,
          ) =>
            anomaly.type ===
            "SPREAD_WIDENING",
        ),
    );

    assert.equal(
      result.results[0]
        .recommendation
        .tradable,
      false,
    );
  },
);

test(
  "Realtime anomaly detector finds AI score jump",
  () => {
    const ticks =
      createStableTicks();

    ticks.push({
      symbol:
        "285A",

      price:
        100,

      volume:
        1000,

      bid:
        99.9,

      ask:
        100.1,

      score:
        95,

      confidence:
        95,

      timestamp:
        Date.parse(
          "2026-08-03T10:00:00.000Z",
        ),
    });

    const result =
      detectRealtimeAnomalies({
        ticks,

        scoreChangeThreshold:
          20,

        confidenceChangeThreshold:
          20,
      });

    assert.ok(
      result.results[0]
        .anomalies.some(
          (
            anomaly,
          ) =>
            anomaly.type ===
            "AI_SCORE_JUMP",
        ),
    );

    assert.ok(
      result.results[0]
        .anomalies.some(
          (
            anomaly,
          ) =>
            anomaly.type ===
            "CONFIDENCE_JUMP",
        ),
    );
  },
);

test(
  "Realtime anomaly detector requests more data",
  () => {
    const result =
      detectRealtimeAnomalies({
        ticks:
          createStableTicks(
            "AAA",
            3,
          ),

        minimumSamples:
          8,
      });

    assert.equal(
      result.results[0]
        .ready,
      false,
    );

    assert.equal(
      result.results[0]
        .recommendation
        .action,
      "COLLECT_MORE_DATA",
    );
  },
);

test(
  "Realtime anomaly detector handles multiple symbols",
  () => {
    const result =
      detectRealtimeAnomalies({
        ticks: [
          ...createStableTicks(
            "AAA",
          ),

          ...createStableTicks(
            "BBB",
          ),
        ],
      });

    assert.equal(
      result.symbolCount,
      2,
    );

    assert.equal(
      result.results.length,
      2,
    );
  },
);

test(
  "Realtime anomaly detector handles empty ticks",
  () => {
    const result =
      detectRealtimeAnomalies({
        ticks:
          [],
      });

    assert.equal(
      result.ready,
      false,
    );

    assert.equal(
      result.tickCount,
      0,
    );

    assert.deepEqual(
      result.results,
      [],
    );
  },
);

test(
  "Realtime anomaly detector validates input",
  () => {
    assert.throws(
      () =>
        detectRealtimeAnomalies({
          ticks:
            "invalid",
        }),

      /ticks must be an array/,
    );
  },
);

test(
  "Realtime anomaly detector class is deterministic",
  () => {
    const detector =
      new RealtimeAnomalyDetectorV2({
        minimumSamples:
          8,

        lookback:
          20,
      });

    const ticks =
      createStableTicks();

    assert.deepEqual(
      detector.detect(
        ticks,
      ),

      detector.detect(
        ticks,
      ),
    );
  },
);