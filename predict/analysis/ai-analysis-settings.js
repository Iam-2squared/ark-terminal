const DEFAULT_SETTINGS = Object.freeze({
  capital: 100000,
  allocation: 0.25,
  lotSize: 100,
  stopPercent: 5,
  targetPercent: 10,
  maximumRiskPercent: 6,
  minimumConfidence: 55,
  minimumScore: 60,

  weights: {
    technical: 1,
    ai: 1,
    macro: 1,
  },
});

function finiteNumber(
  value,
  fallback = 0,
) {
  const parsed =
    Number(value);

  return Number.isFinite(parsed)
    ? parsed
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
      finiteNumber(value),
    ),
  );
}

function normalizeLotSize(value) {
  const parsed =
    Math.floor(
      finiteNumber(
        value,
        DEFAULT_SETTINGS.lotSize,
      ),
    );

  return parsed > 0
    ? parsed
    : DEFAULT_SETTINGS.lotSize;
}

export function normalizeAIAnalysisSettings(
  settings = {},
) {
  return {
    capital:
      Math.max(
        0,
        finiteNumber(
          settings.capital,
          DEFAULT_SETTINGS.capital,
        ),
      ),

    allocation:
      clamp(
        settings.allocation,
        0,
        1,
      ),

    lotSize:
      normalizeLotSize(
        settings.lotSize,
      ),

    stopPercent:
      clamp(
        settings.stopPercent ??
        DEFAULT_SETTINGS.stopPercent,
        0,
        100,
      ),

    targetPercent:
      Math.max(
        0,
        finiteNumber(
          settings.targetPercent,
          DEFAULT_SETTINGS.targetPercent,
        ),
      ),

    maximumRiskPercent:
      Math.max(
        0,
        finiteNumber(
          settings.maximumRiskPercent,
          DEFAULT_SETTINGS.maximumRiskPercent,
        ),
      ),

    minimumConfidence:
      clamp(
        settings.minimumConfidence ??
        DEFAULT_SETTINGS.minimumConfidence,
        0,
        100,
      ),

    minimumScore:
      clamp(
        settings.minimumScore ??
        DEFAULT_SETTINGS.minimumScore,
        0,
        100,
      ),

    weights: {
      technical:
        Math.max(
          0,
          finiteNumber(
            settings.weights?.technical,
            DEFAULT_SETTINGS.weights.technical,
          ),
        ),

      ai:
        Math.max(
          0,
          finiteNumber(
            settings.weights?.ai,
            DEFAULT_SETTINGS.weights.ai,
          ),
        ),

      macro:
        Math.max(
          0,
          finiteNumber(
            settings.weights?.macro,
            DEFAULT_SETTINGS.weights.macro,
          ),
        ),
    },
  };
}

export function mergeAIAnalysisSettings(
  current = {},
  patch = {},
) {
  return normalizeAIAnalysisSettings({
    ...current,
    ...patch,

    weights: {
      ...(current.weights ?? {}),
      ...(patch.weights ?? {}),
    },
  });
}

export function readAIAnalysisSettings({
  storage =
    globalThis.localStorage,
  key =
    "ark-ai-analysis-settings",
} = {}) {
  if (
    !storage ||
    typeof storage.getItem !==
    "function"
  ) {
    return normalizeAIAnalysisSettings();
  }

  try {
    const raw =
      storage.getItem(key);

    if (!raw) {
      return normalizeAIAnalysisSettings();
    }

    return normalizeAIAnalysisSettings(
      JSON.parse(raw),
    );
  }
  catch {
    return normalizeAIAnalysisSettings();
  }
}

export function saveAIAnalysisSettings({
  settings = {},
  storage =
    globalThis.localStorage,
  key =
    "ark-ai-analysis-settings",
} = {}) {
  const normalized =
    normalizeAIAnalysisSettings(
      settings,
    );

  if (
    storage &&
    typeof storage.setItem ===
    "function"
  ) {
    storage.setItem(
      key,
      JSON.stringify(normalized),
    );
  }

  return normalized;
}

export function installAIAnalysisSettings({
  windowRef =
    globalThis.window,
  storage =
    globalThis.localStorage,
} = {}) {
  if (!windowRef) {
    return {
      installed: false,
      settings:
        normalizeAIAnalysisSettings(),
    };
  }

  let settings =
    readAIAnalysisSettings({
      storage,
    });

  windowRef
    .__ARK_ANALYSIS_SETTINGS__ =
    settings;

  windowRef.ArkAIAnalysisSettings = {
    get() {
      return {
        ...settings,

        weights: {
          ...settings.weights,
        },
      };
    },

    update(patch = {}) {
      settings =
        mergeAIAnalysisSettings(
          settings,
          patch,
        );

      saveAIAnalysisSettings({
        settings,
        storage,
      });

      windowRef
        .__ARK_ANALYSIS_SETTINGS__ =
        settings;

      return this.get();
    },

    reset() {
      settings =
        normalizeAIAnalysisSettings();

      saveAIAnalysisSettings({
        settings,
        storage,
      });

      windowRef
        .__ARK_ANALYSIS_SETTINGS__ =
        settings;

      return this.get();
    },
  };

  return {
    installed: true,
    settings:
      windowRef
        .ArkAIAnalysisSettings
        .get(),
  };
}

export const AIAnalysisSettingsInternals = {
  DEFAULT_SETTINGS,
  clamp,
  finiteNumber,
  normalizeLotSize,
};