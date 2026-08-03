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

function extendedNumberOrNull(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const number = Number(value);

  return Number.isFinite(number)
    ? number
    : null;
}

function extendedClamp(
  value,
  minimum = 0,
  maximum = 100,
) {
  return Math.min(
    maximum,
    Math.max(
      minimum,
      value,
    ),
  );
}

function extendedAverage(values) {
  const available =
    values.filter(Number.isFinite);

  if (!available.length) {
    return null;
  }

  return available.reduce(
    (sum, value) => sum + value,
    0,
  ) / available.length;
}

function extendedStandardDeviation(values) {
  const mean =
    extendedAverage(values);

  if (mean === null) {
    return null;
  }

  const variance =
    values.reduce(
      (sum, value) =>
        sum +
        (
          value - mean
        ) ** 2,
      0,
    ) / values.length;

  return Math.sqrt(variance);
}

export function evaluateSector(
  sector = {},
  benchmark = {},
) {
  const return5d =
    extendedNumberOrNull(
      sector.return5d,
    );

  const return20d =
    extendedNumberOrNull(
      sector.return20d,
    );

  const return60d =
    extendedNumberOrNull(
      sector.return60d,
    );

  const benchmarkReturn20d =
    extendedNumberOrNull(
      benchmark.return20d,
    );

  const momentumValues = [];

  if (return5d !== null) {
    momentumValues.push(
      return5d * 0.45,
    );
  }

  if (return20d !== null) {
    momentumValues.push(
      return20d * 0.35,
    );
  }

  if (return60d !== null) {
    momentumValues.push(
      return60d * 0.2,
    );
  }

  const momentumRaw =
    momentumValues.length
      ? momentumValues.reduce(
          (sum, value) =>
            sum + value,
          0,
        )
      : null;

  const relativeStrength =
    return20d !== null &&
    benchmarkReturn20d !== null
      ? return20d -
        benchmarkReturn20d
      : null;

  const percentAbove20 =
    extendedNumberOrNull(
      sector.percentAbove20,
    );

  const percentAbove50 =
    extendedNumberOrNull(
      sector.percentAbove50,
    );

  const advanceDeclineRatio =
    extendedNumberOrNull(
      sector.advanceDeclineRatio,
    );

  const breadthValues = [];

  if (percentAbove20 !== null) {
    breadthValues.push(
      extendedClamp(
        percentAbove20,
      ),
    );
  }

  if (percentAbove50 !== null) {
    breadthValues.push(
      extendedClamp(
        percentAbove50,
      ),
    );
  }

  if (
    advanceDeclineRatio !== null &&
    advanceDeclineRatio >= 0
  ) {
    breadthValues.push(
      extendedClamp(
        50 +
        Math.log(
          Math.max(
            advanceDeclineRatio,
            0.01,
          ),
        ) * 21.7,
      ),
    );
  }

  const breadth =
    extendedAverage(
      breadthValues,
    );

  const relativeVolume =
    extendedNumberOrNull(
      sector.relativeVolume,
    );

  const upVolumeRatio =
    extendedNumberOrNull(
      sector.upVolumeRatio,
    );

  const volumeValues = [];

  if (relativeVolume !== null) {
    volumeValues.push(
      extendedClamp(
        50 +
        (
          relativeVolume - 1
        ) * 25,
      ),
    );
  }

  if (upVolumeRatio !== null) {
    volumeValues.push(
      extendedClamp(
        upVolumeRatio * 100,
      ),
    );
  }

  const volume =
    extendedAverage(
      volumeValues,
    );

  const volatility20d =
    extendedNumberOrNull(
      sector.volatility20d,
    );

  const maxDrawdown60d =
    extendedNumberOrNull(
      sector.maxDrawdown60d,
    );

  const riskValues = [];

  if (volatility20d !== null) {
    riskValues.push(
      extendedClamp(
        100 -
        volatility20d * 4,
      ),
    );
  }

  if (maxDrawdown60d !== null) {
    riskValues.push(
      extendedClamp(
        100 +
        maxDrawdown60d * 2,
      ),
    );
  }

  const risk =
    extendedAverage(
      riskValues,
    );

  const components = [
    {
      key:
        "momentum",

      score:
        momentumRaw === null
          ? null
          : extendedClamp(
              50 +
              momentumRaw * 5,
            ),

      weight:
        30,
    },
    {
      key:
        "relativeStrength",

      score:
        relativeStrength === null
          ? null
          : extendedClamp(
              50 +
              relativeStrength * 7,
            ),

      weight:
        25,
    },
    {
      key:
        "breadth",

      score:
        breadth,

      weight:
        20,
    },
    {
      key:
        "volume",

      score:
        volume,

      weight:
        15,
    },
    {
      key:
        "risk",

      score:
        risk,

      weight:
        10,
    },
  ];

  const available =
    components.filter(
      (component) =>
        Number.isFinite(
          component.score,
        ),
    );

  const weightTotal =
    available.reduce(
      (sum, component) =>
        sum +
        component.weight,
      0,
    );

  const score =
    weightTotal
      ? available.reduce(
          (sum, component) =>
            sum +
            component.score *
              component.weight,
          0,
        ) / weightTotal
      : null;

  let signal =
    "neutral";

  if (
    score !== null &&
    score >= 65
  ) {
    signal =
      "leading";
  } else if (
    score !== null &&
    score <= 35
  ) {
    signal =
      "lagging";
  }

  return {
    sector:
      String(
        sector.name ??
        sector.sector ??
        "UNKNOWN",
      ),

    score:
      score === null
        ? null
        : Math.round(
            score * 100,
          ) / 100,

    signal,
    momentum:
      momentumRaw,

    relativeStrength,
    breadth,
    volume,
    risk,
    components,

    dataQuality: {
      availableComponents:
        available.length,

      totalComponents:
        components.length,
    },
  };
}

export function rankSectorRotation({
  sectors = [],
  benchmark = {},
} = {}) {
  const ranked =
    sectors
      .map(
        (sector) =>
          evaluateSector(
            sector,
            benchmark,
          ),
      )
      .sort(
        (left, right) =>
          (
            right.score ??
            -Infinity
          ) -
          (
            left.score ??
            -Infinity
          ),
      )
      .map(
        (
          sector,
          index,
        ) => ({
          ...sector,
          rank:
            index + 1,
        }),
      );

  const scores =
    ranked
      .map(
        (sector) =>
          sector.score,
      )
      .filter(
        Number.isFinite,
      );

  const dispersion =
    extendedStandardDeviation(
      scores,
    );

  const leaders =
    ranked.filter(
      (sector) =>
        sector.signal ===
        "leading",
    );

  const laggards =
    ranked.filter(
      (sector) =>
        sector.signal ===
        "lagging",
    );

  return {
    version:
      "sector-rotation-v1",

    rotationState:
      dispersion === null
        ? "balanced"
        : dispersion >= 15
          ? "high-dispersion"
          : dispersion <= 5
            ? "low-dispersion"
            : "balanced",

    dispersion:
      dispersion === null
        ? null
        : Math.round(
            dispersion * 100,
          ) / 100,

    leaders,
    laggards,
    sectors:
      ranked,

    summary: {
      sectorCount:
        ranked.length,

      leaderCount:
        leaders.length,

      laggardCount:
        laggards.length,

      strongest:
        ranked[0] ??
        null,

      weakest:
        ranked.length
          ? ranked[
              ranked.length - 1
            ]
          : null,
    },
  };
}
