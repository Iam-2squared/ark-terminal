import test from "node:test";
import assert from "node:assert/strict";

import {
  SectorRotationV3,
  analyzeSectorRotation,
  compareSectorRotation,
} from "../market-intelligence/sector-rotation-v3.js";

const NOW =
  "2026-08-04T06:00:00.000Z";

function sectors() {
  return [
    {
      name:
        "Semiconductors",

      return1d:
        2.5,

      return5d:
        8,

      return20d:
        14,

      relativeStrength:
        20,

      breadthScore:
        70,

      volumeRatio:
        2,

      momentum:
        40,

      earningsRevision:
        20,

      riskScore:
        35,
    },

    {
      name:
        "Banks",

      return1d:
        1,

      return5d:
        3,

      return20d:
        4,

      relativeStrength:
        8,

      breadthScore:
        35,

      volumeRatio:
        1.3,

      momentum:
        15,

      earningsRevision:
        10,

      riskScore:
        45,
    },

    {
      name:
        "Biotechnology",

      return1d:
        -3,

      return5d:
        -8,

      return20d:
        -12,

      relativeStrength:
        -20,

      breadthScore:
        -70,

      volumeRatio:
        1.8,

      momentum:
        -40,

      earningsRevision:
        -20,

      riskScore:
        80,
    },

    {
      name:
        "Utilities",

      return1d:
        0.1,

      return5d:
        0.2,

      return20d:
        1,

      relativeStrength:
        0,

      breadthScore:
        5,

      volumeRatio:
        1,

      momentum:
        0,

      riskScore:
        35,
    },
  ];
}

test(
  "Ranks sector leaders and laggards",
  () => {
    const result =
      analyzeSectorRotation({
        sectors:
          sectors(),

        timestamp:
          NOW,
      });

    assert.equal(
      result.status,
      "READY",
    );

    assert.equal(
      result.sectors[0].name,
      "Semiconductors",
    );

    assert.equal(
      result.rotation
        .leadingSector,
      "Semiconductors",
    );

    assert.equal(
      result.rotation
        .laggingSector,
      "Biotechnology",
    );
  },
);

test(
  "Classifies strong leading sector",
  () => {
    const result =
      analyzeSectorRotation({
        sectors:
          sectors(),

        timestamp:
          NOW,
      });

    const semiconductor =
      result.sectors.find(
        (
          sector,
        ) =>
          sector.name ===
          "Semiconductors",
      );

    assert.equal(
      semiconductor.stage,
      "LEADING",
    );

    assert.equal(
      semiconductor
        .recommendation,
      "OVERWEIGHT",
    );
  },
);

test(
  "Classifies lagging sector",
  () => {
    const result =
      analyzeSectorRotation({
        sectors:
          sectors(),

        timestamp:
          NOW,
      });

    const biotechnology =
      result.sectors.find(
        (
          sector,
        ) =>
          sector.name ===
          "Biotechnology",
      );

    assert.equal(
      biotechnology.stage,
      "LAGGING",
    );

    assert.equal(
      biotechnology
        .recommendation,
      "UNDERWEIGHT",
    );
  },
);

test(
  "Detects meaningful sector rotation",
  () => {
    const result =
      analyzeSectorRotation({
        sectors:
          sectors(),

        timestamp:
          NOW,
      });

    assert.equal(
      result.rotation.detected,
      true,
    );

    assert.ok(
      result.rotation.strength >
      25,
    );
  },
);

test(
  "Returns insufficient data safely",
  () => {
    const result =
      analyzeSectorRotation({
        sectors: [
          {
            name:
              "Only",
          },
        ],

        timestamp:
          NOW,
      });

    assert.equal(
      result.status,
      "INSUFFICIENT_DATA",
    );
  },
);

test(
  "Compares rotation changes",
  () => {
    const previous =
      analyzeSectorRotation({
        sectors:
          sectors(),

        timestamp:
          NOW,
      });

    const nextSectors =
      sectors().map(
        (
          sector,
        ) =>
          sector.name ===
          "Banks"
            ? {
                ...sector,

                return5d:
                  12,

                return20d:
                  18,

                relativeStrength:
                  25,

                breadthScore:
                  80,

                momentum:
                  50,
              }
            : sector,
      );

    const current =
      analyzeSectorRotation({
        sectors:
          nextSectors,

        timestamp:
          "2026-08-05T06:00:00.000Z",
      });

    const comparison =
      compareSectorRotation({
        previous,
        current,
      });

    assert.equal(
      comparison.changed,
      true,
    );

    assert.ok(
      comparison.promoted.some(
        (
          sector,
        ) =>
          sector.name ===
          "Banks",
      ),
    );
  },
);

test(
  "Sector rotation class stores history",
  () => {
    const engine =
      new SectorRotationV3();

    engine.analyze({
      sectors:
        sectors(),

      timestamp:
        NOW,
    });

    engine.analyze({
      sectors:
        sectors(),

      timestamp:
        "2026-08-05T06:00:00.000Z",
    });

    assert.equal(
      engine.getHistory().length,
      2,
    );

    assert.equal(
      engine.latest().status,
      "READY",
    );

    engine.reset();

    assert.equal(
      engine.getHistory().length,
      0,
    );
  },
);

test(
  "Validates timestamp",
  () => {
    assert.throws(
      () =>
        analyzeSectorRotation({
          sectors:
            sectors(),

          timestamp:
            "invalid-date",
        }),

      /timestamp is invalid/,
    );
  },
);