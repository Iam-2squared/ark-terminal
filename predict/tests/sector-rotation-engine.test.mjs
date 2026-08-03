import test from "node:test";
import assert from "node:assert/strict";

import {
  evaluateSector,
  rankSectorRotation,
} from "../market-intelligence/sector-rotation-engine.js";

test(
  "Sector evaluator detects a leading sector",
  () => {
    const result =
      evaluateSector(
        {
          name:
            "Technology",

          return5d:
            4,

          return20d:
            9,

          return60d:
            18,

          percentAbove20:
            82,

          percentAbove50:
            76,

          advanceDeclineRatio:
            3.2,

          relativeVolume:
            1.6,

          upVolumeRatio:
            0.78,

          volatility20d:
            4,

          maxDrawdown60d:
            -5,
        },
        {
          return20d:
            2,
        },
      );

    assert.equal(
      result.sector,
      "Technology",
    );

    assert.equal(
      result.signal,
      "leading",
    );

    assert.ok(
      result.score >= 65,
    );

    assert.equal(
      result.dataQuality.availableComponents,
      5,
    );
  },
);

test(
  "Sector evaluator detects a lagging sector",
  () => {
    const result =
      evaluateSector(
        {
          name:
            "Utilities",

          return5d:
            -5,

          return20d:
            -10,

          return60d:
            -18,

          percentAbove20:
            18,

          percentAbove50:
            22,

          advanceDeclineRatio:
            0.25,

          relativeVolume:
            0.6,

          upVolumeRatio:
            0.2,

          volatility20d:
            18,

          maxDrawdown60d:
            -28,
        },
        {
          return20d:
            3,
        },
      );

    assert.equal(
      result.signal,
      "lagging",
    );

    assert.ok(
      result.score <= 35,
    );
  },
);

test(
  "Sector rotation ranks strongest sector first",
  () => {
    const result =
      rankSectorRotation({
        benchmark: {
          return20d:
            2,
        },

        sectors: [
          {
            name:
              "Technology",

            return5d:
              5,

            return20d:
              10,

            return60d:
              20,

            percentAbove20:
              85,

            percentAbove50:
              80,

            advanceDeclineRatio:
              4,

            relativeVolume:
              1.8,

            upVolumeRatio:
              0.82,

            volatility20d:
              4,

            maxDrawdown60d:
              -4,
          },
          {
            name:
              "Financials",

            return5d:
              1,

            return20d:
              3,

            return60d:
              5,

            percentAbove20:
              58,

            percentAbove50:
              55,

            advanceDeclineRatio:
              1.2,

            relativeVolume:
              1,

            upVolumeRatio:
              0.52,

            volatility20d:
              8,

            maxDrawdown60d:
              -10,
          },
          {
            name:
              "Utilities",

            return5d:
              -4,

            return20d:
              -8,

            return60d:
              -14,

            percentAbove20:
              20,

            percentAbove50:
              25,

            advanceDeclineRatio:
              0.3,

            relativeVolume:
              0.7,

            upVolumeRatio:
              0.25,

            volatility20d:
              16,

            maxDrawdown60d:
              -24,
          },
        ],
      });

    assert.equal(
      result.version,
      "sector-rotation-v1",
    );

    assert.equal(
      result.sectors[0].sector,
      "Technology",
    );

    assert.equal(
      result.sectors[0].rank,
      1,
    );

    assert.equal(
      result.summary.strongest.sector,
      "Technology",
    );

    assert.equal(
      result.summary.weakest.sector,
      "Utilities",
    );
  },
);

test(
  "Sector rotation handles empty input",
  () => {
    const result =
      rankSectorRotation();

    assert.equal(
      result.summary.sectorCount,
      0,
    );

    assert.equal(
      result.summary.strongest,
      null,
    );

    assert.equal(
      result.dispersion,
      null,
    );
  },
);