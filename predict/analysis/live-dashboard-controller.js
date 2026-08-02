import {
  renderAnalysisPanel,
} from "./ui-integration.js";

const DEFAULT_MACRO_INPUT = Object.freeze({
  nikkei: 0,
  nasdaq: 0,
  sox: 0,
  usdjpy: 150,
  vix: 20,
  bondYield: 4,
  oil: 80,
});

const DEFAULT_MARKET_INPUT = Object.freeze({
  trendScore: 50,
  volatility: 20,
  adx: 20,
  rsi: 50,
  vix: 20,
});

function finite(value, fallback = 0) {
  const number = Number(value);

  return Number.isFinite(number)
    ? number
    : fallback;
}

function readFirst(source, paths, fallback = null) {
  for (const path of paths) {
    const value =
      path
        .split(".")
        .reduce(
          (current, key) =>
            current?.[key],
          source,
        );

    if (
      value !== undefined &&
      value !== null &&
      value !== ""
    ) {
      return value;
    }
  }

  return fallback;
}

export function buildDashboardInput(
  source = {},
) {
  const state =
    source.state ??
    source.analysisState ??
    source.latestAnalysis ??
    source;

  const technicalScore =
    finite(
      readFirst(
        state,
        [
          "analysis.technicalScore",
          "analysis.totalScore",
          "aiAnalysis.overallAiScore",
          "prediction.score",
          "score",
        ],
        50,
      ),
      50,
    );

  const confidence =
    finite(
      readFirst(
        state,
        [
          "aiAnalysis.confidence.score",
          "prediction.confidence",
          "analysis.confidence",
          "confidence",
        ],
        50,
      ),
      50,
    );

  const rsi =
    finite(
      readFirst(
        state,
        [
          "indicators.rsi.value",
          "indicators.rsi",
          "rsi",
        ],
        50,
      ),
      50,
    );

  const adx =
    finite(
      readFirst(
        state,
        [
          "indicators.adx.value",
          "indicators.adx",
          "adx",
        ],
        20,
      ),
      20,
    );

  const atrPercent =
    finite(
      readFirst(
        state,
        [
          "indicators.atr.percent",
          "indicators.atrPercent",
          "atrPercent",
        ],
        2.5,
      ),
      2.5,
    );

  return {
    state: {
      ...state,

      analysis: {
        ...(state.analysis ?? {}),

        technicalScore,

        totalScore:
          finite(
            state.analysis?.totalScore,
            technicalScore,
          ),

        confidence,

        dataQualityScore:
          finite(
            state.analysis
              ?.dataQualityScore,
            75,
          ),
      },

      prediction: {
        ...(state.prediction ?? {}),

        confidence:
          finite(
            state.prediction
              ?.confidence,
            confidence,
          ),
      },

      indicators: {
        ...(state.indicators ?? {}),

        rsi,

        adx: {
          value: adx,
        },

        atr: {
          percent:
            atrPercent,
        },
      },
    },

    macroInput: {
      ...DEFAULT_MACRO_INPUT,
      ...(source.macroInput ?? {}),
      ...(state.macroInput ?? {}),
    },

    marketInput: {
      ...DEFAULT_MARKET_INPUT,
      trendScore:
        finite(
          source.marketInput
            ?.trendScore ??
          state.marketInput
            ?.trendScore,
          technicalScore,
        ),

      volatility:
        finite(
          source.marketInput
            ?.volatility ??
          state.marketInput
            ?.volatility,
          atrPercent * 5,
        ),

      adx,

      rsi,

      vix:
        finite(
          source.marketInput?.vix ??
          state.marketInput?.vix ??
          source.macroInput?.vix ??
          state.macroInput?.vix,
          20,
        ),
    },

    portfolioPlan:
      source.portfolioPlan ??
      state.portfolioPlan ??
      {},
  };
}

export function resolveDashboardContainer(
  documentRef = globalThis.document,
) {
  if (!documentRef) {
    return null;
  }

  const selectors = [
    "#arkIntegratedAiDashboard",
    "[data-ark-integrated-ai-dashboard]",
    "#aiAnalysisResult",
    "#ai-analysis-result",
    ".ai-analysis-result",
    ".ai-analysis-content",
  ];

  for (const selector of selectors) {
    const found =
      documentRef.querySelector(selector);

    if (found) {
      return found;
    }
  }

  const container =
    documentRef.createElement("section");

  container.id =
    "arkIntegratedAiDashboard";

  container.dataset
    .arkIntegratedAiDashboard =
    "true";

  container.className =
    "ark-integrated-ai-dashboard";

  const anchor =
    documentRef.querySelector(
      "#aiAnalysis, .ai-analysis, [data-ai-analysis]",
    );

  if (anchor?.parentNode) {
    anchor.insertAdjacentElement(
      "afterend",
      container,
    );
  } else {
    documentRef.body?.appendChild(
      container,
    );
  }

  return container;
}

export function renderLiveAiDashboard({
  source = {},
  documentRef = globalThis.document,
} = {}) {
  const container =
    resolveDashboardContainer(
      documentRef,
    );

  if (!container) {
    return {
      rendered: false,
      reason:
        "Dashboard container unavailable",
    };
  }

  const input =
    buildDashboardInput(source);

  container.innerHTML =
    renderAnalysisPanel(input);

  container.dataset
    .arkDashboardState =
    "ready";

  return {
    rendered: true,
    container,
    input,
  };
}

export function connectLiveAiDashboard({
  eventTarget = globalThis.window,
  documentRef = globalThis.document,
} = {}) {
  if (!eventTarget || !documentRef) {
    return () => {};
  }

  const renderFromEvent =
    (event) => {
      renderLiveAiDashboard({
        source:
          event?.detail ?? {},
        documentRef,
      });
    };

  eventTarget.addEventListener(
    "ark:analysis-ready",
    renderFromEvent,
  );

  eventTarget.addEventListener(
    "ark:ai-analysis-complete",
    renderFromEvent,
  );

  const initialSource =
    eventTarget.__ARK_ANALYSIS_STATE__ ??
    eventTarget.__ARK_LATEST_ANALYSIS__ ??
    null;

  if (initialSource) {
    renderLiveAiDashboard({
      source: initialSource,
      documentRef,
    });
  }

  return () => {
    eventTarget.removeEventListener(
      "ark:analysis-ready",
      renderFromEvent,
    );

    eventTarget.removeEventListener(
      "ark:ai-analysis-complete",
      renderFromEvent,
    );
  };
}

if (
  typeof window !== "undefined" &&
  typeof document !== "undefined"
) {
  window.ArkIntegratedAiDashboard = {
    buildDashboardInput,
    renderLiveAiDashboard,
  };

  if (
    document.readyState === "loading"
  ) {
    document.addEventListener(
      "DOMContentLoaded",
      () => {
        connectLiveAiDashboard();
      },
      {
        once: true,
      },
    );
  } else {
    connectLiveAiDashboard();
  }
}