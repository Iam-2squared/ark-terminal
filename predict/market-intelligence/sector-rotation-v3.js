export const SECTOR_ROTATION_V3_VERSION =
  "sector-rotation-v3";

function clone(value) {
  return value === undefined
    ? undefined
    : structuredClone(value);
}

function finiteNumber(
  value,
  fallback = 0,
) {
  const number =
    Number(value);

  return Number.isFinite(number)
    ? number
    : fallback;
}

function clamp(
  value,
  minimum,
  maximum,
) {
  return Math.min(
    maximum,
    Math.max(
      minimum,
      value,
    ),
  );
}

function round(
  value,
  digits = 2,
) {
  if (!Number.isFinite(value)) {
    return null;
  }

  const factor =
    10 ** digits;

  return (
    Math.round(
      value *
      factor,
    ) /
    factor
  );
}

function normalizeTimestamp(value) {
  const milliseconds =
    typeof value === "number"
      ? value
      : Date.parse(
          value ??
          new Date().toISOString(),
        );

  if (!Number.isFinite(milliseconds)) {
    throw new TypeError(
      "Sector rotation timestamp is invalid.",
    );
  }

  return new Date(
    milliseconds,
  ).toISOString();
}

function normalizeSector(
  sector = {},
) {
  const returns =
    sector.returns &&
    typeof sector.returns ===
      "object"
      ? sector.returns
      : {};

  return {
    name:
      String(
        sector.name ??
        sector.sector ??
        "UNKNOWN",
      ).trim() ||
      "UNKNOWN",

    return1d:
      finiteNumber(
        returns.oneDay ??
        sector.return1d,
        0,
      ),

    return5d:
      finiteNumber(
        returns.fiveDay ??
        sector.return5d,
        0,
      ),

    return20d:
      finiteNumber(
        returns.twentyDay ??
        sector.return20d,
        0,
      ),

    relativeStrength:
      finiteNumber(
        sector.relativeStrength,
        0,
      ),

    breadthScore:
      finiteNumber(
        sector.breadthScore,
        0,
      ),

    volumeRatio:
      Math.max(
        0,
        finiteNumber(
          sector.volumeRatio,
          1,
        ),
      ),

    momentum:
      finiteNumber(
        sector.momentum,
        0,
      ),

    volatility:
      Math.max(
        0,
        finiteNumber(
          sector.volatility,
          0,
        ),
      ),

    valuationScore:
      finiteNumber(
        sector.valuationScore,
        0,
      ),

    earningsRevision:
      finiteNumber(
        sector.earningsRevision,
        0,
      ),

    riskScore:
      clamp(
        finiteNumber(
          sector.riskScore,
          50,
        ),
        0,
        100,
      ),
  };
}

function calculateSectorScore(
  sector,
) {
  const returnScore =
    clamp(
      sector.return1d *
        4 +
      sector.return5d *
        3 +
      sector.return20d *
        1.5,
      -45,
      45,
    );

  const relativeStrengthScore =
    clamp(
      sector.relativeStrength *
        0.8,
      -20,
      20,
    );

  const breadthScore =
    clamp(
      sector.breadthScore *
        0.2,
      -20,
      20,
    );

  const volumeScore =
    clamp(
      (
        sector.volumeRatio -
        1
      ) *
        12,
      -10,
      20,
    );

  const momentumScore =
    clamp(
      sector.momentum *
        0.3,
      -15,
      15,
    );

  const revisionScore =
    clamp(
      sector.earningsRevision *
        0.5,
      -15,
      15,
    );

  const valuationScore =
    clamp(
      sector.valuationScore *
        0.15,
      -10,
      10,
    );

  const volatilityPenalty =
    clamp(
      sector.volatility *
        2,
      0,
      20,
    );

  const riskPenalty =
    clamp(
      (
        sector.riskScore -
        50
      ) *
        0.3,
      -10,
      15,
    );

  const score =
    clamp(
      returnScore +
      relativeStrengthScore +
      breadthScore +
      volumeScore +
      momentumScore +
      revisionScore +
      valuationScore -
      volatilityPenalty -
      riskPenalty,
      -100,
      100,
    );

  return {
    score:
      round(
        score,
      ),

    components: {
      returnScore:
        round(
          returnScore,
        ),

      relativeStrengthScore:
        round(
          relativeStrengthScore,
        ),

      breadthScore:
        round(
          breadthScore,
        ),

      volumeScore:
        round(
          volumeScore,
        ),

      momentumScore:
        round(
          momentumScore,
        ),

      revisionScore:
        round(
          revisionScore,
        ),

      valuationScore:
        round(
          valuationScore,
        ),

      volatilityPenalty:
        round(
          volatilityPenalty,
        ),

      riskPenalty:
        round(
          riskPenalty,
        ),
    },
  };
}

