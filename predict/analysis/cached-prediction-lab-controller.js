import {
  AnalysisCache,
} from "./analysis-cache.js";

import {
  normalizePredictionLabInput,
  renderPredictionLabV2,
} from "./prediction-lab-controller.js";

export const predictionLabCache =
  new AnalysisCache();

function stableValue(value) {
  if (Array.isArray(value)) {
    return value.map(
      stableValue,
    );
  }

  if (
    value &&
    typeof value === "object"
  ) {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map(
          (key) => [
            key,
            stableValue(
              value[key],
            ),
          ],
        ),
    );
  }

  return value;
}

export function createPredictionLabCacheKey(
  source = {},
) {
  return {
    version:
      "prediction-lab-cache-v1",

    input:
      stableValue(
        normalizePredictionLabInput(
          source,
        ),
      ),
  };
}

export function renderCachedPredictionLabV2({
  source = {},
  cache = predictionLabCache,
  maxAgeMs = 30000,
  forceRefresh = false,
} = {}) {
  const key =
    createPredictionLabCacheKey(
      source,
    );

  if (!forceRefresh) {
    const cached =
      cache.get(
        key,
        maxAgeMs,
      );

    if (cached) {
      return {
        html:
          cached.html,

        cacheHit: true,

        createdAt:
          cached.createdAt,

        key,
      };
    }
  }

  const result = {
    html:
      renderPredictionLabV2(
        source,
      ),

    createdAt:
      new Date()
        .toISOString(),
  };

  cache.set(
    key,
    result,
  );

  return {
    ...result,

    cacheHit: false,

    key,
  };
}

export function mountCachedPredictionLabV2({
  source = {},
  documentRef = globalThis.document,
  cache = predictionLabCache,
  maxAgeMs = 30000,
  forceRefresh = false,
} = {}) {
  if (!documentRef) {
    return {
      mounted: false,

      reason:
        "document_unavailable",

      cacheHit: false,
    };
  }

  let container =
    documentRef.querySelector(
      "#arkPredictionLabV2",
    );

  if (!container) {
    container =
      documentRef.createElement(
        "section",
      );

    container.id =
      "arkPredictionLabV2";

    container.className =
      "arkPredictionLabV2Root";

    const anchor =
      documentRef.querySelector(
        "#arkIntegratedAiDashboard, #aiAnalysisResult, .ai-analysis-result",
      );

    if (
      anchor &&
      typeof anchor
        .insertAdjacentElement ===
        "function"
    ) {
      anchor.insertAdjacentElement(
        "afterend",
        container,
      );
    }
    else {
      documentRef.body
        ?.appendChild(
          container,
        );
    }
  }

  const rendered =
    renderCachedPredictionLabV2({
      source,
      cache,
      maxAgeMs,
      forceRefresh,
    });

  container.innerHTML =
    rendered.html;

  container.dataset
    .predictionLabV2Status =
    "ready";

  container.dataset
    .predictionLabCache =
    rendered.cacheHit
      ? "hit"
      : "miss";

  return {
    mounted: true,

    container,

    cacheHit:
      rendered.cacheHit,

    createdAt:
      rendered.createdAt,
  };
}

export function invalidatePredictionLabCache({
  cache = predictionLabCache,
} = {}) {
  cache.clear();

  return {
    cleared: true,

    size:
      cache.size(),
  };
}

export const CachedPredictionLabInternals = {
  stableValue,
};