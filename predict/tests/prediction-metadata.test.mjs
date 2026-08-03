import test from "node:test";
import assert from "node:assert/strict";

import {
  createPredictionId,
  createPredictionMetadata,
  validatePredictionMetadata,
} from "../analysis/prediction-metadata.js";

test(
  "Prediction metadata normalizes a prediction record",
  () => {
    const metadata =
      createPredictionMetadata({
        symbol:
          "285a",

        predictedAt:
          "2026-08-03T00:00:00.000Z",

        timeframe:
          3,

        direction:
          "強気",

        confidence:
          74.8,

        score:
          81,

        entryPrice:
          350,

        targetPrice:
          385,

        stopPrice:
          332.5,

        marketRegime:
          "UPTREND",

        modelVersion:
          "ark-v1",

        dataQualityScore:
          96,
      });

    assert.equal(
      metadata.schemaVersion,
      "prediction-metadata-v1",
    );

    assert.equal(
      metadata.symbol,
      "285A",
    );

    assert.equal(
      metadata.direction,
      "BUY",
    );

    assert.equal(
      metadata.timeframe.value,
      3,
    );

    assert.equal(
      metadata.timeframe.unit,
      "trading-days",
    );

    assert.equal(
      metadata.prices.entry,
      350,
    );

    assert.equal(
      metadata.modelVersion,
      "ark-v1",
    );

    assert.match(
      metadata.predictionId,
      /^pred_/,
    );
  },
);

test(
  "Prediction IDs are deterministic for the same prediction",
  () => {
    const input = {
      symbol:
        "7203",

      predictedAt:
        "2026-08-03T00:00:00.000Z",

      timeframe:
        5,

      modelVersion:
        "ark-v1",
    };

    assert.equal(
      createPredictionId(input),
      createPredictionId(input),
    );
  },
);

test(
  "Prediction metadata validator rejects malformed data",
  () => {
    const result =
      validatePredictionMetadata({
        schemaVersion:
          "prediction-metadata-v1",

        predictionId:
          "",

        symbol:
          "",

        predictedAt:
          "invalid",

        direction:
          "MAYBE",

        timeframe: {
          value: 0,
        },
      });

    assert.equal(
      result.valid,
      false,
    );

    assert.ok(
      result.errors.length >= 4,
    );
  },
);

test(
  "Prediction metadata validator accepts valid metadata",
  () => {
    const metadata =
      createPredictionMetadata({
        symbol:
          "AAPL",

        predictedAt:
          "2026-08-03T00:00:00.000Z",

        timeframe:
          "5d",

        direction:
          "SELL",

        confidence:
          70,

        score:
          30,

        modelVersion:
          "ark-v1",
      });

    const result =
      validatePredictionMetadata(
        metadata,
      );

    assert.equal(
      result.valid,
      true,
    );

    assert.deepEqual(
      result.errors,
      [],
    );
  },
);