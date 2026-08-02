function number(value, fallback = 0) {
  const parsed = Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : fallback;
}

function clamp(value, minimum = 0, maximum = 5) {
  return Math.min(
    maximum,
    Math.max(
      minimum,
      number(value)
    )
  );
}

export function normalizeWeights(weights = {}) {

  const entries =
    Object.entries(weights);

  if (entries.length === 0) {
    return {};
  }

  const total =
    entries.reduce(
      (sum, [, value]) =>
        sum + number(value),
      0
    ) || 1;

  return Object.fromEntries(
    entries.map(
      ([key, value]) => [
        key,
        number(value) / total
      ]
    )
  );
}

export function updateEngineWeights({

weights = {},

results = []

} = {}) {

  const updated = {
    ...weights
  };

  for (const result of results) {

    const key =
      String(result.name);

    const current =
      number(
        updated[key],
        1
      );

    const accuracy =
      number(
        result.accuracy,
        50
      );

    const delta =
      (accuracy - 50) / 100;

    updated[key] =
      clamp(
        current + delta,
        0.2,
        5
      );
  }

  return normalizeWeights(
    updated
  );
}

export class AdaptiveWeightEngine {

  constructor(
    initialWeights = {}
  ) {
    this.weights =
      normalizeWeights(
        initialWeights
      );
  }

  learn(results = []) {

    this.weights =
      updateEngineWeights({

        weights:
          this.weights,

        results

      });

    return this.weights;
  }

  getWeights() {

    return {
      ...this.weights
    };

  }

}

export const
adaptiveWeightEngine =
new AdaptiveWeightEngine();