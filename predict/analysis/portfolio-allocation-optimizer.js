function number(value, fallback = 0) {
  const parsed = Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : fallback;
}

function clamp(value, minimum = 0, maximum = 1) {
  return Math.min(
    maximum,
    Math.max(
      minimum,
      number(value),
    ),
  );
}

function round(value, digits = 4) {
  const factor = 10 ** digits;

  return (
    Math.round(value * factor) /
    factor
  );
}

export function optimizePortfolioAllocation({
  assets = [],
  maximumWeight = 0.35,
} = {}) {
  const normalized =
    assets.map(
      (asset) => {
        const score =
          Math.max(
            0,
            number(
              asset.score,
              50,
            ),
          );

        const confidence =
          Math.max(
            0,
            number(
              asset.confidence,
              50,
            ),
          );

        return {
          symbol:
            String(
              asset.symbol ??
              "",
            ),

          score,

          confidence,

          strength:
            score *
            confidence,
        };
      },
    );

  const totalStrength =
    normalized.reduce(
      (sum, asset) =>
        sum +
        asset.strength,
      0,
    ) || 1;

  let allocation =
    normalized.map(
      (asset) => ({
        ...asset,

        weight:
          asset.strength /
          totalStrength,
      }),
    );

  allocation =
    allocation.map(
      (asset) => ({
        ...asset,

        weight:
          clamp(
            asset.weight,
            0,
            maximumWeight,
          ),
      }),
    );

  const totalWeight =
    allocation.reduce(
      (sum, asset) =>
        sum +
        asset.weight,
      0,
    ) || 1;

  allocation =
    allocation.map(
      (asset) => ({
        symbol:
          asset.symbol,

        score:
          asset.score,

        confidence:
          asset.confidence,

        recommendedWeight:
          round(
            asset.weight /
            totalWeight,
          ),
      }),
    );

  return {
    assets:
      allocation,

    totalWeight:
      round(
        allocation.reduce(
          (sum, asset) =>
            sum +
            asset.recommendedWeight,
          0,
        ),
      ),
  };
}

export class PortfolioAllocationOptimizer {
  optimize(input = {}) {
    return optimizePortfolioAllocation(
      input,
    );
  }
}

export const
portfolioAllocationOptimizer =
new PortfolioAllocationOptimizer();