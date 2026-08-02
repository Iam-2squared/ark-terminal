import test from "node:test";
import assert from "node:assert/strict";

import {
  SECTOR_ROTATION_STATES,
  SectorRotationEngine,
  analyzeSectorRotation,
} from "../market-intelligence/sector-rotation-engine.js";

function report(sectors, timestamp = "2026-08-02T00:00:00.000Z") {
  return { sectors, timestamp };
}

test("Sector rotation identifies leading and lagging sectors", () => {
  const rotation = analyzeSectorRotation({
    current: report([
      { sector: "Technology", score: 75, confidence: 90 },
      { sector: "Energy", score: 30, confidence: 90 },
    ]),
    previous: report(
      [
        { sector: "Technology", score: 60, confidence: 80 },
        { sector: "Energy", score: 50, confidence: 80 },
      ],
      "2026-08-01T00:00:00.000Z",
    ),
  });

  assert.equal(rotation.leaders[0].sector, "Technology");
  assert.equal(rotation.leaders[0].rotationState, SECTOR_ROTATION_STATES.LEADING);
  assert.equal(rotation.weakening[0].sector, "Energy");
  assert.equal(rotation.weakening[0].rotationState, SECTOR_ROTATION_STATES.LAGGING);
  assert.equal(rotation.matchedCount, 2);
  assert.equal(rotation.confidence, 80);
});

test("Mid-ranked sectors can improve or weaken through score momentum", () => {
  const rotation = analyzeSectorRotation({
    current: report([
      { sector: "Finance", score: 55 },
      { sector: "Materials", score: 45 },
    ]),
    previous: report([
      { sector: "Finance", score: 45 },
      { sector: "Materials", score: 60 },
    ]),
  });

  assert.equal(
    rotation.sectors.find((sector) => sector.sector === "Finance").rotationState,
    SECTOR_ROTATION_STATES.IMPROVING,
  );
  assert.equal(
    rotation.sectors.find((sector) => sector.sector === "Materials").rotationState,
    SECTOR_ROTATION_STATES.WEAKENING,
  );
});

test("New sectors remain visible but cannot fabricate rotation history", () => {
  const rotation = analyzeSectorRotation({
    current: report([
      { sector: "Technology", score: 70 },
      { sector: "Healthcare", score: 65 },
    ]),
    previous: report([{ sector: "Technology", score: 60 }]),
  });
  const healthcare = rotation.sectors.find(
    (sector) => sector.sector === "Healthcare",
  );

  assert.equal(healthcare.rotationState, SECTOR_ROTATION_STATES.NEW);
  assert.equal(healthcare.rotationScore, null);
  assert.equal(rotation.matchedCount, 1);
  assert.equal(rotation.coverage, 50);
  assert.equal(rotation.confidence, 50);
});

test("No previous report produces an explicit unavailable rotation score", () => {
  const rotation = analyzeSectorRotation({
    current: report([{ sector: "Technology", score: 70 }]),
  });

  assert.equal(rotation.score, null);
  assert.equal(rotation.direction, "UNKNOWN");
  assert.equal(rotation.coverage, 0);
  assert.equal(rotation.rotationStrength, null);
});

test("Rotation ranks are recomputed from scores rather than trusted input", () => {
  const rotation = analyzeSectorRotation({
    current: report([
      { sector: "A", score: 80, rank: 99 },
      { sector: "B", score: 40, rank: 1 },
    ]),
    previous: report([
      { sector: "A", score: 30, rank: 1 },
      { sector: "B", score: 70, rank: 99 },
    ]),
  });

  assert.equal(rotation.sectors.find((sector) => sector.sector === "A").rank, 1);
  assert.equal(
    rotation.sectors.find((sector) => sector.sector === "A").previousRank,
    2,
  );
});

test("Rotation rejects a previous snapshot from the future", () => {
  assert.throws(
    () =>
      analyzeSectorRotation({
        current: report(
          [{ sector: "A", score: 70 }],
          "2026-08-01T00:00:00.000Z",
        ),
        previous: report(
          [{ sector: "A", score: 60 }],
          "2026-08-02T00:00:00.000Z",
        ),
      }),
    /cannot be newer/,
  );
});

test("Duplicate sectors and zero-confidence rotation are excluded", () => {
  const rotation = analyzeSectorRotation({
    current: report([
      { sector: "A", score: 60 },
      { sector: "A", score: 70 },
      { sector: "B", score: 30, confidence: 0 },
    ]),
    previous: report([
      { sector: "A", score: 50 },
      { sector: "B", score: 40 },
    ]),
  });

  assert.equal(rotation.requestedCount, 2);
  assert.equal(rotation.matchedCount, 1);
  assert.equal(rotation.sectors.find((sector) => sector.sector === "A").score, 70);
  assert.equal(rotation.rotationStrength, 100);
  assert.equal(rotation.coverage, 50);
});

test("SectorRotationEngine exposes stateless comparison", () => {
  const input = {
    current: report([{ sector: "A", score: 70 }]),
    previous: report([{ sector: "A", score: 60 }]),
  };
  const engine = new SectorRotationEngine();

  assert.deepEqual(engine.analyze(input), analyzeSectorRotation(input));
});
