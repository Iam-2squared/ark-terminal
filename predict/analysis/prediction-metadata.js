function finiteOrNull(value) {
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

function clamp(value, minimum = 0, maximum = 100) {
  const number = finiteOrNull(value);

  if (number === null) {
    return null;
  }

  return Math.min(
    maximum,
    Math.max(
      minimum,
      number,
    ),
  );
}

function normalizedSymbol(value) {
  const symbol = String(
    value ?? "",
  )
    .trim()
    .toUpperCase();

  return symbol || "UNKNOWN";
}

function normalizedDirection(value) {
  const direction = String(
    value ?? "HOLD",
  )
    .trim()
    .toUpperCase();

  if (
    direction === "BUY" ||
    direction === "SELL" ||
    direction === "HOLD"
  ) {
    return direction;
  }

  if (
    direction === "強気" ||
    direction === "UP" ||
    direction === "BULLISH"
  ) {
    return "BUY";
  }

  if (
    direction === "弱気" ||
    direction === "DOWN" ||
    direction === "BEARISH"
  ) {
    return "SELL";
  }

  return "HOLD";
}

function normalizedTimeframe(value) {
  const number = finiteOrNull(value);

  if (
    number !== null &&
    number > 0
  ) {
    return {
      value:
        Math.max(
          1,
          Math.floor(number),
        ),

      unit:
        "trading-days",
    };
  }

  const text = String(
    value ?? "5d",
  )
    .trim()
    .toLowerCase();

  const match =
    text.match(
      /^(\d+)\s*(d|day|days|営業日)?$/,
    );

  if (match) {
    return {
      value:
        Math.max(
          1,
          Number(match[1]),
        ),

      unit:
        "trading-days",
    };
  }

  return {
    value: 5,
    unit: "trading-days",
  };
}

function isoDate(value) {
  const date =
    value instanceof Date
      ? value
      : new Date(
          value ?? Date.now(),
        );

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return new Date().toISOString();
  }

  return date.toISOString();
}

function stableHash(value) {
  const text =
    String(value);

  let hash =
    2166136261;

  for (
    let index = 0;
    index < text.length;
    index += 1
  ) {
    hash ^=
      text.charCodeAt(index);

    hash =
      Math.imul(
        hash,
        16777619,
      );
  }

  return (
    hash >>> 0
  )
    .toString(36)
    .padStart(
      7,
      "0",
    );
}

export function createPredictionId({
  symbol,
  predictedAt,
  timeframe,
  modelVersion,
} = {}) {
  const normalized =
    normalizedTimeframe(
      timeframe,
    );

  const timestamp =
    isoDate(
      predictedAt,
    );

  const seed = [
    normalizedSymbol(symbol),
    timestamp,
    normalized.value,
    normalized.unit,
    String(
      modelVersion ??
      "unknown",
    ),
  ].join("|");

  return [
    "pred",
    timestamp
      .replace(
        /[-:.TZ]/g,
        "",
      )
      .slice(
        0,
        14,
      ),
    normalizedSymbol(symbol)
      .replace(
        /[^A-Z0-9]/g,
        "",
      )
      .slice(
        0,
        12,
      ),
    stableHash(seed),
  ].join("_");
}

export function createPredictionMetadata({
  predictionId,
  symbol,
  predictedAt,
  timeframe,
  direction,
  confidence,
  score,
  entryPrice,
  targetPrice,
  stopPrice,
  marketRegime,
  modelVersion,
  dataQualityScore,
  source = "ark-terminal",
} = {}) {
  const normalizedPredictedAt =
    isoDate(
      predictedAt,
    );

  const normalizedTimeframeValue =
    normalizedTimeframe(
      timeframe,
    );

  const normalizedModelVersion =
    String(
      modelVersion ??
      "unknown",
    );

  const normalizedSymbolValue =
    normalizedSymbol(
      symbol,
    );

  return {
    schemaVersion:
      "prediction-metadata-v1",

    predictionId:
      String(
        predictionId ??
        createPredictionId({
          symbol:
            normalizedSymbolValue,

          predictedAt:
            normalizedPredictedAt,

          timeframe:
            normalizedTimeframeValue.value,

          modelVersion:
            normalizedModelVersion,
        }),
      ),

    symbol:
      normalizedSymbolValue,

    predictedAt:
      normalizedPredictedAt,

    timeframe:
      normalizedTimeframeValue,

    direction:
      normalizedDirection(
        direction,
      ),

    confidence:
      clamp(
        confidence,
      ),

    score:
      clamp(
        score,
      ),

    prices: {
      entry:
        finiteOrNull(
          entryPrice,
        ),

      target:
        finiteOrNull(
          targetPrice,
        ),

      stop:
        finiteOrNull(
          stopPrice,
        ),
    },

    marketRegime:
      String(
        marketRegime ??
        "UNKNOWN",
      ),

    modelVersion:
      normalizedModelVersion,

    dataQualityScore:
      clamp(
        dataQualityScore,
      ),

    source:
      String(
        source ??
        "ark-terminal",
      ),
  };
}

export function validatePredictionMetadata(
  metadata,
) {
  const errors = [];

  if (
    !metadata ||
    typeof metadata !== "object" ||
    Array.isArray(metadata)
  ) {
    return {
      valid: false,
      errors: [
        "metadata must be an object",
      ],
    };
  }

  if (
    metadata.schemaVersion !==
    "prediction-metadata-v1"
  ) {
    errors.push(
      "unsupported schemaVersion",
    );
  }

  if (
    typeof metadata.predictionId !==
      "string" ||
    !metadata.predictionId
  ) {
    errors.push(
      "predictionId is required",
    );
  }

  if (
    typeof metadata.symbol !==
      "string" ||
    !metadata.symbol
  ) {
    errors.push(
      "symbol is required",
    );
  }

  if (
    Number.isNaN(
      Date.parse(
        metadata.predictedAt,
      ),
    )
  ) {
    errors.push(
      "predictedAt must be ISO date",
    );
  }

  if (
    ![
      "BUY",
      "SELL",
      "HOLD",
    ].includes(
      metadata.direction,
    )
  ) {
    errors.push(
      "direction must be BUY, SELL or HOLD",
    );
  }

  if (
    !metadata.timeframe ||
    !Number.isInteger(
      metadata.timeframe.value,
    ) ||
    metadata.timeframe.value < 1
  ) {
    errors.push(
      "timeframe must contain positive integer value",
    );
  }

  return {
    valid:
      errors.length === 0,

    errors,
  };
}