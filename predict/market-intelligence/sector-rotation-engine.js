import {
  calculateWeightedScore,
  scoreToSentiment,
} from "./market-score.js";

export const SECTOR_ROTATION_STATES = Object.freeze({
  LEADING: "LEADING",
  IMPROVING: "IMPROVING",
  STABLE: "STABLE",
  WEAKENING: "WEAKENING",
  LAGGING: "LAGGING",
  NEW: "NEW",
});

function finiteOrNull(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function clamp(value, minimum = 0, maximum = 100) {
  return Math.min(maximum, Math.max(minimum, value));
}

function round(value, digits = 2) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function extractSectors(report) {
  const items = Array.isArray(report)
    ? report
    : Array.isArray(report?.sectors)
      ? report.sectors
      : [];

  const normalized = items
    .map((item) => {
      const sector = String(item?.sector ?? item?.name ?? "").trim();
      const score = finiteOrNull(item?.score);
      const confidence = finiteOrNull(item?.confidence);

      if (!sector || score === null) {
        return null;
      }

      return {
        sector,
        score: clamp(score),
        confidence: clamp(confidence ?? 100),
      };
    })
    .filter(Boolean);
  const unique = new Map();

  for (const sector of normalized) {
    unique.set(sector.sector, sector);
  }

  return [...unique.values()]
    .sort((first, second) => second.score - first.score)
    .map((item, index) => ({ ...item, rank: index + 1 }));
}

function validateChronology(current, previous) {
  const currentTime = Date.parse(current?.timestamp);
  const previousTime = Date.parse(previous?.timestamp);

  if (
    Number.isFinite(currentTime) &&
    Number.isFinite(previousTime) &&
    previousTime > currentTime
  ) {
    throw new RangeError(
      "Previous sector snapshot cannot be newer than current snapshot.",
    );
  }
}

function classifyRotation(currentScore, scoreChange) {
  if (currentScore >= 60 && scoreChange >= 0) {
    return SECTOR_ROTATION_STATES.LEADING;
  }

  if (currentScore >= 50 && scoreChange < 0) {
    return SECTOR_ROTATION_STATES.WEAKENING;
  }

  if (currentScore < 40 && scoreChange <= 0) {
    return SECTOR_ROTATION_STATES.LAGGING;
  }

  if (currentScore < 50 && scoreChange > 0) {
    return SECTOR_ROTATION_STATES.IMPROVING;
  }

  if (scoreChange >= 5) {
    return SECTOR_ROTATION_STATES.IMPROVING;
  }

  if (scoreChange <= -5) {
    return SECTOR_ROTATION_STATES.WEAKENING;
  }

  return SECTOR_ROTATION_STATES.STABLE;
}

function compareSector(current, previous) {
  if (!previous) {
    return {
      ...current,
      previousScore: null,
      previousRank: null,
      scoreChange: null,
      rankChange: null,
      rotationScore: null,
      rotationState: SECTOR_ROTATION_STATES.NEW,
      rotationConfidence: 0,
    };
  }

  const scoreChange = current.score - previous.score;
  const momentumScore = clamp(50 + scoreChange * 2.5);

  return {
    ...current,
    previousScore: previous.score,
    previousRank: previous.rank,
    scoreChange: round(scoreChange),
    rankChange: previous.rank - current.rank,
    rotationScore: round(current.score * 0.7 + momentumScore * 0.3),
    rotationState: classifyRotation(current.score, scoreChange),
    rotationConfidence: Math.min(current.confidence, previous.confidence),
  };
}

function rotationStrength(sectors) {
  const changes = sectors
    .filter((sector) => sector.rotationConfidence > 0)
    .map((sector) => sector.scoreChange)
    .filter(Number.isFinite)
    .map(Math.abs);

  if (!changes.length) return null;

  const average =
    changes.reduce((total, change) => total + change, 0) / changes.length;
  return round(clamp(average * 5));
}

export function analyzeSectorRotation({ current, previous } = {}) {
  validateChronology(current, previous);
  const currentSectors = extractSectors(current);
  const previousSectors = extractSectors(previous);
  const previousBySector = new Map(
    previousSectors.map((sector) => [sector.sector, sector]),
  );
  const sectors = currentSectors.map((sector) =>
    compareSector(sector, previousBySector.get(sector.sector)),
  );
  const composite = calculateWeightedScore(
    sectors.map((sector) => ({
      key: sector.sector,
      score: sector.rotationScore,
      confidence: sector.rotationConfidence,
      coverage: sector.rotationScore === null ? 0 : 100,
      weight: 1,
    })),
  );
  const matchedCount = sectors.filter(
    (sector) =>
      sector.rotationScore !== null && sector.rotationConfidence > 0,
  ).length;
  const leaders = sectors
    .filter((sector) =>
      sector.rotationConfidence > 0 &&
      [
        SECTOR_ROTATION_STATES.LEADING,
        SECTOR_ROTATION_STATES.IMPROVING,
      ].includes(sector.rotationState),
    )
    .sort((first, second) => second.rotationScore - first.rotationScore)
    .slice(0, 3);
  const weakening = sectors
    .filter((sector) =>
      sector.rotationConfidence > 0 &&
      [
        SECTOR_ROTATION_STATES.WEAKENING,
        SECTOR_ROTATION_STATES.LAGGING,
      ].includes(sector.rotationState),
    )
    .sort((first, second) => first.rotationScore - second.rotationScore)
    .slice(0, 3);

  return {
    score: composite.score,
    confidence: composite.confidence,
    coverage: composite.coverage,
    direction: scoreToSentiment(composite.score),
    rotationStrength: rotationStrength(sectors),
    matchedCount,
    requestedCount: currentSectors.length,
    currentTimestamp: current?.timestamp ?? null,
    previousTimestamp: previous?.timestamp ?? null,
    leaders,
    weakening,
    sectors,
  };
}

export class SectorRotationEngine {
  analyze(input = {}) {
    return analyzeSectorRotation(input);
  }
}

export const sectorRotationEngine = new SectorRotationEngine();

export default analyzeSectorRotation;
