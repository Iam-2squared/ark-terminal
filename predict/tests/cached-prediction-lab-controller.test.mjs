import assert from "node:assert/strict";
import test from "node:test";

import {
  AnalysisCache,
} from "../analysis/analysis-cache.js";

import {
  createPredictionLabCacheKey,
  invalidatePredictionLabCache,
  mountCachedPredictionLabV2,
  renderCachedPredictionLabV2,
} from "../analysis/cached-prediction-lab-controller.js";

function input() {
  return {
    state: {
      analysis: {
        technicalScore: 82,
        totalScore: 82,
        dataQualityScore: 90,
      },

      prediction: {
        confidence: 85,
      },

      indicators: {
        rsi: 60,

        adx: {
          value: 28,
        },

        atr: {
          percent: 2,
        },
      },
    },

    macroInput: {
      nikkei: 1,
      nasdaq: 1,
      sox: 2,
      vix: 18,
    },

    history: [
      {
        return: 3,
      },
    ],
  };
}

test(
  "Equivalent input creates stable cache key",
  () => {
    const first =
      createPredictionLabCacheKey({
        macroInput: {
          vix: 18,
          nikkei: 1,
        },

        state: {
          analysis: {
            technicalScore: 80,
          },
        },
      });

    const second =
      createPredictionLabCacheKey({
        state: {
          analysis: {
            technicalScore: 80,
          },
        },

        macroInput: {
          nikkei: 1,
          vix: 18,
        },
      });

    assert.deepEqual(
      first,
      second,
    );
  },
);

test(
  "Second render uses cache",
  () => {
    const cache =
      new AnalysisCache();

    const first =
      renderCachedPredictionLabV2({
        source:
          input(),

        cache,
      });

    const second =
      renderCachedPredictionLabV2({
        source:
          input(),

        cache,
      });

    assert.equal(
      first.cacheHit,
      false,
    );

    assert.equal(
      second.cacheHit,
      true,
    );

    assert.equal(
      first.html,
      second.html,
    );
  },
);

test(
  "Force refresh bypasses cache",
  () => {
    const cache =
      new AnalysisCache();

    renderCachedPredictionLabV2({
      source:
        input(),

      cache,
    });

    const result =
      renderCachedPredictionLabV2({
        source:
          input(),

      cache,

      forceRefresh: true,
    });

    assert.equal(
      result.cacheHit,
      false,
    );
  },
);

test(
  "Cached dashboard mounts into document",
  () => {
    const cache =
      new AnalysisCache();

    const container = {
      innerHTML: "",

      dataset: {},
    };

    const documentRef = {
      querySelector() {
        return container;
      },

      createElement() {
        return container;
      },

      body: {
        appendChild() {},
      },
    };

    const result =
      mountCachedPredictionLabV2({
        source:
          input(),

        documentRef,

        cache,
      });

    assert.equal(
      result.mounted,
      true,
    );

    assert.ok(
      container.innerHTML.includes(
        "PREDICTION LAB v2",
      ),
    );

    assert.equal(
      container.dataset
        .predictionLabCache,
      "miss",
    );
  },
);

test(
  "Prediction Lab cache can be cleared",
  () => {
    const cache =
      new AnalysisCache();

    cache.set(
      {
        symbol: "AAA",
      },

      {
        score: 80,
      },
    );

    const result =
      invalidatePredictionLabCache({
        cache,
      });

    assert.equal(
      result.cleared,
      true,
    );

    assert.equal(
      result.size,
      0,
    );
  },
);