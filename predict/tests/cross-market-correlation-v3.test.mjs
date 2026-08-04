import test from "node:test";
import assert from "node:assert/strict";

import {
  CrossMarketCorrelationV3,
  analyzeCrossMarketNetwork,
  analyzeMarketPair,
  buildCorrelationMatrix,
  calculatePearsonCorrelation,
  calculateReturns,
} from "../market-intelligence/cross-market-correlation-v3.js";

test(
  "Calculates price returns",
  () => {
    const result =
      calculateReturns([
        100,
        110,
        99,
      ]);

    assert.equal(
      result.length,
      2,
    );

    assert.equal(
      Number(
        result[0].toFixed(2),
      ),
      0.1,
    );
  },
);

test(
  "Calculates perfect positive correlation",
  () => {
    const result =
      calculatePearsonCorrelation(
        [
          1,
          2,
          3,
          4,
        ],

        [
          10,
          20,
          30,
          40,
        ],
      );

    assert.equal(
      result,
      1,
    );
  },
);

test(
  "Calculates perfect negative correlation",
  () => {
    const result =
      calculatePearsonCorrelation(
        [
          1,
          2,
          3,
          4,
        ],

        [
          40,
          30,
          20,
          10,
        ],
      );

    assert.equal(
      result,
      -1,
    );
  },
);

test(
  "Analyzes correlated market pair",
  () => {
    const result =
      analyzeMarketPair({
        primary: {
          symbol:
            "NIKKEI",

          prices: [
            100,
            102,
            105,
            107,
            110,
            113,
          ],
        },

        secondary: {
          symbol:
            "TOPIX",

          prices: [
            200,
            204,
            210,
            214,
            220,
            226,
          ],
        },
      });

    assert.ok(
      result.correlation >
      0.8,
    );

    assert.equal(
      result.risk
        .concentrationRisk,
      "HIGH",
    );
  },
);

test(
  "Detects hedge potential",
  () => {
    const result =
      analyzeMarketPair({
        useReturns:
          false,

        primary: {
          symbol:
            "EQUITY",

          prices: [
            1,
            2,
            3,
            4,
            5,
          ],
        },

        secondary: {
          symbol:
            "HEDGE",

          prices: [
            5,
            4,
            3,
            2,
            1,
          ],
        },
      });

    assert.equal(
      result.correlation,
      -1,
    );

    assert.equal(
      result.risk
        .hedgePotential,
      "HIGH",
    );
  },
);

test(
  "Builds symmetric correlation matrix",
  () => {
    const result =
      buildCorrelationMatrix({
        useReturns:
          false,

        markets: [
          {
            symbol:
              "A",

            prices: [
              1,
              2,
              3,
            ],
          },

          {
            symbol:
              "B",

            prices: [
              2,
              4,
              6,
            ],
          },
        ],
      });

    assert.equal(
      result.matrix.A.A,
      1,
    );

    assert.equal(
      result.matrix.A.B,
      result.matrix.B.A,
    );
  },
);

test(
  "Builds cross-market network",
  () => {
    const result =
      analyzeCrossMarketNetwork({
        correlationThreshold:
          0.8,

        markets: [
          {
            symbol:
              "A",

            prices: [
              100,
              102,
              104,
              106,
              108,
            ],
          },

          {
            symbol:
              "B",

            prices: [
              200,
              204,
              208,
              212,
              216,
            ],
          },

          {
            symbol:
              "C",

            prices: [
              100,
              90,
              105,
              88,
              110,
            ],
          },
        ],
      });

    assert.ok(
      result.summary
        .strongLinkCount >=
      1,
    );

    assert.ok(
      result.exposureGroups
        .some(
          (
            group,
          ) =>
            group.includes(
              "A",
            ) &&
            group.includes(
              "B",
            ),
        ),
    );
  },
);

test(
  "Correlation class stores history",
  () => {
    const intelligence =
      new CrossMarketCorrelationV3();

    intelligence.analyzePair({
      useReturns:
        false,

      primary: {
        symbol:
          "A",

        prices: [
          1,
          2,
          3,
        ],
      },

      secondary: {
        symbol:
          "B",

        prices: [
          2,
          4,
          6,
        ],
      },
    });

    assert.equal(
      intelligence
        .getHistory()
        .length,
      1,
    );

    assert.equal(
      intelligence.latest()
        .primarySymbol,
      "A",
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
  "Returns null for insufficient correlation data",
  () => {
    const result =
      calculatePearsonCorrelation(
        [
          1,
        ],

        [
          2,
        ],
      );

    assert.equal(
      result,
      null,
    );
  },
);