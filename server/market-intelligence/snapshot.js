function finiteOrNull(value) {
  const number =
    Number(value);

  return Number.isFinite(number)
    ? number
    : null;
}

function normalizeMarketSnapshot(
  input = {},
) {
  const indices =
    input.indices &&
    typeof input.indices ===
      "object"
      ? input.indices
      : {};

  return {
    capturedAt:
      input.capturedAt ||
      new Date().toISOString(),

    indices: {
      nikkei:
        finiteOrNull(
          indices.nikkei,
        ),

      topix:
        finiteOrNull(
          indices.topix,
        ),

      nasdaq:
        finiteOrNull(
          indices.nasdaq,
        ),

      sox:
        finiteOrNull(
          indices.sox,
        ),

      sp500:
        finiteOrNull(
          indices.sp500,
        ),
    },

    volatility:
      finiteOrNull(
        input.volatility,
      ),

    breadth:
      finiteOrNull(
        input.breadth,
      ),

    sentiment:
      finiteOrNull(
        input.sentiment,
      ),

    volumeRatio:
      finiteOrNull(
        input.volumeRatio,
      ),
  };
}

module.exports = {
  normalizeMarketSnapshot,
};