import assert from "node:assert/strict";
import test from "node:test";

import {
  applyCloudOutcomes,
  mergePredictionRecords,
  mirrorPredictionToCloud,
  savePredictionToCloud,
  selectCloudPredictions,
} from "../cloud/prediction-cloud-repository.js";

function samplePrediction(
  overrides = {},
) {
  return {
    id:
      "prediction-1",
    createdAt:
      "2026-08-01T00:00:00.000Z",
    symbol:
      "7203.T",
    period:
      5,
    status:
      "pending",
    source:
      "live",
    predictionPrice:
      100,
    actualPrice:
      null,
    actualReturn:
      null,
    hit:
      null,
    ...overrides,
  };
}

test(
  "Cloud prediction selection excludes walk-forward archives",
  () => {
    const selected = selectCloudPredictions([
      samplePrediction(),
      samplePrediction({
        id:
          "walk-forward-1",
        source:
          "walk-forward",
      }),
      {
        id:
          "missing-source",
        createdAt:
          "2026-08-02T00:00:00.000Z",
        symbol:
          "6758.T",
      },
    ]);

    assert.deepEqual(
      selected.map((record) => record.id),
      [
        "prediction-1",
        "missing-source",
      ],
    );
  },
);

test(
  "Cloud outcomes update matching predictions only",
  () => {
    const result = applyCloudOutcomes(
      [
        samplePrediction(),
        samplePrediction({
          id:
            "prediction-2",
          symbol:
            "6758.T",
        }),
      ],
      [
        {
          id:
            "prediction-1",
          status:
            "resolved",
          actualPrice:
            110,
          actualReturn:
            10,
          hit:
            true,
        },
      ],
    );

    assert.equal(
      result[0].status,
      "resolved",
    );
    assert.equal(
      result[0].actualReturn,
      10,
    );
    assert.equal(
      result[1].status,
      "pending",
    );
  },
);

test(
  "Prediction merge preserves unique ids and newer values",
  () => {
    const cloud = samplePrediction({
      updatedAt:
        "2026-08-02T00:00:00.000Z",
      status:
        "resolved",
    });
    const local = samplePrediction({
      updatedAt:
        "2026-08-01T00:00:00.000Z",
      status:
        "pending",
    });

    const merged = mergePredictionRecords(
      [local],
      [cloud],
    );

    assert.equal(merged.length, 1);
    assert.equal(
      merged[0].status,
      "resolved",
    );
  },
);

test(
  "Resolved prediction is written to prediction and outcome collections",
  async () => {
    const requests = [];
    const record = samplePrediction({
      status:
        "resolved",
      actualPrice:
        110,
      actualReturn:
        10,
      hit:
        true,
    });

    const fetchImpl = async (url, options) => {
      requests.push({
        url,
        options,
      });

      return {
        ok: true,
        status: 200,
        json:
          async () => ({
            saved: true,
          }),
      };
    };

    const result = await savePredictionToCloud(
      record,
      {
        fetchImpl,
      },
    );

    assert.equal(result.saved, true);
    assert.equal(result.outcomeSaved, true);
    assert.equal(requests.length, 2);

    const firstBody = JSON.parse(
      requests[0].options.body,
    );
    const secondBody = JSON.parse(
      requests[1].options.body,
    );

    assert.equal(
      firstBody.collection,
      "predictions",
    );
    assert.equal(
      secondBody.collection,
      "prediction_outcomes",
    );
    assert.equal(
      requests[0].options.credentials,
      "include",
    );
  },
);

test(
  "Prediction mirror is a no-op when cloud session is unavailable",
  async () => {
    let saveCalls = 0;

    const result = await mirrorPredictionToCloud(
      samplePrediction(),
      {
        statusProvider:
          async () => ({
            configured: true,
            authenticated: false,
            storageConfigured: true,
          }),
        fetchImpl:
          async () => {
            saveCalls += 1;
            throw new Error(
              "should not be called",
            );
          },
      },
    );

    assert.equal(result.saved, false);
    assert.equal(
      result.reason,
      "not_authenticated",
    );
    assert.equal(saveCalls, 0);
  },
);
