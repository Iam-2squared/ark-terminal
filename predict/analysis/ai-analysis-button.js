function resolveButtonAnchor(
  documentRef,
) {
  const selectors = [
    "#aiAnalysis",
    ".ai-analysis",
    "[data-ai-analysis]",
    "#arkPredictionLabV3",
    "#arkPredictionLabV2",
    "main",
  ];

  for (const selector of selectors) {
    const anchor =
      documentRef.querySelector(
        selector,
      );

    if (anchor) {
      return anchor;
    }
  }

  return documentRef.body ?? null;
}

export function createAIAnalysisButton({
  documentRef = globalThis.document,
  label = "AI分析を実行",
} = {}) {
  if (!documentRef) {
    return null;
  }

  const existing =
    documentRef.querySelector(
      "#aiAnalysisButton",
    );

  if (existing) {
    return existing;
  }

  const button =
    documentRef.createElement(
      "button",
    );

  button.id =
    "aiAnalysisButton";

  button.type =
    "button";

  button.className =
    "arkAIAnalysisButton";

  button.dataset
    .aiAnalysisButton =
    "true";

  button.dataset
    .aiAnalysisState =
    "ready";

  button.textContent =
    label;

  return button;
}

export function installAIAnalysisButton({
  documentRef = globalThis.document,
  label = "AI分析を実行",
} = {}) {
  if (!documentRef) {
    return {
      installed: false,
      reason:
        "document_unavailable",
      button: null,
    };
  }

  const existing =
    documentRef.querySelector(
      "#aiAnalysisButton",
    );

  if (existing) {
    return {
      installed: true,
      reused: true,
      button:
        existing,
    };
  }

  const button =
    createAIAnalysisButton({
      documentRef,
      label,
    });

  if (!button) {
    return {
      installed: false,
      reason:
        "button_creation_failed",
      button: null,
    };
  }

  const wrapper =
    documentRef.createElement(
      "div",
    );

  wrapper.className =
    "arkAIAnalysisButtonWrap";

  wrapper.dataset
    .aiAnalysisButtonWrap =
    "true";

  wrapper.appendChild(
    button,
  );

  const anchor =
    resolveButtonAnchor(
      documentRef,
    );

  if (
    anchor &&
    typeof anchor
      .insertAdjacentElement ===
      "function"
  ) {
    anchor.insertAdjacentElement(
      "afterend",
      wrapper,
    );
  }
  else if (
    documentRef.body &&
    typeof documentRef.body
      .appendChild ===
      "function"
  ) {
    documentRef.body.appendChild(
      wrapper,
    );
  }
  else {
    return {
      installed: false,
      reason:
        "mount_target_unavailable",
      button: null,
    };
  }

  return {
    installed: true,
    reused: false,
    button,
    wrapper,
  };
}

export function setAIAnalysisButtonState({
  button,
  state = "ready",
  labels = {},
} = {}) {
  if (!button) {
    return false;
  }

  const normalized =
    String(state)
      .toLowerCase();

  const defaultLabels = {
    ready:
      "AI分析を実行",

    running:
      "AI分析中...",

    success:
      "分析完了",

    error:
      "再試行",
  };

  const label =
    labels[normalized] ??
    defaultLabels[normalized] ??
    defaultLabels.ready;

  button.dataset
    .aiAnalysisState =
    normalized;

  button.disabled =
    normalized ===
    "running";

  button.textContent =
    label;

  return true;
}

export function connectAIAnalysisButtonState({
  eventTarget = globalThis.window,
  documentRef = globalThis.document,
} = {}) {
  if (
    !eventTarget ||
    !documentRef
  ) {
    return () => {};
  }

  const button =
    documentRef.querySelector(
      "#aiAnalysisButton",
    );

  if (!button) {
    return () => {};
  }

  const startHandler = () => {
    setAIAnalysisButtonState({
      button,
      state:
        "running",
    });
  };

  const completeHandler = () => {
    setAIAnalysisButtonState({
      button,
      state:
        "success",
    });

    const timeout =
      eventTarget.setTimeout ??
      globalThis.setTimeout;

    timeout?.(
      () => {
        setAIAnalysisButtonState({
          button,
          state:
            "ready",
        });
      },
      1200,
    );
  };

  const errorHandler = () => {
    setAIAnalysisButtonState({
      button,
      state:
        "error",
    });
  };

  eventTarget.addEventListener(
    "ark:ai-analysis-start",
    startHandler,
  );

  eventTarget.addEventListener(
    "ark:ai-analysis-complete",
    completeHandler,
  );

  eventTarget.addEventListener(
    "ark:ai-analysis-error",
    errorHandler,
  );

  return () => {
    eventTarget.removeEventListener(
      "ark:ai-analysis-start",
      startHandler,
    );

    eventTarget.removeEventListener(
      "ark:ai-analysis-complete",
      completeHandler,
    );

    eventTarget.removeEventListener(
      "ark:ai-analysis-error",
      errorHandler,
    );
  };
}

export function initializeAIAnalysisButton({
  eventTarget = globalThis.window,
  documentRef = globalThis.document,
} = {}) {
  const installation =
    installAIAnalysisButton({
      documentRef,
    });

  const cleanup =
    installation.installed
      ? connectAIAnalysisButtonState({
          eventTarget,
          documentRef,
        })
      : () => {};

  return {
    ...installation,
    cleanup,
  };
}