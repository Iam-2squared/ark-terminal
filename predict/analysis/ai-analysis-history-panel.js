import {
  summarizeAnalysisHistory,
} from "./ai-analysis-history.js";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

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

function formatDate(value) {
  const date =
    new Date(value);

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return "--";
  }

  return date.toLocaleString(
    "ja-JP",
  );
}

function actionClass(
  action = "HOLD",
) {
  const normalized =
    String(action)
      .toUpperCase();

  if (
    normalized === "BUY" ||
    normalized === "STRONG BUY"
  ) {
    return "positive";
  }

  if (
    normalized === "SELL" ||
    normalized === "REDUCE" ||
    normalized === "NO TRADE"
  ) {
    return "negative";
  }

  return "neutral";
}

export function buildAnalysisHistoryViewModel(
  history = [],
) {
  const safeHistory =
    Array.isArray(history)
      ? history
      : [];

  const summary =
    summarizeAnalysisHistory(
      safeHistory,
    );

  const items =
    safeHistory.map(
      (item) => ({
        id:
          item.id,

        createdAt:
          item.createdAt,

        createdAtLabel:
          formatDate(
            item.createdAt,
          ),

        symbol:
          item.symbol ??
          "--",

        action:
          item.action ??
          "HOLD",

        actionClass:
          actionClass(
            item.action,
          ),

        score:
          finiteNumber(
            item.score,
            50,
          ),

        confidence:
          finiteNumber(
            item.confidence,
            0,
          ),

        agreementRate:
          finiteNumber(
            item.agreementRate,
            0,
          ),

        executable:
          item.executable === true,

        shares:
          finiteNumber(
            item.shares,
            0,
          ),

        entryPrice:
          finiteNumber(
            item.entryPrice,
            0,
          ),
      }),
    );

  return {
    summary,
    items,
  };
}

export function renderAnalysisHistoryPanel(
  history = [],
) {
  const view =
    buildAnalysisHistoryViewModel(
      history,
    );

  const rows =
    view.items.length
      ? view.items
          .map(
            (item) => `
              <article
                class="arkAIHistoryItem"
                data-analysis-history-id="${escapeHtml(
                  item.id,
                )}"
              >
                <div class="arkAIHistoryMain">
                  <div>
                    <span class="arkAIHistorySymbol">
                      ${escapeHtml(
                        item.symbol,
                      )}
                    </span>

                    <small>
                      ${escapeHtml(
                        item.createdAtLabel,
                      )}
                    </small>
                  </div>

                  <span class="arkAIHistoryAction ${escapeHtml(
                    item.actionClass,
                  )}">
                    ${escapeHtml(
                      item.action,
                    )}
                  </span>
                </div>

                <div class="arkAIHistoryMetrics">
                  <span>
                    Score
                    <strong>${item.score}</strong>
                  </span>

                  <span>
                    Confidence
                    <strong>${item.confidence}%</strong>
                  </span>

                  <span>
                    Agreement
                    <strong>${item.agreementRate}%</strong>
                  </span>

                  <span>
                    Shares
                    <strong>${item.shares}</strong>
                  </span>

                  <span>
                    Entry
                    <strong>¥${item.entryPrice}</strong>
                  </span>
                </div>
              </article>
            `,
          )
          .join("")
      : `
          <p class="arkAIHistoryEmpty">
            まだAI分析履歴はありません。
          </p>
        `;

  return `
    <section class="arkAIHistoryPanel">
      <header class="arkAIHistoryHeader">
        <div>
          <span class="arkAIHistoryEyebrow">
            AI ANALYSIS HISTORY
          </span>

          <h3>
            分析履歴
          </h3>
        </div>

        <button
          type="button"
          class="arkAIHistoryClear"
          data-ai-history-clear
        >
          履歴を削除
        </button>
      </header>

      <div class="arkAIHistorySummary">
        <article>
          <span>分析回数</span>
          <strong>${view.summary.total}</strong>
        </article>

        <article>
          <span>実行候補</span>
          <strong>${view.summary.executableCount}</strong>
        </article>

        <article>
          <span>平均スコア</span>
          <strong>${view.summary.averageScore}</strong>
        </article>

        <article>
          <span>平均信頼度</span>
          <strong>${view.summary.averageConfidence}%</strong>
        </article>
      </div>

      <div class="arkAIHistoryList">
        ${rows}
      </div>
    </section>
  `;
}

export function resolveAnalysisHistoryContainer(
  documentRef =
    globalThis.document,
) {
  if (!documentRef) {
    return null;
  }

  const existing =
    documentRef.querySelector(
      "#arkAIAnalysisHistory",
    );

  if (existing) {
    return existing;
  }

  const container =
    documentRef.createElement(
      "section",
    );

  container.id =
    "arkAIAnalysisHistory";

  container.className =
    "arkAIAnalysisHistoryRoot";

  const anchor =
    documentRef.querySelector(
      "#arkAIExplainability, #arkAIResultPresenter, #arkPredictionLabV3",
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

export function mountAnalysisHistoryPanel({
  history = [],
  documentRef =
    globalThis.document,
} = {}) {
  const container =
    resolveAnalysisHistoryContainer(
      documentRef,
    );

  if (!container) {
    return {
      mounted: false,
      reason:
        "document_unavailable",
    };
  }

  container.innerHTML =
    renderAnalysisHistoryPanel(
      history,
    );

  container.dataset
    .aiHistoryState =
    "ready";

  return {
    mounted: true,
    container,
  };
}

export function connectAnalysisHistoryPanel({
  eventTarget =
    globalThis.window,

  documentRef =
    globalThis.document,

  store,
} = {}) {
  if (
    !eventTarget ||
    !documentRef ||
    !store
  ) {
    return () => {};
  }

  const render =
    () => {
      const result =
        mountAnalysisHistoryPanel({
          history:
            store.all(),

          documentRef,
        });

      if (!result.mounted) {
        return;
      }

      const clearButton =
        result.container
          .querySelector?.(
            "[data-ai-history-clear]",
          );

      clearButton?.addEventListener(
        "click",
        () => {
          store.clear();

          eventTarget
            .__ARK_ANALYSIS_HISTORY__ =
            [];

          render();
        },
        {
          once: true,
        },
      );
    };

  const completeHandler =
    () => {
      render();
    };

  eventTarget.addEventListener(
    "ark:ai-analysis-complete",
    completeHandler,
  );

  render();

  return () => {
    eventTarget.removeEventListener(
      "ark:ai-analysis-complete",
      completeHandler,
    );
  };
}