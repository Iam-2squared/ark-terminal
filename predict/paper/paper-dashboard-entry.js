import {
  createPaperLearningBridge,
} from "./paper-learning-bridge.js";
import {
  createPaperDashboardController,
} from "./paper-dashboard-controller.js";

export const PAPER_DASHBOARD_ENTRY_VERSION =
  "paper-dashboard-entry-v1";

let controller = null;

function resolveRoot(
  documentRef =
    globalThis.document,
) {
  if (
    !documentRef ||
    typeof documentRef
      .getElementById !==
      "function"
  ) {
    return null;
  }

  return documentRef.getElementById(
    "paper-trading-dashboard",
  );
}

export function startPaperDashboard({
  documentRef =
    globalThis.document,

  storage =
    globalThis.localStorage,

  initialCash =
    1_000_000,
} = {}) {
  if (controller) {
    return controller;
  }

  const root =
    resolveRoot(
      documentRef,
    );

  if (!root) {
    return null;
  }

  controller =
    createPaperDashboardController({
      root,
      storage,
      initialCash,
    });

  const learningBridge =
    createPaperLearningBridge({
      dashboardController:
        controller,
    });

  controller.render();

  if (
    typeof window !==
    "undefined"
  ) {
    window.ArkPaperTrading = {
      controller,

      getState:
        () =>
          controller.getState(),

      getBroker:
        () =>
          controller.getBroker(),

      getSnapshot:
        () =>
          controller.getSnapshot(),

      submitOrder:
        (options) =>
          controller.submitOrder(
            options,
          ),

      fillOrder:
        (options) =>
          controller.fillOrder(
            options,
          ),

      cancelOrder:
        (options) =>
          controller.cancelOrder(
            options,
          ),

      updatePrices:
        (prices) =>
          controller.updatePrices(
            prices,
          ),

      activateKillSwitch:
        (options) =>
          controller
            .activateKillSwitch(
              options,
            ),

      deactivateKillSwitch:
        () =>
          controller
            .deactivateKillSwitch(),

      reset:
        () =>
          controller.reset(),

      render:
        () =>
          controller.render(),

      analyzeLearning:
        () =>
          learningBridge.analyze(),

      enqueueLearning:
        (options) =>
          learningBridge.enqueue(
            options,
          ),

      reviewLearning:
        (options) =>
          learningBridge.review(
            options,
          ),

      applyLearning:
        (options) =>
          learningBridge.apply(
            options,
          ),

      getLearningState:
        () =>
          learningBridge.getState(),

      getLearningSummary:
        () =>
          learningBridge.getSummary(),

      getLearningQueue:
        () =>
          learningBridge.getQueue(),
    };
  }

  return controller;
}

export function stopPaperDashboard() {
  controller = null;

  if (
    typeof window !==
    "undefined" &&
    window.ArkPaperTrading
  ) {
    delete window.ArkPaperTrading;
  }
}

if (
  typeof window !==
    "undefined" &&
  typeof document !==
    "undefined"
) {
  const start = () => {
    startPaperDashboard();
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

export const PaperDashboardEntryInternals = {
  resolveRoot,
};