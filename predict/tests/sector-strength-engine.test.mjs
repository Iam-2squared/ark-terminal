import test from "node:test";
import assert from "node:assert/strict";

import {
  SectorStrengthEngine,
  analyzeSectorStrength,
} from "../market-intelligence/sector-strength-engine.js";

function observation(symbol, sector, changePercent, ratio = 1) {
  return {
    symbol,
    sector,
    changePercent,
    volume: 100 * ratio,
    averageVolume: 100,
    turnover: 1000 * ratio,
    averageTurnover: 1000,
    confidence: 100,
  };
}

function sectorInputs() {
  return [
    observation("T1", "Technology", 2, 2),
    observation("T2", "Technology", 1, 1.5),
    observation("T3", "Technology", -0.5, 1),
    observation("E1", "Energy", -2, 2),
    observation("E2", "Energy", -1, 1.5),
    observation("E3", "Energy", 0.5, 1),
  ];
}

test("Sector strength ranks broad positive sectors above weak sectors", () => {
  const report = analyzeSectorStrength(sectorInputs());

  assert.equal(report.sectorCount, 2);
  assert.equal(report.leaders[0].sector, "Technology");
  assert.equal(report.leaders[0].rank, 1);
  assert.equal(report.laggards[0].sector, "Energy");
  assert.ok(report.leaders[0].score > report.laggards[0].score);
  assert.ok(report.dispersion > 0);
});

test("Sector strength reuses liquidity metrics for each sector", () => {
  const report = analyzeSectorStrength(sectorInputs());
  const technology = report.sectors.find(
    (sector) => sector.sector === "Technology",
  );

  assert.equal(technology.medianVolumeRatio, 1.5);
  assert.equal(typeof technology.liquidity.score, "number");
  assert.equal(technology.components.length, 3);
});

test("Small sector samples remain usable with reduced confidence", () => {
  const report = analyzeSectorStrength([
    observation("T1", "Technology", 2, 2),
  ]);

  assert.equal(report.sectorCount, 1);
  assert.equal(report.sectors[0].score, 100);
  assert.ok(report.sectors[0].confidence < 40);
});

test("Existing industry field is accepted as the sector source", () => {
  const report = analyzeSectorStrength([
    {
      ...observation("A", "ignored", 1),
      sector: undefined,
      industry: "Finance",
    },
  ]);

  assert.equal(report.sectors[0].sector, "Finance");
});

test("Unclassified or missing-change rows reduce sector coverage", () => {
  const inputs = sectorInputs();
  inputs.push({ symbol: "UNKNOWN", changePercent: 1 });
  inputs.push({ symbol: "MISSING", sector: "Technology" });
  const report = analyzeSectorStrength(inputs);

  assert.equal(report.availableCount, 6);
  assert.equal(report.requestedCount, 8);
  assert.equal(report.coverage, 75);
  assert.ok(report.confidence <= 75);
});

test("Missing sector changes reduce confidence once rather than twice", () => {
  const report = analyzeSectorStrength(
    [
      observation("A", "Technology", 1),
      { symbol: "B", sector: "Technology" },
    ],
    { targetConstituentsPerSector: 1 },
  );

  assert.equal(report.coverage, 50);
  assert.equal(report.confidence, 50);
});

test("No valid sector data stays explicitly unavailable", () => {
  const report = analyzeSectorStrength([
    { symbol: "A", changePercent: 1 },
  ]);

  assert.equal(report.score, null);
  assert.equal(report.confidence, 0);
  assert.equal(report.sectorCount, 0);
});

test("SectorStrengthEngine exposes stateless analysis", () => {
  const engine = new SectorStrengthEngine();
  assert.deepEqual(
    engine.analyze(sectorInputs()),
    analyzeSectorStrength(sectorInputs()),
  );
});

test("Sector strength timestamp can be audited by rotation engine", () => {
  const inputs = sectorInputs();
  inputs[0].timestamp = "2026-08-01T00:00:00Z";
  inputs[1].timestamp = "2026-08-02T00:00:00Z";
  const report = analyzeSectorStrength(inputs);

  assert.equal(report.timestamp, "2026-08-02T00:00:00.000Z");
});
