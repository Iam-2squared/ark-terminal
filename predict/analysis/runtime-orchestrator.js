import {
  buildAnalysisCore,
} from "./analysis-core.js";

import {
  renderAnalysisPanel,
} from "./ui-integration.js";

function finite(value, fallback = 0) {
  const number = Number(value);

  return Number.isFinite(number)
    ? number
    : fallback;
}

export function normalizeRuntimeInput(
  input = {},
) {
  const state =
    input.state ??
    input.analysisState ??
    input;

  return {
    state: {
      ...state,

      analysis: {
        ...(state.analysis ?? {}),

        technicalScore:
          finite(
            state.analysis?.technicalScore ??
            state.analysis?.totalScore ??
            state.totalScore,
            50,
          ),

        totalScore:
          finite(
            state.analysis?.totalScore ??
            state.analysis?.technicalScore ??
            state.totalScore,
            50,
          ),

        confidence:
          finite(
            state.analysis?.confidence ??
            state.prediction?.confidence ??
            state.confidence,
            50,
          ),

        dataQualityScore:
          finite(
            state.analysis?.dataQualityScore ??
            state.dataQualityScore,
            75,
          ),
      },

      prediction: {
        ...(state.prediction ?? {}),

        confidence:
          finite(
            state.prediction?.confidence ??
            state.analysis?.confidence ??
            state.confidence,
            50,
          ),
      },

      indicators: {
        ...(state.indicators ?? {}),

        rsi:
          finite(
            state.indicators?.rsi?.value ??
            state.indicators?.rsi ??
            state.rsi,
            50,
          ),

        adx: {
          value:
            finite(
              state.indicators?.adx?.value ??
              state.indicators?.adx ??
              state.adx,
              20,
            ),
        },

        atr: {
          percent:
            finite(
              state.indicators?.atr?.percent ??
              state.indicators?.atrPercent ??
              state.atrPercent,
              2.5,
            ),
        },
      },
    },

    macroInput: {
      nikkei:
        finite(
          input.macroInput?.nikkei ??
          state.macroInput?.nikkei,
          0,
        ),

      nasdaq:
        finite(
          input.macroInput?.nasdaq ??
          state.macroInput?.nasdaq,
          0,
        ),

      sox:
        finite(
          input.macroInput?.sox ??
          state.macroInput?.sox,
          0,
        ),

      usdjpy:
        finite(
          input.macroInput?.usdjpy ??
          state.macroInput?.usdjpy,
          150,
        ),

      vix:
        finite(
          input.macroInput?.vix ??
          state.macroInput?.vix,
          20,
        ),

      bondYield:
        finite(
          input.macroInput?.bondYield ??
          state.macroInput?.bondYield,
          4,
        ),

      oil:
        finite(
          input.macroInput?.oil ??
          state.macroInput?.oil,
          80,
        ),
    },

    marketInput: {
      trendScore:
        finite(
          input.marketInput?.trendScore ??
          state.marketInput?.trendScore ??
          state.analysis?.technicalScore,
          50,
        ),

      volatility:
        finite(
          input.marketInput?.volatility ??
          state.marketInput?.volatility,
          20,
        ),

      adx:
        finite(
          input.marketInput?.adx ??
          state.indicators?.adx?.value ??
          state.indicators?.adx,
          20,
        ),

      rsi:
        finite(
          input.marketInput?.rsi ??
          state.indicators?.rsi?.value ??
          state.indicators?.rsi,
          50,
        ),

      vix:
        finite(
          input.marketInput?.vix ??
          input.macroInput?.vix ??
          state.marketInput?.vix ??
          state.macroInput?.vix,
          20,
        ),
    },

    portfolioPlan:
      input.portfolioPlan ??
      state.portfolioPlan ??
      {},
  };
}

export function executeAiRuntime(
  input = {},
) {
  const normalized =
    normalizeRuntimeInput(
      input,
    );

  const analysis =
    buildAnalysisCore(
      normalized,
    );

  const html =
    renderAnalysisPanel(
      normalized,
    );

  return {
    version:
      "ark-ai-runtime-v1",

    generatedAt:
      new Date().toISOString(),

    normalized,

    analysis,

    html,

    status: "ready",
  };
}

export function renderAiRuntime({
  input = {},
  documentRef = globalThis.document,
  selector = "#arkIntegratedAiDashboard",
} = {}) {
  if (!documentRef) {
    return {
      rendered: false,
      reason:
        "document_unavailable",
    };
  }

  let container =
    documentRef.querySelector(
      selector,
    );

  if (!container) {
    container =
      documentRef.createElement(
        "section",
      );

    container.id =
      selector.startsWith("#")
        ? selector.slice(1)
        : "arkIntegratedAiDashboard";

    container.className =
      "ark-integrated-ai-dashboard";

    documentRef.body?.appendChild(
      container,
    );
  }

  const runtime =
    executeAiRuntime(
      input,
    );

  container.innerHTML =
    runtime.html;

  container.dataset
    .arkRuntimeStatus =
    "ready";

  return {
    rendered: true,
    container,
    runtime,
  };
}

export function connectAiRuntime({
  eventTarget = globalThis.window,
  documentRef = globalThis.document,
} = {}) {
  if (
    !eventTarget ||
    !documentRef
  ) {
    return () => {};
  }

  const handler =
    (event) => {
      const input =
        event?.detail ??
        eventTarget
          .__ARK_ANALYSIS_STATE__ ??
        {};

      eventTarget
        .__ARK_ANALYSIS_STATE__ =
        input;

      renderAiRuntime({
        input,
        documentRef,
      });
    };

  eventTarget.addEventListener(
    "ark:analysis-ready",
    handler,
  );

  eventTarget.addEventListener(
    "ark:ai-analysis-complete",
    handler,
  );

  const initial =
    eventTarget
      .__ARK_ANALYSIS_STATE__;

  if (initial) {
    renderAiRuntime({
      input: initial,
      documentRef,
    });
  }

  return () => {
    eventTarget.removeEventListener(
      "ark:analysis-ready",
      handler,
    );

    eventTarget.removeEventListener(
      "ark:ai-analysis-complete",
      handler,
    );
  };
}

if (
  typeof window !== "undefined" &&
  typeof document !== "undefined"
) {
  window.ArkAiRuntime = {
    executeAiRuntime,
    normalizeRuntimeInput,
    renderAiRuntime,
  };

  const start = () => {
    connectAiRuntime();
  };

  if (
    document.readyState ===
    "loading"
  ) {
    document.addEventListener(
      "DOMContentLoaded",
      start,
      {
        once: true,
      },
    );
  }
  else {
    start();
  }
}