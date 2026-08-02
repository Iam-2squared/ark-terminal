import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAccuracyAuditRating,
  buildAccuracyAuditReport,
  exportAccuracyAuditCsv,
  exportAccuracyAuditJson,
} from "../analysis/accuracy-audit-report.js";

test(
  "Small sample receives sample shortage rating",
  () => {
    const result =
      buildAccuracyAuditRating({
        total:
          20,

        accuracy:
          100,

        profitFactor:
          10,

        averageStrategyReturn:
          5,

        maximumDrawdown:
          0,
      });

    assert.equal(
      result.grade,
      "N",
    );

    assert.equal(
      result.usable,
      false,
    );
  },
);

test(
  "Strong audit receives A rating",
  () => {
    const result =
      buildAccuracyAuditRating({
        total:
          300,

        accuracy:
          60,

        profitFactor:
          1.6,

        averageStrategyReturn:
          0.7,

        maximumDrawdown:
          10,
      });

    assert.equal(
      result.grade,
      "A",
    );

    assert.equal(
      result.usable,
      true,
    );
  },
);

test(
  "Audit report exposes important metrics",
  () => {
    const report =
      buildAccuracyAuditReport({
        version:
          "walk-forward-accuracy-audit-v1",

        horizon:
          5,

        sourceRows:
          400,

        summary: {
          total:
            300,

          accuracy:
            57,

          buyPrecision:
            60,

          sellPrecision:
            52,

          averageStrategyReturn:
            0.4,

          profitFactor:
            1.3,

          maximumDrawdown:
            12,

          calibrationError:
            0.18,
        },
      });

    assert.equal(
      report.horizon,
      5,
    );

    assert.equal(
      report.predictionCount,
      300,
    );

    assert.equal(
      report.labels.accuracy,
      "57%",
    );
  },
);

test(
  "Audit exports JSON and CSV",
  () => {
    const report = {
      version:
        "accuracy-audit-report-v1",

      rating: {
        grade:
          "B",
      },
    };

    const json =
      exportAccuracyAuditJson(
        report,
      );

    assert.equal(
      JSON.parse(json)
        .rating
        .grade,
      "B",
    );

    const csv =
      exportAccuracyAuditCsv({
        predictions: [
          {
            symbol:
              "AAA",

            entryDate:
              "2026-01-01",

            exitDate:
              "2026-01-06",

            horizon:
              5,

            action:
              "BUY",

            correct:
              true,
          },
        ],
      });

    assert.ok(
      csv.includes(
        "symbol",
      ),
    );

    assert.ok(
      csv.includes(
        "AAA",
      ),
    );
  },
);