import { analyzeLiquidity } from "./liquidity-engine.js";
import { calculateBreadthBalanceScore } from "./market-breadth.js";
import {
  normalizeMarketObservations,
  resolveLatestObservationTimestamp,
  summarizeObservationCoverage,
} from "./market-observation-normalizer.js";
import {
  calculateWeightedScore,
  scoreDirectionalChange,
} from "./market-score.js";

export const SECTOR_STRENGTH_WEIGHTS = Object.freeze({
  momentum: 60,
  breadth: 25,
  liquidity: 15,
});

function round(value, digits = 2) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function normalizedPositive(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : fallback;
}

function weightedAverage(items, selector) {
  let totalWeight = 0;
  let weightedValue = 0;

  for (const item of items) {
    const value = selector(item);
    const weight = item.confidence / 100;

    if (Number.isFinite(value) && weight > 0) {
      weightedValue += value * weight;
      totalWeight += weight;
    }
  }

  return totalWeight > 0 ? weightedValue / totalWeight : null;
}

function sampleConfidence(summary, targetConstituents) {
  const factor = Math.min(1, summary.availableCount / targetConstituents);
  return round(summary.confidence * factor, 1);
}

function groupBySector(observations) {
  const groups = new Map();

  for (const observation of observations) {
    if (!observation.sector) continue;

    if (!groups.has(observation.sector)) {
      groups.set(observation.sector, []);
    }

    groups.get(observation.sector).push(observation);
  }

  return groups;
}

function analyzeSector(
  sector,
  observations,
  { changeScale, targetConstituents },
) {
  const changeSummary = summarizeObservationCoverage(
    observations,
    (item) => item.changePercent !== null,
    { expectedCount: observations.length },
  );

  if (!changeSummary.availableCount) {
    return null;
  }

  const averageChangePercent = weightedAverage(
    changeSummary.items,
    (item) => item.changePercent,
  );
  const advancers = changeSummary.items.filter(
    (item) => item.changePercent > 0,
  ).length;
  const decliners = changeSummary.items.filter(
    (item) => item.changePercent < 0,
  ).length;
  const unchanged = changeSummary.availableCount - advancers - decliners;
  const confidence = sampleConfidence(changeSummary, targetConstituents);
  const momentum = {
    key: "momentum",
    score: scoreDirectionalChange(averageChangePercent, {
      scale: changeScale,
    }),
    confidence,
    coverage: changeSummary.coverage,
    weight: SECTOR_STRENGTH_WEIGHTS.momentum,
  };
  const breadth = {
    key: "breadth",
    score: calculateBreadthBalanceScore({
      advancers,
      decliners,
      total: changeSummary.availableCount,
    }),
    confidence,
    coverage: changeSummary.coverage,
    weight: SECTOR_STRENGTH_WEIGHTS.breadth,
  };
  const liquidityReport = analyzeLiquidity(observations, {
    expectedCount: observations.length,
  });
  const liquidity = {
    key: "liquidity",
    score: liquidityReport.score,
    confidence: round(
      liquidityReport.confidence *
        Math.min(1, changeSummary.availableCount / targetConstituents),
      1,
    ),
    coverage: liquidityReport.coverage,
    weight: SECTOR_STRENGTH_WEIGHTS.liquidity,
  };
  const components = [momentum, breadth, liquidity];
  const composite = calculateWeightedScore(
    components.map((component) => ({
      key: component.key,
      report: component,
      weight: component.weight,
    })),
  );

  return {
    sector,
    score: composite.score,
    confidence: composite.confidence,
    coverage: composite.coverage,
    constituentCount: observations.length,
    availableCount: changeSummary.availableCount,
    averageChangePercent: round(averageChangePercent, 3),
    advancers,
    decliners,
    unchanged,
    medianVolumeRatio: liquidityReport.medianVolumeRatio,
    momentum,
    breadth,
    liquidity,
    components,
  };
}

function standardDeviation(values) {
  if (!values.length) return null;

  const mean = values.reduce((total, value) => total + value, 0) / values.length;
  const variance =
    values.reduce((total, value) => total + (value - mean) ** 2, 0) /
    values.length;
  return round(Math.sqrt(variance));
}

export function analyzeSectorStrength(
  inputs = [],
  {
    expectedCount = null,
    changeScale = 2,
    targetConstituentsPerSector = 3,
  } = {},
) {
  const observations = normalizeMarketObservations(inputs);
  const normalizedScale = normalizedPositive(Math.abs(changeScale), 2);
  const targetConstituents = normalizedPositive(
    targetConstituentsPerSector,
    3,
  );
  const sectorCoverage = summarizeObservationCoverage(
    observations,
    (item) => item.sector !== null && item.changePercent !== null,
    { expectedCount },
  );
  const sectors = [...groupBySector(observations)]
    .map(([sector, items]) =>
      analyzeSector(sector, items, {
        changeScale: normalizedScale,
        targetConstituents,
      }),
    )
    .filter(Boolean)
    .sort((first, second) => second.score - first.score)
    .map((sector, index) => ({ ...sector, rank: index + 1 }));
  const aggregate = calculateWeightedScore(
    sectors.map((sector) => ({
      key: sector.sector,
      report: sector,
      weight: 1,
    })),
  );
  const adjustedConfidence = round(
    Math.min(aggregate.confidence, sectorCoverage.confidence),
    1,
  );
  const positiveSectors = sectors.filter((sector) => sector.score > 50).length;
  const negativeSectors = sectors.filter((sector) => sector.score < 50).length;

  return {
    score: aggregate.score,
    confidence: adjustedConfidence,
    coverage: sectorCoverage.coverage,
    timestamp: resolveLatestObservationTimestamp(observations),
    availableCount: sectorCoverage.availableCount,
    requestedCount: sectorCoverage.requestedCount,
    sectorCount: sectors.length,
    positiveSectors,
    negativeSectors,
    neutralSectors: sectors.length - positiveSectors - negativeSectors,
    dispersion: standardDeviation(sectors.map((sector) => sector.score)),
    leaders: sectors.slice(0, 3),
    laggards: [...sectors].reverse().slice(0, 3),
    sectors,
  };
}

export class SectorStrengthEngine {
  analyze(inputs = [], options = {}) {
    return analyzeSectorStrength(inputs, options);
  }
}

export const sectorStrengthEngine = new SectorStrengthEngine();

export default analyzeSectorStrength;