function classifyStage({
  score,
  return5d,
  return20d,
  relativeStrength,
}) {
  if (
    score >= 50 &&
    return5d > 0 &&
    return20d > 0 &&
    relativeStrength > 0
  ) {
    return "LEADING";
  }

  if (
    score >= 15 &&
    return5d > 0
  ) {
    return "IMPROVING";
  }

  if (
    score <= -50 &&
    return5d < 0 &&
    return20d < 0
  ) {
    return "LAGGING";
  }

  if (
    score <= -15 &&
    return5d < 0
  ) {
    return "WEAKENING";
  }

  return "NEUTRAL";
}

function recommendationForStage(
  stage,
) {
  const recommendations = {
    LEADING:
      "OVERWEIGHT",

    IMPROVING:
      "ACCUMULATE",

    NEUTRAL:
      "HOLD",

    WEAKENING:
      "REDUCE",

    LAGGING:
      "UNDERWEIGHT",
  };

  return (
    recommendations[
      stage
    ] ??
    "HOLD"
  );
}

export function analyzeSectorRotation({
  sectors = [],
  timestamp =
    new Date().toISOString(),
  minimumSectorCount = 3,
} = {}) {
  const evaluatedAt =
    normalizeTimestamp(
      timestamp,
    );

  const normalized =
    sectors.map(
      normalizeSector,
    );

  if (
    normalized.length <
    minimumSectorCount
  ) {
    return {
      version:
        SECTOR_ROTATION_V3_VERSION,

      evaluatedAt,

      status:
        "INSUFFICIENT_DATA",

      sectors: [],

      leaders: [],

      laggards: [],

      rotation: {
        detected:
          false,

        strength:
          0,

        direction:
          "UNKNOWN",
      },
    };
  }

  const scored =
    normalized.map(
      (
        sector,
      ) => {
        const calculation =
          calculateSectorScore(
            sector,
          );

        const stage =
          classifyStage({
            score:
              calculation.score,

            return5d:
              sector.return5d,

            return20d:
              sector.return20d,

            relativeStrength:
              sector.relativeStrength,
          });

        return {
          ...sector,

          score:
            calculation.score,

          stage,

          recommendation:
            recommendationForStage(
              stage,
            ),

          components:
            calculation.components,
        };
      },
    );

  scored.sort(
    (
      left,
      right,
    ) =>
      right.score -
      left.score,
  );

  const leaders =
    scored
      .filter(
        (
          sector,
        ) =>
          [
            "LEADING",
            "IMPROVING",
          ].includes(
            sector.stage,
          ),
      )
      .slice(
        0,
        5,
      );

  const laggards =
    scored
      .filter(
        (
          sector,
        ) =>
          [
            "LAGGING",
            "WEAKENING",
          ].includes(
            sector.stage,
          ),
      )
      .slice(
        -5,
      )
      .reverse();

  const topScore =
    scored[0]?.score ??
    0;

  const bottomScore =
    scored.at(-1)?.score ??
    0;

  const spread =
    topScore -
    bottomScore;

  const positiveCount =
    scored.filter(
      (
        sector,
      ) =>
        sector.score >
        10,
    ).length;

  const negativeCount =
    scored.filter(
      (
        sector,
      ) =>
        sector.score <
        -10,
    ).length;

  let direction =
    "BALANCED";

  if (
    positiveCount >
    negativeCount
  ) {
    direction =
      "RISK_ON";
  }
  else if (
    negativeCount >
    positiveCount
  ) {
    direction =
      "RISK_OFF";
  }

  const rotationStrength =
    clamp(
      spread,
      0,
      100,
    );

  return {
    version:
      SECTOR_ROTATION_V3_VERSION,

    evaluatedAt,

    status:
      "READY",

    sectors:
      scored,

    leaders,

    laggards,

    rotation: {
      detected:
        spread >= 25,

      strength:
        round(
          rotationStrength,
        ),

      direction,

      scoreSpread:
        round(
          spread,
        ),

      leadingSector:
        leaders[0]?.name ??
        null,

      laggingSector:
        laggards[0]?.name ??
        null,
    },

    summary: {
      sectorCount:
        scored.length,

      leadingCount:
        scored.filter(
          (
            sector,
          ) =>
            sector.stage ===
            "LEADING",
        ).length,

      improvingCount:
        scored.filter(
          (
            sector,
          ) =>
            sector.stage ===
            "IMPROVING",
        ).length,

      weakeningCount:
        scored.filter(
          (
            sector,
          ) =>
            sector.stage ===
            "WEAKENING",
        ).length,

      laggingCount:
        scored.filter(
          (
            sector,
          ) =>
            sector.stage ===
            "LAGGING",
        ).length,
    },
  };
}

