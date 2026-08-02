function analyzeDrawdown(
  values = [],
) {
  const normalized =
    (Array.isArray(values)
      ? values
      : [])
      .map(Number)
      .filter(Number.isFinite);

  if (normalized.length === 0) {
    return {
      maximumDrawdownPercent:
        0,

      peakValue:
        null,

      troughValue:
        null,

      sampleCount:
        0,
    };
  }

  let peak =
    normalized[0];

  let peakAtMaximumDrawdown =
    peak;

  let troughAtMaximumDrawdown =
    peak;

  let maximumDrawdownPercent =
    0;

  for (const value of normalized) {
    if (value > peak) {
      peak = value;
    }

    const drawdownPercent =
      peak > 0
        ? (
            (
              value -
              peak
            ) /
            peak
          ) * 100
        : 0;

    if (
      drawdownPercent <
      maximumDrawdownPercent
    ) {
      maximumDrawdownPercent =
        drawdownPercent;

      peakAtMaximumDrawdown =
        peak;

      troughAtMaximumDrawdown =
        value;
    }
  }

  return {
    maximumDrawdownPercent,
    peakValue:
      peakAtMaximumDrawdown,

    troughValue:
      troughAtMaximumDrawdown,

    sampleCount:
      normalized.length,
  };
}

module.exports = {
  analyzeDrawdown,
};