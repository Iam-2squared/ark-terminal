function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function normalizeStatus(status = "idle") {
  const normalized =
    String(status)
      .trim()
      .toLowerCase();

  const allowed = new Set([
    "idle",
    "running",
    "success",
    "error",
  ]);

  return allowed.has(normalized)
    ? normalized
    : "idle";
}

export function buildAIAnalysisStatusViewModel({
  status = "idle",
  message = "",
  symbol = null,
  startedAt = null,
  completedAt = null,
} = {}) {
  const normalizedStatus =
    normalizeStatus(status);

  const defaultMessages = {
    idle:
      "AI分析の準備ができています",

    running:
      "市場データと分析エンジンを処理しています",

    success:
      "AI分析が完了しました",

    error:
      "AI分析中にエラーが発生しました",
  };

  return {
    status:
      normalizedStatus,

    message:
      message ||
      defaultMessages[
        normalizedStatus
      ],

    symbol:
      symbol ??
      "--",

    startedAt,

    completedAt,

    busy:
      normalizedStatus ===
      "running",

    successful:
      normalizedStatus ===
      "success",

    failed:
      normalizedStatus ===
      "error",
  };
}

export function renderAIAnalysisStatus(
  input = {},
) {
  const view =
    buildAIAnalysisStatusViewModel(
      input,
    );

  const spinner =
    view.busy
      ? `
        <span
          class="arkAIStatusSpinner"
          aria-hidden="true"
        ></span>
      `
      : "";

  return `
    <section
      class="arkAIStatusPanel ${escapeHtml(
        view.status,
      )}"
      data-ai-status="${escapeHtml(
        view.status,
      )}"
      aria-live="polite"
    >
      <div class="arkAIStatusIcon">
        ${spinner}
      </div>

      <div class="arkAIStatusContent">
        <span class="arkAIStatusEyebrow">
          AI ANALYSIS STATUS
        </span>

        <strong>
          ${escapeHtml(
            view.message,
          )}
        </strong>

        <small>
          Symbol:
          ${escapeHtml(
            view.symbol,
          )}
        </small>
      </div>
    </section>
  `;
}

export function resolveAIStatusContainer(
  documentRef =
    globalThis.document,
) {
  if (!documentRef) {
    return null;
  }

  const existing =
    documentRef.querySelector(
      "#arkAIAnalysisStatus",
    );

  if (existing) {
    return existing;
  }

  const container =
    documentRef.createElement(
      "section",
    );

  container.id =
    "arkAIAnalysisStatus";

  container.className =
    "arkAIAnalysisStatusRoot";

  const anchor =
    documentRef.querySelector(
      "#aiAnalysisButton, .arkAIAnalysisButtonWrap, #arkAIResultPresenter",
    );

  if (
    anchor &&
    typeof anchor
      .insertAdjacentElement ===
      "function"
  ) {
    anchor.insertAdjacentElement(
      "afterend",
      container,
    );
  }
  else {
    documentRef.body?.appendChild(
      container,
    );
  }

  return container;
}

export function mountAIAnalysisStatus({
  input = {},
  documentRef =
    globalThis.document,
} = {}) {
  const container =
    resolveAIStatusContainer(
      documentRef,
    );

  if (!container) {
    return {
      mounted: false,
      reason:
        "document_unavailable",
    };
  }

  const view =
    buildAIAnalysisStatusViewModel(
      input,
    );

  container.innerHTML =
    renderAIAnalysisStatus(
      view,
    );

  container.dataset
    .aiStatus =
    view.status;

  container.hidden =
    view.status ===
    "idle";

  return {
    mounted: true,
    container,
    view,
  };
}

export function connectAIAnalysisStatusPanel({
  eventTarget =
    globalThis.window,

  documentRef =
    globalThis.document,
} = {}) {
  if (
    !eventTarget ||
    !documentRef
  ) {
    return () => {};
  }

  let startedAt =
    null;

  const startHandler =
    (event) => {
      startedAt =
        new Date()
          .toISOString();

      mountAIAnalysisStatus({
        documentRef,

        input: {
          status:
            "running",

          symbol:
            event?.detail
              ?.input
              ?.symbol ??
            "--",

          startedAt,
        },
      });
    };

  const completeHandler =
    (event) => {
      mountAIAnalysisStatus({
        documentRef,

        input: {
          status:
            "success",

          symbol:
            event?.detail
              ?.symbol ??
            "--",

          startedAt,

          completedAt:
            new Date()
              .toISOString(),
        },
      });
    };

  const errorHandler =
    (event) => {
      mountAIAnalysisStatus({
        documentRef,

        input: {
          status:
            "error",

          symbol:
            event?.detail
              ?.input
              ?.symbol ??
            "--",

          message:
            event?.detail
              ?.message ??
            "AI分析中にエラーが発生しました",

          startedAt,

          completedAt:
            new Date()
              .toISOString(),
        },
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

export const AIAnalysisStatusInternals = {
  escapeHtml,
  normalizeStatus,
};