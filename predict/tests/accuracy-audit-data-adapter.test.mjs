import assert from "node:assert/strict";
import test from "node:test";

import {
  adaptMarketHistory,
  buildAuditRows,
  normalizeMarketHistoryRow,
  validateMarketHistory,
} from "../analysis/accuracy-audit-data-adapter.js";

test(
  "Market row aliases are normalized",
  () => {
    const result =
      normalizeMarketHistoryRow({
        Date:
          "2026-01-01",

        Open:
          "100",

        High:
          "110",

        Low:
          "95",

        Close:
          "105",

        Volume:
          "5000",
      });

    assert.equal(
      result.date,
      "2026-01-01",
    );

    assert.equal(
      result.close,
      105,
    );

    assert.equal(
      result.volume,
      5000,
    );
  },
);

test(
  "Market history is sorted and deduplicated",
  () => {
    const result =
      adaptMarketHistory({
        symbol:
          "AAA",

        rows: [
          {
            date:
              "2026-01-02",

            close:
              102,
          },

          {
            date:
              "2026-01-01",

            close:
              100,
          },

          {
            date:
              "2026-01-02",

            close:
              103,
          },
        ],
      });

    assert.equal(
      result.length,
      2,
    );

    assert.equal(
      result[0].date,
      "2026-01-01",
    );

    assert.equal(
      result[1].close,
      103,
    );

    assert.equal(
      result[0].symbol,
      "AAA",
    );
  },
);

test(
  "Insufficient history is rejected",
  () => {
    const result =
      validateMarketHistory({
        rows: [
          {
            date:
              "2026-01-01",

            close:
              100,
          },
        ],

        minimumRows:
          30,
      });

    assert.equal(
      result.valid,
      false,
    );

    assert.ok(
      result.errors.includes(
        "insufficient_rows",
      ),
    );
  },
);

test(
  "Feature builder only receives visible history",
  () => {
    const rows =
      buildAuditRows({
        symbol:
          "AAA",

        rows: [
          {
            date:
              "2026-01-01",

            close:
              100,
          },

          {
            date:
              "2026-01-02",

            close:
              101,
          },
        ],

        featureBuilder({
          history,
        }) {
          return {
            visibleRows:
              history.length,
          };
        },
      });

    assert.equal(
      rows[0]
        .features
        .visibleRows,
      1,
    );

    assert.equal(
      rows[1]
        .features
        .visibleRows,
      2,
    );
  },
);