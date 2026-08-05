import {
  mountCachedPredictionLabV2,
} from "./cached-prediction-lab-controller.js";

import {
  normalizeAnalysisEventSource,
} from "./analysis-event-bridge.js";

import {
  startModelPerformanceUiV1,
} from "./model-performance-ui-v1.js";

let cleanupCurrentListeners = null;
let cleanupModelPerformanceUi = null;

export function createPredictionLabRuntime({
  windowRef = globalThis.window,
  documentRef = globalThis.document,
} = {}) {
  if (
    !windowRef ||
    !documentRef
  ) {
    return {
      started: false,
      stop() {},
      render() {
        return {
          mounted: false,
          reason: "environment_unavailable",
        };
      },
    };
  }

  let lastSignature = "";

  const render =
    (source = {}) => {
      const normalized =
        normalizeAnalysisEventSource(
          source,
        );

      let signature = "";

      try {
        signature =
          JSON.stringify(normalized);
      }
      catch {
        signature =
          String(Date.now());
      }

      if (
        signature === lastSignature
      ) {
        return {
          mounted: false,
          reason: "duplicate_payload",
        };
      }

      lastSignature =
        signature;

      windowRef
        .__ARK_ANALYSIS_STATE__ =
        normalized;

      return mountCachedPredictionLabV2({
        source: normalized,
        documentRef,
      });
    };

  const handleAnalysis =
    (event) => {
      render(
        event?.detail ??
        event ??
        {},
      );
    };

  const eventNames = [
    "ark:analysis-ready",
    "ark:ai-analysis-complete",
    "ark:analysis-complete",
    "ark:prediction-complete",
    "ai-analysis-complete",
  ];

  for (const eventName of eventNames) {
    windowRef.addEventListener(
      eventName,
      handleAnalysis,
    );
  }

  const initialState =
    windowRef
      .__ARK_ANALYSIS_STATE__ ??
    windowRef
      .__ARK_LATEST_ANALYSIS__ ??
    windowRef
      .__ARK_AI_ANALYSIS__ ??
    null;

  if (initialState) {
    render(initialState);
  }

  cleanupModelPerformanceUi?.();
  const modelPerformanceUi =
    startModelPerformanceUiV1({
      windowRef,
      documentRef,
    });
  cleanupModelPerformanceUi =
    modelPerformanceUi.stop;

  const stop = () => {
    for (const eventName of eventNames) {
      windowRef.removeEventListener(
        eventName,
        handleAnalysis,
      );
    }

    modelPerformanceUi.stop();

    if (
      cleanupModelPerformanceUi ===
      modelPerformanceUi.stop
    ) {
      cleanupModelPerformanceUi = null;
    }
  };

  return {
    started: true,
    render,
    stop,
  };
}

export function startPredictionLabRuntime({
  windowRef = globalThis.window,
  documentRef = globalThis.document,
} = {}) {
  cleanupCurrentListeners?.();

  const runtime =
    createPredictionLabRuntime({
      windowRef,
      documentRef,
    });

  cleanupCurrentListeners =
    runtime.stop;

  return runtime;
}

export function stopPredictionLabRuntime() {
  cleanupCurrentListeners?.();
  cleanupCurrentListeners = null;
  cleanupModelPerformanceUi?.();
  cleanupModelPerformanceUi = null;
}

if (
  typeof window !== "undefined" &&
  typeof document !== "undefined"
) {
  window.ArkPredictionLabRuntime = {
    start:
      startPredictionLabRuntime,

    stop:
      stopPredictionLabRuntime,
  };

  const start = () => {
    startPredictionLabRuntime();
  };

  if (
    document.readyState === "loading"
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