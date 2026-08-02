import assert from "node:assert/strict";
import test from "node:test";

import {
  installAIAnalysisSettings,
  mergeAIAnalysisSettings,
  normalizeAIAnalysisSettings,
  readAIAnalysisSettings,
  saveAIAnalysisSettings,
} from "../analysis/ai-analysis-settings.js";

function createStorage() {
  const values =
    new Map();

  return {
    getItem(key) {
      return values.has(key)
        ? values.get(key)
        : null;
    },

    setItem(
      key,
      value,
    ) {
      values.set(
        key,
        String(value),
      );
    },
  };
}

test(
  "Settings use safe defaults",
  () => {
    const result =
      normalizeAIAnalysisSettings({
        capital: -100,
        allocation: 2,
        lotSize: 0,
      });

    assert.equal(
      result.capital,
      0,
    );

    assert.equal(
      result.allocation,
      1,
    );

    assert.equal(
      result.lotSize,
      100,
    );

    assert.equal(
      result.minimumScore,
      60,
    );
  },
);

test(
  "Settings are merged",
  () => {
    const result =
      mergeAIAnalysisSettings(
        {
          capital: 100000,

          weights: {
            technical: 1,
            ai: 1,
            macro: 1,
          },
        },

        {
          capital: 200000,

          weights: {
            ai: 2,
          },
        },
      );

    assert.equal(
      result.capital,
      200000,
    );

    assert.equal(
      result.weights.technical,
      1,
    );

    assert.equal(
      result.weights.ai,
      2,
    );
  },
);

test(
  "Settings persist in storage",
  () => {
    const storage =
      createStorage();

    saveAIAnalysisSettings({
      storage,

      settings: {
        capital: 300000,
        allocation: 0.4,
      },
    });

    const result =
      readAIAnalysisSettings({
        storage,
      });

    assert.equal(
      result.capital,
      300000,
    );

    assert.equal(
      result.allocation,
      0.4,
    );
  },
);

test(
  "Settings API is installed",
  () => {
    const storage =
      createStorage();

    const windowRef = {};

    const result =
      installAIAnalysisSettings({
        windowRef,
        storage,
      });

    assert.equal(
      result.installed,
      true,
    );

    const updated =
      windowRef
        .ArkAIAnalysisSettings
        .update({
          capital: 500000,
          minimumConfidence: 70,
        });

    assert.equal(
      updated.capital,
      500000,
    );

    assert.equal(
      updated.minimumConfidence,
      70,
    );

    assert.equal(
      windowRef
        .__ARK_ANALYSIS_SETTINGS__
        .capital,
      500000,
    );

    const reset =
      windowRef
        .ArkAIAnalysisSettings
        .reset();

    assert.equal(
      reset.capital,
      100000,
    );
  },
);