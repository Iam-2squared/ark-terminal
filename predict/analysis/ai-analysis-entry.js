import { installHistoryExportApi } from "./ai-analysis-history-export.js";
import { connectAnalysisHistoryPanel } from "./ai-analysis-history-panel.js";
import { connectAIAnalysisHistory } from "./ai-analysis-history.js";
import { connectAIExplainabilityPanel } from "./ai-explainability-panel.js";
import { connectAIAnalysisStatusPanel } from "./ai-analysis-status-panel.js";
import { installAISettingsButton, connectAIAnalysisSettingsUI } from "./ai-analysis-settings-ui.js";
import { installAIAnalysisSettings } from "./ai-analysis-settings.js";
import { initializeAIAnalysisButton } from "./ai-analysis-button.js";
import "./ai-analysis-input-builder.js";
import {
  AIAnalysisController,
  connectAIAnalysisButton,
} from "./ai-analysis-controller.js";

import {
  connectAIResultPresenter,
} from "./ai-result-presenter.js";

let currentCleanup = null;

function defaultInputProvider({
  windowRef = globalThis.window,
} = {}) {
  return (
    windowRef?.__ARK_ANALYSIS_INPUT__ ??
    windowRef?.__ARK_ANALYSIS_STATE__ ??
    {}
  );
}

export function createAIAnalysisApplication({
  windowRef = globalThis.window,
  documentRef = globalThis.document,
  runner,
  inputProvider,
} = {}) {
  if (
    !windowRef ||
    !documentRef
  ) {
    return {
      started: false,

      controller: null,

      analyze: async () => ({
        status: "unavailable",
        result: null,
        error: null,
      }),

      stop() {},
    };
  }

  const controller =
    new AIAnalysisController({
      eventTarget:
        windowRef,

      ...(runner
        ? {
            runner,
          }
        : {}),
    });

  const provideInput =
    typeof inputProvider ===
    "function"
      ? inputProvider
      : () =>
          defaultInputProvider({
            windowRef,
          });

  const cleanupButton =
    connectAIAnalysisButton({
      controller,
      documentRef,
      inputProvider:
        provideInput,
    });

  const cleanupPresenter =
    connectAIResultPresenter({
      eventTarget:
        windowRef,

      documentRef,
    });

  const analyze =
    async (
      input = provideInput(),
    ) => {
      return controller.analyze(
        input,
      );
    };

  const stop = () => {
    cleanupButton();
    cleanupPresenter();
  };

  windowRef.ArkAIAnalysis = {
    analyze,
    controller,

    getState:
      () =>
        controller.getState(),
  };

  return {
    started: true,

    controller,

    analyze,

    stop,
  };
}

export function startAIAnalysisApplication({
  windowRef = globalThis.window,
  documentRef = globalThis.document,
  runner,
  inputProvider,
} = {}) {
  currentCleanup?.();

  const application =
    createAIAnalysisApplication({
      windowRef,
      documentRef,
      runner,
      inputProvider,
    });

  currentCleanup =
    application.stop;

  return application;
}

export function stopAIAnalysisApplication() {
  currentCleanup?.();
  currentCleanup = null;
}

if (
  typeof window !== "undefined" &&
  typeof document !== "undefined"
) {
  const start = () => {
    installAIAnalysisSettings({
      windowRef: window,
      storage: window.localStorage,
    });

    initializeAIAnalysisButton({
      eventTarget: window,
      documentRef: document,
    });

    installAISettingsButton({
      documentRef: document,
    });

    connectAIAnalysisSettingsUI({
      windowRef: window,
      documentRef: document,
    });

    connectAIAnalysisStatusPanel({
      eventTarget: window,
      documentRef: document,
    });

    connectAIExplainabilityPanel({
      eventTarget: window,
      documentRef: document,
    });

    const historyConnection =
      connectAIAnalysisHistory({
        eventTarget: window,
        storage: window.localStorage,
        limit: 100,
      });

    connectAnalysisHistoryPanel({
      eventTarget: window,
      documentRef: document,
      store: historyConnection.store,
    });

    installHistoryExportApi({
      windowRef: window,
    });

    startAIAnalysisApplication();
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