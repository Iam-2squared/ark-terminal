import {
  runAIAnalysis,
} from "./ai-result-composer.js";

function createCustomEvent(
  eventTarget,
  name,
  detail,
) {
  const EventConstructor =
    eventTarget?.CustomEvent ??
    globalThis.CustomEvent;

  if (
    typeof EventConstructor !==
    "function"
  ) {
    return null;
  }

  return new EventConstructor(
    name,
    {
      detail,
    },
  );
}

export class AIAnalysisController {
  constructor({
    eventTarget =
      globalThis.window,

    runner =
      runAIAnalysis,
  } = {}) {
    this.eventTarget =
      eventTarget;

    this.runner =
      runner;

    this.running =
      false;

    this.lastResult =
      null;

    this.lastError =
      null;
  }

  emit(
    name,
    detail,
  ) {
    if (
      !this.eventTarget ||
      typeof this.eventTarget
        .dispatchEvent !==
        "function"
    ) {
      return false;
    }

    const event =
      createCustomEvent(
        this.eventTarget,
        name,
        detail,
      );

    if (!event) {
      return false;
    }

    this.eventTarget
      .dispatchEvent(
        event,
      );

    return true;
  }

  async analyze(
    input = {},
  ) {
    if (this.running) {
      return {
        status:
          "busy",

        result:
          this.lastResult,

        error:
          null,
      };
    }

    this.running =
      true;

    this.lastError =
      null;

    this.emit(
      "ark:ai-analysis-start",
      {
        input,
      },
    );

    try {
      const result =
        await this.runner(
          input,
        );

      this.lastResult =
        result;

      if (this.eventTarget) {
        this.eventTarget
          .__ARK_LATEST_ANALYSIS__ =
          result;

        this.eventTarget
          .__ARK_ANALYSIS_STATE__ =
          result;
      }

      this.emit(
        "ark:ai-analysis-complete",
        result,
      );

      return {
        status:
          "ready",

        result,

        error:
          null,
      };
    }
    catch (error) {
      this.lastError =
        error;

      const payload = {
        status:
          "error",

        message:
          error?.message ??
          String(error),

        input,
      };

      this.emit(
        "ark:ai-analysis-error",
        payload,
      );

      return {
        status:
          "error",

        result:
          null,

        error:
          payload,
      };
    }
    finally {
      this.running =
        false;
    }
  }

  getState() {
    return {
      running:
        this.running,

      lastResult:
        this.lastResult,

      lastError:
        this.lastError,
    };
  }

  reset() {
    this.running =
      false;

    this.lastResult =
      null;

    this.lastError =
      null;

    return this.getState();
  }
}

export function connectAIAnalysisButton({
  controller,
  documentRef =
    globalThis.document,

  buttonSelector =
    "#aiAnalysisButton, #ai-analysis-button, [data-ai-analysis-button]",

  inputProvider =
    () => (
      globalThis.window
        ?.__ARK_ANALYSIS_INPUT__ ??
      {}
    ),
} = {}) {
  if (
    !controller ||
    !documentRef
  ) {
    return () => {};
  }

  const button =
    documentRef.querySelector(
      buttonSelector,
    );

  if (!button) {
    return () => {};
  }

  const handleClick =
    async () => {
      button.disabled =
        true;

      button.dataset
        .aiAnalysisState =
        "running";

      try {
        await controller.analyze(
          inputProvider(),
        );
      }
      finally {
        button.disabled =
          false;

        button.dataset
          .aiAnalysisState =
          "ready";
      }
    };

  button.addEventListener(
    "click",
    handleClick,
  );

  return () => {
    button.removeEventListener(
      "click",
      handleClick,
    );
  };
}

export const
aiAnalysisController =
new AIAnalysisController();

if (
  typeof window !== "undefined" &&
  typeof document !== "undefined"
) {
  window.ArkAIAnalysisController = {
    controller:
      aiAnalysisController,

    analyze:
      (input = {}) =>
        aiAnalysisController
          .analyze(input),
  };

  const start = () => {
    connectAIAnalysisButton({
      controller:
        aiAnalysisController,
    });
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