export function compareSectorRotation({
  previous,
  current,
} = {}) {
  if (
    !previous ||
    !current
  ) {
    return {
      changed:
        false,

      promoted: [],

      demoted: [],

      newLeader:
        null,

      previousLeader:
        null,
    };
  }

  const previousMap =
    new Map(
      (
        previous.sectors ??
        []
      ).map(
        (
          sector,
        ) => [
          sector.name,
          sector,
        ],
      ),
    );

  const promoted = [];
  const demoted = [];

  const stageValue = {
    LEADING:
      2,

    IMPROVING:
      1,

    NEUTRAL:
      0,

    WEAKENING:
      -1,

    LAGGING:
      -2,
  };

  for (
    const sector of
    current.sectors ??
    []
  ) {
    const before =
      previousMap.get(
        sector.name,
      );

    if (!before) {
      continue;
    }

    const difference =
      (
        stageValue[
          sector.stage
        ] ??
        0
      ) -
      (
        stageValue[
          before.stage
        ] ??
        0
      );

    if (difference > 0) {
      promoted.push({
        name:
          sector.name,

        from:
          before.stage,

        to:
          sector.stage,
      });
    }

    if (difference < 0) {
      demoted.push({
        name:
          sector.name,

        from:
          before.stage,

        to:
          sector.stage,
      });
    }
  }

  const previousLeader =
    previous.leaders?.[0]
      ?.name ??
    null;

  const newLeader =
    current.leaders?.[0]
      ?.name ??
    null;

  return {
    changed:
      promoted.length >
        0 ||
      demoted.length >
        0 ||
      previousLeader !==
        newLeader,

    promoted,

    demoted,

    newLeader,

    previousLeader,
  };
}

export class SectorRotationV3 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };

    this.history = [];
  }

  analyze(input = {}) {
    const result =
      analyzeSectorRotation({
        ...this.config,
        ...input,
      });

    this.history.push(
      clone(result),
    );

    return clone(result);
  }

  compareLatest() {
    if (
      this.history.length <
      2
    ) {
      return compareSectorRotation({
        previous:
          null,

        current:
          this.history.at(-1) ??
          null,
      });
    }

    return compareSectorRotation({
      previous:
        this.history.at(-2),

      current:
        this.history.at(-1),
    });
  }

  getHistory() {
    return clone(
      this.history,
    );
  }

  latest() {
    return clone(
      this.history.at(-1) ??
      null,
    );
  }

  reset() {
    this.history = [];

    return [];
  }
}

export const sectorRotationV3 =
  new SectorRotationV3();

export default analyzeSectorRotation;