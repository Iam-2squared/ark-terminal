import test from "node:test";
import assert from "node:assert/strict";

import {
  ConceptDriftDetectorV2,
  detectConceptDrift,
  detectModelDriftBatch,
} from "../learning/concept-drift-detector-v2.js";

function createStableRecords() {
  return Array.from(
    {
      length:
        100,
    },
    (
      _,
      index,
    ) => ({
      id:
        `stable-${index}`,

      modelId:
        "stable-model",

      prediction: {
        direction:
          index % 5 === 0
            ? "SELL"
            : "BUY",

        confidence:
          70,
      },

      actualReturn:
        index % 5 === 0
          ? -1
          : 1,

      timestamp:
        new Date(
          Date.parse(
            "2026-01-01T00:00:00.000Z",
          ) +
          index *
          86400000,
        ).toISOString(),

      features: {
        rsi:
          50 +
          (
            index % 3
          ),

        volatility:
          2 +
          (
            index % 2
          ) *
          0.1,
      },
    }),
  );
}

function createDriftedRecords() {
  const records =
    createStableRecords();

  for (
    let index =
      records.length - 20;
    index <
      records.length;
    index += 1
  ) {
    records[index] = {
      ...records[index],

      prediction: {
        direction:
          "BUY",

        confidence:
          90,
      },

      actualReturn:
        -3,

      features: {
        rsi:
          85,

        volatility:
          8,
      },
    };
  }

  return records;
}

test(
  "Concept drift detector identifies stable behavior",
  () => {
    const result =
      detectConceptDrift({
        records:
          createStableRecords(),

        baselineWindow:
          60,

        recentWindow:
          20,

        minimumSamples:
          40,
      });

    assert.equal(
      result.version,
      "concept-drift-detector-v2",
    );

    assert.equal(
      result.ready,
      true,
    );

    assert.equal(
      result.driftDetected,
      false,
    );

    assert.ok(
      result.driftScore < 55,
    );

    assert.equal(
      result.recommendation.action,
      "CONTINUE",
    );
  },
);

test(
  "Concept drift detector identifies degraded model",
  () => {
    const result =
      detectConceptDrift({
        records:
          createDriftedRecords(),

        baselineWindow:
          60,

        recentWindow:
          20,

        minimumSamples:
          40,
      });

    assert.equal(
      result.ready,
      true,
    );

    assert.equal(
      result.driftDetected,
      true,
    );

    assert.ok(
      [
        "HIGH",
        "CRITICAL",
      ].includes(
        result.driftLevel,
      ),
    );

    assert.ok(
      result.performanceDrift
        .accuracyDrop >
      50,
    );

    assert.equal(
      result.recommendation
        .allowPromotion,
      false,
    );
  },
);

test(
  "Concept drift detector measures feature shift",
  () => {
    const result =
      detectConceptDrift({
        records:
          createDriftedRecords(),

        baselineWindow:
          60,

        recentWindow:
          20,
      });

    const rsi =
      result.featureDrift.find(
        (
          feature,
        ) =>
          feature.feature ===
          "rsi",
      );

    assert.ok(rsi);

    assert.ok(
      rsi.standardizedShift >
      1,
    );

    assert.ok(
      rsi.driftScore >
      25,
    );
  },
);

test(
  "Concept drift detector detects loss streak",
  () => {
    const result =
      detectConceptDrift({
        records:
          createDriftedRecords(),

        recentWindow:
          20,
      });

    assert.equal(
      result.sequentialDrift
        .recentLossStreak,
      20,
    );

    assert.equal(
      result.sequentialDrift
        .maximumLossStreak,
      20,
    );
  },
);

test(
  "Concept drift detector requires enough samples",
  () => {
    const result =
      detectConceptDrift({
        records:
          createStableRecords()
            .slice(
              0,
              10,
            ),

        minimumSamples:
          40,
      });

    assert.equal(
      result.ready,
      false,
    );

    assert.equal(
      result.recommendation
        .action,
      "COLLECT_MORE_DATA",
    );
  },
);

test(
  "Concept drift detector rejects invalid records",
  () => {
    assert.throws(
      () =>
        detectConceptDrift({
          records:
            "invalid",
        }),

      /records must be an array/,
    );
  },
);

test(
  "Concept drift batch reports drifted models",
  () => {
    const stable =
      createStableRecords();

    const drifted =
      createDriftedRecords()
        .map(
          (
            record,
          ) => ({
            ...record,

            modelId:
              "drifted-model",
          }),
        );

    const result =
      detectModelDriftBatch({
        models: [
          {
            id:
              "stable-model",
          },

          {
            id:
              "drifted-model",
          },
        ],

        records: [
          ...stable,
          ...drifted,
        ],

        config: {
          minimumSamples:
            40,

          recentWindow:
            20,

          baselineWindow:
            60,
        },
      });

    assert.equal(
      result.modelCount,
      2,
    );

    assert.equal(
      result.driftedModelCount,
      1,
    );
  },
);

test(
  "Concept drift detector is deterministic",
  () => {
    const detector =
      new ConceptDriftDetectorV2({
        baselineWindow:
          60,

        recentWindow:
          20,

        minimumSamples:
          40,
      });

    const records =
      createDriftedRecords();

    assert.deepEqual(
      detector.detect(
        records,
      ),

      detector.detect(
        records,
      ),
    );
  },
);